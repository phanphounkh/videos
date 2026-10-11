"""Placeholder image generator - MOCK, no AI involved.

It draws a real PNG: a deterministic gradient and educational diagram derived
from the prompt hash. Why bother drawing something real instead of returning a
1x1 pixel?

  - the renderer, the browser and FFmpeg all receive genuine image bytes of the
    correct dimensions, so nothing downstream is faked;
  - every scene looks different, which makes the editor and timeline readable;
  - the neutral diagram works for every narration language without rendering
    provider prompts or placeholder labels into the lesson.

Replace it by setting IMAGE_PROVIDER to a real provider.
"""

import asyncio
import hashlib
import io
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

    # A deterministic educational diagram. It reads like lesson material when
    # placed on the studio board instead of looking like a generic placeholder.
    digest = hashlib.sha256(prompt.encode("utf-8")).digest()
    grid = max(48, width // 20)
    for x in range(0, width, grid):
        draw.line([(x, 0), (x, height)], fill=(45, 58, 89), width=1)
    for y in range(0, height, grid):
        draw.line([(0, y), (width, y)], fill=(45, 58, 89), width=1)

    layers = [0.2, 0.5, 0.8]
    nodes: list[tuple[int, int]] = []
    for layer_index, x_ratio in enumerate(layers):
        count = 3 if layer_index != 1 else 4
        for index in range(count):
            x = int(width * x_ratio)
            y = int(height * (0.24 + index * (0.52 / max(count - 1, 1))))
            nodes.append((x, y))

    first, middle, last = nodes[:3], nodes[3:7], nodes[7:]
    for left_layer, right_layer in ((first, middle), (middle, last)):
        for left in left_layer:
            for right in right_layer:
                if (left[1] + right[1] + digest[6]) % 3:
                    draw.line([left, right], fill=(96, 165, 250), width=max(2, width // 500))

    radius = max(10, min(width, height) // 42)
    for index, (x, y) in enumerate(nodes):
        color = (251, 191, 36) if index in {3, 5, 8} else (226, 232, 240)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color,
                     outline=(15, 23, 42), width=max(2, radius // 5))

    badge_font = _load_font(max(14, width // 65))
    draw.rounded_rectangle(
        [int(width * 0.05), int(height * 0.06), int(width * 0.29), int(height * 0.13)],
        radius=max(8, width // 100), fill=(15, 23, 42), outline=(245, 158, 11),
        width=max(2, width // 600),
    )
    draw.text(
        (int(width * 0.17), int(height * 0.095)), "LESSON VISUAL", font=badge_font,
        fill=(251, 191, 36), anchor="mm",
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
