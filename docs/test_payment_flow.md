# Stripe Payment Flow Test Checklist

## Test the complete payment integration

### 1. Registration Flow
- [ ] Register new user at `/auth/register`
- [ ] Verify user is created with `FREE` plan in database
- [ ] Verify registration returns `checkout_url` in response
- [ ] Verify automatic redirect to Stripe checkout

### 2. Stripe Checkout
- [ ] Complete payment in Stripe checkout (use test card: 4242 4242 4242 4242)
- [ ] Verify redirect back to app after successful payment

### 3. Webhook Processing
- [ ] Verify `checkout.session.completed` webhook is received
- [ ] Verify user is upgraded from `FREE` to `STANDARD` plan
- [ ] Verify `stripe_subscription_id` is saved to user record

### 4. Access Control
- [ ] Try accessing `/` (upload page) with FREE plan - should get 402 error
- [ ] Try accessing `/` with STANDARD plan - should work
- [ ] Try processing a file - verify it works with subscription

### 5. Usage Reporting
- [ ] Process a file with multiple names
- [ ] Check Stripe dashboard for meter events
- [ ] Verify usage is reported immediately (not just queued)

### 6. Billing Page
- [ ] Check `/billing` page shows active subscription
- [ ] Verify portal link works for managing subscription
- [ ] Test cancellation flow

## Database Queries to Verify

```sql
-- Check user plan status
SELECT id, email, plan, stripe_customer_id, stripe_subscription_id 
FROM users 
WHERE email = 'test@example.com';

-- Check webhook events
SELECT * FROM webhook_events 
ORDER BY created_at DESC 
LIMIT 10;

-- Check processing jobs and usage
SELECT id, user_id, processed_rows, successful_parses 
FROM processing_jobs 
WHERE user_id = (SELECT id FROM users WHERE email = 'test@example.com')
ORDER BY created_at DESC;
```

## Environment Variables to Verify

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_METER_WEBHOOK_SECRET=whsec_...
STRIPE_STANDARD_MONTHLY_PRICE_ID=price_...
STRIPE_STANDARD_YEARLY_PRICE_ID=price_...
STRIPE_METER_NAME=tidyframe_token
```

## Common Issues and Fixes

1. **Webhook not received**: Check webhook URL matches Stripe dashboard
2. **User not upgraded**: Check webhook secret is correct
3. **Usage not reported**: Check meter name matches Stripe configuration
4. **402 errors after payment**: Check plan upgrade in webhook handler

## Summary of Changes Made

### Backend
1. Fixed webhook URLs to match Stripe configuration (`/api/stripe/webhook` and `/api/stripe/meter/webhook`)
2. Users now start with `FREE` plan on registration (not `STANDARD`)
3. Registration creates Stripe checkout session and returns URL
4. Added `checkout.session.completed` webhook handler to upgrade plans
5. Subscription deletion now downgrades to `FREE` plan
6. Usage is reported immediately using Meter Events API v2
7. Billing middleware blocks `FREE` plan users from processing

### Frontend
1. Extended `LoginResponse` type to include checkout fields
2. AuthContext handles checkout redirect after registration
3. RegisterPage doesn't show success toast when redirecting
4. API service handles 402 errors and redirects to pricing
5. User type now includes `'free'` plan option

### Database
1. Added `FREE` plan type to `PlanType` enum
2. Default plan for new users is `FREE` (requires payment to upgrade)

## Testing Commands

```bash
# Watch backend logs
docker-compose logs -f backend

# Test webhook locally with Stripe CLI
stripe listen --forward-to localhost:8000/api/stripe/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.created

# Check meter events
stripe events list --type=v1.billing.meter.error_report_triggered
```