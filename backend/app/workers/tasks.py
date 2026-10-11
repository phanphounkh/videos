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
    from app.services.render_service import RenderService

    factory = get_session_factory()
    async with factory() as session:
        await RenderService(session).execute_job(uuid.UUID(job_id))
    return job_id


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
