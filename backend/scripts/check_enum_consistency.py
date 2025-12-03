"""
Script to check for enum case consistency between database and Python models
Run this to identify any data inconsistencies
"""

import asyncio
import sys
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, "/app")

from app.core.config import settings
from app.models.user import User, PlanType


async def check_enum_consistency():
    """Check if all plan values in database match Python enum"""

    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("\n=== Checking Enum Consistency ===\n")

        # Check what values are actually in the database
        result = await session.execute(
            text("SELECT DISTINCT plan FROM users ORDER BY plan")
        )
        db_values = [row[0] for row in result]

        python_values = [e.value for e in PlanType]
        print(f"Database plan values: {db_values}")
        print(f"Python enum values: {python_values}")

        # Check for case mismatches
        python_values_lower = {e.value.lower() for e in PlanType}
        db_values_lower = {v.lower() for v in db_values if v}

        mismatches = []
        for db_val in db_values:
            if db_val and db_val.lower() in python_values_lower:
                # Find matching Python enum
                matching = [e for e in PlanType if e.value.lower() == db_val.lower()]
                if matching and matching[0].value != db_val:
                    mismatches.append((db_val, matching[0].value))

        if mismatches:
            print("\n⚠️  CASE MISMATCHES FOUND:")
            for db_val, expected in mismatches:
                print(f"  - Database: '{db_val}' | Expected: '{expected}'")
                # Count how many users have this value
                count_result = await session.execute(
                    select(User).where(User.plan == db_val)
                )
                count = len(count_result.scalars().all())
                print(f"    Affected users: {count}")
        else:
            print("\n✅ All enum values are consistent!")

        # Check for users with paid plans but no subscription ID
        print("\n=== Checking Data Consistency ===\n")

        result = await session.execute(
            select(User).where(
                User.plan.in_([PlanType.STANDARD, PlanType.ENTERPRISE]),
                User.stripe_subscription_id == None
            )
        )
        inconsistent_users = result.scalars().all()

        if inconsistent_users:
            print(f"⚠️  Found {len(inconsistent_users)} users with paid plan but no subscription ID:")
            for user in inconsistent_users:
                print(f"  - {user.email} | Plan: {user.plan.value} | Customer ID: {user.stripe_customer_id}")
        else:
            print("✅ All paid users have subscription IDs!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_enum_consistency())
