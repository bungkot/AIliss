from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_phase5"
down_revision: str | Sequence[str] | None = "004_phase4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()

    if "expansionrelease" not in tables:
        op.create_table(
            "expansionrelease",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("campaign_id", sa.Uuid(), nullable=False),
            sa.Column("target_type", sa.String(length=32), nullable=False),
            sa.Column("target_name", sa.String(length=128), nullable=False),
            sa.Column("config_hash", sa.String(length=64), nullable=False),
            sa.Column("policy_evidence_hash", sa.String(length=64), nullable=False),
            sa.Column("fixture_evidence_hash", sa.String(length=64), nullable=False),
            sa.Column("evaluation_evidence_hash", sa.String(length=64), nullable=False),
            sa.Column("rollout_percent", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("approved_by", sa.String(length=200), nullable=True),
            sa.Column("reason", sa.String(length=2000), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "campaign_id",
                "target_type",
                "target_name",
                name="uq_expansionrelease_campaign_target",
            ),
        )
        op.create_index(
            "ix_expansionrelease_campaign_id", "expansionrelease", ["campaign_id"]
        )
        op.create_index(
            "ix_expansionrelease_target_type", "expansionrelease", ["target_type"]
        )
        op.create_index(
            "ix_expansionrelease_target_name", "expansionrelease", ["target_name"]
        )
        op.create_index(
            "ix_expansionrelease_status", "expansionrelease", ["status"]
        )

    if "resourcebudget" not in tables:
        op.create_table(
            "resourcebudget",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("campaign_id", sa.Uuid(), nullable=False),
            sa.Column("worker_pool", sa.String(length=32), nullable=False),
            sa.Column("max_concurrency", sa.Integer(), nullable=False),
            sa.Column("max_requests_per_second", sa.Integer(), nullable=False),
            sa.Column("max_bytes", sa.Integer(), nullable=False),
            sa.Column("max_tokens", sa.Integer(), nullable=False),
            sa.Column("max_spend_usd", sa.Float(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "campaign_id",
                "worker_pool",
                name="uq_resourcebudget_campaign_pool",
            ),
        )
        op.create_index(
            "ix_resourcebudget_campaign_id", "resourcebudget", ["campaign_id"]
        )
        op.create_index(
            "ix_resourcebudget_worker_pool", "resourcebudget", ["worker_pool"]
        )


def downgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "resourcebudget" in tables:
        op.drop_index("ix_resourcebudget_worker_pool", table_name="resourcebudget")
        op.drop_index("ix_resourcebudget_campaign_id", table_name="resourcebudget")
        op.drop_table("resourcebudget")
    if "expansionrelease" in tables:
        op.drop_index("ix_expansionrelease_status", table_name="expansionrelease")
        op.drop_index("ix_expansionrelease_target_name", table_name="expansionrelease")
        op.drop_index("ix_expansionrelease_target_type", table_name="expansionrelease")
        op.drop_index(
            "ix_expansionrelease_campaign_id", table_name="expansionrelease"
        )
        op.drop_table("expansionrelease")
