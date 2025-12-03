"""Add legal compliance fields to user model

Revision ID: legal_compliance_001
Revises: 
Create Date: 2025-09-12 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'legal_compliance_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add legal compliance fields to users table"""
    
    # Add legal compliance timestamp fields
    op.add_column('users', sa.Column('age_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('privacy_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('arbitration_acknowledged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('location_confirmed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add consent evidence fields for legal protection
    op.add_column('users', sa.Column('consent_ip_address', postgresql.INET(), nullable=True))
    op.add_column('users', sa.Column('consent_user_agent', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('country_code', sa.String(length=2), nullable=True))
    
    # Create indexes for performance and legal queries
    op.create_index('idx_users_age_verified_at', 'users', ['age_verified_at'])
    op.create_index('idx_users_terms_accepted_at', 'users', ['terms_accepted_at'])
    op.create_index('idx_users_privacy_accepted_at', 'users', ['privacy_accepted_at'])
    op.create_index('idx_users_consent_ip_address', 'users', ['consent_ip_address'])
    op.create_index('idx_users_country_code', 'users', ['country_code'])


def downgrade() -> None:
    """Remove legal compliance fields from users table"""
    
    # Drop indexes first
    op.drop_index('idx_users_country_code')
    op.drop_index('idx_users_consent_ip_address')
    op.drop_index('idx_users_privacy_accepted_at')
    op.drop_index('idx_users_terms_accepted_at')
    op.drop_index('idx_users_age_verified_at')
    
    # Drop columns
    op.drop_column('users', 'country_code')
    op.drop_column('users', 'birth_date')
    op.drop_column('users', 'consent_user_agent')
    op.drop_column('users', 'consent_ip_address')
    op.drop_column('users', 'location_confirmed_at')
    op.drop_column('users', 'arbitration_acknowledged_at')
    op.drop_column('users', 'privacy_accepted_at')
    op.drop_column('users', 'terms_accepted_at')
    op.drop_column('users', 'age_verified_at')