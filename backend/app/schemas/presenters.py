"""Model -> response-schema conversion.

WHY a separate module: several response fields are DERIVED, not stored -
pixel dimensions from the aspect ratio, a scene's `start_time` from the durations
of the scenes before it, media URLs from storage keys. Computing them in one
place keeps routes and services free of presentation logic.
"""

from app.models.project import Project
from app.models.scene import Scene
from app.schemas.project import ProjectResponse
from app.schemas.scene import CaptionResponse, SceneResponse
from app.services.storage.urls import public_url


def project_to_response(project: Project) -> ProjectResponse:
    width, height = project.dimensions
    thumbnail_key: str | None = None

    # Prefer an explicit thumbnail; otherwise fall back to the first scene image
    # so a freshly generated project still shows a picture on its card.
    for scene in project.scenes:
        if scene.image_asset is not None:
            thumbnail_key = scene.image_asset.storage_key
            break

    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        prompt=project.prompt,
        status=project.status,  # type: ignore[arg-type]
        language=project.language,
        aspect_ratio=project.aspect_ratio,
        style=project.style,
        tone=project.tone,
        audience=project.audience,
        voice=project.voice,
        target_duration=project.target_duration,
        fps=project.fps,
        width=width,
        height=height,
        duration=project.duration,
        scene_count=len(project.scenes),
        thumbnail_url=public_url(thumbnail_key),
        error_message=project.error_message,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def scene_to_response(scene: Scene, start_time: float = 0.0) -> SceneResponse:
    return SceneResponse(
        id=scene.id,
        project_id=scene.project_id,
        scene_number=scene.scene_number,
        narration=scene.narration,
        visual_prompt=scene.visual_prompt,
        on_screen_text=scene.on_screen_text,
        duration=scene.duration,
        start_time=round(start_time, 3),
        transition=scene.transition,
        background_color=scene.background_color,
        language=scene.language,
        settings=scene.settings or {},
        image_url=public_url(scene.image_asset.storage_key if scene.image_asset else None),
        audio_url=public_url(scene.audio_asset.storage_key if scene.audio_asset else None),
        video_url=public_url(scene.video_asset.storage_key if scene.video_asset else None),
        captions=[CaptionResponse.model_validate(c) for c in scene.captions],
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


def scenes_to_response(scenes: list[Scene]) -> list[SceneResponse]:
    """Converts a whole timeline, accumulating each scene's start time."""
    out: list[SceneResponse] = []
    cursor = 0.0
    for scene in sorted(scenes, key=lambda s: s.scene_number):
        out.append(scene_to_response(scene, cursor))
        cursor += scene.duration
    return out
