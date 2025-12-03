"""
Data export service for CCPA compliance and legal data requests
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.job import ProcessingJob
from app.models.parse_log import ParseLog
from app.models.user import User

logger = structlog.get_logger()


class DataExportService:
    """Service for exporting user data for CCPA compliance"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all user data for CCPA compliance
        Returns comprehensive user data export including legal consent records
        """
        user = await self._get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        logger.info("Exporting user data for CCPA compliance", user_id=user_id)

        # Core user data
        user_data = {
            "personal_information": await self._export_personal_info(user),
            "account_details": await self._export_account_details(user),
            "legal_consent_records": await self._export_legal_consent(user),
            "usage_statistics": await self._export_usage_stats(user),
            "processing_history": await self._export_processing_history(user),
            "api_access": await self._export_api_access(user),
            "export_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "export_format": "CCPA_compliant",
                "data_retention_policy": "As per Privacy Policy",
                "user_rights_info": "https://tidyframe.com/legal/privacy-policy#user-rights",
            },
        }

        logger.info(
            "User data export completed",
            user_id=user_id,
            data_categories=len(user_data),
        )
        return user_data

    async def _get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _export_personal_info(self, user: User) -> Dict[str, Any]:
        """Export personal information"""
        return {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "company_name": user.company_name,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "country_code": user.country_code,
        }

    async def _export_account_details(self, user: User) -> Dict[str, Any]:
        """Export account and subscription details"""
        return {
            "user_id": str(user.id),
            "plan_type": user.plan,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": (
                user.last_login_at.isoformat() if user.last_login_at else None
            ),
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
            "monthly_limit": user.monthly_limit,
            "parses_this_month": user.parses_this_month,
            "month_reset_date": (
                user.month_reset_date.isoformat() if user.month_reset_date else None
            ),
            "custom_monthly_limit": user.custom_monthly_limit,
        }

    async def _export_legal_consent(self, user: User) -> Dict[str, Any]:
        """Export legal consent records - CRITICAL FOR LEGAL PROTECTION"""
        return {
            "consent_evidence": user.get_consent_evidence(),
            "compliance_status": {
                "is_legally_compliant": user.is_legally_compliant,
                "has_valid_consent": user.has_valid_consent,
                "is_age_verified": user.is_age_verified,
                "has_accepted_terms": user.has_accepted_terms(),
                "has_accepted_privacy": user.has_accepted_privacy(),
                "has_acknowledged_arbitration": user.has_acknowledged_arbitration(),
                "has_confirmed_us_location": user.has_confirmed_us_location(),
            },
            "consent_timestamps": {
                "age_verified_at": (
                    user.age_verified_at.isoformat() if user.age_verified_at else None
                ),
                "terms_accepted_at": (
                    user.terms_accepted_at.isoformat()
                    if user.terms_accepted_at
                    else None
                ),
                "privacy_accepted_at": (
                    user.privacy_accepted_at.isoformat()
                    if user.privacy_accepted_at
                    else None
                ),
                "arbitration_acknowledged_at": (
                    user.arbitration_acknowledged_at.isoformat()
                    if user.arbitration_acknowledged_at
                    else None
                ),
                "location_confirmed_at": (
                    user.location_confirmed_at.isoformat()
                    if user.location_confirmed_at
                    else None
                ),
            },
        }

    async def _export_usage_stats(self, user: User) -> Dict[str, Any]:
        """Export usage statistics"""
        # Get parse log statistics
        parse_count_stmt = select(func.count(ParseLog.id)).where(
            ParseLog.user_id == user.id
        )
        parse_count = await self.db.execute(parse_count_stmt)
        total_parses = parse_count.scalar() or 0

        # Get job statistics
        job_count_stmt = select(func.count(ProcessingJob.id)).where(
            ProcessingJob.user_id == user.id
        )
        job_count = await self.db.execute(job_count_stmt)
        total_jobs = job_count.scalar() or 0

        return {
            "total_parses_all_time": total_parses,
            "total_jobs_all_time": total_jobs,
            "current_month_parses": user.parses_this_month,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": (
                user.locked_until.isoformat() if user.locked_until else None
            ),
        }

    async def _export_processing_history(self, user: User) -> List[Dict[str, Any]]:
        """Export processing job history (last 100 jobs for performance)"""
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.user_id == user.id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(100)
        )

        result = await self.db.execute(stmt)
        jobs = result.scalars().all()

        return [
            {
                "job_id": str(job.id),
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "file_name": job.file_name,
                "file_size": job.file_size,
                "total_names": job.total_names,
                "processed_names": job.processed_names,
                "error_message": job.error_message,
            }
            for job in jobs
        ]

    async def _export_api_access(self, user: User) -> List[Dict[str, Any]]:
        """Export API key information"""
        stmt = select(APIKey).where(APIKey.user_id == user.id)
        result = await self.db.execute(stmt)
        api_keys = result.scalars().all()

        return [
            {
                "api_key_id": str(api_key.id),
                "name": api_key.name,
                "is_active": api_key.is_active,
                "created_at": api_key.created_at.isoformat(),
                "last_used_at": (
                    api_key.last_used_at.isoformat() if api_key.last_used_at else None
                ),
                "usage_count": api_key.usage_count,
            }
            for api_key in api_keys
        ]

    async def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Delete all user data for CCPA right to deletion
        WARNING: This is irreversible and will delete ALL user data
        """
        user = await self._get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        logger.warning(
            "CCPA data deletion requested", user_id=user_id, email=user.email
        )

        deletion_report = {
            "user_id": user_id,
            "email": user.email,
            "deletion_timestamp": datetime.utcnow().isoformat(),
            "deleted_data_types": [],
        }

        try:
            # Delete related data first (foreign key constraints)

            # Delete API keys
            api_keys_stmt = select(APIKey).where(APIKey.user_id == user.id)
            api_keys_result = await self.db.execute(api_keys_stmt)
            api_keys = api_keys_result.scalars().all()

            for api_key in api_keys:
                await self.db.delete(api_key)
            deletion_report["deleted_data_types"].append(f"API Keys ({len(api_keys)})")

            # Delete parse logs
            parse_logs_stmt = select(ParseLog).where(ParseLog.user_id == user.id)
            parse_logs_result = await self.db.execute(parse_logs_stmt)
            parse_logs = parse_logs_result.scalars().all()

            for parse_log in parse_logs:
                await self.db.delete(parse_log)
            deletion_report["deleted_data_types"].append(
                f"Parse Logs ({len(parse_logs)})"
            )

            # Delete processing jobs
            jobs_stmt = select(ProcessingJob).where(ProcessingJob.user_id == user.id)
            jobs_result = await self.db.execute(jobs_stmt)
            jobs = jobs_result.scalars().all()

            for job in jobs:
                await self.db.delete(job)
            deletion_report["deleted_data_types"].append(
                f"Processing Jobs ({len(jobs)})"
            )

            # Delete user account last
            await self.db.delete(user)
            deletion_report["deleted_data_types"].append("User Account")

            await self.db.commit()

            logger.warning(
                "CCPA data deletion completed",
                user_id=user_id,
                deleted_items=len(deletion_report["deleted_data_types"]),
            )

            deletion_report["status"] = "SUCCESS"
            deletion_report["message"] = "All user data has been permanently deleted"

        except Exception as e:
            await self.db.rollback()
            logger.error("CCPA data deletion failed", user_id=user_id, error=str(e))
            deletion_report["status"] = "FAILED"
            deletion_report["error"] = str(e)
            raise

        return deletion_report
