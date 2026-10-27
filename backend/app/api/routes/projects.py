"""Project endpoints."""

import uuid

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, SessionDep
from app.core.exceptions import ValidationError
from app.schemas.common import Page
from app.schemas.presenters import project_to_response, scenes_to_response
from app.schemas.project import (
    BulkProjectsRequest,
    BulkProjectsResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.schemas.scene import ProjectDetailResponse
from app.services.project_service import ProjectService
from app.services.queue import enqueue

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=Page[ProjectResponse], summary="List my projects")
async def list_projects(
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    view: str = Query(default="all", pattern="^(all|recent|starred|trash)$"),
    folder: str | None = Query(default=None, description="A folder id, or 'none' for no folder"),
    q: str | None = Query(default=None, max_length=200),
    sort: str = Query(default="recent", pattern="^(recent|title|created)$"),
) -> Page[ProjectResponse]:
    folder_id: uuid.UUID | str | None = None
    if folder == "none":
        folder_id = "none"
    elif folder:
        try:
            folder_id = uuid.UUID(folder)
        except ValueError:
            raise ValidationError("folder must be an id or 'none'.") from None
    items, total = await ProjectService(session).list(
        current_user.id, limit=limit, offset=offset, view=view, folder=folder_id, q=q, sort=sort
    )
    return Page(
        items=[project_to_response(p, current_user) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/bulk", response_model=BulkProjectsResponse)
async def bulk_projects(
    payload: BulkProjectsRequest, current_user: CurrentUser, session: SessionDep
) -> BulkProjectsResponse:
    """One action (trash, restore, delete, star, unstar, move, duplicate) on many projects."""
    changed = await ProjectService(session).bulk(
        current_user.id, payload.ids, payload.action, payload.folder_id
    )
    return BulkProjectsResponse(changed=changed)


@router.delete("/trash", status_code=status.HTTP_204_NO_CONTENT)
async def empty_trash(current_user: CurrentUser, session: SessionDep) -> Response:
    """Permanently deletes everything in the trash."""
    await ProjectService(session).empty_trash(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest, current_user: CurrentUser, session: SessionDep
) -> ProjectResponse:
    project = await ProjectService(session).create(current_user.id, payload)
    return project_to_response(project, current_user)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> ProjectResponse:
    project = await ProjectService(session).get(project_id, current_user.id)
    return project_to_response(project, current_user)


@router.get(
    "/{project_id}/detail",
    response_model=ProjectDetailResponse,
    summary="Project plus its full scene timeline (one call for the editor)",
)
async def get_project_detail(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> ProjectDetailResponse:
    project = await ProjectService(session).get(project_id, current_user.id)
    return ProjectDetailResponse(
        project=project_to_response(project, current_user),
        scenes=scenes_to_response(list(project.scenes)),
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> ProjectResponse:
    project = await ProjectService(session).update(project_id, current_user.id, payload)
    return project_to_response(project, current_user)


@router.post(
    "/{project_id}/thumbnail",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Redraw the project's thumbnail from its current title and script",
)
async def regenerate_thumbnail(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> dict[str, str]:
    project = await ProjectService(session).get(project_id, current_user.id)
    await enqueue("generate_thumbnail", str(project.id))
    return {"status": "queued"}


@router.post(
    "/{project_id}/duplicate", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED
)
async def duplicate_project(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> ProjectResponse:
    project = await ProjectService(session).duplicate(project_id, current_user.id)
    return project_to_response(project, current_user)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> ProjectResponse:
    return project_to_response(
        await ProjectService(session).restore(project_id, current_user.id), current_user
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    permanent: bool = Query(default=False, description="Skip the trash"),
) -> Response:
    """Moves a project to the trash (restorable for 30 days); `permanent=true` deletes it."""
    service = ProjectService(session)
    if permanent:
        await service.delete(project_id, current_user.id)
    else:
        await service.trash(project_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
