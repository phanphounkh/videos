"""Project endpoints."""

import uuid

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, SessionDep
from app.schemas.common import Page
from app.schemas.presenters import project_to_response, scenes_to_response
from app.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
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
) -> Page[ProjectResponse]:
    items, total = await ProjectService(session).list(
        current_user.id, limit=limit, offset=offset
    )
    return Page(
        items=[project_to_response(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest, current_user: CurrentUser, session: SessionDep
) -> ProjectResponse:
    project = await ProjectService(session).create(current_user.id, payload)
    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> ProjectResponse:
    project = await ProjectService(session).get(project_id, current_user.id)
    return project_to_response(project)


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
        project=project_to_response(project),
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
    return project_to_response(project)


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


@router.post("/{project_id}/duplicate", response_model=ProjectResponse,
             status_code=status.HTTP_201_CREATED)
async def duplicate_project(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> ProjectResponse:
    project = await ProjectService(session).duplicate(project_id, current_user.id)
    return project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> Response:
    await ProjectService(session).delete(project_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
