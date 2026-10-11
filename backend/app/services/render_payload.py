"""Builds the normalised composition payload handed to the renderer.

RULE (project requirement #32): the renderer must not query the database. It
receives one self-contained JSON document describing the whole video - sizes,
fps, every scene, media URLs, captions - and is a pure function of it.

Media URLs must be reachable FROM THE RENDERER PROCESS. That is why they are
built from `S3_PUBLIC_BASE_URL` rather than the internal endpoint.
"""

from typing import Any

from app.core.logging import get_logger
from app.models.project import Project
from app.services.storage.urls import renderer_url

log = get_logger(__name__)


def build_composition_payload(project: Project) -> dict[str, Any]:
    width, height = project.dimensions
    scenes: list[dict[str, Any]] = []

    for scene in sorted(project.scenes, key=lambda s: s.scene_number):
        # renderer_url, NOT public_url: headless Chromium fetches these from
        # inside the worker container.
        visual_url = renderer_url(scene.image_asset.storage_key) if scene.image_asset else None
        visual_type = "image" if scene.image_asset else None
        # A video asset takes precedence over a still image when present.
        if scene.video_asset is not None:
            visual_url = renderer_url(scene.video_asset.storage_key)
            visual_type = "video"

        scenes.append(
            {
                "id": str(scene.id),
                "sceneNumber": scene.scene_number,
                "duration": float(scene.duration),
                "visualUrl": visual_url,
                "visualType": visual_type,
                "audioUrl": (
                    renderer_url(scene.audio_asset.storage_key) if scene.audio_asset else None
                ),
                "onScreenText": scene.on_screen_text,
                "narration": scene.narration,
                "captions": [
                    {
                        "text": caption.text,
                        "start": float(caption.start_time),
                        "end": float(caption.end_time),
                    }
                    for caption in sorted(scene.captions, key=lambda c: c.start_time)
                ],
                "transition": scene.transition,
                "backgroundColor": scene.background_color,
            }
        )

    payload = {
        "project": {
            "width": width,
            "height": height,
            "fps": project.fps,
            "title": project.title,
            "language": project.language,
        },
        "scenes": scenes,
    }
    log.info(
        "render_payload_built",
        project_id=str(project.id),
        scenes=len(scenes),
        duration=sum(s["duration"] for s in scenes),
    )
    return payload
