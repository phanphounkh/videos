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
import os
import shutil
import tempfile

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
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
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
