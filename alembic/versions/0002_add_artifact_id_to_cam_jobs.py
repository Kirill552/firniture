from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore

revision = "0002_add_artifact_id_to_cam_jobs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cam_jobs",
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cam_jobs", "artifact_id")
