"""Folders: named groups of the signed-in person's projects."""

import uuid

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, SessionDep
from app.core.exceptions import NotFoundError
from app.models.folder import Folder
from app.models.project import Project
from app.schemas.folder import FolderRequest, FolderResponse
from app.schemas.presenters import project_to_response

router = APIRouter(prefix="/folders", tags=["folders"])

MAX_FOLDERS = 200


async def _owned(session: SessionDep, folder_id: uuid.UUID, owner_id: uuid.UUID) -> Folder:
    folder = await session.get(Folder, folder_id)
    if folder is None or folder.owner_id != owner_id:
        raise NotFoundError("Folder was not found.", code="FOLDER_NOT_FOUND")
    return folder


async def _response(session: SessionDep, folder: Folder) -> FolderResponse:
    live = (Project.folder_id == folder.id, Project.deleted_at.is_(None))
    count = (
        await session.execute(select(func.count()).select_from(Project).where(*live))
    ).scalar_one()
    latest = (
        await session.execute(
            select(Project).where(*live).order_by(Project.updated_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        project_count=int(count),
        cover_url=project_to_response(latest).thumbnail_url if latest else None,
        created_at=folder.created_at,
    )


@router.get("", response_model=list[FolderResponse])
async def list_folders(user: CurrentUser, session: SessionDep) -> list[FolderResponse]:
    folders = (
        (
            await session.execute(
                select(Folder)
                .where(Folder.owner_id == user.id)
                .order_by(Folder.name)
                .limit(MAX_FOLDERS)
            )
        )
        .scalars()
        .all()
    )
    return [await _response(session, f) for f in folders]


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FolderRequest, user: CurrentUser, session: SessionDep
) -> FolderResponse:
    folder = Folder(owner_id=user.id, name=payload.name.strip())
    session.add(folder)
    await session.commit()
    return await _response(session, folder)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def rename_folder(
    folder_id: uuid.UUID, payload: FolderRequest, user: CurrentUser, session: SessionDep
) -> FolderResponse:
    folder = await _owned(session, folder_id, user.id)
    folder.name = payload.name.strip()
    await session.commit()
    return await _response(session, folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(folder_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Response:
    """Deletes the folder only: its projects stay, moved out to the top level."""
    folder = await _owned(session, folder_id, user.id)
    await session.delete(folder)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
