"""document conversations and messages

Revision ID: a1b2c3d4e5f6
Revises: 09ab38d8f260
Create Date: 2026-06-15 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '09ab38d8f260'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'document_conversations',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('doc_type', sa.String(length=30), nullable=True),
        sa.Column('document_id', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_document_conversations_document_id'),
        'document_conversations', ['document_id'], unique=False,
    )
    op.create_index(
        op.f('ix_document_conversations_status'),
        'document_conversations', ['status'], unique=False,
    )
    op.create_index(
        op.f('ix_document_conversations_created_at'),
        'document_conversations', ['created_at'], unique=False,
    )

    op.create_table(
        'document_messages',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('conversation_id', sa.String(length=40), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('doc_version', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['document_conversations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_document_messages_conversation_id'),
        'document_messages', ['conversation_id'], unique=False,
    )
    op.create_index(
        op.f('ix_document_messages_created_at'),
        'document_messages', ['created_at'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_document_messages_created_at'), table_name='document_messages')
    op.drop_index(op.f('ix_document_messages_conversation_id'), table_name='document_messages')
    op.drop_table('document_messages')
    op.drop_index(op.f('ix_document_conversations_created_at'), table_name='document_conversations')
    op.drop_index(op.f('ix_document_conversations_status'), table_name='document_conversations')
    op.drop_index(op.f('ix_document_conversations_document_id'), table_name='document_conversations')
    op.drop_table('document_conversations')
