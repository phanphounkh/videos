"""ffprobe-based duration measurement.

This uses real FFmpeg (already required by the project) to generate a tone of a
known length, which is the only honest way to test that we measure rather than
guess.
"""

import asyncio
import shutil

import pytest

from app.services.media import probe_duration

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


async def _tone(seconds: float) -> bytes:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", f"{seconds}", "-c:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", "pipe:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    return stdout


async def test_duration_is_measured_from_real_mp3_bytes() -> None:
    """Regression: piping MP3 to ffprobe yields NO duration (not seekable), so
    the implementation must write a temp file. Before that fix this returned
    None and callers silently fell back to an estimate."""
    data = await _tone(3.0)
    assert data

    measured = await probe_duration(data)
    assert measured is not None
    assert measured == pytest.approx(3.0, abs=0.15)


async def test_garbage_bytes_return_none() -> None:
    assert await probe_duration(b"this is not audio at all") is None
