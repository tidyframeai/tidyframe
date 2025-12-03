"""
User model for authentication and account management
"""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PlanType(str, enum.Enum):
    FREE = "FREE"  # Registered but no subscription
    ANONYMOUS = "ANONYMOUS"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"


class User(Base):
    __tablename__ = "users"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth-only users

    # OAuth integration
    google_id = Column(String(255), unique=True, nullable=True, index=True)

    # API access
    api_key_hash = Column(String(255), unique=True, nullable=True, index=True)

    # Stripe integration
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)

    # Plan and usage
    plan = Column(SQLEnum(PlanType), default=PlanType.FREE, nullable=False)
    parses_this_month = Column(Integer, default=0, nullable=False)
    month_reset_date = Column(DateTime(timezone=True), server_default=func.now())

    # Custom limits (admin-configurable)
    custom_monthly_limit = Column(Integer, nullable=True)  # Override default plan limit

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(
        Boolean, default=False, nullable=False
    )  # Proper admin flag, independent of plan

    # Security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Legal compliance fields - CRITICAL FOR LAWSUIT PROTECTION
    age_verified_at = Column(DateTime(timezone=True), nullable=True)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    privacy_accepted_at = Column(DateTime(timezone=True), nullable=True)
    arbitration_acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    location_confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # Consent evidence (for legal compliance)
    consent_ip_address = Column(INET, nullable=True)
    consent_user_agent = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=True)  # For age verification
    country_code = Column(String(2), nullable=True)  # For geographic restrictions

    # Relationships (defined here to avoid circular imports)
    jobs = relationship("ProcessingJob", back_populates="user", lazy="dynamic")
    parse_logs = relationship("ParseLog", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split("@")[0]

    @property
    def monthly_limit(self) -> int:
        """Get monthly parse limit based on plan or custom limit"""
        from app.core.config import settings

        # If custom limit is set, use that
        if self.custom_monthly_limit is not None:
            return self.custom_monthly_limit

        # Otherwise use plan-based limits
        if self.plan == PlanType.STANDARD:
            return settings.STANDARD_TIER_MONTHLY_LIMIT
        elif self.plan == PlanType.ENTERPRISE:
            return settings.ENTERPRISE_TIER_MONTHLY_LIMIT
        else:
            return settings.ANONYMOUS_LIFETIME_LIMIT

    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription"""
        return self.plan in [PlanType.STANDARD, PlanType.ENTERPRISE]

    @property
    def is_enterprise(self) -> bool:
        """Check if user has enterprise subscription"""
        return self.plan == PlanType.ENTERPRISE

    def can_parse(self, count: int = 1) -> bool:
        """
        Check if user can perform additional parses

        Returns True for:
        - Admin users (unlimited, bypass billing)
        - Enterprise users (unlimited, included in plan)
        - Standard users (unlimited, overage billing applies after limit)

        Returns False for:
        - Free users (hard limit at 5 parses, must upgrade)
        """
        # Admin users have unlimited parsing (bypass billing)
        if self.is_admin:
            return True

        # Enterprise users have unlimited parsing (no overage charges)
        if self.plan == PlanType.ENTERPRISE:
            return True

        # CRITICAL: STANDARD users can always parse (overage billing after limit)
        # This enables the $0.01/parse overage revenue model
        if self.plan == PlanType.STANDARD:
            return True

        # FREE users have hard limit (same as ANONYMOUS - 5 parses)
        # They must upgrade to STANDARD to parse more
        return (self.parses_this_month + count) <= self.monthly_limit

    def is_account_locked(self) -> bool:
        """Check if account is locked due to failed login attempts"""
        from datetime import datetime, timezone

        if self.locked_until is None:
            return False

        return datetime.now(timezone.utc) < self.locked_until

    def is_legally_compliant(self) -> bool:
        """Check if user has provided all required legal consents"""
        return all(
            [
                self.age_verified_at is not None,
                self.terms_accepted_at is not None,
                self.privacy_accepted_at is not None,
                self.arbitration_acknowledged_at is not None,
                self.location_confirmed_at is not None,
            ]
        )

    def has_valid_age_verification(self) -> bool:
        """Check if user has verified they are 18+"""
        return self.age_verified_at is not None

    def has_accepted_terms(self) -> bool:
        """Check if user has accepted Terms of Service"""
        return self.terms_accepted_at is not None

    def has_accepted_privacy(self) -> bool:
        """Check if user has accepted Privacy Policy"""
        return self.privacy_accepted_at is not None

    def has_acknowledged_arbitration(self) -> bool:
        """Check if user has acknowledged mandatory arbitration"""
        return self.arbitration_acknowledged_at is not None

    def has_confirmed_us_location(self) -> bool:
        """Check if user has confirmed US location"""
        return self.location_confirmed_at is not None

    def get_consent_evidence(self) -> dict:
        """Get consent evidence for legal documentation"""
        return {
            "consent_ip_address": (
                str(self.consent_ip_address) if self.consent_ip_address else None
            ),
            "consent_user_agent": self.consent_user_agent,
            "age_verified_at": (
                self.age_verified_at.isoformat() if self.age_verified_at else None
            ),
            "terms_accepted_at": (
                self.terms_accepted_at.isoformat() if self.terms_accepted_at else None
            ),
            "privacy_accepted_at": (
                self.privacy_accepted_at.isoformat()
                if self.privacy_accepted_at
                else None
            ),
            "arbitration_acknowledged_at": (
                self.arbitration_acknowledged_at.isoformat()
                if self.arbitration_acknowledged_at
                else None
            ),
            "location_confirmed_at": (
                self.location_confirmed_at.isoformat()
                if self.location_confirmed_at
                else None
            ),
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "country_code": self.country_code,
        }
