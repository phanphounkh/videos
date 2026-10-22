"""ARQ task definitions.

Each task is a plain `async def` that opens its OWN database session. A worker
process is not an HTTP request, so there is no request-scoped session to inherit.

Tasks take primitive arguments (strings) because everything that crosses Redis
must be JSON-serialisable - never pass an ORM object.
"""

import uuid
from typing import Any

from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.models.enums import ProjectStatus
from app.repositories.project_repository import ProjectRepository

log = get_logger(__name__)


async def render_project(ctx: dict[str, Any], job_id: str) -> str:
    """Render one project to MP4. Owner of the heavy lifting: RenderService."""
    try:
        from app.services.render_service import RenderService

        factory = get_session_factory()
        async with factory() as session:
            await RenderService(session).execute_job(uuid.UUID(job_id))
    except Exception as exc:
        # RenderService records the failures it expects. Anything else (even
        # failing to import it) would leave the job "queued" forever and the
        # editor waiting on a worker that has already given up, so record it.
        log.exception("render_task_crashed", job_id=job_id)
        await _mark_render_failed(job_id, f"The render worker crashed: {exc}")
        raise
    return job_id


async def _mark_render_failed(job_id: str, message: str) -> None:
    """Fails an unfinished render job and frees its project. Deliberately
    depends on nothing but the models, so it works when the rest does not."""
    from datetime import UTC, datetime

    from app.models.enums import RenderStatus
    from app.models.project import Project
    from app.models.render_job import RenderJob

    factory = get_session_factory()
    async with factory() as session:
        job = await session.get(RenderJob, uuid.UUID(job_id))
        if job is None or job.status in {RenderStatus.COMPLETED, RenderStatus.FAILED}:
            return
        job.status = RenderStatus.FAILED
        job.error_message = message[:2000]
        job.completed_at = datetime.now(UTC)
        project = await session.get(Project, job.project_id)
        if project is not None and project.status == ProjectStatus.RENDERING:
            project.status = ProjectStatus.READY
        await session.commit()


async def generate_scene_media(
    ctx: dict[str, Any], scene_id: str, owner_id: str, *, image: bool = True, voice: bool = True
) -> dict[str, Any]:
    """Generate the image and/or narration for ONE scene.

    One scene per job on purpose (requirement #34): if scene 4's image provider
    fails, scenes 1-3 keep their media and only scene 4 is retried.
    """
    from app.services.generation_service import GenerationService

    factory = get_session_factory()
    results: dict[str, Any] = {"scene_id": scene_id}
    async with factory() as session:
        service = GenerationService(session)
        if image:
            outcome = await service.generate_scene_image(uuid.UUID(scene_id), uuid.UUID(owner_id))
            results["image"] = outcome.status
        if voice:
            outcome = await service.generate_scene_voice(uuid.UUID(scene_id), uuid.UUID(owner_id))
            results["voice"] = outcome.status
    return results


async def generate_project_media(
    ctx: dict[str, Any], project_id: str, owner_id: str
) -> dict[str, Any]:
    """Generate presenter narration for every scene, then mark the project ready."""
    from app.services.generation_service import GenerationService

    factory = get_session_factory()
    summary = {"project_id": project_id, "scenes": 0, "voices": 0, "failures": 0}

    async with factory() as session:
        project = await ProjectRepository(session).get_for_owner(
            uuid.UUID(project_id), uuid.UUID(owner_id)
        )
        if project is None:
            log.warning("project_media_project_missing", project_id=project_id)
            return summary
        scene_ids = [str(scene.id) for scene in project.scenes]
        project.status = ProjectStatus.GENERATING
        await session.commit()

    for scene_id in scene_ids:
        async with factory() as session:
            service = GenerationService(session)
            summary["scenes"] += 1
            try:
                voice_outcome = await service.generate_scene_voice(
                    uuid.UUID(scene_id), uuid.UUID(owner_id)
                )
                summary["voices"] += int(voice_outcome.asset is not None)
                if voice_outcome.asset is None:
                    summary["failures"] += 1
            except Exception as exc:  # noqa: BLE001
                summary["failures"] += 1
                log.warning("scene_voice_job_failed", scene_id=scene_id, error=str(exc)[:200])

    async with factory() as session:
        project = await ProjectRepository(session).get_for_owner(
            uuid.UUID(project_id), uuid.UUID(owner_id)
        )
        if project is not None:
            project.status = ProjectStatus.READY
            await session.commit()

    log.info("project_media_completed", **summary)
    return summary


async def generate_thumbnail(ctx: dict[str, Any], project_id: str) -> str | None:
    """Draw the project's cover image. Failing leaves the old cover (or none)."""
    from app.services.thumbnail_service import ThumbnailService

    factory = get_session_factory()
    try:
        async with factory() as session:
            asset = await ThumbnailService(session).generate(uuid.UUID(project_id))
    except Exception as exc:  # noqa: BLE001 - a cover must never fail the project
        log.warning("thumbnail_failed", project_id=project_id, error=str(exc)[:300])
        return None
    return str(asset.id) if asset else None
