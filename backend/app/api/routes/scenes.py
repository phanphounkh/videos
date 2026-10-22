"""Scene endpoints.

Scenes are addressed two ways on purpose:
  /projects/{project_id}/scenes   - collection operations (list, create, reorder)
  /scenes/{scene_id}              - operations on one scene the client already has
"""

import uuid

from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUser, SessionDep
from app.schemas.presenters import scenes_to_response
from app.schemas.scene import (
    CaptionsReplaceRequest,
    SceneCreateRequest,
    SceneReorderRequest,
    SceneResponse,
    SceneSplitRequest,
    SceneTrimRequest,
    SceneUpdateRequest,
)
from app.schemas.timeline import TimelineSnapshot
from app.services.scene_service import SceneService
from app.services.timeline_service import TimelineService

project_scenes_router = APIRouter(prefix="/projects/{project_id}/scenes", tags=["scenes"])
scenes_router = APIRouter(prefix="/scenes", tags=["scenes"])


def _one(scenes: list, scene_id: uuid.UUID) -> SceneResponse:
    """Picks a single scene out of a fully-timed timeline.

    We always convert the whole project so `start_time` is correct - a scene's
    start depends on every scene before it.
    """
    for item in scenes:
        if item.id == scene_id:
            return item
    raise AssertionError("scene missing from its own project timeline")


@project_scenes_router.get("", response_model=list[SceneResponse])
async def list_scenes(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> list[SceneResponse]:
    scenes = await SceneService(session).list_for_project(project_id, current_user.id)
    return scenes_to_response(list(scenes))


@project_scenes_router.post("", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(
    project_id: uuid.UUID,
    payload: SceneCreateRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> SceneResponse:
    service = SceneService(session)
    scene = await service.create(project_id, current_user.id, payload)
    timeline = scenes_to_response(list(await service.list_for_project(project_id, current_user.id)))
    return _one(timeline, scene.id)


@project_scenes_router.post("/reorder", response_model=list[SceneResponse])
async def reorder_scenes(
    project_id: uuid.UUID,
    payload: SceneReorderRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> list[SceneResponse]:
    scenes = await SceneService(session).reorder(project_id, current_user.id, payload.scene_ids)
    return scenes_to_response(list(scenes))


@project_scenes_router.put("/timeline", response_model=list[SceneResponse])
async def restore_timeline(
    project_id: uuid.UUID,
    payload: TimelineSnapshot,
    current_user: CurrentUser,
    session: SessionDep,
) -> list[SceneResponse]:
    """Make the project match a saved snapshot exactly (undo / redo)."""
    scenes = await TimelineService(session).restore(project_id, current_user.id, payload)
    return scenes_to_response(scenes)


@scenes_router.put("/{scene_id}/captions", response_model=SceneResponse)
async def edit_captions(
    scene_id: uuid.UUID,
    payload: CaptionsReplaceRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> SceneResponse:
    """Replace the scene's captions with a hand-edited list."""
    service = SceneService(session)
    scene = await service.set_captions(
        scene_id,
        current_user.id,
        [(c.text, c.start_time, c.end_time) for c in payload.captions],
    )
    timeline = scenes_to_response(
        list(await service.list_for_project(scene.project_id, current_user.id))
    )
    return _one(timeline, scene_id)


@scenes_router.post("/{scene_id}/captions/reset", response_model=SceneResponse)
async def reset_captions(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> SceneResponse:
    """Throw away hand edits and rebuild captions from the narration."""
    service = SceneService(session)
    scene = await service.reset_captions(scene_id, current_user.id)
    timeline = scenes_to_response(
        list(await service.list_for_project(scene.project_id, current_user.id))
    )
    return _one(timeline, scene_id)


@scenes_router.post("/{scene_id}/split", response_model=list[SceneResponse])
async def split_scene(
    scene_id: uuid.UUID,
    payload: SceneSplitRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> list[SceneResponse]:
    scenes = await SceneService(session).split(scene_id, current_user.id, payload.at)
    return scenes_to_response(list(scenes))


@scenes_router.post("/{scene_id}/trim", response_model=list[SceneResponse])
async def trim_scene(
    scene_id: uuid.UUID,
    payload: SceneTrimRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> list[SceneResponse]:
    scenes = await SceneService(session).trim(
        scene_id, current_user.id, payload.start, payload.end
    )
    return scenes_to_response(list(scenes))


@scenes_router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> SceneResponse:
    service = SceneService(session)
    scene = await service.get_owned(scene_id, current_user.id)
    timeline = scenes_to_response(
        list(await service.list_for_project(scene.project_id, current_user.id))
    )
    return _one(timeline, scene_id)


@scenes_router.patch("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: uuid.UUID,
    payload: SceneUpdateRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> SceneResponse:
    service = SceneService(session)
    scene = await service.update(scene_id, current_user.id, payload)
    timeline = scenes_to_response(
        list(await service.list_for_project(scene.project_id, current_user.id))
    )
    return _one(timeline, scene_id)


@scenes_router.post("/{scene_id}/duplicate", response_model=SceneResponse,
                    status_code=status.HTTP_201_CREATED)
async def duplicate_scene(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> SceneResponse:
    service = SceneService(session)
    scene = await service.duplicate(scene_id, current_user.id)
    timeline = scenes_to_response(
        list(await service.list_for_project(scene.project_id, current_user.id))
    )
    return _one(timeline, scene.id)


@scenes_router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(
    scene_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> Response:
    await SceneService(session).delete(scene_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
