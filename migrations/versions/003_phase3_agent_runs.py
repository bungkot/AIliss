from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_phase3"
down_revision: str | Sequence[str] | None = "002_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "agentrun" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "agentrun",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("prompt", sa.String(length=4000), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("config_hash", sa.String(length=128), nullable=False),
        sa.Column("tool_allowlist", sa.String(length=4000), nullable=False),
        sa.Column("redaction_flags", sa.String(length=1000), nullable=False),
        sa.Column("citations", sa.String(length=8000), nullable=False),
        sa.Column("terminal_status", sa.String(length=32), nullable=False),
        sa.Column("recommendation", sa.String(length=4000), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("tool_calls", sa.Integer(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("bytes_used", sa.Integer(), nullable=False),
        sa.Column("spend_usd", sa.Float(), nullable=False),
        sa.Column("wall_seconds", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agentrun_campaign_id", "agentrun", ["campaign_id"], unique=False)


def downgrade() -> None:
    if "agentrun" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_agentrun_campaign_id", table_name="agentrun")
        op.drop_table("agentrun")
