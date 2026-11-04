"""phase 2 artifact and resolution contracts

Revision ID: 002_phase2
Revises: 001_phase1
Create Date: 2026-11-04
"""

from alembic import op
from sqlmodel import SQLModel

from ailiss import models  # noqa: F401

revision = "002_phase2"
down_revision = "001_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    SQLModel.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    for table_name in ("entityresolutiondecision", "artifact"):
        op.execute(f'DROP TABLE IF EXISTS "{table_name}"')
