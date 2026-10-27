"""Draws the gallery thumbnails once, with the renderer, into the web app's static folder.

    cd backend && uv run python scripts/render_template_thumbnails.py

The files (frontend/static/templates/<key>.jpg) are small and committed, so the gallery
shows real pictures without rendering anything at request time. Re-run it after changing
the templates or the thumbnail look.
"""

import asyncio
import sys
from pathlib import Path

from app.services.purposes import get_purpose
from app.services.templates import TEMPLATES, mood_of
from app.services.thumbnail_service import SHORT_SIDE, _render

OUT = Path(__file__).resolve().parents[2] / "frontend" / "static" / "templates"
RATIOS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1)}


def payload(template, index: int) -> dict:
    purpose = get_purpose(template.purpose)
    w, h = RATIOS[template.aspect_ratio]
    scale = SHORT_SIDE / min(w, h)
    return {
        "project": {
            "width": round(w * scale),
            "height": round(h * scale),
            "fps": 30,
            "title": template.title,
            "language": "en",
            "purpose": template.purpose,
            # The animated host on every cover: it is what makes a Sorya video recognisable.
            "presenter": True,
            "ctaText": purpose.cta_text,
        },
        "headline": template.headline,
        "kicker": purpose.label,
        "imageUrl": None,
        "mood": mood_of(index),
        "cta": None,
    }


async def main(only: set[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    failed = 0
    for index, template in enumerate(TEMPLATES):
        if only and template.key not in only:
            continue
        try:
            data = await _render(payload(template, index))
        except Exception as exc:  # noqa: BLE001 - report and carry on with the rest
            print(f"FAILED {template.key}: {exc}", file=sys.stderr)
            failed += 1
            continue
        (OUT / f"{template.key}.jpg").write_bytes(data)
        print(f"ok {template.key} ({len(data) // 1024} KB)")
    return failed


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(set(sys.argv[1:]))))
