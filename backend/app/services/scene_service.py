"""Scene use cases: CRUD, reorder, duplicate.

ORDERING INVARIANT: for every project, `scene_number` is exactly 1..N with no
gaps and no duplicates. Every mutation ends by writing the full desired order
through `_apply_order`, so there is a single place where ordering can be wrong.

WHY `_apply_order` needs two passes: (project_id, scene_number) is UNIQUE, so
assigning final numbers one row at a time can transiently collide with a row
that still holds that number. The first pass parks every row at a NEGATIVE
number - negatives can never collide with the positive numbers still in the
table, nor with each other - and the second pass writes the final values.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.caption import Caption
from app.models.scene import Scene
from app.repositories.scene_repository import SceneRepository
from app.schemas.scene import SceneCreateRequest, SceneUpdateRequest
from app.services.caption_service import CaptionService
from app.services.project_service import ProjectService

log = get_logger(__name__)


class SceneService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scenes = SceneRepository(session)
        self.projects = ProjectService(session)
        self.captions = CaptionService(session)

    # ------------------------------------------------------------------ reads
    async def list_for_project(
        self, project_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Sequence[Scene]:
        await self.projects.get(project_id, owner_id)  # ownership check
        return await self.scenes.list_for_project(project_id)

    async def get_owned(self, scene_id: uuid.UUID, owner_id: uuid.UUID) -> Scene:
        scene = await self.scenes.get_with_project(scene_id)
        if scene is None or scene.project.owner_id != owner_id:
            raise NotFoundError("Scene was not found.", code="SCENE_NOT_FOUND")
        return scene

    # -------------------------------------------------------------- mutations
    async def create(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, payload: SceneCreateRequest
    ) -> Scene:
        project = await self.projects.get(project_id, owner_id)
        existing = sorted(project.scenes, key=lambda s: s.scene_number)

        # 1-based insert position, clamped to the end of the timeline.
        position = min(max(payload.scene_number or len(existing) + 1, 1), len(existing) + 1)

        scene = Scene(
            project_id=project_id,
            # Temporary number beyond the current maximum: unique by construction,
            # replaced by _apply_order below.
            scene_number=len(existing) + 1_000,
            narration=payload.narration,
            visual_prompt=payload.visual_prompt,
            on_screen_text=payload.on_screen_text,
            duration=payload.duration,
            transition=payload.transition,
            background_color=payload.background_color,
            language=payload.language or project.language,
            settings=payload.settings,
        )
        self.session.add(scene)
        await self.session.flush()

        # Captions are derived from narration, so a manually added scene has them
        # immediately - the editor never shows a scene without captions.
        await self.captions.rebuild(scene)

        order = [s.id for s in existing]
        order.insert(position - 1, scene.id)
        await self._apply_order(project_id, order)

        await self.session.commit()
        log.info("scene_created", scene_id=str(scene.id), project_id=str(project_id))
        return await self.get_owned(scene.id, owner_id)

    async def update(
        self, scene_id: uuid.UUID, owner_id: uuid.UUID, payload: SceneUpdateRequest
    ) -> Scene:
        scene = await self.get_owned(scene_id, owner_id)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(scene, field, value)

        # Editing narration, duration or language invalidates caption timings.
        if {"narration", "duration", "language"} & changes.keys():
            await self.captions.rebuild(scene)

        await self.session.commit()
        log.info("scene_updated", scene_id=str(scene_id), fields=sorted(changes))
        return await self.get_owned(scene_id, owner_id)

    async def delete(self, scene_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        scene = await self.get_owned(scene_id, owner_id)
        project_id = scene.project_id
        await self.scenes.delete(scene)
        await self.session.flush()

        remaining = await self.scenes.list_for_project(project_id)
        await self._apply_order(
            project_id, [s.id for s in sorted(remaining, key=lambda s: s.scene_number)]
        )
        await self.session.commit()
        log.info("scene_deleted", scene_id=str(scene_id))

    async def duplicate(self, scene_id: uuid.UUID, owner_id: uuid.UUID) -> Scene:
        source = await self.get_owned(scene_id, owner_id)
        siblings = sorted(
            await self.scenes.list_for_project(source.project_id), key=lambda s: s.scene_number
        )

        copy = Scene(
            project_id=source.project_id,
            scene_number=len(siblings) + 1_000,  # temporary, see create()
            narration=source.narration,
            visual_prompt=source.visual_prompt,
            on_screen_text=source.on_screen_text,
            duration=source.duration,
            transition=source.transition,
            background_color=source.background_color,
            language=source.language,
            settings=dict(source.settings or {}),
            image_asset_id=source.image_asset_id,
            video_asset_id=source.video_asset_id,
            audio_asset_id=source.audio_asset_id,
        )
        self.session.add(copy)
        await self.session.flush()

        for caption in source.captions:
            self.session.add(
                Caption(
                    scene_id=copy.id,
                    segment_index=caption.segment_index,
                    text=caption.text,
                    start_time=caption.start_time,
                    end_time=caption.end_time,
                    language=caption.language,
                )
            )
        await self.session.flush()

        order = [s.id for s in siblings]
        order.insert(order.index(source.id) + 1, copy.id)  # right after the original
        await self._apply_order(source.project_id, order)

        await self.session.commit()
        log.info("scene_duplicated", source_id=str(scene_id), scene_id=str(copy.id))
        return await self.get_owned(copy.id, owner_id)

    async def reorder(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, scene_ids: list[uuid.UUID]
    ) -> Sequence[Scene]:
        project = await self.projects.get(project_id, owner_id)
        existing = {scene.id for scene in project.scenes}

        if set(scene_ids) != existing or len(scene_ids) != len(existing):
            raise ValidationError(
                "scene_ids must contain exactly every scene of this project, once each.",
                code="INVALID_SCENE_ORDER",
                details={"expected": len(existing), "received": len(set(scene_ids))},
            )

        await self._apply_order(project_id, scene_ids)
        await self.session.commit()
        log.info("scenes_reordered", project_id=str(project_id), count=len(scene_ids))
        return await self.scenes.list_for_project(project_id)

    # ----------------------------------------------------------------- helpers
    async def _apply_order(self, project_id: uuid.UUID, order: list[uuid.UUID]) -> None:
        """Writes `order` as scene_number 1..N. See the module docstring."""
        scenes = {s.id: s for s in await self.scenes.list_for_project(project_id)}

        for position, scene_id in enumerate(order, start=1):
            scene = scenes.get(scene_id)
            if scene is not None:
                scene.scene_number = -position  # park out of the way of positives
        await self.session.flush()

        for position, scene_id in enumerate(order, start=1):
            scene = scenes.get(scene_id)
            if scene is not None:
                scene.scene_number = position
        await self.session.flush()
