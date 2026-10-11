"""Project use cases: create, read, update, delete, duplicate.

Ownership is enforced here for every operation by loading the project through
`get_for_owner`, so there is no code path that can reach someone else's project.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.caption import Caption
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.scene import Scene
from app.repositories.project_repository import ProjectRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.storage import get_storage, scene_upload_key

log = get_logger(__name__)


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.scenes = SceneRepository(session)

    async def create(self, owner_id: uuid.UUID, payload: ProjectCreateRequest) -> Project:
        project = Project(
            owner_id=owner_id,
            title=payload.title.strip(),
            description=payload.description,
            language=payload.language,
            aspect_ratio=payload.aspect_ratio,
            style=payload.style,
            tone=payload.tone,
            audience=payload.audience,
            voice=payload.voice,
            target_duration=payload.target_duration,
            fps=payload.fps,
            status=ProjectStatus.DRAFT,
        )
        self.projects.add(project)
        await self.session.commit()
        log.info("project_created", project_id=str(project.id), owner_id=str(owner_id))
        # Re-read through the repository: it eager-loads scenes AND each scene's
        # assets. `session.refresh(project, ["scenes"])` loads only the scenes,
        # so the presenter's `scene.image_asset` access would then trigger lazy
        # IO inside an async request and raise MissingGreenlet.
        return await self.get(project.id, owner_id)

    async def get(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
        project = await self.projects.get_for_owner(project_id, owner_id)
        if project is None:
            # 404 (not 403) for someone else's project: a 403 would confirm that
            # the id exists, which leaks information.
            raise NotFoundError("Project was not found.", code="PROJECT_NOT_FOUND")
        return project

    async def list(
        self, owner_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Project], int]:
        items = await self.projects.list_for_owner(owner_id, limit=limit, offset=offset)
        total = await self.projects.count_for_owner(owner_id)
        return items, total

    async def update(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, payload: ProjectUpdateRequest
    ) -> Project:
        project = await self.get(project_id, owner_id)
        # exclude_unset: a PATCH that omits a field must not overwrite it with None.
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self.session.commit()
        log.info("project_updated", project_id=str(project.id))
        return await self.get(project_id, owner_id)

    async def delete(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        project = await self.get(project_id, owner_id)
        await self.projects.delete(project)
        await self.session.commit()
        log.info("project_deleted", project_id=str(project_id))

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
            tone=source.tone,
            audience=source.audience,
            voice=source.voice,
            target_duration=source.target_duration,
            fps=source.fps,
            status=source.status,
        )
        self.projects.add(copy)
        await self.session.flush()  # assigns copy.id without ending the transaction

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
        self, source: Asset, *, project_id: uuid.UUID, scene_id: uuid.UUID
    ) -> Asset:
        storage = get_storage()
        data = await storage.get_bytes(source.storage_key)
        filename = source.storage_key.rsplit("/", 1)[-1] or f"{source.id}.bin"
        key = scene_upload_key(
            str(project_id), str(scene_id), f"copy-{source.id.hex[:8]}-{filename}"
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
