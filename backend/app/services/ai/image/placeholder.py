"""Placeholder image generator - MOCK, no AI involved.

It draws a real PNG: a deterministic gradient derived from the prompt hash, plus
the prompt text wrapped onto the image. Why bother drawing something real instead
of returning a 1x1 pixel?

  - the renderer, the browser and FFmpeg all receive genuine image bytes of the
    correct dimensions, so nothing downstream is faked;
  - every scene looks different, which makes the editor and timeline readable;
  - Khmer text is drawn with a Khmer font, which proves the font chain works.

Replace it by setting IMAGE_PROVIDER to a real provider.
"""

import asyncio
import hashlib
import io
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.logging import get_logger
from app.services.ai.base import ImageProvider, ImageResult

log = get_logger(__name__)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
KHMER_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansKhmer-Bold.ttf",
    "/usr/share/fonts/khmeros/KhmerOS.ttf",
]


def _load_font(size: int, khmer: bool = False) -> ImageFont.FreeTypeFont:
    for candidate in (KHMER_FONT_CANDIDATES if khmer else []) + FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    # Last resort: PIL's built-in bitmap font (no Khmer glyphs, but never crashes).
    return ImageFont.load_default(size)


def _palette(seed: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    top = (40 + digest[0] % 90, 40 + digest[1] % 90, 70 + digest[2] % 120)
    bottom = (10 + digest[3] % 40, 10 + digest[4] % 40, 20 + digest[5] % 60)
    return top, bottom


def _render_png(prompt: str, width: int, height: int) -> bytes:
    top, bottom = _palette(prompt)
    image = Image.new("RGB", (width, height), bottom)
    draw = ImageDraw.Draw(image)

    # Vertical gradient, one horizontal line at a time.
    for y in range(height):
        ratio = y / max(height - 1, 1)
        draw.line(
            [(0, y), (width, y)],
            fill=(
                int(top[0] + (bottom[0] - top[0]) * ratio),
                int(top[1] + (bottom[1] - top[1]) * ratio),
                int(top[2] + (bottom[2] - top[2]) * ratio),
            ),
        )

    # Geometric accent so scenes are visually distinguishable at a glance.
    digest = hashlib.sha256(prompt.encode("utf-8")).digest()
    radius = int(min(width, height) * (0.18 + (digest[6] % 20) / 100))
    cx = int(width * (0.2 + (digest[7] % 60) / 100))
    cy = int(height * (0.2 + (digest[8] % 60) / 100))
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(255, 255, 255, 40),
        width=max(2, radius // 24),
    )

    # The prompt is drawn small and dim near the top: the renderer puts the
    # scene title in the middle and captions at the bottom, so a big centred
    # block of prompt text would collide with both.
    is_khmer = any("\u1780" <= ch <= "\u17ff" for ch in prompt)
    font = _load_font(max(14, width // 70), khmer=is_khmer)
    wrapped = textwrap.fill(prompt[:160], width=60)

    draw.multiline_text(
        (width // 2, int(height * 0.12)),
        wrapped,
        font=font,
        fill=(205, 208, 225),
        anchor="ma",
        align="center",
        spacing=8,
    )
    label_font = _load_font(max(12, width // 90))
    draw.text(
        (width // 2, height - max(18, height // 28)),
        "placeholder image - no AI image provider configured",
        font=label_font,
        fill=(170, 172, 190),
        anchor="mm",
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


class PlaceholderImageProvider(ImageProvider):
    name = "placeholder"

    async def generate_image(
        self, prompt: str, width: int, height: int, *, style: str | None = None
    ) -> ImageResult:
        seed = f"{prompt}|{style or ''}"
        # Pillow is CPU-bound: run it off the event loop.
        data = await asyncio.to_thread(_render_png, seed, width, height)
        log.info(
            "image_generation_completed",
            provider=self.name,
            is_mock=True,
            width=width,
            height=height,
            bytes=len(data),
        )
        return ImageResult(
            data=data,
            mime_type="image/png",
            width=width,
            height=height,
            provider=self.name,
            is_placeholder=True,
        )
