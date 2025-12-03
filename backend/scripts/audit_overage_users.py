#!/usr/bin/env python3
"""
Overage Billing Audit Script

Identifies users who should have been charged overage fees but weren't
due to the broken get_current_usage() implementation.

This script:
1. Finds Standard tier users with parses_this_month > 100,000
2. Calculates missed overage revenue
3. Generates detailed report for revenue recovery decisions
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add the backend app to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def audit_overage_users():
    """Audit users with overage parses and calculate missed revenue"""

    from app.core.database import AsyncSessionLocal
    from app.core.config import settings
    from app.models.user import User, PlanType
    from app.models.parse_log import ParseLog
    from sqlalchemy import select, func, and_

    print("=" * 80)
    print("🔍 OVERAGE BILLING AUDIT")
    print("=" * 80)
    print(f"Audit started at: {datetime.now(timezone.utc).isoformat()}")
    print()

    async with AsyncSessionLocal() as db:
        try:
            # Get Standard tier users with overage parses
            standard_limit = settings.STANDARD_TIER_MONTHLY_LIMIT  # 100,000
            overage_price = settings.OVERAGE_PRICE_PER_UNIT  # $0.01

            print(f"📊 Configuration:")
            print(f"   Standard Tier Limit: {standard_limit:,} parses/month")
            print(f"   Overage Price: ${overage_price:.2f} per parse")
            print()

            # Query users with overage
            stmt = select(User).where(
                and_(
                    User.plan == PlanType.STANDARD,
                    User.parses_this_month > standard_limit,
                )
            )

            result = await db.execute(stmt)
            overage_users = result.scalars().all()

            if not overage_users:
                print("✅ No Standard tier users with overage parses found!")
                print(
                    "   This is expected if the system is new or if all users are within limits."
                )
                return True

            print(f"⚠️  Found {len(overage_users)} users with overage parses\n")
            print("-" * 80)

            total_overage_parses = 0
            total_missed_revenue = 0
            user_reports: List[Dict[str, Any]] = []

            for user in overage_users:
                current_parses = user.parses_this_month
                overage_parses = current_parses - standard_limit
                overage_cost = overage_parses * overage_price

                total_overage_parses += overage_parses
                total_missed_revenue += overage_cost

                # Get parse logs for this user to understand usage pattern
                parse_logs_stmt = (
                    select(func.count(ParseLog.id), func.sum(ParseLog.row_count))
                    .where(ParseLog.user_id == user.id)
                    .where(ParseLog.success == True)
                )
                parse_result = await db.execute(parse_logs_stmt)
                parse_count, total_parses_all_time = parse_result.one()

                user_report = {
                    "user_id": str(user.id),
                    "email": user.email,
                    "current_month_parses": current_parses,
                    "overage_parses": overage_parses,
                    "overage_cost_usd": overage_cost,
                    "total_jobs": parse_count or 0,
                    "all_time_parses": total_parses_all_time or 0,
                    "stripe_customer_id": user.stripe_customer_id,
                    "subscription_id": user.stripe_subscription_id,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                user_reports.append(user_report)

                print(f"📧 {user.email}")
                print(f"   User ID: {user.id}")
                print(f"   Current Month: {current_parses:,} parses")
                print(f"   Overage: {overage_parses:,} parses")
                print(f"   Missed Revenue: ${overage_cost:.2f}")
                print(f"   Total Jobs: {parse_count or 0}")
                print(f"   All-Time Parses: {total_parses_all_time or 0:,}")
                print(
                    f"   Stripe Customer: {user.stripe_customer_id or 'Not linked'}"
                )
                print(
                    f"   Subscription: {user.stripe_subscription_id or 'Not linked'}"
                )
                print()

            print("=" * 80)
            print("💰 REVENUE IMPACT SUMMARY")
            print("=" * 80)
            print(f"Users with overage: {len(overage_users)}")
            print(f"Total overage parses: {total_overage_parses:,}")
            print(f"Total missed revenue: ${total_missed_revenue:.2f}")
            print()

            # Calculate average overage per user
            avg_overage = total_overage_parses / len(overage_users)
            avg_missed_revenue = total_missed_revenue / len(overage_users)
            print(f"Average overage per user: {avg_overage:,.0f} parses")
            print(f"Average missed revenue per user: ${avg_missed_revenue:.2f}")
            print()

            # Categorize by severity
            high_overage = [u for u in user_reports if u["overage_parses"] > 50000]
            medium_overage = [
                u
                for u in user_reports
                if 10000 < u["overage_parses"] <= 50000
            ]
            low_overage = [
                u for u in user_reports if u["overage_parses"] <= 10000
            ]

            print("📊 SEVERITY BREAKDOWN")
            print(f"   High (>50K overage): {len(high_overage)} users")
            print(f"   Medium (10K-50K): {len(medium_overage)} users")
            print(f"   Low (<10K): {len(low_overage)} users")
            print()

            # Recommendations
            print("=" * 80)
            print("📋 RECOMMENDATIONS")
            print("=" * 80)
            print("1. IMMEDIATE ACTIONS:")
            print("   ✅ Deploy the fixed overage billing code")
            print("   ✅ Verify STRIPE_METER_ID is configured correctly")
            print("   ✅ Monitor logs for 'Meter usage for customer' messages")
            print()
            print("2. REVENUE RECOVERY OPTIONS:")
            print("   Option A: Contact high overage users directly")
            print("   Option B: Apply prorated charges to next invoice")
            print("   Option C: Goodwill gesture - waive past charges, fix going forward")
            print(
                "   Option D: Grandfather existing users, apply to new overages only"
            )
            print()
            print("3. COMMUNICATION:")
            print("   - Be transparent about the billing system fix")
            print("   - Emphasize improved accuracy going forward")
            print(
                "   - Consider offering usage monitoring dashboard to prevent surprises"
            )
            print()

            # Export detailed report
            print("=" * 80)
            print("📄 DETAILED REPORT")
            print("=" * 80)

            # Sort by overage amount (highest first)
            user_reports.sort(key=lambda x: x["overage_cost_usd"], reverse=True)

            for i, report in enumerate(user_reports, 1):
                print(f"\n{i}. {report['email']}")
                print(f"   Overage: ${report['overage_cost_usd']:.2f} ({report['overage_parses']:,} parses)")
                if report['stripe_customer_id']:
                    print(f"   Stripe: {report['stripe_customer_id']}")

            print()
            print("=" * 80)
            print("✅ Audit completed successfully")
            print("=" * 80)

            return True

        except Exception as e:
            print(f"❌ Error during audit: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = asyncio.run(audit_overage_users())
    sys.exit(0 if success else 1)
