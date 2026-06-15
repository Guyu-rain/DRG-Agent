"""add mode column to document_conversations

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_conversations",
        sa.Column("mode", sa.String(20), nullable=False, server_default="doc_chat"),
    )
    op.create_index(
        op.f("ix_document_conversations_mode"),
        "document_conversations",
        ["mode"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_conversations_mode"), table_name="document_conversations")
    op.drop_column("document_conversations", "mode")
