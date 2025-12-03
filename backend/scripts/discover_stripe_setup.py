#!/usr/bin/env python3
"""
Discover and validate complete Stripe billing configuration

This script queries Stripe to:
1. Find the meter ID for event name "tidyframe_token"
2. Validate overage price configuration
3. Verify meter is linked to the price
4. Display complete billing setup for verification
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the backend app to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def discover_stripe_setup():
    """Discover complete Stripe billing configuration"""
    import stripe
    from app.core.config import settings

    # Initialize Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not stripe.api_key or stripe.api_key.startswith("your-") or stripe.api_key.startswith("sk_test") and len(stripe.api_key) < 20:
        print("❌ STRIPE_SECRET_KEY not configured properly!")
        print(f"   Current value starts with: {stripe.api_key[:15] if stripe.api_key else 'None'}...")
        return False

    print("=" * 80)
    print("🔍 STRIPE BILLING CONFIGURATION DISCOVERY")
    print("=" * 80)
    print()

    # Known configuration from environment
    print("📋 CURRENT ENVIRONMENT CONFIGURATION:")
    print(f"   Product ID: {settings.STRIPE_PRODUCT_ID}")
    print(f"   Overage Price ID: {settings.STRIPE_OVERAGE_PRICE_ID}")
    print(f"   Current STRIPE_METER_ID: {settings.STRIPE_METER_ID}")
    print(f"   Standard Monthly: {settings.STRIPE_STANDARD_MONTHLY_PRICE_ID}")
    print(f"   Standard Yearly: {settings.STRIPE_STANDARD_YEARLY_PRICE_ID}")
    print()

    try:
        # Step 1: List all billing meters
        print("🔍 Step 1: Discovering Billing Meters...")
        print("-" * 80)

        meters = stripe.billing.Meter.list(limit=100)

        tidyframe_meter = None
        for meter in meters.data:
            print(f"\n📊 Meter: {meter.id}")
            print(f"   Event Name: {meter.event_name}")
            print(f"   Display Name: {meter.display_name}")
            print(f"   Status: {meter.status}")

            if meter.event_name == "tidyframe_token":
                tidyframe_meter = meter
                print("   ✅ THIS IS THE TIDYFRAME METER!")

        if not tidyframe_meter:
            print("\n❌ ERROR: Could not find meter with event_name='tidyframe_token'")
            print("   You need to create a meter in Stripe Dashboard first!")
            print("   Go to: https://dashboard.stripe.com/billing/meters")
            return False

        print()
        print("=" * 80)
        print("✅ FOUND TIDYFRAME METER")
        print("=" * 80)
        print(f"Meter ID: {tidyframe_meter.id}")
        print(f"Event Name: {tidyframe_meter.event_name}")
        print(f"Display Name: {tidyframe_meter.display_name}")
        print(f"Status: {tidyframe_meter.status}")
        if tidyframe_meter.get('default_aggregation'):
            print(f"Aggregation: {tidyframe_meter['default_aggregation'].get('formula', 'N/A')}")
        print()

        # Step 2: Validate overage price
        print("🔍 Step 2: Validating Overage Price Configuration...")
        print("-" * 80)

        overage_price_id = settings.STRIPE_OVERAGE_PRICE_ID
        if not overage_price_id or overage_price_id.startswith("price_your-"):
            print("❌ STRIPE_OVERAGE_PRICE_ID not configured!")
            return False

        price = stripe.Price.retrieve(overage_price_id)

        print(f"\n💰 Overage Price: {price.id}")
        print(f"   Product: {price.product}")
        print(f"   Unit Amount: ${price.unit_amount / 100:.2f}")
        print(f"   Currency: {price.currency.upper()}")
        print(f"   Billing Scheme: {price.billing_scheme}")
        print(f"   Active: {price.active}")

        if price.recurring:
            print(f"   Recurring: {price.recurring.interval}")
            print(f"   Usage Type: {price.recurring.usage_type}")
            meter_linked = price.recurring.get('meter')
            print(f"   Linked Meter: {meter_linked if meter_linked else 'NOT SET ❌'}")

            # CRITICAL: Check if meter is linked
            if meter_linked:
                if meter_linked == tidyframe_meter.id:
                    print("   ✅ METER IS CORRECTLY LINKED TO PRICE!")
                else:
                    print(f"   ❌ METER MISMATCH!")
                    print(f"      Price meter: {meter_linked}")
                    print(f"      Expected: {tidyframe_meter.id}")
                    return False
            else:
                print("   ❌ WARNING: Price does not have a meter linked!")
                print("      This price will not track usage correctly.")
                print("      You need to update the price in Stripe Dashboard to link the meter.")
        else:
            print("   ❌ ERROR: Overage price is not recurring!")
            return False

        print()

        # Step 3: Validate product configuration
        print("🔍 Step 3: Validating Product Configuration...")
        print("-" * 80)

        product_id = settings.STRIPE_PRODUCT_ID
        if product_id and not product_id.startswith("prod_your-"):
            product = stripe.Product.retrieve(product_id)
            print(f"\n📦 Product: {product.id}")
            print(f"   Name: {product.name}")
            print(f"   Active: {product.active}")
            if product.get('default_price'):
                print(f"   Default Price: {product.default_price}")
        else:
            print("\n⚠️  STRIPE_PRODUCT_ID not configured")

        print()

        # Step 4: Validate subscription prices
        print("🔍 Step 4: Validating Subscription Prices...")
        print("-" * 80)

        monthly_price_id = settings.STRIPE_STANDARD_MONTHLY_PRICE_ID
        yearly_price_id = settings.STRIPE_STANDARD_YEARLY_PRICE_ID

        if monthly_price_id and not monthly_price_id.startswith("price_your-"):
            monthly_price = stripe.Price.retrieve(monthly_price_id)
            print(f"\n💵 Monthly Subscription: {monthly_price.id}")
            print(f"   Amount: ${monthly_price.unit_amount / 100:.2f}/{monthly_price.recurring.interval}")
            print(f"   Product: {monthly_price.product}")
            print(f"   Active: {monthly_price.active}")
        else:
            print("\n⚠️  Monthly subscription price not configured")

        if yearly_price_id and not yearly_price_id.startswith("price_your-"):
            yearly_price = stripe.Price.retrieve(yearly_price_id)
            print(f"\n💵 Yearly Subscription: {yearly_price.id}")
            print(f"   Amount: ${yearly_price.unit_amount / 100:.2f}/{yearly_price.recurring.interval}")
            print(f"   Product: {yearly_price.product}")
            print(f"   Active: {yearly_price.active}")
        else:
            print("\n⚠️  Yearly subscription price not configured")

        print()

        # Step 5: Generate configuration recommendations
        print("=" * 80)
        print("📝 RECOMMENDED ENVIRONMENT CONFIGURATION")
        print("=" * 80)
        print()
        print("Add/update these in your .env files:")
        print()
        print("# ============================================================================")
        print("# Stripe Meter Configuration (CRITICAL FOR OVERAGE BILLING)")
        print("# ============================================================================")
        print(f"STRIPE_METER_EVENT_NAME=tidyframe_token")
        print(f"STRIPE_METER_ID={tidyframe_meter.id}")
        print()
        print("# ============================================================================")
        print("# Stripe Product/Price Configuration")
        print("# ============================================================================")
        print(f"STRIPE_PRODUCT_ID={settings.STRIPE_PRODUCT_ID}")
        print(f"STRIPE_OVERAGE_PRICE_ID={settings.STRIPE_OVERAGE_PRICE_ID}")
        print(f"STRIPE_STANDARD_MONTHLY_PRICE_ID={settings.STRIPE_STANDARD_MONTHLY_PRICE_ID}")
        print(f"STRIPE_STANDARD_YEARLY_PRICE_ID={settings.STRIPE_STANDARD_YEARLY_PRICE_ID}")
        print()

        # Step 6: Configuration validation summary
        print("=" * 80)
        print("✅ CONFIGURATION VALIDATION SUMMARY")
        print("=" * 80)
        print()

        checks = []

        # Check 1: Meter exists
        if tidyframe_meter:
            checks.append(("✅", f"Meter exists: {tidyframe_meter.id}"))
            checks.append(("✅", f"Event name: {tidyframe_meter.event_name}"))
        else:
            checks.append(("❌", "Meter not found"))

        # Check 2: Overage price configured
        if price.recurring and price.recurring.get('usage_type') == 'metered':
            checks.append(("✅", "Overage price is metered billing type"))
        else:
            checks.append(("❌", "Overage price is not metered"))

        # Check 3: Meter linked to price
        if price.recurring and price.recurring.get('meter') == tidyframe_meter.id:
            checks.append(("✅", "Overage price correctly linked to meter"))
        else:
            checks.append(("❌", "Overage price NOT linked to meter - FIX REQUIRED"))

        # Check 4: Price matches configuration
        expected_overage = settings.OVERAGE_PRICE_PER_UNIT * 100  # Convert to cents
        actual_overage = price.unit_amount
        if abs(expected_overage - actual_overage) < 1:  # Allow for rounding
            checks.append(("✅", f"Overage price correct: ${price.unit_amount / 100:.2f} per unit"))
        else:
            checks.append(("⚠️", f"Overage price mismatch: Stripe=${actual_overage/100:.2f}, Config=${expected_overage/100:.2f}"))

        # Check 5: Environment variable status
        current_meter_id = settings.STRIPE_METER_ID
        if current_meter_id == tidyframe_meter.id:
            checks.append(("✅", "STRIPE_METER_ID correctly set to meter ID"))
        elif current_meter_id == "tidyframe_token":
            checks.append(("❌", "STRIPE_METER_ID contains event name instead of meter ID"))
            checks.append(("🔧", f"REQUIRED FIX: Update STRIPE_METER_ID={tidyframe_meter.id}"))
        else:
            checks.append(("⚠️", f"STRIPE_METER_ID has unexpected value: {current_meter_id}"))

        for status, message in checks:
            print(f"{status} {message}")

        print()

        # Determine overall status
        failed_checks = [c for c in checks if c[0] == "❌"]
        if failed_checks:
            print("=" * 80)
            print("❌ CONFIGURATION HAS ERRORS - MUST BE FIXED BEFORE DEPLOYMENT")
            print("=" * 80)
            print()
            print("NEXT STEPS:")
            print("1. Copy the configuration above to your .env files")
            print(f"2. Update STRIPE_METER_ID={tidyframe_meter.id}")
            print("3. If meter not linked to price, update in Stripe Dashboard")
            print("4. Re-run this script to verify")
            print()
            return False
        else:
            print("=" * 80)
            print("✅ ALL CHECKS PASSED - CONFIGURATION IS VALID")
            print("=" * 80)
            print()
            print("You can proceed with deployment!")
            print()
            return True

    except stripe.error.StripeError as e:
        print(f"\n❌ Stripe API Error: {e}")
        print(f"   Error type: {type(e).__name__}")
        if hasattr(e, 'user_message'):
            print(f"   Message: {e.user_message}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(discover_stripe_setup())
    sys.exit(0 if success else 1)
