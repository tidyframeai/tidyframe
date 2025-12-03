"""Add indexes for Stripe fields and plan consistency constraints

Revision ID: add_stripe_indexes
Revises: add_legal_compliance_fields
Create Date: 2025-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_stripe_indexes'
down_revision: Union[str, None] = 'legal_compliance_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes and data consistency constraints"""

    # Add indexes for Stripe customer ID lookups (used heavily in webhooks)
    op.create_index(
        'idx_users_stripe_customer_id',
        'users',
        ['stripe_customer_id'],
        unique=False
    )

    # Add index for Stripe subscription ID lookups
    op.create_index(
        'idx_users_stripe_subscription_id',
        'users',
        ['stripe_subscription_id'],
        unique=False
    )

    # Add composite index for webhook event processing queries
    op.create_index(
        'idx_webhook_events_processed_created',
        'webhook_events',
        ['processed', 'created_at'],
        unique=False
    )

    # Add index for webhook event type filtering
    op.create_index(
        'idx_webhook_events_type_source',
        'webhook_events',
        ['event_type', 'source'],
        unique=False
    )


def downgrade() -> None:
    """Remove indexes"""
    op.drop_index('idx_webhook_events_type_source', table_name='webhook_events')
    op.drop_index('idx_webhook_events_processed_created', table_name='webhook_events')
    op.drop_index('idx_users_stripe_subscription_id', table_name='users')
    op.drop_index('idx_users_stripe_customer_id', table_name='users')
