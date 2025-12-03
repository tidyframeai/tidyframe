#!/usr/bin/env python3
"""
Production Admin User Setup for TidyFrame
Creates admin user with proper enterprise permissions and file upload bypass
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the backend app to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def setup_admin_user():
    """Create admin user with full enterprise permissions"""
    
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, PlanType
    from app.core.security import get_password_hash
    from sqlalchemy import select
    from datetime import datetime, timezone
    import uuid
    
    # Get admin credentials from environment
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@tidyframe.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    print(f"🔧 Setting up admin user: {admin_email}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin exists
            result = await db.execute(
                select(User).where(User.email == admin_email)
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                print("✅ Admin user already exists - updating...")
                # Update existing admin
                admin.password_hash = get_password_hash(admin_password)
                admin.plan = PlanType.ENTERPRISE
                admin.is_admin = True
                admin.email_verified = True
                admin.is_active = True
                admin.custom_monthly_limit = 10000000  # Unlimited processing
                admin.parses_this_month = 0
            else:
                print("🆕 Creating new admin user...")
                # Create new admin
                admin = User(
                    id=uuid.uuid4(),
                    email=admin_email,
                    password_hash=get_password_hash(admin_password),
                    plan=PlanType.ENTERPRISE,
                    is_admin=True,  # CRITICAL: Admin flag for file upload bypass
                    email_verified=True,
                    is_active=True,
                    custom_monthly_limit=10000000,  # 10M names per month
                    parses_this_month=0,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(admin)
            
            await db.commit()
            
            print("✅ Admin user configured successfully!")
            print(f"   📧 Email: {admin_email}")
            print(f"   🔑 Password: {'*' * len(admin_password)}")
            print(f"   👑 Plan: ENTERPRISE")
            print(f"   🔓 Admin Privileges: YES (bypasses subscription checks)")
            print(f"   📊 Monthly Limit: {admin.custom_monthly_limit:,} names")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up admin: {e}")
            await db.rollback()
            return False

if __name__ == "__main__":
    success = asyncio.run(setup_admin_user())
    sys.exit(0 if success else 1)