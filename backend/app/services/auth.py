"""
Authentication service
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import PlanType, User
from app.schemas.auth import UserCreate
from app.services.email import EmailService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service class"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not user.password_hash:
            return None  # OAuth user
        if not self.verify_password(password, user.password_hash):
            # Update failed login attempts
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.LOCKOUT_DURATION_MINUTES
                )
            await self.db.commit()
            return None

        # Reset failed attempts on successful login
        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.locked_until = None

        user.last_login_at = datetime.utcnow()
        await self.db.commit()
        return user

    async def create_user(self, user_create: UserCreate, client_ip: str = None) -> User:
        """Create a new user with legal compliance"""
        # Parse full name into first and last name
        first_name, last_name = self._parse_full_name(user_create.full_name)

        # Create user with basic information
        db_user = User(
            email=user_create.email,
            password_hash=self.get_password_hash(user_create.password),
            first_name=first_name,
            last_name=last_name,
            company_name=user_create.company,
            plan=PlanType.STANDARD,
            parses_this_month=0,
            month_reset_date=datetime.utcnow(),
        )

        # Add legal compliance data if provided
        if user_create.consent:
            consent_time = datetime.fromisoformat(
                user_create.consent.consent_timestamp.replace("Z", "+00:00")
            )

            if user_create.consent.age_verified:
                db_user.age_verified_at = consent_time
            if user_create.consent.terms_accepted:
                db_user.terms_accepted_at = consent_time
            if user_create.consent.privacy_accepted:
                db_user.privacy_accepted_at = consent_time
            if user_create.consent.arbitration_acknowledged:
                db_user.arbitration_acknowledged_at = consent_time
            if user_create.consent.location_confirmed:
                db_user.location_confirmed_at = consent_time

            # Store consent evidence for legal protection
            if client_ip:
                db_user.consent_ip_address = client_ip
            db_user.consent_user_agent = user_create.consent.user_agent
            db_user.country_code = "US"  # US-only service per Terms of Service

        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)

        # Send verification email
        await self.send_verification_email(db_user.email)

        return db_user

    def _parse_full_name(
        self, full_name: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """Parse full name into first and last name components"""
        if not full_name:
            return None, None

        parts = full_name.strip().split()
        if len(parts) == 1:
            return parts[0], None
        elif len(parts) >= 2:
            return parts[0], parts[-1]  # First and last, ignore middle names
        else:
            return None, None

    async def create_oauth_user(
        self, email: str, google_id: str, full_name: str = None
    ) -> User:
        """Create a new OAuth user"""
        db_user = User(
            email=email,
            google_id=google_id,
            full_name=full_name,
            plan=PlanType.STANDARD,
            parses_this_month=0,
            month_reset_date=datetime.utcnow(),
            email_verified=True,  # OAuth emails are pre-verified
        )

        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)

        return db_user

    def create_verification_token(self, email: str) -> str:
        """Create email verification token"""
        expire = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
        payload = {"email": email, "exp": expire, "type": "email_verification"}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_reset_token(self, email: str) -> str:
        """Create password reset token"""
        expire = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS)
        payload = {"email": email, "exp": expire, "type": "password_reset"}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async def send_verification_email(self, email: str):
        """Send email verification"""
        token = self.create_verification_token(email)
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        await self.email_service.send_verification_email(email, verification_url)

    async def request_password_reset(self, email: str):
        """Request password reset"""
        user = await self.get_user_by_email(email)
        if user:
            token = self.create_reset_token(email)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            await self.email_service.send_password_reset_email(email, reset_url)

    async def verify_email_token(self, token: str) -> bool:
        """Verify email verification token"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            if payload.get("type") != "email_verification":
                return False

            email = payload.get("email")
            user = await self.get_user_by_email(email)
            if user:
                user.email_verified = True
                await self.db.commit()
                return True

        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False

        return False

    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password with token"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            if payload.get("type") != "password_reset":
                return False

            email = payload.get("email")
            user = await self.get_user_by_email(email)
            if user:
                user.password_hash = self.get_password_hash(new_password)
                user.failed_login_attempts = 0
                user.locked_until = None
                await self.db.commit()
                return True

        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False

        return False
