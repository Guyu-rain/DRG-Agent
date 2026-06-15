"""add reasoning summary to document messages

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-15 15:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_messages",
        sa.Column("reasoning_summary", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_messages", "reasoning_summary")
