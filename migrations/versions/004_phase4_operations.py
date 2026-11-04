from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_phase4"
down_revision: str | Sequence[str] | None = "003_phase3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()

    if "durableoperation" not in tables:
        op.create_table(
            "durableoperation",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("campaign_id", sa.Uuid(), nullable=False),
            sa.Column("task_name", sa.String(length=128), nullable=False),
            sa.Column("worker_pool", sa.String(length=32), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("correlation_id", sa.String(length=128), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("last_error", sa.String(length=2000), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key"),
        )
        op.create_index("ix_durableoperation_campaign_id", "durableoperation", ["campaign_id"])
        op.create_index("ix_durableoperation_task_name", "durableoperation", ["task_name"])
        op.create_index(
            "ix_durableoperation_correlation_id",
            "durableoperation",
            ["correlation_id"],
        )

    if "retentionpolicy" not in tables:
        op.create_table(
            "retentionpolicy",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("campaign_id", sa.Uuid(), nullable=False),
            sa.Column("public_business_days", sa.Integer(), nullable=False),
            sa.Column("personal_data_days", sa.Integer(), nullable=True),
            sa.Column("export_enabled", sa.Boolean(), nullable=False),
            sa.Column("deletion_enabled", sa.Boolean(), nullable=False),
            sa.Column("legal_hold", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("campaign_id"),
        )
        op.create_index("ix_retentionpolicy_campaign_id", "retentionpolicy", ["campaign_id"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "retentionpolicy" in tables:
        op.drop_index("ix_retentionpolicy_campaign_id", table_name="retentionpolicy")
        op.drop_table("retentionpolicy")
    if "durableoperation" in tables:
        op.drop_index("ix_durableoperation_campaign_id", table_name="durableoperation")
        op.drop_index("ix_durableoperation_task_name", table_name="durableoperation")
        op.drop_index("ix_durableoperation_correlation_id", table_name="durableoperation")
        op.drop_table("durableoperation")
