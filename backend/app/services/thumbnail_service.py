"""Project thumbnails: a cover image drawn by the renderer in the video's own style.

The text on a thumbnail depends on the video: a story or social post shows its hook
(the first scene's key phrase), every other purpose shows its title. The look
(stage, host, sticker, badge, closing chip) is the same as the video's, because
the renderer draws it with the same components.
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.enums import AssetSource, AssetType
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.services.avatars import avatar_spec, sync_spec
from app.services.purposes import get_purpose
from app.services.storage import get_storage, thumbnail_key
from app.services.storage.urls import renderer_url
from app.services.telemetry import Event, record

log = get_logger(__name__)

# The thumbnail's short side in pixels; plenty for a card or a platform cover.
SHORT_SIDE = 720
MAX_HEADLINE_CHARS = 48
RENDER_TIMEOUT_SECONDS = 180

# Purposes whose thumbnail leads with the video's hook instead of its title.
HOOK_PURPOSES = {"story", "social_post"}


def _shorten(text: str, limit: int = MAX_HEADLINE_CHARS) -> str:
    """Whitespace-normalised and cut at a word boundary so it fits the sticker."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # Khmer and Chinese have no spaces between words; then a hard cut is all there is.
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip(" ,.;:-")


def thumbnail_payload(project: Project, avatar: dict[str, Any] | None = None) -> dict[str, Any]:
    """The JSON the renderer's Thumbnail composition is drawn from."""
    template = get_purpose(project.purpose)
    scenes = sorted(project.scenes, key=lambda scene: scene.scene_number)
    first = scenes[0] if scenes else None

    hook = first.on_screen_text if first and first.on_screen_text else None
    headline = _shorten(hook if hook and project.purpose in HOOK_PURPOSES else project.title)

    picture = next((s.image_asset for s in scenes if s.image_asset is not None), None)

    width, height = project.dimensions
    scale = SHORT_SIDE / min(width, height)
    project_json: dict[str, Any] = {
        "width": round(width * scale),
        "height": round(height * scale),
        "fps": 30,
        "title": project.title,
        "language": project.language,
        "purpose": project.purpose,
        "presenter": project.presenter,
        "ctaText": project.cta_text,
    }
    if project.presenter:
        project_json["avatar"] = sync_spec(project, avatar)
    return {
        "project": project_json,
        "headline": headline or "Sorya",
        "kicker": template.label,
        # The video opens on its hook beat, so the cover wears the same colours.
        "mood": "hook",
        "imageUrl": renderer_url(picture.storage_key) if picture else None,
        "cta": project.cta_text,
    }


class ThumbnailService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate(self, project_id: uuid.UUID) -> Asset | None:
        """Draws the thumbnail and makes it the project's cover. None if the
        project is gone or has no scenes yet."""
        project = await ProjectRepository(self.session).get(project_id)
        if project is None or not project.scenes:
            return None

        started = time.perf_counter()
        try:
            data = await _render(
                thumbnail_payload(
                    project, await avatar_spec(self.session, project) if project.presenter else None
                )
            )
        except Exception as exc:
            record(
                Event(
                    name="render_thumbnail",
                    level="error",
                    outcome="error",
                    duration_ms=round((time.perf_counter() - started) * 1000),
                    user_id=str(project.owner_id),
                    properties={
                        "project_id": str(project.id),
                        "error_code": str(getattr(exc, "code", type(exc).__name__))[:64],
                    },
                )
            )
            raise
        record(
            Event(
                name="render_thumbnail",
                outcome="ok",
                duration_ms=round((time.perf_counter() - started) * 1000),
                user_id=str(project.owner_id),
                properties={"project_id": str(project.id), "bytes": len(data)},
            )
        )

        key = thumbnail_key(str(project.id), uuid.uuid4().hex)
        stored = await get_storage().put_bytes(key, data, "image/jpeg")
        width, height = project.dimensions
        scale = SHORT_SIDE / min(width, height)

        previous = project.thumbnail_asset
        asset = Asset(
            project_id=project.id,
            scene_id=None,
            type=AssetType.THUMBNAIL,
            source=AssetSource.GENERATED,
            storage_key=stored.storage_key,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            width=round(width * scale),
            height=round(height * scale),
            provider="remotion",
        )
        self.session.add(asset)
        await self.session.flush()
        project.thumbnail_asset_id = asset.id
        await self.session.flush()
        old_key = previous.storage_key if previous else None
        if previous is not None:
            await self.session.delete(previous)
        await self.session.commit()

        if old_key:
            try:
                await get_storage().delete(old_key)
            except Exception:  # noqa: BLE001 - an orphaned old cover is harmless
                log.warning("thumbnail_old_delete_failed", key=old_key)

        log.info("thumbnail_generated", project_id=str(project.id), bytes=len(data))
        return asset


def _prepare(payload: dict[str, Any]) -> tuple[Path, Path, Path, Path]:
    """Blocking filesystem setup: (renderer_dir, entry, input json, output jpg)."""
    renderer_dir = Path(get_settings().renderer_dir).resolve()
    entry = renderer_dir / "src" / "thumbnail.ts"
    if not entry.exists():
        raise ProviderError(
            f"Thumbnail entrypoint {entry} not found. Set RENDERER_DIR.",
            code="RENDERER_NOT_FOUND",
        )
    workdir = Path(tempfile.gettempdir()) / f"avs-thumb-{uuid.uuid4().hex}"
    workdir.mkdir(parents=True)
    source = workdir / "thumbnail.json"
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return renderer_dir, entry, source, workdir / "thumbnail.jpg"


def _read_and_clean(output: Path) -> bytes | None:
    data = output.read_bytes() if output.exists() else None
    shutil.rmtree(output.parent, ignore_errors=True)
    return data


async def _render(payload: dict[str, Any]) -> bytes:
    """Runs the renderer's thumbnail CLI and returns the JPEG bytes."""
    npx = shutil.which("npx")
    if npx is None:
        raise ProviderError("npx (Node.js) is not installed.", code="NODE_NOT_FOUND")

    renderer_dir, entry, source, output = await asyncio.to_thread(_prepare, payload)
    failure: str | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            npx,
            "tsx",
            str(entry),
            str(source),
            str(output),
            cwd=str(renderer_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "REMOTION_DISABLE_TELEMETRY": "1"},
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), RENDER_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            process.kill()
            raise ProviderError("Thumbnail rendering timed out.", code="RENDER_TIMEOUT") from exc
        if process.returncode != 0:
            tail = stdout.decode("utf-8", errors="replace").strip().splitlines()[-3:]
            failure = " | ".join(tail)[:500]
    finally:
        data = await asyncio.to_thread(_read_and_clean, output)

    if failure is not None or data is None:
        raise ProviderError(
            f"Thumbnail rendering failed: {failure or 'no output file'}", code="RENDER_FAILED"
        )
    return data
