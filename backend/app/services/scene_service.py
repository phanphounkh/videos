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

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.caption import Caption
from app.models.enums import AssetType, Transition
from app.models.scene import Scene
from app.repositories.scene_repository import SceneRepository
from app.schemas.scene import SceneCreateRequest, SceneUpdateRequest
from app.schemas.scene_settings import merge_scene_settings
from app.services.caption_service import CAPTIONS_EDITED_KEY, CaptionService
from app.services.project_service import ProjectService
from app.services.timeline_ops import CutResult, cut_window

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

        # Settings merge instead of replace: the editor changes one key at a time
        # and must not wipe the speech data the generator stored next to it.
        if "settings" in changes:
            patch = changes.pop("settings")
            if patch is not None:
                scene.settings = merge_scene_settings(scene.settings or {}, patch)
        for field in ("image_asset_id", "video_asset_id"):
            if field in changes:
                await self._check_asset(
                    changes[field],
                    scene.project_id,
                    AssetType.IMAGE if field == "image_asset_id" else AssetType.VIDEO,
                )
        for field, value in changes.items():
            setattr(scene, field, value)
        if "video_asset_id" in changes:
            # A different clip starts from its own beginning.
            scene.settings = merge_scene_settings(scene.settings or {}, {"trim_start": None})

        # New narration or language makes the old captions wrong: rebuild them. A
        # length change alone keeps hand-edited captions (clipped to the scene).
        if {"narration", "language"} & changes.keys():
            await self.captions.rebuild(scene)
        elif "duration" in changes:
            if (scene.settings or {}).get(CAPTIONS_EDITED_KEY):
                await self.captions.clamp(scene)
            else:
                await self.captions.rebuild(scene)

        await self.session.commit()
        log.info("scene_updated", scene_id=str(scene_id), fields=sorted(changes))
        return await self.get_owned(scene_id, owner_id)

    async def _check_asset(
        self, asset_id: uuid.UUID | None, project_id: uuid.UUID, expected: AssetType
    ) -> None:
        """A scene may only use media that belongs to its own project."""
        if asset_id is None:
            return
        asset = await self.session.get(Asset, asset_id)
        if asset is None or asset.project_id != project_id:
            raise ValidationError("That media does not belong to this project.",
                                  code="ASSET_NOT_FOUND")
        if asset.type != expected:
            raise ValidationError(f"That media is a {asset.type}, not a {expected}.",
                                  code="ASSET_TYPE_MISMATCH")

    # --------------------------------------------------------------- captions
    async def set_captions(
        self, scene_id: uuid.UUID, owner_id: uuid.UUID, items: list[tuple[str, float, float]]
    ) -> Scene:
        scene = await self.get_owned(scene_id, owner_id)
        await self.captions.replace(scene, items)
        await self.session.commit()
        log.info("captions_edited", scene_id=str(scene_id), count=len(items))
        return await self.get_owned(scene_id, owner_id)

    async def reset_captions(self, scene_id: uuid.UUID, owner_id: uuid.UUID) -> Scene:
        """Back to captions built from the narration and the voice."""
        scene = await self.get_owned(scene_id, owner_id)
        await self.captions.rebuild(scene)
        await self.session.commit()
        return await self.get_owned(scene_id, owner_id)

    # ----------------------------------------------------- split and trim
    async def split(
        self, scene_id: uuid.UUID, owner_id: uuid.UUID, at: float
    ) -> Sequence[Scene]:
        """Cuts a scene in two at `at` seconds. Nothing is lost: narration,
        captions, voice, layers and the uploaded clip continue across the cut."""
        scene = await self.get_owned(scene_id, owner_id)
        siblings = sorted(
            await self.scenes.list_for_project(scene.project_id), key=lambda s: s.scene_number
        )
        first = self._cut(scene, 0.0, at)
        second = self._cut(scene, at, scene.duration)

        tail = Scene(
            project_id=scene.project_id,
            scene_number=len(siblings) + 1_000,  # temporary, see create()
            visual_prompt=scene.visual_prompt,
            # The key-point sticker belongs to the first half; a cut must not
            # make it pop up twice.
            on_screen_text=None,
            # No whoosh in the middle of what looks like one continuous shot.
            transition=Transition.NONE,
            background_color=scene.background_color,
            language=scene.language,
            image_asset_id=scene.image_asset_id,
            video_asset_id=scene.video_asset_id,
            audio_asset_id=scene.audio_asset_id,
            narration=second.narration,
            duration=second.duration,
            settings=second.settings,
        )
        self.session.add(tail)
        await self.session.flush()
        await self._write_captions(tail.id, second, scene.language)

        scene.narration = first.narration
        scene.duration = first.duration
        scene.settings = first.settings
        await self._write_captions(scene.id, first, scene.language)
        self.session.expire(scene, ["captions"])

        order = [s.id for s in siblings]
        order.insert(order.index(scene.id) + 1, tail.id)
        await self._apply_order(scene.project_id, order)
        await self.session.commit()
        log.info("scene_split", scene_id=str(scene_id), at=at)
        return await self.scenes.list_for_project(scene.project_id)

    async def trim(
        self, scene_id: uuid.UUID, owner_id: uuid.UUID, start: float, end: float
    ) -> Sequence[Scene]:
        """Keeps only [start, end] of a scene (dragging a clip's edges)."""
        scene = await self.get_owned(scene_id, owner_id)
        kept = self._cut(scene, start, end)
        scene.narration = kept.narration
        scene.duration = kept.duration
        scene.settings = kept.settings
        await self._write_captions(scene.id, kept, scene.language)
        self.session.expire(scene, ["captions"])
        await self.session.commit()
        log.info("scene_trimmed", scene_id=str(scene_id), start=start, end=end)
        return await self.scenes.list_for_project(scene.project_id)

    @staticmethod
    def _cut(scene: Scene, a: float, b: float) -> CutResult:
        return cut_window(
            duration=scene.duration,
            narration=scene.narration,
            captions=[(c.text, c.start_time, c.end_time) for c in scene.captions],
            settings=scene.settings or {},
            a=a,
            b=b,
        )

    async def _write_captions(
        self, scene_id: uuid.UUID, cut: CutResult, language: str | None
    ) -> None:
        # Explicit DELETE + add, as in CaptionService: assigning to the
        # relationship would lazy-load inside the async context.
        await self.session.execute(delete(Caption).where(Caption.scene_id == scene_id))
        for index, (text, start, end) in enumerate(cut.captions):
            self.session.add(
                Caption(
                    scene_id=scene_id,
                    segment_index=index,
                    text=text,
                    start_time=start,
                    end_time=end,
                    language=language or "en",
                )
            )
        await self.session.flush()

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
