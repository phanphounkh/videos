"""Generation use cases: prompt -> script -> scenes, and per-scene media.

This is the heart of the product. Read the three entry points:

  generate_script_and_scenes()  prompt  -> LLM -> validated script -> scene rows
  generate_scene_image()        scene   -> ImageProvider -> storage -> Asset
  generate_scene_voice()        scene   -> TTSProvider  -> storage -> Asset
                                        -> captions timed against the real audio

RELIABILITY RULE (project requirement #34): a failure in one scene must never
destroy the project. Each media method is independent and idempotent - calling
it again replaces that scene's asset and nothing else.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.enums import AssetSource, AssetType, GenerationStatus, ProjectStatus
from app.models.project import Project
from app.models.scene import Scene
from app.models.voice_generation import VoiceGeneration
from app.repositories.scene_repository import SceneRepository
from app.schemas.generation import GeneratedScript, GenerateRequest
from app.services.ai import ScriptRequest, get_image_provider, get_llm_provider, get_tts_provider
from app.services.caption_service import CaptionService
from app.services.project_service import ProjectService
from app.services.storage import get_storage, scene_image_key, scene_voice_key

log = get_logger(__name__)


@dataclass(slots=True)
class MediaOutcome:
    asset: Asset | None
    status: GenerationStatus
    provider: str
    message: str | None = None


class GenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)
        self.scenes = SceneRepository(session)
        self.captions = CaptionService(session)

    # ------------------------------------------------------------------ script
    async def generate_script_and_scenes(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, payload: GenerateRequest
    ) -> Project:
        project = await self.projects.get(project_id, owner_id)

        log.info(
            "video_generation_started",
            project_id=str(project_id),
            prompt_chars=len(payload.prompt),
        )
        project.status = ProjectStatus.GENERATING
        project.prompt = payload.prompt
        project.error_message = None
        if payload.aspect_ratio:
            project.aspect_ratio = payload.aspect_ratio
        project.language = payload.language
        project.style = payload.style
        project.tone = payload.tone or project.tone
        project.audience = payload.audience or project.audience
        project.voice = payload.voice or project.voice
        project.target_duration = payload.duration
        await self.session.commit()

        try:
            provider = get_llm_provider()
            script = await provider.generate_script(
                ScriptRequest(
                    prompt=payload.prompt,
                    duration=payload.duration,
                    language=payload.language,
                    style=str(payload.style),
                    tone=payload.tone,
                    audience=payload.audience,
                )
            )
        except ProviderError as exc:
            # Persist the failure: the project must not stay stuck in "generating".
            project.status = ProjectStatus.FAILED
            project.error_message = exc.message
            await self.session.commit()
            log.warning("video_generation_failed", project_id=str(project_id), error=exc.message)
            raise

        await self._replace_scenes(project, script)

        project.title = script.title
        project.description = script.description or project.description
        project.status = ProjectStatus.READY
        await self.session.commit()

        # `_replace_scenes` deleted the old rows with a bulk DELETE and inserted
        # the new ones directly, so the Project instance still holds the stale
        # `scenes` collection from the identity map. Expire it, or the response
        # reports scene_count=0 for a project that really has scenes.
        self.session.expire(project, ["scenes"])

        log.info(
            "script_generated_persisted",
            project_id=str(project_id),
            scenes=len(script.scenes),
            provider=provider.name,
        )
        refreshed = await self.projects.get(project_id, owner_id)
        return refreshed

    async def _replace_scenes(self, project: Project, script: GeneratedScript) -> None:
        """Generation replaces the timeline wholesale - it is a new script."""
        await self.scenes.delete_for_project(project.id)
        await self.session.flush()

        for generated in script.scenes:
            scene = Scene(
                project_id=project.id,
                scene_number=generated.scene_number,
                narration=generated.narration,
                visual_prompt=generated.visual_prompt,
                on_screen_text=generated.on_screen_text,
                duration=generated.duration,
                transition=generated.transition,
                language=script.language,
                settings={},
            )
            self.session.add(scene)
            await self.session.flush()
            # Captions are derived from narration immediately so the editor has
            # something to show before any audio exists; they are recomputed
            # against the real audio duration once voice is generated.
            await self._write_captions(scene, generated.duration)
        await self.session.flush()

    # ------------------------------------------------------------------- image
    async def generate_scene_image(
        self, scene_id: uuid.UUID, owner_id: uuid.UUID, *, prompt_override: str | None = None
    ) -> MediaOutcome:
        scene = await self._owned_scene(scene_id, owner_id)
        project = scene.project
        prompt = prompt_override or scene.visual_prompt or scene.narration[:300]
        if not prompt.strip():
            return MediaOutcome(None, GenerationStatus.FAILED, "none",
                                "This scene has no visual prompt to generate from.")

        width, height = project.dimensions
        provider = get_image_provider()
        log.info("image_generation_started", scene_id=str(scene_id), provider=provider.name)

        try:
            result = await provider.generate_image(
                prompt, width, height, style=project.style
            )
        except ProviderError as exc:
            log.warning("image_generation_failed", scene_id=str(scene_id), error=exc.message)
            return MediaOutcome(None, GenerationStatus.FAILED, provider.name, exc.message)

        extension = "png" if result.mime_type.endswith("png") else "jpg"
        key = scene_image_key(str(project.id), str(scene.id), extension)
        stored = await get_storage().put_bytes(key, result.data, result.mime_type)

        asset = await self._replace_asset(
            project_id=project.id,
            scene_id=scene.id,
            asset_type=AssetType.IMAGE,
            storage_key=stored.storage_key,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            width=result.width,
            height=result.height,
            provider=result.provider,
            prompt=prompt,
            previous_asset_id=scene.image_asset_id,
        )
        scene.image_asset_id = asset.id
        await self.session.commit()

        message = (
            "Placeholder image (no AI image provider configured)."
            if result.is_placeholder else None
        )
        return MediaOutcome(asset, GenerationStatus.COMPLETED, result.provider, message)

    # ------------------------------------------------------------------- voice
    async def generate_scene_voice(
        self, scene_id: uuid.UUID, owner_id: uuid.UUID, *, voice_override: str | None = None
    ) -> MediaOutcome:
        scene = await self._owned_scene(scene_id, owner_id)
        project = scene.project
        text = scene.narration.strip()
        if not text:
            return MediaOutcome(None, GenerationStatus.FAILED, "none",
                                "This scene has no narration to speak.")

        language = scene.language or project.language
        voice = voice_override or project.voice or "default"
        provider = get_tts_provider(language)

        attempt = VoiceGeneration(
            scene_id=scene.id,
            provider=provider.name,
            voice=voice,
            language=language,
            text=text,
            status=GenerationStatus.RUNNING,
        )
        self.session.add(attempt)
        await self.session.flush()

        try:
            result = await provider.generate(text, language, voice)
        except ProviderError as exc:
            attempt.status = GenerationStatus.FAILED
            attempt.error_message = exc.message
            await self.session.commit()
            log.warning("voice_generation_failed", scene_id=str(scene_id), error=exc.message)
            return MediaOutcome(None, GenerationStatus.FAILED, provider.name, exc.message)

        extension = "mp3" if "mpeg" in result.mime_type else "wav"
        key = scene_voice_key(str(project.id), str(scene.id), extension)
        stored = await get_storage().put_bytes(key, result.data, result.mime_type)

        asset = await self._replace_asset(
            project_id=project.id,
            scene_id=scene.id,
            asset_type=AssetType.AUDIO,
            storage_key=stored.storage_key,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            duration=result.duration,
            provider=result.provider,
            prompt=text[:500],
            previous_asset_id=scene.audio_asset_id,
        )
        scene.audio_asset_id = asset.id

        # The scene length must match the narration, or the render either cuts
        # the voice off mid-sentence (scene too short) or holds a silent frame
        # (scene too long). A small tail is kept so speech does not end exactly
        # on the cut.
        spoken = round(result.duration + 0.35, 2)
        if abs(spoken - scene.duration) > 0.2:
            scene.duration = spoken

        attempt.status = GenerationStatus.COMPLETED
        attempt.asset_id = asset.id
        attempt.duration = result.duration
        # Record the voice that was ACTUALLY used, not the alias that was asked
        # for ("female"), so the history says km-KH-SreymomNeural and a result
        # can be reproduced later.
        attempt.voice = result.voice
        attempt.provider = result.provider

        # Re-time captions against the ACTUAL audio length.
        await self._write_captions(scene, scene.duration, replace=True)
        await self.session.commit()

        message = (
            "Silent placeholder audio (no TTS provider configured) - the video will have no speech."
            if result.is_placeholder else None
        )
        return MediaOutcome(asset, GenerationStatus.COMPLETED, result.provider, message)

    # ---------------------------------------------------------------- captions
    async def regenerate_captions(self, scene_id: uuid.UUID, owner_id: uuid.UUID) -> int:
        scene = await self._owned_scene(scene_id, owner_id)
        count = await self.captions.rebuild(scene)
        await self.session.commit()
        return count

    async def _write_captions(
        self, scene: Scene, duration: float, *, replace: bool = False
    ) -> int:
        # `replace` is kept for call-site readability; CaptionService always
        # rewrites, which is the only safe behaviour for derived data.
        del replace
        return await self.captions.rebuild(scene, duration)

    # ----------------------------------------------------------------- helpers
    async def _owned_scene(self, scene_id: uuid.UUID, owner_id: uuid.UUID) -> Scene:
        from app.services.scene_service import SceneService

        return await SceneService(self.session).get_owned(scene_id, owner_id)

    async def _replace_asset(
        self,
        *,
        project_id: uuid.UUID,
        scene_id: uuid.UUID,
        asset_type: AssetType,
        storage_key: str,
        mime_type: str,
        size_bytes: int,
        provider: str,
        prompt: str | None = None,
        duration: float | None = None,
        width: int | None = None,
        height: int | None = None,
        previous_asset_id: uuid.UUID | None = None,
    ) -> Asset:
        """Creates the Asset row, reusing the row when the key is unchanged.

        Storage keys are deterministic (one image per scene), so a regeneration
        overwrites the object. Reusing the row keeps `storage_key` unique and
        avoids orphaned records.
        """
        existing = await self.session.get(Asset, previous_asset_id) if previous_asset_id else None
        if existing is not None and existing.storage_key == storage_key:
            existing.mime_type = mime_type
            existing.size_bytes = size_bytes
            existing.duration = duration
            existing.width = width
            existing.height = height
            existing.provider = provider
            existing.prompt = prompt
            await self.session.flush()
            return existing

        asset = Asset(
            project_id=project_id,
            scene_id=scene_id,
            type=asset_type,
            source=AssetSource.GENERATED,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            duration=duration,
            width=width,
            height=height,
            provider=provider,
            prompt=prompt,
        )
        self.session.add(asset)
        await self.session.flush()
        return asset
