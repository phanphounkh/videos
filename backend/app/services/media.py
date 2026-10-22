"""Media inspection helpers (FFmpeg/FFprobe).

WHY this exists: a TTS provider's own duration estimate is a guess, but caption
timings and scene lengths must match the audio EXACTLY, or narration drifts out
of sync and gets clipped at the scene boundary. So after synthesising audio we
measure the real file.

WHY a temp file and not a pipe: MP3 has no duration in a header - ffprobe
derives it by seeking/scanning, which it cannot do on a non-seekable stdin pipe.
Piping returns no duration at all, which silently falls back to the estimate and
produces exactly the drift this module exists to prevent.
"""

import asyncio
import json
import math
import os
import shutil
import tempfile
from array import array
from dataclasses import dataclass

from app.core.logging import get_logger

log = get_logger(__name__)


async def probe_duration(data: bytes, suffix: str = ".mp3") -> float | None:
    """Returns the duration of an audio/video buffer in seconds, or None."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        log.warning("ffprobe_missing")
        return None

    def _write_temp() -> str:
        handle, path = tempfile.mkstemp(suffix=suffix, prefix="avs-probe-")
        with os.fdopen(handle, "wb") as file:
            file.write(data)
        return path

    def _cleanup(path: str) -> None:
        if os.path.exists(path):
            os.unlink(path)

    path = await asyncio.to_thread(_write_temp)
    try:
        process = await asyncio.create_subprocess_exec(
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            log.warning("ffprobe_failed", returncode=process.returncode)
            return None

        try:
            duration = float(json.loads(stdout)["format"]["duration"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            log.warning("ffprobe_no_duration")
            return None
        return round(duration, 3) if duration > 0 else None
    finally:
        await asyncio.to_thread(_cleanup, path)


@dataclass(slots=True)
class MediaInfo:
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    has_audio: bool = False


# Codecs Chromium (the editor preview AND the renderer) decodes everywhere.
WEB_VIDEO_CODECS = {"h264", "vp8", "vp9", "av1"}


async def _run(*command: str, limit: float) -> tuple[int, bytes]:
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        async with asyncio.timeout(limit):
            stdout, _ = await process.communicate()
    except TimeoutError:
        process.kill()
        raise
    return process.returncode or 0, stdout


async def _with_temp_file(data: bytes, suffix: str, work):
    def _write() -> str:
        handle, path = tempfile.mkstemp(suffix=suffix, prefix="avs-media-")
        with os.fdopen(handle, "wb") as file:
            file.write(data)
        return path

    def _remove(path: str) -> None:
        if os.path.exists(path):
            os.unlink(path)

    path = await asyncio.to_thread(_write)
    try:
        return await work(path)
    finally:
        await asyncio.to_thread(_remove, path)


async def probe_media(data: bytes, suffix: str) -> MediaInfo:
    """Duration, size and video codec of an uploaded file. Fields are None when
    FFprobe is missing or cannot read the file."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        log.warning("ffprobe_missing")
        return MediaInfo()

    async def work(path: str) -> MediaInfo:
        try:
            code, stdout = await _run(
                ffprobe, "-v", "error", "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height",
                "-of", "json", path,
                limit=60,
            )
            if code != 0:
                return MediaInfo()
            parsed = json.loads(stdout)
        except (TimeoutError, json.JSONDecodeError):
            return MediaInfo()

        info = MediaInfo()
        try:
            duration = float(parsed.get("format", {}).get("duration"))
            info.duration = round(duration, 3) if duration > 0 else None
        except (TypeError, ValueError):
            pass
        for stream in parsed.get("streams", []):
            if stream.get("codec_type") == "video" and info.video_codec is None:
                info.video_codec = stream.get("codec_name")
                info.width = stream.get("width")
                info.height = stream.get("height")
            elif stream.get("codec_type") == "audio":
                info.has_audio = True
        return info

    return await _with_temp_file(data, suffix, work)


async def to_web_video(data: bytes, suffix: str) -> bytes | None:
    """Re-encodes a video to H.264/AAC MP4 so every browser and the renderer can
    play it (phones record HEVC, which Chromium often cannot). None on failure."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None

    def _read_and_remove(output: str) -> bytes | None:
        if not os.path.exists(output):
            return None
        try:
            with open(output, "rb") as file:
                return file.read()
        finally:
            os.unlink(output)

    async def work(path: str) -> bytes | None:
        output = path + ".web.mp4"
        try:
            code, _ = await _run(
                ffmpeg, "-v", "error", "-y", "-i", path,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart", output,
                limit=600,
            )
        except TimeoutError:
            code = -1
        result = await asyncio.to_thread(_read_and_remove, output)
        return result if code == 0 else None

    return await _with_temp_file(data, suffix, work)


# Envelope resolution. 30 values per second matches the default project fps; the
# renderer resamples for other frame rates.
ENVELOPE_FPS = 30
_ENVELOPE_SAMPLE_RATE = 8000


async def loudness_envelope(data: bytes, fps: int = ENVELOPE_FPS) -> list[int]:
    """Per-frame loudness of an audio buffer, scaled 0-100.

    WHY: the presenter's mouth, head and gestures follow how loud the voice is
    at each frame. Doing it here, once, keeps the renderer a pure function of
    its payload, and lets the editor preview show the same lip-sync without
    decoding audio in the browser.

    Returns an empty list when FFmpeg is missing or cannot decode the audio;
    the renderer then falls back to a generic talking animation.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None or not data:
        return []

    process = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-v",
        "error",
        "-i",
        "pipe:0",
        "-ac",
        "1",
        "-ar",
        str(_ENVELOPE_SAMPLE_RATE),
        "-f",
        "s16le",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    pcm, _ = await process.communicate(data)
    if process.returncode != 0 or len(pcm) < 2:
        log.warning("loudness_envelope_failed", returncode=process.returncode)
        return []

    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    window = _ENVELOPE_SAMPLE_RATE / fps
    frames = math.ceil(len(samples) / window)
    rms: list[float] = []
    for index in range(frames):
        chunk = samples[int(index * window) : int((index + 1) * window)]
        if not chunk:
            rms.append(0.0)
            continue
        rms.append(math.sqrt(sum(s * s for s in chunk) / len(chunk)))

    # Normalise against a loud-but-typical level, not the single loudest frame,
    # so one plosive does not make the rest of the scene look mumbled.
    ranked = sorted(rms)
    reference = ranked[int(len(ranked) * 0.95)] if ranked else 0.0
    if reference <= 0:
        return [0] * len(rms)
    return [min(100, round(100 * value / reference)) for value in rms]


async def to_mp3(data: bytes, mime_type: str, *, sample_rate: int = 24000) -> bytes:
    """Transcodes provider audio (WAV, or raw 16-bit PCM) to MP3.

    WHY: every voice in the system is stored as MP3, whichever provider made
    it, so storage keys, the browser player and the renderer never branch on
    format. Raw PCM ("audio/l16") has no header, so its layout is passed in.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode audio")

    raw_pcm = "l16" in mime_type.lower() or "pcm" in mime_type.lower()
    source = ["-f", "s16le", "-ar", str(sample_rate), "-ac", "1"] if raw_pcm else []
    process = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-v",
        "error",
        *source,
        "-i",
        "pipe:0",
        "-ac",
        "1",
        "-ar",
        "24000",
        "-b:a",
        "96k",
        "-f",
        "mp3",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate(data)
    if process.returncode != 0 or not out:
        raise RuntimeError(f"ffmpeg could not encode audio: {err.decode(errors='replace')[:200]}")
    return out
