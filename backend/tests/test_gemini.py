"""Gemini story, voice and subtitle alignment - without any network call.

A fake HTTP transport stands in for the Gemini API, so these tests check the
exact requests we send and how every kind of answer is handled.
"""

import base64
import io
import json
import math
import shutil
import struct
import wave
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.schemas.generation import GeneratedScene, GeneratedScript
from app.services.ai import gemini as gemini_module
from app.services.ai.base import ScriptRequest
from app.services.ai.gemini import GeminiClient, rate_limit_wait, response_audio, response_text
from app.services.ai.llm import GeminiLLMProvider, OpenRouterLLMProvider, get_llm_provider
from app.services.ai.llm.gemini import gemini_schema, same_structure
from app.services.ai.speech import EdgeTTSProvider, GeminiTTSProvider, get_tts_provider
from app.services.ai.speech.gemini_aligner import validate_alignment
from app.services.ai.speech.timing import speech_units

KHMER = "តើឆ្មាអាចនិយាយបានទេ? រឿងនេះនឹងធ្វើឲ្យអ្នកភ្ញាក់ផ្អើល!"


@pytest.fixture
def gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-only-key")
    # Pacing is process-wide and real-time; tests must never wait on it.
    monkeypatch.setattr(get_settings(), "gemini_requests_per_minute", 0)


