"""persist bounded AI Council sessions"""
from alembic import op
import sqlalchemy as sa

revision = "20261025_02"
down_revision = "20261007_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "council_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(32)),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("report", sa.JSON()),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("debate", sa.JSON(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_council_sessions_symbol", "council_sessions", ["symbol"])
    op.create_index("ix_council_sessions_status", "council_sessions", ["status"])


def downgrade() -> None:
    op.drop_table("council_sessions")
