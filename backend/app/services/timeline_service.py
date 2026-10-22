"""Restore a whole timeline from a snapshot: the engine behind undo and redo.

Every editor action changes something on the server immediately. To undo it, the
client keeps the timeline as it was and sends it back here; this makes the
project match that snapshot exactly - deleted scenes come back with their old
ids, removed scenes go away, order, text, layers, captions, media choices and
music are all restored in one transaction.

Media files are never deleted by editing (only by deleting the project), so a
snapshot can always point at the same assets it did before.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.caption import Caption
from app.models.enums import AssetType
from app.models.scene import Scene
from app.schemas.timeline import SceneSnapshot, TimelineSnapshot
from app.services.project_service import ProjectService
from app.services.scene_service import SceneService

log = get_logger(__name__)


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)
        self.scene_service = SceneService(session)

    async def restore(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, snapshot: TimelineSnapshot
    ) -> list[Scene]:
        project = await self.projects.get(project_id, owner_id)
        existing = {scene.id: scene for scene in project.scenes}

        await self._check_scene_ids(project_id, snapshot, existing)
        await self._check_assets(project_id, snapshot)

        keep = {scene.id for scene in snapshot.scenes}
        for scene_id, scene in existing.items():
            if scene_id not in keep:
                await self.session.delete(scene)
        await self.session.flush()

        order: list[uuid.UUID] = []
        for index, data in enumerate(snapshot.scenes):
            scene = existing.get(data.id)
            if scene is None:
                scene = Scene(id=data.id, project_id=project_id, scene_number=100_000 + index)
                self.session.add(scene)
            self._apply(scene, data)
            await self.session.flush()
            await self._write_captions(scene.id, data)
            order.append(scene.id)

        await self.scene_service._apply_order(project_id, order)

        project.music_asset_id = snapshot.music_asset_id
        project.settings = {**(project.settings or {}), "music": snapshot.music.model_dump()}
        await self.session.commit()
        log.info("timeline_restored", project_id=str(project_id), scenes=len(order))
        return list(await self.scene_service.scenes.list_for_project(project_id))

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _apply(scene: Scene, data: SceneSnapshot) -> None:
        scene.narration = data.narration
        scene.visual_prompt = data.visual_prompt
        scene.on_screen_text = data.on_screen_text
        scene.duration = data.duration
        scene.transition = data.transition
        scene.background_color = data.background_color
        scene.language = data.language
        scene.settings = data.settings
        scene.image_asset_id = data.image_asset_id
        scene.video_asset_id = data.video_asset_id
        scene.audio_asset_id = data.audio_asset_id

    async def _write_captions(self, scene_id: uuid.UUID, data: SceneSnapshot) -> None:
        await self.session.execute(delete(Caption).where(Caption.scene_id == scene_id))
        for index, caption in enumerate(data.captions):
            self.session.add(
                Caption(
                    scene_id=scene_id,
                    segment_index=index,
                    text=caption.text,
                    start_time=caption.start_time,
                    end_time=caption.end_time,
                    language=caption.language,
                )
            )
        await self.session.flush()
        # The scene may already hold a loaded captions collection; drop it so the
        # response reads the rows just written.
        scene = await self.session.get(Scene, scene_id)
        if scene is not None:
            self.session.expire(scene, ["captions"])

    async def _check_scene_ids(
        self,
        project_id: uuid.UUID,
        snapshot: TimelineSnapshot,
        existing: dict[uuid.UUID, Scene],
    ) -> None:
        """A scene id that is not ours must not exist anywhere (never steal one)."""
        foreign = [s.id for s in snapshot.scenes if s.id not in existing]
        if not foreign:
            return
        taken = (
            await self.session.execute(select(Scene.id).where(Scene.id.in_(foreign)))
        ).scalars().all()
        if taken:
            raise ValidationError(
                "The snapshot refers to a scene of another project.",
                code="SCENE_PROJECT_MISMATCH",
            )

    async def _check_assets(self, project_id: uuid.UUID, snapshot: TimelineSnapshot) -> None:
        wanted: dict[uuid.UUID, str] = {}
        for scene in snapshot.scenes:
            for asset_id, kind in (
                (scene.image_asset_id, AssetType.IMAGE),
                (scene.video_asset_id, AssetType.VIDEO),
                (scene.audio_asset_id, AssetType.AUDIO),
            ):
                if asset_id is not None:
                    wanted[asset_id] = kind
        if snapshot.music_asset_id is not None:
            wanted[snapshot.music_asset_id] = AssetType.MUSIC
        if not wanted:
            return

        rows = (
            await self.session.execute(
                select(Asset.id, Asset.type).where(
                    Asset.id.in_(list(wanted)), Asset.project_id == project_id
                )
            )
        ).all()
        found = {row.id: row.type for row in rows}
        for asset_id, kind in wanted.items():
            if asset_id not in found:
                raise ValidationError(
                    "The snapshot uses media that is not in this project.",
                    code="ASSET_NOT_FOUND",
                )
            # Voice audio is stored as `audio`; music as `music`. Anything else
            # in a slot is a client bug and would render as a broken video.
            if found[asset_id] != kind:
                raise ValidationError(
                    f"Media {asset_id} is a {found[asset_id]}, expected {kind}.",
                    code="ASSET_TYPE_MISMATCH",
                )
