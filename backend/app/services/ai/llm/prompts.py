"""Prompt and structured-output contract for generated video scripts."""

import json

from app.services.purposes import get_purpose

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
                    "mood": {
                        "type": "string",
                        "enum": ["hook", "setup", "rising", "twist", "climax", "payoff"],
                    },
                    "delivery": {"type": "string", "maxLength": 120},
                },
                "required": [
                    "scene_number",
                    "narration",
                    "visual_prompt",
                    "on_screen_text",
                    "duration",
                    "transition",
                    "mood",
                    "delivery",
                ],
            },
        },
    },
    "required": ["title", "description", "language", "estimated_duration", "scenes"],
}


_BASE_PROMPT = """You are an expert short-video scriptwriter. You write scripts that are
read aloud by a text-to-speech voice, shown as subtitles, and cut into scenes.

Return one JSON object matching the supplied schema and nothing else.

{purpose_guide}

How the video is made (write FOR this):
{presentation}
- mood is the beat of the scene and drives colours and energy: hook (attention-
  grabbing), setup (friendly, explaining), rising (building), twist (surprising),
  climax (intense), payoff (satisfying). Scene 1 is hook and the last scene is
  payoff; choose the rest by what the scene actually does, not by position.
  Informational videos mostly use setup and rising between the hook and payoff.
- delivery is a short English voice direction for that scene, at most 8 words,
  e.g. "excited and fast", "calm and reassuring", "warm and slow, smiling".
- visual_prompt becomes the picture for the scene.

General requirements:
- Follow the user's prompt faithfully and keep its subject. Never substitute
  another topic.
- Every scene must add something new. Never repeat narration, never use generic
  filler, never pad to reach the duration.
- Write vivid spoken narration with concrete details and conversational rhythm.
  Short and varied sentences are better than formal exposition.
- Never invent facts, numbers, quotes or claims the user did not provide unless
  they are well-established. Do not present fiction as fact.

{language_rules}

Scene requirements:
- narration is the exact speech for that scene. Size it to the duration: Khmer is
  spoken at about twelve Khmer characters per second, English at about two and a
  half words per second.
- on_screen_text is one short phrase that pops up as a sticker (the limit is in
  the purpose notes above; never more than 5 words): the hook, key point, feature,
  reveal or payoff. Not a heading.
- visual_prompt is an English description of the SAME moment: subject, setting,
  emotion and lighting. No typography, captions, logos or watermarks.
- The sum of scene durations must closely match the requested duration.
- The title should be specific and engaging without making a false promise.
"""

_PRESENTER_ON = """- One animated host is on screen for the whole video and speaks every line to
  camera in one voice. Nobody else appears or speaks.
- So narration is the host talking to the viewer: personal, lively, with the
  occasional direct question. The host's face, gestures and colours follow mood.
- visual_prompt becomes the background art behind the host."""

_PRESENTER_OFF = """- There is no on-screen host. The narration is a voice-over played over the
  scene's picture, so write it as a confident narrator speaking to the viewer.
- Narration must work without seeing a person: describe, show and explain.
- visual_prompt is the full-screen picture the viewer watches, so make it concrete
  and visually clear."""

_KHMER_RULES = """Khmer requirements (narration is read aloud by a voice and shown as subtitles):
- When language is km, write title, description, narration, and on_screen_text in
  natural modern Khmer script with correct standard spelling. Never transliterate
  Khmer using Latin letters.
- Write how a charismatic Khmer creator actually talks, not a stiff word-for-word
  translation, and not overly formal literary or royal vocabulary.
- Write numbers, dates, times and amounts as Khmer words (ថ្ងៃទីដប់បួន ខែមេសា, not
  14/4). No digits, emoji, hashtags, symbols, abbreviations or brackets in narration.
- Keep English words out of Khmer narration except established proper names and
  product names.
- Separate phrases with single spaces, as natural Khmer writing does, about every
  three to six words; subtitles break on those spaces. End sentences with ។ ? or !
  so the voice pauses in the right places."""

_SPOKEN_RULES = """Spoken-language requirements:
- Write title, description, narration and on_screen_text in the requested language.
- Write numbers, dates and amounts the way they are spoken. No emoji, hashtags,
  symbols or brackets in narration, so the voice reads it cleanly.
- End sentences with punctuation so the voice pauses in the right places."""


def system_prompt(purpose: str = "story", presenter: bool = True, language: str = "") -> str:
    """The system prompt for one purpose, with or without an on-screen host.

    Khmer and general spoken-language rules are both included unless `language`
    says which one applies, so a model that is told the language in the user
    message always has the right rules.
    """
    template = get_purpose(purpose)
    if language.lower().startswith("km"):
        rules = _KHMER_RULES
    elif language:
        rules = _SPOKEN_RULES
    else:
        rules = _SPOKEN_RULES + "\n\n" + _KHMER_RULES
    return _BASE_PROMPT.format(
        purpose_guide=template.guide,
        presentation=_PRESENTER_ON if presenter else _PRESENTER_OFF,
        language_rules=rules,
    )


# Back-compat name: the default (story, with host) prompt.
SYSTEM_PROMPT = system_prompt("story", True)


def build_user_prompt(
    *,
    prompt: str,
    duration: int,
    language: str,
    style: str,
    tone: str | None,
    audience: str | None,
    purpose: str = "story",
    presenter: bool = True,
) -> str:
    template = get_purpose(purpose)
    # Scene length is a trade-off per purpose: long enough to land one idea, short
    # enough that the picture, sticker and transition keep changing.
    scene_count = max(3, min(30, round(duration / template.scene_seconds)))
    spec = {
        "original_user_prompt": prompt,
        "video_purpose": template.label,
        "target_duration_seconds": duration,
        "spoken_language": language,
        "has_on_screen_host": presenter,
        "style": style,
        "tone": tone or template.tone,
        "audience": audience or template.audience,
        "target_scene_count": scene_count,
        "average_seconds_per_scene": round(duration / scene_count, 1),
        "non_negotiable": [
            "follow the original prompt",
            "follow the purpose notes in the system prompt",
            "no invented facts, numbers, quotes or claims",
            "no repeated scene purpose",
            "narration written for speech: numbers as words, no symbols",
        ],
    }
    return (
        "Create the complete video script described below. Treat original_user_prompt as the "
        "source of truth and do not replace its topic.\n\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
        + "\n\nReturn only the schema-compliant JSON object."
    )
