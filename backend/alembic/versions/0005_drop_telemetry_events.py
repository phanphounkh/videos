"""telemetry moved to its own service: drop telemetry_events (users.is_admin stays)

Revision ID: 0005_drop_telemetry_events
Revises: 0004_telemetry
Create Date: 2026-10-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_drop_telemetry_events"
down_revision: str | None = "0004_telemetry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS telemetry_events")


def downgrade() -> None:
    # The table's data lives in the telemetry service now; nothing to restore.
    pass
