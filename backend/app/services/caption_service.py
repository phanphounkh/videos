"""Caption building, shared by the scene editor and the generation pipeline.

WHY its own module: captions are derived data - whenever narration, duration or
language changes they must be rebuilt. One implementation means the editor and
the AI pipeline can never disagree about segmentation or timing.

IMPLEMENTATION NOTE: this deliberately uses an explicit DELETE statement and
`session.add()` instead of assigning to `scene.captions`. Assigning to a
relationship collection makes SQLAlchemy load the old collection first, and if
it is not already loaded that lazy load happens outside the async greenlet
context and raises MissingGreenlet. The collection is expired afterwards so the
next read returns the new rows.
"""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caption import Caption
from app.models.scene import Scene
from app.services.ai.speech import distribute_timings, split_into_segments


class CaptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def rebuild(self, scene: Scene, duration: float | None = None) -> int:
        """Replaces a scene's captions. Returns how many segments were written."""
        await self.session.execute(delete(Caption).where(Caption.scene_id == scene.id))

        language = scene.language or "en"
        total = duration if duration is not None else scene.duration
        segments = split_into_segments(scene.narration, language=language)
        timings = distribute_timings(segments, total, language=language)

        for index, (text, start, end) in enumerate(timings):
            self.session.add(
                Caption(
                    scene_id=scene.id,
                    segment_index=index,
                    text=text,
                    start_time=start,
                    end_time=end,
                    language=language,
                )
            )

        await self.session.flush()
        # The in-memory collection is now stale (rows were deleted behind the
        # ORM's back); expire it so the next access re-reads from the database.
        self.session.expire(scene, ["captions"])
        return len(timings)
