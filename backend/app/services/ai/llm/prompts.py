"""Prompt construction for script generation.

Kept out of the provider so the wording can be tuned without touching HTTP code,
and so the same prompt can be reused by a different provider.
"""

import json

SYSTEM_PROMPT = """You are a professional short-form video scriptwriter.

You reply with ONE JSON object and nothing else. No prose, no explanation, no
markdown code fences.

Schema:
{
  "title": string,
  "description": string,
  "language": string (BCP-47, e.g. "en" or "km"),
  "estimated_duration": number (seconds),
  "scenes": [
    {
      "scene_number": integer starting at 1,
      "narration": string - what the narrator says, in the target language,
      "visual_prompt": string - ENGLISH description of the image to generate,
      "on_screen_text": string - a SHORT title card (<= 8 words), target language,
      "duration": number - seconds for this scene,
      "transition": one of "none" | "fade" | "slide"
    }
  ]
}

Rules:
- The sum of scene durations must be within 10% of the requested duration.
- Narration must be natural spoken language, not bullet points.
- visual_prompt is ALWAYS in English (image models are trained on English) and
  must describe a concrete, filmable image - no text rendering requests.
- Narration and on_screen_text use the requested language exactly.
- For Khmer (km), write proper Khmer script, never transliteration.
"""


def build_user_prompt(
    *,
    prompt: str,
    duration: int,
    language: str,
    style: str,
    tone: str | None,
    audience: str | None,
) -> str:
    # ~12 narrated words per 5 seconds; 6-8s per scene reads well and keeps
    # image counts (and therefore cost) sane.
    scene_count = max(3, min(12, round(duration / 7)))
    spec = {
        "request": prompt,
        "target_duration_seconds": duration,
        "language": language,
        "style": style,
        "tone": tone or "clear and friendly",
        "audience": audience or "general audience",
        "target_scene_count": scene_count,
        "seconds_per_scene": round(duration / scene_count, 1),
    }
    return (
        "Write a video script for this request.\n\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
        + "\n\nReturn only the JSON object."
    )
