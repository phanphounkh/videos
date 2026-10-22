"""ffprobe-based duration measurement and the loudness envelope used for lip-sync.

This uses real FFmpeg (already required by the project) to generate a tone of a
known length, which is the only honest way to test that we measure rather than
guess.
"""

import asyncio
import shutil

import pytest

from app.services.media import loudness_envelope, probe_duration

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


async def _tone_then_silence() -> bytes:
    """One second of tone followed by one second of silence, as MP3."""
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=220:duration=1",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=1",
        "-filter_complex", "[0][1]concat=n=2:v=0:a=1",
        "-c:a", "libmp3lame", "-f", "mp3", "pipe:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    return stdout


async def test_envelope_tracks_loud_and_quiet_frames() -> None:
    envelope = await loudness_envelope(await _tone_then_silence(), fps=30)
    assert 55 <= len(envelope) <= 66  # ~2 s at 30 fps, plus encoder padding
    assert all(0 <= value <= 100 for value in envelope)
    assert min(envelope[5:25]) > 60
    assert max(envelope[40:55]) < 5


async def test_undecodable_audio_gives_an_empty_envelope() -> None:
    assert await loudness_envelope(b"not audio at all") == []
