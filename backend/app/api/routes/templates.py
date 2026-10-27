"""The template gallery."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import CurrentUser
from app.services.purposes import get_purpose
from app.services.templates import CATEGORIES, TEMPLATES, mood_of

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateResponse(BaseModel):
    key: str
    title: str
    category: str
    purpose: str
    aspect_ratio: str
    duration: int
    prompt: str
    presenter: bool
    # Served by the web app (static/templates/<key>.jpg).
    thumbnail_url: str
    # What the cover says and its colour mood: the web app redraws the cover live on hover.
    headline: str
    kicker: str
    mood: str


class TemplateList(BaseModel):
    categories: list[str]
    templates: list[TemplateResponse]


@router.get("", response_model=TemplateList)
async def list_templates(_: CurrentUser) -> TemplateList:
    return TemplateList(
        categories=list(CATEGORIES),
        templates=[
            TemplateResponse(
                key=t.key,
                title=t.title,
                category=t.category,
                purpose=t.purpose,
                aspect_ratio=t.aspect_ratio,
                duration=t.duration,
                prompt=t.prompt,
                presenter=get_purpose(t.purpose).presenter,
                thumbnail_url=f"/templates/{t.key}.jpg",
                headline=t.headline,
                kicker=get_purpose(t.purpose).label,
                mood=mood_of(i),
            )
            for i, t in enumerate(TEMPLATES)
        ],
    )