def _wav(seconds: float) -> bytes:
    """A 24 kHz mono tone, the shape Gemini TTS returns."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        frames = int(seconds * 24000)
        out.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / 24000)))
                for i in range(frames)
            )
        )
    return buffer.getvalue()


def _step(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"status": "completed", "steps": [{"type": "model_output", "content": list(blocks)}]}


def _client(handler: Callable[[dict[str, Any]], httpx.Response]) -> tuple[GeminiClient, list]:
    seen: list[dict[str, Any]] = []

    def route(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"headers": dict(request.headers), "url": str(request.url), "body": body})
        return handler(body)

    return GeminiClient(transport=httpx.MockTransport(route)), seen


# ---------------------------------------------------------------- client
def test_client_requires_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "gemini_api_key", "  ")
    with pytest.raises(ProviderError) as exc:
        GeminiClient()
    assert exc.value.code == "PROVIDER_NOT_CONFIGURED"


def test_response_parsing_reads_text_and_audio_blocks() -> None:
    payload = _step(
        {"type": "text", "text": '{"a":'},
        {"type": "text", "text": " 1}"},
        {"type": "audio", "data": base64.b64encode(b"RIFF").decode(), "mime_type": "audio/wav"},
    )
    assert response_text(payload) == '{"a": 1}'
    assert response_audio(payload) == (b"RIFF", "audio/wav")
    with pytest.raises(ProviderError):
        response_audio(_step({"type": "text", "text": "no audio"}))


async def test_client_sends_key_header_and_does_not_retry_bad_requests(gemini_key: None) -> None:
    client, seen = _client(lambda body: httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(ProviderError) as exc:
        await client.interact({"model": "m", "input": "x"})
    assert exc.value.code == "GEMINI_PROVIDER_ERROR"
    assert len(seen) == 1  # a 400 fails identically every time
    assert seen[0]["headers"]["x-goog-api-key"] == "test-only-key"
    assert seen[0]["url"].endswith("/v1beta/interactions")


async def test_failed_interaction_status_is_an_error(gemini_key: None) -> None:
    client, _ = _client(
        lambda body: httpx.Response(
            200, json={"status": "failed", "errors": [{"message": "quota"}]}
        )
    )
    with pytest.raises(ProviderError, match="quota"):
        await client.interact({"model": "m", "input": "x"})


def test_rate_limit_wait_follows_what_gemini_asks() -> None:
    real = httpx.Response(
        429,
        json={
            "error": {"message": "Rate limit exceeded (5 requests per minute). Please retry in 33s"}
        },
    )
    assert rate_limit_wait(real) == 34.0
    assert rate_limit_wait(httpx.Response(429, headers={"retry-after": "7"})) == 7.5
    assert rate_limit_wait(httpx.Response(429, text="slow down")) == 30.0


async def test_rate_limits_are_waited_out_without_using_retries(
    gemini_key: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(gemini_module.asyncio, "sleep", fake_sleep)
    answers = iter(
        [httpx.Response(429, text="Please retry in 12s")] * 5
        + [httpx.Response(200, json=_step({"type": "text", "text": "ok"}))]
    )
    client, seen = _client(lambda body: next(answers))
    assert response_text(await client.interact({"model": "m", "input": "x"})) == "ok"
    assert len(seen) == 6  # five 429s exceed MAX_ATTEMPTS, yet the call succeeds
    assert waits == [13.0] * 5


async def test_pacer_spaces_requests_per_model(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [1000.0]
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(gemini_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(gemini_module.asyncio, "sleep", fake_sleep)
    pacer = gemini_module._RequestPacer()
    for _ in range(3):
        await pacer.wait_turn("tts", 3)
    await pacer.wait_turn("other", 3)  # separate budget per model
    assert waits == []
    await pacer.wait_turn("tts", 3)  # the fourth within a minute waits for a slot
    assert len(waits) == 1 and 59 < waits[0] <= 60.5


# ------------------------------------------------------------- alignment
def test_khmer_units_follow_the_written_phrases() -> None:
    units = speech_units(KHMER, language="km")
    # Written phrases are kept; one longer than the unit limit is split on
    # cluster boundaries, never through a cluster.
    assert units[0] == "តើឆ្មាអាចនិយាយបានទេ?"
    assert len(units) == 3
    assert "".join(units[1:]) == "រឿងនេះនឹងធ្វើឲ្យអ្នកភ្ញាក់ផ្អើល!"
    assert all(len(unit) <= 24 for unit in units)


def test_valid_alignment_becomes_marks() -> None:
    marks = validate_alignment(
        ["a", "b", "c"],
        [
            {"index": 0, "start": 0.1, "end": 0.9},
            {"index": 1, "start": 0.8, "end": 1.6},
            {"index": 2, "start": 1.7, "end": 2.9},
        ],
        3.0,
    )
    assert marks is not None
    assert [(m.text, m.start, m.end) for m in marks] == [
        ("a", 0.1, 0.8),  # small overlap trimmed
        ("b", 0.8, 1.6),
        ("c", 1.7, 2.9),
    ]


@pytest.mark.parametrize(
    "items",
    [
        [{"index": 0, "start": 0.1, "end": 1.0}],  # a unit is missing
        [{"index": 0, "start": 1.5, "end": 2.0}, {"index": 1, "start": 0.2, "end": 0.6}],  # order
        [
            {"index": 0, "start": 0.0, "end": 0.2},
            {"index": 1, "start": 0.2, "end": 0.4},
        ],  # collapsed
        [
            {"index": 0, "start": 0.1, "end": 1.0},
            {"index": 1, "start": 9.0, "end": 9.5},
        ],  # too late
        [{"index": 0, "start": "soon", "end": 1.0}, {"index": 1, "start": 1, "end": 2}],  # garbage
    ],
)
def test_untrustworthy_alignment_is_rejected(items: list[dict[str, Any]]) -> None:
    assert validate_alignment(["a", "b"], items, 3.0) is None


# ------------------------------------------------------------------- TTS
def test_tts_request_reads_text_verbatim_with_direction_in_style(gemini_key: None) -> None:
    provider = GeminiTTSProvider(client=GeminiClient())
    body = provider.request_body(KHMER, "km", "female", "whispering, suspenseful")

    content = body["input"][0]["content"][0]
    assert body["model"] == get_settings().gemini_tts_model
    assert body["response_format"] == {"type": "audio"}
    assert body["generation_config"]["speech_config"] == [{"voice": "Kore"}]
    assert content["text"] == KHMER  # never mixed with directions
    style = content["annotations"][0]["style"]
    assert "Khmer" in style and "whispering, suspenseful" in style


def test_tts_voice_resolution(gemini_key: None) -> None:
    provider = GeminiTTSProvider(client=GeminiClient())
    assert provider.resolve_voice("male") == "Puck"
    assert provider.resolve_voice("charon") == "Charon"
    # Another provider's voice id falls back to the configured default.
    assert provider.resolve_voice("km-KH-PisethNeural") == get_settings().gemini_tts_voice


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
async def test_tts_returns_mp3_measured_duration_and_aligned_marks(gemini_key: None) -> None:
    wav = _wav(2.0)

    def handler(body: dict[str, Any]) -> httpx.Response:
        if body["model"] == get_settings().gemini_tts_model:
            audio = {
                "type": "audio",
                "data": base64.b64encode(wav).decode(),
                "mime_type": "audio/wav",
            }
            return httpx.Response(200, json=_step(audio))
        # The aligner: it must receive the audio and the exact units.
        assert body["input"][1]["type"] == "audio"
        assert "តើឆ្មាអាចនិយាយបានទេ?" in body["input"][0]["text"]
        sent = json.loads(body["input"][0]["text"].split("\n", 1)[1])
        units = {
            "units": [
                {
                    "index": u["index"],
                    "start": 0.05 + 0.6 * u["index"],
                    "end": 0.6 + 0.6 * u["index"],
                }
                for u in sent
            ]
        }
        return httpx.Response(200, json=_step({"type": "text", "text": json.dumps(units)}))

    client, seen = _client(handler)
    result = await GeminiTTSProvider(client=client).generate(KHMER, "km", "", style="excited")

    assert result.mime_type == "audio/mpeg" and result.data[:3] in (
        b"ID3",
        b"\xff\xf3",
        b"\xff\xfb",
    )
    assert result.duration == pytest.approx(2.0, abs=0.15)
    assert [m.text for m in result.marks] == speech_units(KHMER, language="km")
    assert result.provider == "gemini-tts" and result.voice == get_settings().gemini_tts_voice
    assert len(seen) == 2


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
async def test_bad_alignment_falls_back_to_audio_pauses(gemini_key: None) -> None:
    wav = _wav(1.5)

    def handler(body: dict[str, Any]) -> httpx.Response:
        if body["model"] == get_settings().gemini_tts_model:
            audio = {
                "type": "audio",
                "data": base64.b64encode(wav).decode(),
                "mime_type": "audio/wav",
            }
            return httpx.Response(200, json=_step(audio))
        return httpx.Response(200, json=_step({"type": "text", "text": '{"units": []}'}))

    client, seen = _client(handler)
    result = await GeminiTTSProvider(client=client).generate(KHMER, "km", "")
    # Timed from the audio instead: every unit, in order, inside the clip.
    assert [m.text for m in result.marks] == speech_units(KHMER, language="km")
    assert all(0 <= m.start < m.end <= result.duration for m in result.marks)
    assert len(seen) == 3  # one voice call, two alignment attempts


async def test_used_up_daily_quota_fails_fast_and_is_remembered(
    gemini_key: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gemini_module, "_exhausted_until", {})
    quota = httpx.Response(
        429,
        json={
            "error": {"message": "limit: 20 requests per day on Free Tier. Please retry in 6h35m3s"}
        },
        headers={"retry-after": "23703"},
    )
    client, seen = _client(lambda body: quota)
    with pytest.raises(ProviderError) as exc:
        await client.interact({"model": "daily", "input": "x"})
    assert exc.value.code == "GEMINI_QUOTA_EXHAUSTED"
    assert "6h" in exc.value.message
    # The next call for that model fails without touching the network...
    with pytest.raises(ProviderError):
        await client.interact({"model": "daily", "input": "x"})
    assert len(seen) == 1
    # ...while other models are unaffected.
    ok, _ = _client(lambda body: httpx.Response(200, json=_step({"type": "text", "text": "hi"})))
    assert response_text(await ok.interact({"model": "other", "input": "x"})) == "hi"


# ----------------------------------------------------------------- story
def _script(moods: list[str], narration: str = "តើឆ្មាអាចនិយាយបានទេ?") -> GeneratedScript:
    return GeneratedScript(
        title="ឆ្មា",
        language="km",
        scenes=[
            GeneratedScene(
                scene_number=i + 1,
                narration=narration,
                visual_prompt="a cat",
                duration=8,
                mood=mood,
                delivery="excited",
            )
            for i, mood in enumerate(moods)
        ],
    )


def test_story_schema_is_adapted_for_gemini(gemini_key: None) -> None:
    body = GeminiLLMProvider(client=GeminiClient()).draft_body(
        ScriptRequest(prompt="ពិធីបុណ្យចូលឆ្នាំខ្មែរ", duration=60, language="km", style="storytelling")
    )
    schema_text = json.dumps(body["response_format"]["schema"])
    assert "minLength" not in schema_text and '["string", "null"]' not in schema_text
    assert "minItems" not in schema_text and "maxItems" not in schema_text  # Gemini: HTTP 400
    scene = body["response_format"]["schema"]["properties"]["scenes"]["items"]
    assert {"mood", "delivery"} <= set(scene["required"])
    assert "ពិធីបុណ្យចូលឆ្នាំខ្មែរ" in body["input"]
    assert "one animated host" in body["system_instruction"].lower()


def test_gemini_schema_keeps_enums_and_nested_structure() -> None:
    adapted = gemini_schema({"type": ["string", "null"], "maxLength": 5, "enum": ["a"]})
    assert adapted == {"type": "string", "enum": ["a"]}


def test_review_may_only_change_wording() -> None:
    draft = _script(["hook", "twist", "payoff"])
    assert same_structure(draft, _script(["hook", "twist", "payoff"], narration="អូ! ឆ្មានិយាយបាន!"))
    assert not same_structure(draft, _script(["hook", "payoff"]))
    assert not same_structure(draft, _script(["hook", "climax", "payoff"]))


async def test_story_uses_reviewed_khmer_when_structure_is_kept(gemini_key: None) -> None:
    draft = _script(["hook", "rising", "payoff"], narration="ឆ្មា និយាយ 2 ដង")
    fixed = _script(["hook", "rising", "payoff"], narration="ឆ្មា និយាយ ពីរដង")
    answers = iter([draft, fixed])
    client, seen = _client(
        lambda body: httpx.Response(
            200, json=_step({"type": "text", "text": next(answers).model_dump_json()})
        )
    )
    script = await GeminiLLMProvider(client=client).generate_script(
        ScriptRequest(prompt="ឆ្មា", duration=24, language="km", style="storytelling")
    )
    assert script.scenes[0].narration == "ឆ្មា និយាយ ពីរដង"
    assert script.scenes[1].mood == "rising"
    assert len(seen) == 2


async def test_story_keeps_draft_when_review_breaks_structure(gemini_key: None) -> None:
    answers = iter([_script(["hook", "twist", "payoff"]), _script(["hook"])])
    client, _ = _client(
        lambda body: httpx.Response(
            200, json=_step({"type": "text", "text": next(answers).model_dump_json()})
        )
    )
    script = await GeminiLLMProvider(client=client).generate_script(
        ScriptRequest(prompt="ឆ្មា", duration=24, language="km", style="storytelling")
    )
    assert len(script.scenes) == 3


def test_unknown_mood_is_dropped_not_fatal() -> None:
    scene = GeneratedScene(
        scene_number=1,
        narration="x",
        visual_prompt="y",
        duration=5,
        mood="Sad",
        on_screen_text="  ",
    )
    assert scene.mood is None and scene.on_screen_text is None


# -------------------------------------------------------------- factories
def test_factories_fall_back_until_the_key_is_added(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai import speech

    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "tts_provider", "gemini")
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "openrouter_api_key", "test-only-key")
    speech._gemini_provider.cache_clear()
    get_llm_provider.cache_clear()
    try:
        assert isinstance(get_tts_provider("km"), EdgeTTSProvider)
        assert isinstance(get_llm_provider(), OpenRouterLLMProvider)

        get_llm_provider.cache_clear()
        monkeypatch.setattr(settings, "gemini_api_key", "test-only-key")
        assert isinstance(get_tts_provider("km"), GeminiTTSProvider)
        assert isinstance(get_llm_provider(), GeminiLLMProvider)
    finally:
        speech._gemini_provider.cache_clear()
        get_llm_provider.cache_clear()
