"""AI generation endpoints.

Timing model, which is the whole point of this module:

  POST /projects/{id}/generate      script generation runs INLINE (seconds), then
                                    presenter voice jobs are QUEUED (minutes).
  POST /scenes/{id}/generate-image  runs inline - a single image is fast and the
  POST /scenes/{id}/generate-voice   editor wants the result immediately.
  POST /scenes/{id}/regenerate      both of the above for one scene.
"""

import uuid

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, SessionDep
from app.core.logging import get_logger
from app.models.enums import ProjectStatus
from app.schemas.generation import GenerateRequest, GenerateResponse, SceneMediaResponse
from app.services.generation_service import GenerationService
from app.services.queue import enqueue
from app.services.storage.urls import public_url

log = get_logger(__name__)

projects_router = APIRouter(prefix="/projects", tags=["generation"])
scenes_router = APIRouter(prefix="/scenes", tags=["generation"])


@projects_router.post(
    "/{project_id}/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Prompt -> structured script -> scenes (and queue presenter narration)",
)
async def generate_video(
    project_id: uuid.UUID,
    payload: GenerateRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> GenerateResponse:
    service = GenerationService(session)
    project = await service.generate_script_and_scenes(project_id, current_user.id, payload)

    if project.scenes:
        # The cover is drawn from the new script, whether or not media follows.
        # Best effort: a missing cover must never fail the generation request.
        try:
            await enqueue("generate_thumbnail", str(project.id))
        except Exception:  # noqa: BLE001
            log.warning("thumbnail_enqueue_failed", project_id=str(project.id))

    queued = 0
    if payload.generate_media and project.scenes:
        await enqueue("generate_project_media", str(project.id), str(current_user.id))
        queued = len(project.scenes)
        # Report "generating" immediately. The worker will also set this, but it
        # may not have picked the job up yet, and a client that sees "ready"
        # first would stop polling and never show the generated media.
        project.status = ProjectStatus.GENERATING
        await session.commit()

    return GenerateResponse(
        project_id=project.id,
        title=project.title,
        status=project.status,
        scene_count=len(project.scenes),
        duration=project.duration,
        media_jobs_queued=queued,
    )


@scenes_router.post("/{scene_id}/generate-image", response_model=SceneMediaResponse)
async def generate_scene_image(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> SceneMediaResponse:
    outcome = await GenerationService(session).generate_scene_image(scene_id, current_user.id)
    return SceneMediaResponse(
        scene_id=scene_id,
        asset_id=outcome.asset.id if outcome.asset else None,
        url=public_url(outcome.asset.storage_key) if outcome.asset else None,
        status=outcome.status,
        provider=outcome.provider,
        message=outcome.message,
    )


@scenes_router.post("/{scene_id}/generate-voice", response_model=SceneMediaResponse)
async def generate_scene_voice(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> SceneMediaResponse:
    outcome = await GenerationService(session).generate_scene_voice(scene_id, current_user.id)
    return SceneMediaResponse(
        scene_id=scene_id,
        asset_id=outcome.asset.id if outcome.asset else None,
        url=public_url(outcome.asset.storage_key) if outcome.asset else None,
        status=outcome.status,
        provider=outcome.provider,
        message=outcome.message,
    )


@scenes_router.post(
    "/{scene_id}/regenerate",
    response_model=list[SceneMediaResponse],
    summary="Regenerate image + voice (+ captions) for one scene only",
)
async def regenerate_scene(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> list[SceneMediaResponse]:
    service = GenerationService(session)
    responses: list[SceneMediaResponse] = []
    for outcome in (
        await service.generate_scene_image(scene_id, current_user.id),
        await service.generate_scene_voice(scene_id, current_user.id),
    ):
        responses.append(
            SceneMediaResponse(
                scene_id=scene_id,
                asset_id=outcome.asset.id if outcome.asset else None,
                url=public_url(outcome.asset.storage_key) if outcome.asset else None,
                status=outcome.status,
                provider=outcome.provider,
                message=outcome.message,
            )
        )
    return responses


@scenes_router.post(
    "/{scene_id}/captions",
    response_model=dict[str, int],
    summary="Recompute caption segments and timings for one scene",
)
async def regenerate_captions(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> dict[str, int]:
    count = await GenerationService(session).regenerate_captions(scene_id, current_user.id)
    return {"captions": count}
