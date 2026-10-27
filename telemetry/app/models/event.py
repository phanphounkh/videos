import uuid

from sqlalchemy import BigInteger, Float, Identity, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import mapped_column

from app.database import Base


class Event(Base):
    """One row per event, from anywhere: the API, the render worker or a browser.

    One wide table on purpose. Every question the admin panel asks (what happened in
    this session, what failed in the last hour, which user did that) is a filter or a
    group-by over this one table, with no joins.

      source      who produced it: backend | worker | frontend
      event_type  llm_usage (an AI call) | product (anything else the app did) | log
      name        what happened: api_request, scene_created, page_view, click ...
      level       debug | info | warning | error
      session_id  one browser tab's visit; backend events carry it too (the browser sends
                  it on every API call), which is what lets an admin follow one person's
                  clicks through to the server work they caused
      request_id  one HTTP request, shared by the browser's network event and the
                  backend's api_request event
      properties  everything else about the event (scrubbed of emails and tokens)

    `seq` is arrival order: a strictly increasing number the admin panel uses to page
    through results and to tail new events live.
    """

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_created_at", "created_at"),
        Index("ix_events_type_name_created", "event_type", "name", "created_at"),
        Index("ix_events_source_created", "source", "created_at"),
        Index("ix_events_user_created", "user_id", "created_at"),
        Index("ix_events_session_created", "session_id", "created_at"),
        Index("ix_events_request", "request_id"),
        Index("ix_events_errors", "created_at", postgresql_where=text("level = 'error'")),
    )

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seq = mapped_column(BigInteger, Identity(), nullable=False, unique=True)

    event_type = mapped_column(String(16), nullable=False)
    name = mapped_column(String(100), nullable=False)
    source = mapped_column(String(16), nullable=False)
    level = mapped_column(String(8), nullable=False, server_default="info")
    # ok | error: whether the thing that happened worked, when that applies.
    outcome = mapped_column(String(8), nullable=True)

    # Null for anonymous events: the login page, errors before anyone signed in,
    # requests that failed authentication.
    user_id = mapped_column(String(64), nullable=True)
    session_id = mapped_column(String(64), nullable=True)
    request_id = mapped_column(String(64), nullable=True)

    # The route (a template such as /api/projects/{project_id}) or the page path.
    path = mapped_column(String(300), nullable=True)
    duration_ms = mapped_column(Integer, nullable=True)

    # llm_usage
    model = mapped_column(String(100), nullable=True)
    provider = mapped_column(String(50), nullable=True)
    prompt_tokens = mapped_column(Integer, nullable=True)
    completion_tokens = mapped_column(Integer, nullable=True)
    total_tokens = mapped_column(Integer, nullable=True)
    finish_reason = mapped_column(String(50), nullable=True)
    cost_usd = mapped_column(Float, nullable=True)

    properties = mapped_column(JSONB, nullable=False, server_default="{}")

    platform = mapped_column(String(16), nullable=True)
    os = mapped_column(String(60), nullable=True)
    browser = mapped_column(String(60), nullable=True)

    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
