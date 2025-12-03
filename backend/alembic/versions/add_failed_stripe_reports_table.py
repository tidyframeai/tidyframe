"""Add failed_stripe_reports table for usage report retry queue

Revision ID: add_failed_stripe_reports
Revises: add_stripe_indexes
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_failed_stripe_reports'
down_revision: Union[str, None] = 'add_stripe_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create failed_stripe_reports table for revenue protection"""

    # Create failed_stripe_reports table
    op.create_table(
        'failed_stripe_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('customer_id', sa.String(255), nullable=False, index=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('succeeded_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create composite index for retry query optimization
    op.create_index(
        'idx_failed_stripe_reports_retry_ready',
        'failed_stripe_reports',
        ['succeeded_at', 'retry_count', 'next_retry_at'],
        unique=False
    )


def downgrade() -> None:
    """Drop failed_stripe_reports table"""
    op.drop_index('idx_failed_stripe_reports_retry_ready', table_name='failed_stripe_reports')
    op.drop_table('failed_stripe_reports')
