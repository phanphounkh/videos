"""Project use cases: create, read, update, delete, duplicate.

Ownership is enforced here for every operation by loading the project through
`get_for_owner`, so there is no code path that can reach someone else's project.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.caption import Caption
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.scene import Scene
from app.repositories.project_repository import ProjectRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest

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
        """Deep-copies a project, its scenes and their captions.

        Asset pointers are copied by reference: the duplicate reuses the same
        images and audio files rather than re-generating or re-uploading them.
        """
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
                image_asset_id=scene.image_asset_id,
                video_asset_id=scene.video_asset_id,
                audio_asset_id=scene.audio_asset_id,
            )
            self.session.add(new_scene)
            await self.session.flush()
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

    async def set_status(
        self, project: Project, status: ProjectStatus, error_message: str | None = None
    ) -> None:
        project.status = status
        project.error_message = error_message
        await self.session.commit()
