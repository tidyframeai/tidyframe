"""Add billing reset tracking columns to prevent webhook/celery race conditions

Revision ID: add_billing_reset_tracking
Revises: add_failed_stripe_reports
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_billing_reset_tracking'
down_revision: Union[str, None] = 'add_failed_stripe_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add columns to track billing reset source and timestamp"""

    # Add last_reset_at column
    op.add_column(
        'users',
        sa.Column('last_reset_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add last_reset_source column
    op.add_column(
        'users',
        sa.Column('last_reset_source', sa.String(20), nullable=True)
    )


def downgrade() -> None:
    """Remove billing reset tracking columns"""
    op.drop_column('users', 'last_reset_source')
    op.drop_column('users', 'last_reset_at')
