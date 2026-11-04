"""phase 1 core contracts

Revision ID: 001_phase1
Revises:
Create Date: 2026-11-04
"""

from alembic import op
from sqlmodel import SQLModel

from ailiss import models  # noqa: F401

revision = "001_phase1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    SQLModel.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    for table in reversed(SQLModel.metadata.sorted_tables):
        op.drop_table(table.name)
