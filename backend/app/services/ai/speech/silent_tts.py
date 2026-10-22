"""Silent TTS provider - MOCK, there is NO speech in the output.

It produces a real, valid MP3 of exactly the estimated narration duration, using
FFmpeg's `anullsrc` (digital silence). Be clear about what this is:

  IMPLEMENTED: real audio file, correct duration, correct container/codec, stored
               in object storage, timed against captions, muxed by the renderer.
  NOT IMPLEMENTED: actual speech. The video will be silent.

Why do this at all instead of skipping audio? Because every other part of the
pipeline - scene timing, caption alignment, FFmpeg audio muxing, the editor's
voice track - depends on an audio asset existing with a known duration. Wiring a
real provider later is then a drop-in change rather than new plumbing.

Set TTS_PROVIDER=elevenlabs (or add your own class) for real narration.
"""

import asyncio
import shutil

from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.services.ai.base import AudioResult, TTSProvider
from app.services.ai.speech.timing import estimate_duration

log = get_logger(__name__)


class SilentTTSProvider(TTSProvider):
    name = "mock-silence"

    def supports_language(self, language: str) -> bool:
        return True  # silence is language-agnostic

    async def generate(
        self, text: str, language: str, voice: str, *, style: str | None = None
    ) -> AudioResult:
        duration = estimate_duration(text, language=language)
        data = await self._encode_silence(duration)
        log.info(
            "voice_generation_completed",
            provider=self.name,
            is_mock=True,
            language=language,
            duration=duration,
            bytes=len(data),
        )
        return AudioResult(
            data=data,
            mime_type="audio/mpeg",
            duration=duration,
            provider=self.name,
            voice=voice or "none",
            is_placeholder=True,
        )

    @staticmethod
    async def _encode_silence(duration: float) -> bytes:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise ProviderError(
                "ffmpeg is not installed, so audio cannot be produced.",
                code="FFMPEG_NOT_FOUND",
            )

        process = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=44100",
            "-t",
            f"{duration:.3f}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "64k",
            "-f",
            "mp3",
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0 or not stdout:
            raise ProviderError(
                f"ffmpeg failed to encode audio: {stderr.decode()[:300]}",
                code="TTS_PROVIDER_ERROR",
            )
        return stdout
