"""Add legal consent tracking fields

Revision ID: legal_consent_001  
Revises: add_is_admin_col
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'legal_consent_001'
down_revision = 'add_is_admin_col'
branch_labels = None
depends_on = None


def upgrade():
    """Add legal compliance fields to users table"""
    # Add age verification and consent tracking
    op.add_column('users', sa.Column('age_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('privacy_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('arbitration_acknowledged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('location_confirmed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Store consent metadata for legal evidence
    op.add_column('users', sa.Column('consent_ip_address', postgresql.INET(), nullable=True))
    op.add_column('users', sa.Column('consent_user_agent', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('country_code', sa.String(length=2), nullable=True))
    
    # Add indices for compliance queries
    op.create_index('idx_users_age_verified', 'users', ['age_verified_at'])
    op.create_index('idx_users_terms_accepted', 'users', ['terms_accepted_at'])
    op.create_index('idx_users_privacy_accepted', 'users', ['privacy_accepted_at'])
    op.create_index('idx_users_country_code', 'users', ['country_code'])


def downgrade():
    """Remove legal compliance fields"""
    op.drop_index('idx_users_country_code', table_name='users')
    op.drop_index('idx_users_privacy_accepted', table_name='users')
    op.drop_index('idx_users_terms_accepted', table_name='users')
    op.drop_index('idx_users_age_verified', table_name='users')
    
    op.drop_column('users', 'country_code')
    op.drop_column('users', 'birth_date')
    op.drop_column('users', 'consent_user_agent')
    op.drop_column('users', 'consent_ip_address')
    op.drop_column('users', 'location_confirmed_at')
    op.drop_column('users', 'arbitration_acknowledged_at')
    op.drop_column('users', 'privacy_accepted_at')
    op.drop_column('users', 'terms_accepted_at')
    op.drop_column('users', 'age_verified_at')