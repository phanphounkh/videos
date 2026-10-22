"""The catalogue of video purposes the create form is built from."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.purposes import PURPOSES

router = APIRouter(prefix="/purposes", tags=["purposes"])


class PurposeResponse(BaseModel):
    key: str
    label: str
    description: str
    aspect_ratio: str
    duration: int
    style: str
    tone: str
    audience: str
    presenter: bool
    cta_text: str | None
    example_prompt: str


@router.get("", response_model=list[PurposeResponse])
async def list_purposes() -> list[PurposeResponse]:
    """Every purpose with the defaults the create form should preselect."""
    return [
        PurposeResponse(
            key=str(t.key),
            label=t.label,
            description=t.description,
            aspect_ratio=str(t.aspect_ratio),
            duration=t.duration,
            style=str(t.style),
            tone=t.tone,
            audience=t.audience,
            presenter=t.presenter,
            cta_text=t.cta_text,
            example_prompt=t.example_prompt,
        )
        for t in PURPOSES.values()
    ]
