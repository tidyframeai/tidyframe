#!/usr/bin/env python3
"""
Validate Stripe billing configuration for overage billing

This script validates that all Stripe configuration is correct:
1. Environment variables are set
2. IDs have correct format
3. Meter ID matches event name in Stripe
4. Overage price is linked to meter
5. Subscription prices are active
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the backend app to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def validate_stripe_config():
    """Validate complete Stripe billing configuration"""
    import stripe
    from app.core.config import settings

    # Initialize Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not stripe.api_key:
        print("❌ STRIPE_SECRET_KEY not configured!")
        return False

    print("=" * 80)
    print("✅ STRIPE CONFIGURATION VALIDATION")
    print("=" * 80)
    print()

    all_checks_passed = True
    checks = []

    # Section 1: Environment Variable Validation
    print("📋 Section 1: Environment Variables")
    print("-" * 80)

    env_vars = {
        "STRIPE_SECRET_KEY": settings.STRIPE_SECRET_KEY,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        "STRIPE_WEBHOOK_SECRET": settings.STRIPE_WEBHOOK_SECRET,
        "STRIPE_BILLING_METER_WEBHOOK_SECRET": settings.STRIPE_BILLING_METER_WEBHOOK_SECRET,
        "STRIPE_PRODUCT_ID": settings.STRIPE_PRODUCT_ID,
        "STRIPE_STANDARD_MONTHLY_PRICE_ID": settings.STRIPE_STANDARD_MONTHLY_PRICE_ID,
        "STRIPE_STANDARD_YEARLY_PRICE_ID": settings.STRIPE_STANDARD_YEARLY_PRICE_ID,
        "STRIPE_OVERAGE_PRICE_ID": settings.STRIPE_OVERAGE_PRICE_ID,
        "STRIPE_METER_EVENT_NAME": settings.STRIPE_METER_EVENT_NAME,
        "STRIPE_METER_ID": settings.STRIPE_METER_ID,
    }

    for var_name, var_value in env_vars.items():
        if not var_value or var_value.startswith(("your-", "sk_test_" + "x" * 10)):
            checks.append(("❌", f"{var_name} not configured"))
            all_checks_passed = False
        else:
            checks.append(("✅", f"{var_name} configured"))

    # Special validation for meter event name
    if settings.STRIPE_METER_EVENT_NAME == "tidyframe_token":
        checks.append(("✅", "STRIPE_METER_EVENT_NAME is 'tidyframe_token'"))
    else:
        checks.append(("⚠️", f"STRIPE_METER_EVENT_NAME is '{settings.STRIPE_METER_EVENT_NAME}' (expected 'tidyframe_token')"))

    # Special validation for meter ID format
    if settings.STRIPE_METER_ID:
        if settings.STRIPE_METER_ID.startswith("mtr_"):
            checks.append(("✅", f"STRIPE_METER_ID has correct format: {settings.STRIPE_METER_ID}"))
        else:
            checks.append(("❌", f"STRIPE_METER_ID does not start with 'mtr_': {settings.STRIPE_METER_ID}"))
            all_checks_passed = False

    for status, message in checks:
        print(f"{status} {message}")

    print()

    # Section 2: Stripe API Validation
    print("📋 Section 2: Stripe API Validation")
    print("-" * 80)

    try:
        # Validate meter exists and matches
        meters = stripe.billing.Meter.list(limit=100)
        tidyframe_meter = None

        for meter in meters.data:
            if meter.event_name == settings.STRIPE_METER_EVENT_NAME:
                tidyframe_meter = meter
                break

        if tidyframe_meter:
            print(f"✅ Found meter with event_name='{settings.STRIPE_METER_EVENT_NAME}'")
            print(f"   Meter ID: {tidyframe_meter.id}")

            if tidyframe_meter.id == settings.STRIPE_METER_ID:
                print(f"✅ STRIPE_METER_ID matches meter in Stripe")
            else:
                print(f"❌ STRIPE_METER_ID mismatch!")
                print(f"   Environment: {settings.STRIPE_METER_ID}")
                print(f"   Stripe: {tidyframe_meter.id}")
                print(f"   → Update STRIPE_METER_ID={tidyframe_meter.id}")
                all_checks_passed = False
        else:
            print(f"❌ No meter found with event_name='{settings.STRIPE_METER_EVENT_NAME}'")
            print("   → Create a meter in Stripe Dashboard with this event name")
            all_checks_passed = False

        # Validate overage price
        overage_price = stripe.Price.retrieve(settings.STRIPE_OVERAGE_PRICE_ID)
        print(f"\n✅ Overage price exists: {overage_price.id}")
        print(f"   Amount: ${overage_price.unit_amount / 100:.2f}")
        print(f"   Currency: {overage_price.currency.upper()}")

        if overage_price.recurring:
            if overage_price.recurring.get('usage_type') == 'metered':
                print(f"✅ Overage price is metered")
            else:
                print(f"❌ Overage price is not metered: {overage_price.recurring.get('usage_type')}")
                all_checks_passed = False

            if tidyframe_meter and overage_price.recurring.get('meter') == tidyframe_meter.id:
                print(f"✅ Overage price linked to correct meter")
            elif tidyframe_meter:
                print(f"❌ Overage price not linked to meter!")
                print(f"   Price meter: {overage_price.recurring.get('meter')}")
                print(f"   Expected: {tidyframe_meter.id}")
                print("   → Update the price in Stripe Dashboard to link the meter")
                all_checks_passed = False
        else:
            print(f"❌ Overage price is not recurring!")
            all_checks_passed = False

        # Validate subscription prices
        monthly_price = stripe.Price.retrieve(settings.STRIPE_STANDARD_MONTHLY_PRICE_ID)
        print(f"\n✅ Monthly price exists: {monthly_price.id}")
        print(f"   Amount: ${monthly_price.unit_amount / 100:.2f}/{monthly_price.recurring.interval}")
        print(f"   Active: {monthly_price.active}")

        if settings.STRIPE_STANDARD_YEARLY_PRICE_ID:
            yearly_price = stripe.Price.retrieve(settings.STRIPE_STANDARD_YEARLY_PRICE_ID)
            print(f"\n✅ Yearly price exists: {yearly_price.id}")
            print(f"   Amount: ${yearly_price.unit_amount / 100:.2f}/{yearly_price.recurring.interval}")
            print(f"   Active: {yearly_price.active}")

        print()

        # Section 3: Configuration Summary
        print("=" * 80)
        print("📊 CONFIGURATION SUMMARY")
        print("=" * 80)
        print()

        if all_checks_passed:
            print("✅ ALL VALIDATION CHECKS PASSED!")
            print()
            print("Your Stripe billing configuration is correct and ready for production.")
            print()
            print("Configuration:")
            print(f"  • Meter Event Name: {settings.STRIPE_METER_EVENT_NAME}")
            print(f"  • Meter ID: {settings.STRIPE_METER_ID}")
            print(f"  • Overage Price: {settings.STRIPE_OVERAGE_PRICE_ID}")
            print(f"  • Monthly Price: {settings.STRIPE_STANDARD_MONTHLY_PRICE_ID}")
            if settings.STRIPE_STANDARD_YEARLY_PRICE_ID:
                print(f"  • Yearly Price: {settings.STRIPE_STANDARD_YEARLY_PRICE_ID}")
            print()
        else:
            print("❌ VALIDATION FAILED - FIX REQUIRED")
            print()
            print("Please fix the errors above before deploying to production.")
            print()

        return all_checks_passed

    except stripe.error.StripeError as e:
        print(f"\n❌ Stripe API Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(validate_stripe_config())
    sys.exit(0 if success else 1)
