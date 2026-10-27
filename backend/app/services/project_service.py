"""Project use cases: create, read, update, delete, duplicate.

Ownership is enforced here for every operation by loading the project through
`get_for_owner`, so there is no code path that can reach someone else's project.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.caption import Caption
from app.models.enums import ProjectStatus
from app.models.folder import Folder
from app.models.project import Project
from app.models.scene import Scene
from app.repositories.project_repository import ProjectRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.avatars import validate_choice
from app.services.purposes import get_purpose
from app.services.storage import get_storage, project_upload_key, scene_upload_key
from app.services.telemetry import Event, record

log = get_logger(__name__)

# How long a trashed project can still be restored.
TRASH_DAYS = 30


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.scenes = SceneRepository(session)

    async def create(self, owner_id: uuid.UUID, payload: ProjectCreateRequest) -> Project:
        if payload.folder_id is not None:
            await self._require_folder(payload.folder_id, owner_id)
        if payload.avatar is not None:
            await validate_choice(self.session, owner_id, payload.avatar)
        project = Project(
            avatar=payload.avatar,
            folder_id=payload.folder_id,
            settings={"resolution": payload.resolution} if payload.resolution != "fhd" else {},
            owner_id=owner_id,
            title=payload.title.strip(),
            description=payload.description,
            language=payload.language,
            aspect_ratio=payload.aspect_ratio,
            style=payload.style,
            purpose=payload.purpose,
            presenter=(
                payload.presenter
                if payload.presenter is not None
                else get_purpose(payload.purpose).presenter
            ),
            cta_text=payload.cta_text or get_purpose(payload.purpose).cta_text,
            tone=payload.tone,
            audience=payload.audience,
            voice=payload.voice,
            target_duration=payload.target_duration,
            fps=payload.fps,
            status=ProjectStatus.DRAFT,
        )
        self.projects.add(project)
        await self.session.commit()
        record(
            Event(
                name="project_created",
                user_id=str(owner_id),
                properties={
                    "project_id": str(project.id),
                    "purpose": str(payload.purpose),
                    "language": payload.language,
                    "aspect_ratio": str(payload.aspect_ratio),
                },
            )
        )
        log.info("project_created", project_id=str(project.id), owner_id=str(owner_id))
        # Re-read through the repository: it eager-loads scenes AND each scene's
        # assets. `session.refresh(project, ["scenes"])` loads only the scenes,
        # so the presenter's `scene.image_asset` access would then trigger lazy
        # IO inside an async request and raise MissingGreenlet.
        return await self.get(project.id, owner_id)

    async def get(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, *, include_trashed: bool = False
    ) -> Project:
        project = await self.projects.get_for_owner(
            project_id, owner_id, include_trashed=include_trashed
        )
        if project is None:
            # 404 (not 403) for someone else's project: a 403 would confirm that
            # the id exists, which leaks information.
            raise NotFoundError("Project was not found.", code="PROJECT_NOT_FOUND")
        return project

    async def list(
        self,
        owner_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        view: str = "all",
        folder: uuid.UUID | str | None = None,
        q: str | None = None,
        sort: str = "recent",
    ) -> tuple[Sequence[Project], int]:
        if view == "trash":
            await self.purge_expired_trash(owner_id)
            sort = "trashed"
        items = await self.projects.list_for_owner(
            owner_id, limit=limit, offset=offset, view=view, folder=folder, q=q, sort=sort
        )
        total = await self.projects.count_for_owner(owner_id, view=view, folder=folder, q=q)
        return items, total

    async def update(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, payload: ProjectUpdateRequest
    ) -> Project:
        project = await self.get(project_id, owner_id)
        # exclude_unset: a PATCH that omits a field must not overwrite it with None.
        changes = payload.model_dump(exclude_unset=True)
        music = changes.pop("music", None)
        resolution = changes.pop("resolution", None)
        if resolution is not None:
            project.settings = {**(project.settings or {}), "resolution": resolution}
        if changes.get("avatar"):
            await validate_choice(self.session, owner_id, changes["avatar"])
        if changes.get("folder_id"):
            await self._require_folder(changes["folder_id"], owner_id)
        if music is not None:
            # Reassign, never mutate in place: SQLAlchemy only sees a new dict.
            project.settings = {**(project.settings or {}), "music": music}
        for field, value in changes.items():
            # purpose and presenter are NOT NULL: an explicit null means "leave it".
            if value is None and field in {"purpose", "presenter", "starred"}:
                continue
            setattr(project, field, value)
        await self.session.commit()
        log.info("project_updated", project_id=str(project.id))
        return await self.get(project_id, owner_id)

    async def _require_folder(self, folder_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        folder = await self.session.get(Folder, folder_id)
        if folder is None or folder.owner_id != owner_id:
            raise NotFoundError("Folder was not found.", code="FOLDER_NOT_FOUND")

    async def trash(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        """Moves a project to the trash; it can be restored for 30 days."""
        project = await self.get(project_id, owner_id)
        project.deleted_at = datetime.now(UTC)
        await self.session.commit()
        log.info("project_trashed", project_id=str(project_id))

    async def restore(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
        project = await self.get(project_id, owner_id, include_trashed=True)
        project.deleted_at = None
        await self.session.commit()
        log.info("project_restored", project_id=str(project_id))
        return await self.get(project_id, owner_id)

    async def delete(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        """Deletes a project for good, trashed or not."""
        project = await self.get(project_id, owner_id, include_trashed=True)
        await self.projects.delete(project)
        await self.session.commit()
        log.info("project_deleted", project_id=str(project_id))

    async def empty_trash(self, owner_id: uuid.UUID) -> int:
        trashed = await self.projects.list_for_owner(
            owner_id, view="trash", limit=100_000, sort="trashed"
        )
        for project in trashed:
            await self.projects.delete(project)
        await self.session.commit()
        log.info("trash_emptied", owner_id=str(owner_id), projects=len(trashed))
        return len(trashed)

    async def purge_expired_trash(self, owner_id: uuid.UUID) -> None:
        """Whatever has sat in the trash for more than 30 days is deleted."""
        cutoff = datetime.now(UTC) - timedelta(days=TRASH_DAYS)
        old = (
            (
                await self.session.execute(
                    select(Project).where(Project.owner_id == owner_id, Project.deleted_at < cutoff)
                )
            )
            .scalars()
            .all()
        )
        for project in old:
            await self.projects.delete(project)
        if old:
            await self.session.commit()

    async def bulk(
        self,
        owner_id: uuid.UUID,
        ids: Sequence[uuid.UUID],
        action: str,
        folder_id: uuid.UUID | None = None,
    ) -> int:
        """Applies one action to many of the person's projects. Ids that are not theirs
        (or do not exist) are skipped, never an error. Returns how many were changed."""
        if action == "move" and folder_id is not None:
            await self._require_folder(folder_id, owner_id)
        done = 0
        for project_id in dict.fromkeys(ids):
            trashed_ok = action in {"restore", "delete"}
            project = await self.projects.get_for_owner(
                project_id, owner_id, include_trashed=trashed_ok
            )
            if project is None:
                continue
            if action == "trash":
                project.deleted_at = datetime.now(UTC)
            elif action == "restore":
                project.deleted_at = None
            elif action == "star":
                project.starred = True
            elif action == "unstar":
                project.starred = False
            elif action == "move":
                project.folder_id = folder_id
            elif action == "delete":
                await self.projects.delete(project)
            elif action == "duplicate":
                await self.duplicate(project_id, owner_id)
            done += 1
        await self.session.commit()
        log.info("projects_bulk", action=action, requested=len(ids), changed=done)
        return done

    async def duplicate(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
        """Deep-copy a project, including independent scene media objects."""
        source = await self.get(project_id, owner_id)

        copy = Project(
            owner_id=owner_id,
            title=f"{source.title} (copy)",
            description=source.description,
            prompt=source.prompt,
            language=source.language,
            aspect_ratio=source.aspect_ratio,
            style=source.style,
            purpose=source.purpose,
            presenter=source.presenter,
            avatar=source.avatar,
            cta_text=source.cta_text,
            tone=source.tone,
            audience=source.audience,
            voice=source.voice,
            target_duration=source.target_duration,
            fps=source.fps,
            status=source.status,
            settings=dict(source.settings or {}),
        )
        self.projects.add(copy)
        await self.session.flush()  # assigns copy.id without ending the transaction

        if source.music_asset is not None:
            # Same reason as the scene assets below: share nothing that is
            # deleted together with the original project.
            music_copy = await self._copy_scene_asset(
                source.music_asset, project_id=copy.id, scene_id=None
            )
            copy.music_asset_id = music_copy.id

        for scene in source.scenes:
            new_scene = Scene(
                project_id=copy.id,
                scene_number=scene.scene_number,
                narration=scene.narration,
                visual_prompt=scene.visual_prompt,
                on_screen_text=scene.on_screen_text,
                duration=scene.duration,
                transition=scene.transition,
                background_color=scene.background_color,
                language=scene.language,
                settings=dict(scene.settings or {}),
            )
            self.session.add(new_scene)
            await self.session.flush()

            # Asset rows belong to a project and are deleted with it. Sharing
            # their ids here would make the duplicate lose all media when the
            # original project is deleted, so copy both bytes and metadata under
            # the new project/scene namespace.
            for relationship, foreign_key in (
                ("image_asset", "image_asset_id"),
                ("video_asset", "video_asset_id"),
                ("audio_asset", "audio_asset_id"),
            ):
                source_asset = getattr(scene, relationship)
                if source_asset is not None:
                    copied_asset = await self._copy_scene_asset(
                        source_asset, project_id=copy.id, scene_id=new_scene.id
                    )
                    setattr(new_scene, foreign_key, copied_asset.id)

            for caption in scene.captions:
                self.session.add(
                    Caption(
                        scene_id=new_scene.id,
                        segment_index=caption.segment_index,
                        text=caption.text,
                        start_time=caption.start_time,
                        end_time=caption.end_time,
                        language=caption.language,
                    )
                )

        await self.session.commit()
        refreshed = await self.projects.get_for_owner(copy.id, owner_id)
        assert refreshed is not None
        log.info("project_duplicated", source_id=str(project_id), project_id=str(copy.id))
        return refreshed

    async def _copy_scene_asset(
        self, source: Asset, *, project_id: uuid.UUID, scene_id: uuid.UUID | None
    ) -> Asset:
        storage = get_storage()
        data = await storage.get_bytes(source.storage_key)
        filename = source.storage_key.rsplit("/", 1)[-1] or f"{source.id}.bin"
        unique = f"copy-{source.id.hex[:8]}-{filename}"
        key = (
            scene_upload_key(str(project_id), str(scene_id), unique)
            if scene_id is not None
            else project_upload_key(str(project_id), unique)
        )
        stored = await storage.put_bytes(key, data, source.mime_type)

        copied = Asset(
            project_id=project_id,
            scene_id=scene_id,
            type=source.type,
            source=source.source,
            storage_key=stored.storage_key,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            duration=source.duration,
            width=source.width,
            height=source.height,
            original_filename=source.original_filename,
            provider=source.provider,
            prompt=source.prompt,
        )
        self.session.add(copied)
        await self.session.flush()
        return copied

    async def set_status(
        self, project: Project, status: ProjectStatus, error_message: str | None = None
    ) -> None:
        project.status = status
        project.error_message = error_message
        await self.session.commit()
