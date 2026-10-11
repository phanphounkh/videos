"""Prompt and structured-output contract for social entertainment stories."""

import json

SCRIPT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 300},
        "description": {"type": "string", "maxLength": 5000},
        "language": {"type": "string", "maxLength": 16},
        "estimated_duration": {"type": "number", "minimum": 0},
        "scenes": {
            "type": "array",
            "minItems": 3,
            "maxItems": 40,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scene_number": {"type": "integer", "minimum": 1},
                    "narration": {"type": "string", "minLength": 1, "maxLength": 5000},
                    "visual_prompt": {"type": "string", "minLength": 1, "maxLength": 2000},
                    "on_screen_text": {"type": ["string", "null"], "maxLength": 500},
                    "duration": {"type": "number", "minimum": 1, "maximum": 60},
                    "transition": {"type": "string", "enum": ["none", "fade", "slide"]},
                },
                "required": [
                    "scene_number",
                    "narration",
                    "visual_prompt",
                    "on_screen_text",
                    "duration",
                    "transition",
                ],
            },
        },
    },
    "required": ["title", "description", "language", "estimated_duration", "scenes"],
}


SYSTEM_PROMPT = """You are an expert Khmer entertainment writer for TikTok,
Facebook Reels, and YouTube Shorts. Turn the user's exact idea into one complete,
emotionally engaging animated story—not a lesson, explainer, or list.

Return one JSON object matching the supplied schema and nothing else.

Story requirements:
- Follow the user's prompt faithfully. Preserve its subject, characters, setting,
  genre, and requested events. Never substitute neural networks or another topic.
- Build ONE continuous story. Every scene must cause or motivate the next scene.
- Open on action, surprise, danger, curiosity, or a provocative line in the first
  two seconds. Never begin with a greeting, channel introduction, or definition.
- Use this arc across the whole timeline: hook, character desire and setup,
  rising complications, a meaningful twist, climax, satisfying emotional or funny
  payoff, then a brief natural question that invites comments.
- Every scene must introduce a new action, discovery, decision, consequence, or
  emotional change. Never repeat narration, summaries, or generic phase templates.
- Write vivid spoken narration with concrete details and conversational rhythm.
  Short and varied sentences are better than formal exposition.
- Keep claims responsible. Do not fabricate real news or present fiction as fact.

Khmer requirements:
- When language is km, write title, description, narration, and on_screen_text in
  natural modern Khmer script. Never transliterate Khmer using Latin letters.
- Avoid stiff word-for-word translation. Write how a charismatic Khmer creator
  would actually tell the story aloud.
- Proper names may remain in their established spelling, but all connective speech
  must be Khmer.

Scene requirements:
- narration is the exact speech for that scene and must fill its duration naturally.
- on_screen_text is one punchy important phrase, maximum 6 words. It appears briefly,
  so use it only for the hook, reveal, decision, twist, or payoff—not a lesson heading.
- visual_prompt is an English animation-shot description of the SAME story moment,
  with character continuity, camera framing, emotion, lighting, and action. Do not
  request typography or captions.
- The sum of scene durations must closely match the requested duration.
- The title should be curiosity-driven without making a false promise.
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
    # Longer story beats give each scene enough time to establish action and
    # consequence without turning the video into a rapid list of disconnected cards.
    scene_count = max(4, min(14, round(duration / 12)))
    spec = {
        "original_user_prompt": prompt,
        "target_duration_seconds": duration,
        "spoken_language": language,
        "format": "animated social entertainment story",
        "distribution": ["Facebook Reels", "YouTube Shorts", "TikTok"],
        "style": style,
        "tone": tone or "funny, emotional, and fast-paced",
        "audience": audience or "Khmer social media viewers",
        "target_scene_count": scene_count,
        "average_seconds_per_scene": round(duration / scene_count, 1),
        "non_negotiable": [
            "follow the original prompt",
            "one connected story",
            "no educational template",
            "no repeated scene purpose",
            "strong payoff",
        ],
    }
    return (
        "Create the complete story described below. Treat original_user_prompt as the source of "
        "truth and do not replace its topic.\n\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
        + "\n\nReturn only the schema-compliant JSON object."
    )
