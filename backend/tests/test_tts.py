"""TTS provider selection and voice routing.

No network: the Edge provider's synthesis call is patched out. What is tested is
the logic we own - voice resolution per language, duration measured from the
audio rather than estimated, and the fallback when a language is unsupported.
"""

import pytest

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.services.ai.speech import get_tts_provider
from app.services.ai.speech.edge_tts_provider import EdgeTTSProvider
from app.services.ai.speech.silent_tts import SilentTTSProvider


def test_khmer_routes_to_a_khmer_voice() -> None:
    provider = EdgeTTSProvider()
    assert provider._resolve_voice("km", "") == "km-KH-PisethNeural"
    assert provider._resolve_voice("km-KH", "") == "km-KH-PisethNeural"
    assert provider._resolve_voice("km", "female") == "km-KH-SreymomNeural"


def test_english_and_aliases() -> None:
    provider = EdgeTTSProvider()
    assert provider._resolve_voice("en", "") == "en-US-AriaNeural"
    assert provider._resolve_voice("en", "male") == "en-US-GuyNeural"


def test_an_explicit_voice_id_is_respected() -> None:
    provider = EdgeTTSProvider()
    assert provider._resolve_voice("km", "km-KH-SreymomNeural") == "km-KH-SreymomNeural"


def test_unknown_language_falls_back_to_a_real_voice() -> None:
    provider = EdgeTTSProvider()
    assert provider._resolve_voice("xx", "") == "en-US-AriaNeural"
    assert provider.supports_language("km")
    assert not provider.supports_language("xx")


async def test_empty_text_is_rejected() -> None:
    with pytest.raises(ProviderError) as exc:
        await EdgeTTSProvider().generate("   ", "en", "")
    assert exc.value.code == "TTS_EMPTY_TEXT"


async def test_duration_is_measured_from_the_audio_not_estimated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A guessed duration drifts captions out of sync, so it must be measured."""
    provider = EdgeTTSProvider()

    async def fake_synth(text: str, voice: str, rate: str, volume: str) -> bytes:
        return b"ID3-fake-mp3-bytes"

    async def fake_probe(data: bytes) -> float:
        return 7.42

    monkeypatch.setattr(provider, "_synthesize", fake_synth)
    monkeypatch.setattr("app.services.ai.speech.edge_tts_provider.probe_duration", fake_probe)

    result = await provider.generate("hello there", "en", "")
    assert result.duration == 7.42
    assert result.is_placeholder is False
    assert result.provider == "edge-tts"
    assert result.voice == "en-US-AriaNeural"


async def test_synthesis_failure_becomes_a_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = EdgeTTSProvider()

    async def boom(text: str, voice: str, rate: str, volume: str) -> bytes:
        raise RuntimeError("network down")

    monkeypatch.setattr(provider, "_synthesize", boom)
    monkeypatch.setattr("app.services.ai.speech.edge_tts_provider.asyncio.sleep", _no_sleep)

    with pytest.raises(ProviderError) as exc:
        await provider.generate("hello", "en", "")
    assert exc.value.code == "TTS_PROVIDER_ERROR"


async def _no_sleep(seconds: float) -> None:
    return None


def test_factory_honours_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()

    monkeypatch.setattr(settings, "tts_provider", "mock")
    assert isinstance(get_tts_provider("km"), SilentTTSProvider)

    monkeypatch.setattr(settings, "tts_provider", "edge")
    assert isinstance(get_tts_provider("km"), EdgeTTSProvider)
    # An unsupported language falls back to silence rather than wrong-language audio.
    assert isinstance(get_tts_provider("xx"), SilentTTSProvider)
