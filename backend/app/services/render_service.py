"""Render use cases: create a render job, report status, run the render.

Split in two halves on purpose:
  - `create_job` runs INSIDE the HTTP request: validate, insert a RenderJob row,
    push a message onto Redis, return 202 immediately.
  - `execute_job` runs INSIDE THE WORKER: build the payload, invoke Remotion +
    FFmpeg, stream progress into the database, upload the MP4, finish the row.

`async def` does not make FFmpeg non-blocking (requirement #33). The render is a
separate OS process; we await its output rather than pretending it is async work.
"""

import asyncio
import json
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ProviderError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.enums import AssetSource, AssetType, ProjectStatus, RenderStatus
from app.models.render_job import RenderJob
from app.repositories.project_repository import ProjectRepository
from app.repositories.render_job_repository import RenderJobRepository
from app.services.project_service import ProjectService
from app.services.render_payload import build_composition_payload
from app.services.storage import get_storage, render_key

log = get_logger(__name__)

MAX_LOG_CHARS = 20_000


def _resolve_renderer(renderer_dir: str) -> tuple[Path, Path | None]:
    """Blocking filesystem probe, called via asyncio.to_thread."""
    directory = Path(renderer_dir).resolve()
    entry = directory / "src" / "render.ts"
    return directory, (entry if entry.exists() else None)


class RenderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.jobs = RenderJobRepository(session)
        self.projects = ProjectService(session)

    # ------------------------------------------------- called from the request
    async def create_job(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> RenderJob:
        project = await self.projects.get(project_id, owner_id)

        if not project.scenes:
            raise ConflictError(
                "This project has no scenes to render. Generate or add a scene first.",
                code="PROJECT_EMPTY",
            )
        if any(scene.duration <= 0 for scene in project.scenes):
            raise ConflictError("Every scene must have a positive duration.",
                                code="INVALID_TIMELINE")

        job = RenderJob(project_id=project.id, status=RenderStatus.QUEUED, progress=0)
        self.session.add(job)
        project.status = ProjectStatus.RENDERING
        await self.session.commit()

        from app.services.queue import enqueue

        await enqueue("render_project", str(job.id))
        log.info("render_queued", job_id=str(job.id), project_id=str(project_id))
        return job

    async def get_job(self, job_id: uuid.UUID, owner_id: uuid.UUID) -> RenderJob:
        job = await self.jobs.get_with_project(job_id)
        if job is None or job.project.owner_id != owner_id:
            raise NotFoundError("Render job was not found.", code="RENDER_JOB_NOT_FOUND")
        return job

    # -------------------------------------------------- called from the worker
    async def execute_job(self, job_id: uuid.UUID) -> None:
        job = await self.jobs.get(job_id)
        if job is None:
            log.warning("render_job_missing", job_id=str(job_id))
            return

        project = await ProjectRepository(self.session).get(job.project_id)
        if project is None:
            await self._fail(job, "The project no longer exists.")
            return

        job.status = RenderStatus.PREPARING
        job.started_at = datetime.now(UTC)
        job.progress = 1
        await self.session.commit()
        log.info("render_started", job_id=str(job_id), project_id=str(project.id))

        collected_logs: list[str] = []
        try:
            payload = build_composition_payload(project)
            output_path, logs = await self._run_renderer(job, payload)
            collected_logs = logs

            job.status = RenderStatus.UPLOADING
            job.progress = 96
            await self.session.commit()

            # Reading a 100 MB MP4 is blocking I/O: keep it off the event loop.
            data = await asyncio.to_thread(Path(output_path).read_bytes)
            key = render_key(str(project.id), str(job.id))
            stored = await get_storage().put_bytes(key, data, "video/mp4")

            asset = Asset(
                project_id=project.id,
                type=AssetType.RENDER,
                source=AssetSource.GENERATED,
                storage_key=stored.storage_key,
                mime_type="video/mp4",
                size_bytes=stored.size_bytes,
                duration=project.duration,
                width=project.dimensions[0],
                height=project.dimensions[1],
                provider="remotion+ffmpeg",
            )
            self.session.add(asset)
            await self.session.flush()

            job.output_asset_id = asset.id
            job.status = RenderStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.now(UTC)
            job.logs = self._tail(collected_logs)
            project.status = ProjectStatus.COMPLETED
            await self.session.commit()

            log.info(
                "render_completed",
                job_id=str(job_id),
                size_bytes=stored.size_bytes,
                storage_key=stored.storage_key,
            )
        except Exception as exc:  # noqa: BLE001 - a render must never crash the worker
            await self._fail(job, str(exc), collected_logs)
            raise
        finally:
            shutil.rmtree(Path(tempfile.gettempdir()) / f"avs-render-{job.id}", ignore_errors=True)

    async def _run_renderer(
        self, job: RenderJob, payload: dict
    ) -> tuple[str, list[str]]:
        """Spawns the Remotion CLI and streams its JSON progress lines."""
        settings = get_settings()
        renderer_dir, entry = await asyncio.to_thread(_resolve_renderer, settings.renderer_dir)
        if entry is None:
            raise ProviderError(
                f"Renderer entrypoint src/render.ts not found under {renderer_dir}. "
                "Set RENDERER_DIR to the renderer project directory.",
                code="RENDERER_NOT_FOUND",
            )

        workdir = Path(tempfile.gettempdir()) / f"avs-render-{job.id}"
        payload_path = workdir / "composition.json"
        output_path = workdir / "out.mp4"

        def _write_payload() -> None:
            workdir.mkdir(parents=True, exist_ok=True)
            # ensure_ascii=False keeps Khmer readable in the payload we hand over.
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        await asyncio.to_thread(_write_payload)

        npx = shutil.which("npx")
        if npx is None:
            raise ProviderError("npx (Node.js) is not installed.", code="NODE_NOT_FOUND")

        process = await asyncio.create_subprocess_exec(
            npx, "tsx", str(entry), str(payload_path), str(output_path),
            cwd=str(renderer_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "REMOTION_DISABLE_TELEMETRY": "1"},
        )

        logs: list[str] = []
        assert process.stdout is not None
        try:
            await asyncio.wait_for(
                self._consume(process, job, logs), timeout=settings.render_timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            raise ProviderError(
                f"Rendering exceeded {settings.render_timeout_seconds}s and was cancelled.",
                code="RENDER_TIMEOUT",
            ) from exc

        if process.returncode != 0:
            raise ProviderError(
                f"The renderer exited with code {process.returncode}. "
                f"Last output: {' | '.join(logs[-3:])[:500]}",
                code="RENDER_FAILED",
            )
        def _has_output() -> bool:
            return output_path.exists() and output_path.stat().st_size > 0

        if not await asyncio.to_thread(_has_output):
            raise ProviderError("The renderer produced no output file.", code="RENDER_FAILED")

        return str(output_path), logs

    async def _consume(self, process, job: RenderJob, logs: list[str]) -> None:
        """Reads renderer stdout line by line, persisting progress as it moves."""
        last_persisted = -1
        while True:
            raw = await process.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip()
            if not line:
                continue
            logs.append(line)

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # plain log output from Remotion, keep it in `logs`

            stage = event.get("stage")
            progress = int(event.get("progress", job.progress))
            if stage == "rendering":
                job.status = RenderStatus.RENDERING
            elif stage == "preparing":
                job.status = RenderStatus.PREPARING
            elif stage == "failed":
                raise ProviderError(
                    f"Renderer reported failure: {event.get('error', 'unknown')}",
                    code="RENDER_FAILED",
                )

            # Commit at most every 5% - the frontend polls, it does not need
            # a database write per frame.
            if progress - last_persisted >= 5:
                job.progress = min(progress, 95)
                await self.session.commit()
                last_persisted = progress

        await process.wait()

    async def _fail(self, job: RenderJob, message: str, logs: list[str] | None = None) -> None:
        job.status = RenderStatus.FAILED
        job.error_message = message[:2000]
        job.completed_at = datetime.now(UTC)
        if logs:
            job.logs = self._tail(logs)
        project = await ProjectRepository(self.session).get(job.project_id)
        if project is not None:
            # Back to READY, not FAILED: the scenes are still fine, only the
            # render failed, so the user can fix something and retry.
            project.status = ProjectStatus.READY
        await self.session.commit()
        log.warning("render_failed", job_id=str(job.id), error=message[:300])

    @staticmethod
    def _tail(logs: list[str]) -> str:
        text = "\n".join(logs)
        return text[-MAX_LOG_CHARS:]
