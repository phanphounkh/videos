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
from app.schemas.project import MusicSettings
from app.services.caption_service import speech_settings
from app.services.storage.urls import renderer_url

log = get_logger(__name__)


def _layers(settings: dict[str, Any]) -> list[dict[str, Any]]:
    """Editor overlay layers in the renderer's camelCase."""
    return [
        {
            "id": layer["id"],
            "type": layer["type"],
            "text": layer["text"],
            "x": layer["x"],
            "y": layer["y"],
            "fontSize": layer["font_size"],
            "rotation": layer["rotation"],
            "color": layer["color"],
            "background": layer["background"],
            "weight": layer["weight"],
            "animation": layer["animation"],
            "start": layer["start"],
            "end": layer["end"],
        }
        for layer in settings.get("layers") or []
    ]


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

        speech = speech_settings(scene) or {}

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
                # Real speech timing and loudness, when the voice was generated
                # from the current narration. Empty lists make the renderer fall
                # back to estimated karaoke timing and a generic talking loop.
                "words": [
                    {"text": text, "start": float(start), "end": float(end)}
                    for text, start, end in speech.get("words", [])
                ],
                "mouth": list(speech.get("mouth", [])),
                "mouthFps": int(speech.get("fps", 30)),
                # The story's emotional beat; null lets the renderer derive it
                # from the scene's position in the video.
                "mood": (scene.settings or {}).get("mood"),
                # Editor settings: overlays, sound levels, and where in the voice
                # and the uploaded clip this scene starts (after a split or trim).
                "layers": _layers(scene.settings or {}),
                "audioStart": float((scene.settings or {}).get("audio_start", 0)),
                "voiceVolume": float((scene.settings or {}).get("voice_volume", 1)),
                "clipVolume": float((scene.settings or {}).get("clip_volume", 0)),
                "trimStart": float((scene.settings or {}).get("trim_start", 0)),
                "mediaFit": (scene.settings or {}).get("media_fit", "cover"),
                "kenBurns": bool((scene.settings or {}).get("ken_burns", True)),
            }
        )

    music = MusicSettings.model_validate((project.settings or {}).get("music") or {})
    payload = {
        "project": {
            "width": width,
            "height": height,
            "fps": project.fps,
            "title": project.title,
            "language": project.language,
            "purpose": project.purpose,
            "presenter": project.presenter,
            "ctaText": project.cta_text,
            "music": music.enabled,
            # None plays the renderer's built-in bed.
            "musicUrl": (
                renderer_url(project.music_asset.storage_key) if project.music_asset else None
            ),
            "musicVolume": music.volume,
            "musicFadeIn": music.fade_in,
            "musicFadeOut": music.fade_out,
            "musicDuck": music.duck,
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
