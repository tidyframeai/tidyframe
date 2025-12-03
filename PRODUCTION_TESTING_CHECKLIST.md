# TidyFrame Production Testing Checklist

## Prerequisites

Before running tests, ensure:
- [ ] Database migrations executed: `cd backend && alembic upgrade head`
- [ ] Celery workers running: `celery -A app.core.celery_app worker --loglevel=info`
- [ ] Celery beat scheduler running: `celery -A app.core.celery_app beat --loglevel=info`
- [ ] Stripe CLI installed for webhook testing: `stripe listen --forward-to localhost:8000/api/billing/stripe/webhook`
- [ ] Test mode enabled in Stripe Dashboard

---

## Phase 1: Database Migrations ✅

### Execute Migrations
```bash
cd /home/aditya/dev/tidyframe/backend
alembic upgrade head
```

### Verify Tables Created
```bash
psql $DATABASE_URL -c "\d failed_stripe_reports"
psql $DATABASE_URL -c "\d+ users" | grep -E "last_reset_at|last_reset_source"
```

**Expected Output:**
- `failed_stripe_reports` table with columns: id, user_id, customer_id, quantity, retry_count, next_retry_at, succeeded_at
- `users` table has new columns: last_reset_at, last_reset_source

---

## Phase 2: Complete Subscription Flow 🔄

### Test A1: New Subscription Checkout

**Steps:**
1. Navigate to `/pricing` or click "Upgrade to Standard" from dashboard
2. Click "Start Free Trial" or "Subscribe" for Standard plan ($99/month)
3. Use Stripe test card: `4242 4242 4242 4242`, Exp: 12/34, CVC: 123
4. Complete checkout

**Verify:**
- [ ] Redirected to `/dashboard/billing?success=true`
- [ ] Dashboard shows "Activating Your Subscription" banner (grace period)
- [ ] After ~10 seconds, banner disappears (webhook processed)
- [ ] User plan shows "STANDARD" in dashboard
- [ ] `parses_this_month` reset to 0
- [ ] `month_reset_date` set to 30 days from now

**Database Check:**
```sql
SELECT
  id, email, plan, parses_this_month,
  last_reset_at, last_reset_source,
  stripe_customer_id, stripe_subscription_id
FROM users
WHERE email = 'YOUR_TEST_EMAIL';
```

**Expected:**
- `plan = 'STANDARD'`
- `parses_this_month = 0`
- `last_reset_source = 'webhook'`
- `last_reset_at` is recent timestamp

---

### Test A2: File Upload & Parse Tracking

**Steps:**
1. Navigate to `/dashboard/upload`
2. Upload test CSV with 1000 rows:
   ```csv
   name
   John Smith
   Jane Doe
   ...  (add 998 more rows)
   ```
3. Wait for processing to complete

**Verify:**
- [ ] Processing completes successfully
- [ ] Dashboard shows 1000 parses used
- [ ] `parses_this_month` incremented by 1000
- [ ] No errors in backend logs

**Database Checks:**
```sql
-- Check parse count updated
SELECT email, parses_this_month, monthly_limit
FROM users
WHERE email = 'YOUR_TEST_EMAIL';

-- Check Stripe usage reported
SELECT COUNT(*) FROM failed_stripe_reports
WHERE user_id = (SELECT id FROM users WHERE email = 'YOUR_TEST_EMAIL');
```

**Expected:**
- `parses_this_month = 1000`
- `failed_stripe_reports` count = 0 (no failed reports)

**Stripe Dashboard Check:**
1. Go to Stripe Dashboard → Billing → Meters
2. Find "tidyframe_token" meter
3. Verify 1000 events recorded for customer

---

### Test A3: Overage Warning Popup

**Steps:**
1. Set user limit to 500 parses (via Django admin or SQL):
   ```sql
   UPDATE users
   SET custom_monthly_limit = 500
   WHERE email = 'YOUR_TEST_EMAIL';
   ```
2. Navigate to `/dashboard/upload`
3. Upload CSV with 1000 rows

**Verify:**
- [ ] **Overage warning popup appears** before upload
- [ ] Shows correct overage amount: 500 parses
- [ ] Shows correct overage cost: $5.00 (500 × $0.01)
- [ ] Warning message: "This upload will exceed your monthly limit by 500 parses..."
- [ ] Two buttons: "Continue with Upload" and "Cancel"
- [ ] Clicking "Cancel" closes popup without uploading
- [ ] Clicking "Continue" proceeds with upload

**After Upload:**
```sql
-- Verify overage flag set correctly
SELECT
  pl.row_count,
  pl.is_overage,
  u.parses_this_month
FROM parse_logs pl
JOIN users u ON pl.user_id = u.id
WHERE u.email = 'YOUR_TEST_EMAIL'
ORDER BY pl.timestamp DESC
LIMIT 1;
```

**Expected:**
- `is_overage = true` for rows beyond 500 limit
- `parses_this_month = 1500` (500 + 1000)

---

## Phase 3: Subscription Cancellation Flow 🚫

### Test B1: Cancel Subscription (Retain Access)

**Steps:**
1. Navigate to `/dashboard/billing`
2. Click "Manage Subscription" button
3. In Stripe portal, click "Cancel plan"
4. Select "Cancel at end of billing period"
5. Confirm cancellation

**Verify:**
- [ ] Redirected back to dashboard
- [ ] Billing page shows "Your subscription will end on [DATE]"
- [ ] `cancel_at_period_end = true` in subscription status
- [ ] User **can still upload files** (access retained until period end)
- [ ] Dashboard shows warning: "Subscription ending soon"

**Database Check:**
```sql
SELECT email, plan, stripe_subscription_id, month_reset_date
FROM users
WHERE email = 'YOUR_TEST_EMAIL';
```

**Expected:**
- `plan` still shows 'STANDARD' (doesn't change until period ends)

---

### Test B2: Period End Downgrade

**Trigger Webhook (Stripe CLI):**
```bash
stripe trigger customer.subscription.deleted
```

**Verify:**
- [ ] User plan downgraded to 'FREE'
- [ ] Dashboard shows "Upgrade to Standard" button
- [ ] Upload page shows "5 parses remaining" (anonymous limit)
- [ ] stripe_subscription_id cleared

**Database Check:**
```sql
SELECT email, plan, stripe_subscription_id
FROM users
WHERE email = 'YOUR_TEST_EMAIL';
```

**Expected:**
- `plan = 'FREE'`
- `stripe_subscription_id = NULL`

---

## Phase 4: Billing Reset Coordination ⚙️

### Test C1: Webhook Primary Reset

**Setup:**
1. Ensure Celery beat is running
2. User has STANDARD subscription active

**Trigger Invoice Webhook:**
```bash
stripe trigger invoice.payment_succeeded
```

**Verify:**
- [ ] `parses_this_month` reset to 0
- [ ] `last_reset_source = 'webhook'`
- [ ] `last_reset_at` updated to current timestamp
- [ ] Backend logs show: `payment_succeeded_processed`

---

### Test C2: Celery Fallback (Webhook Handled)

**Steps:**
1. Wait 1 minute after webhook reset
2. Manually trigger Celery task:
   ```bash
   celery -A app.core.celery_app call app.workers.cleanup.reset_monthly_usage
   ```

**Verify:**
- [ ] Celery logs show: `celery_reset_skipped_webhook_handled`
- [ ] `parses_this_month` **not changed** (still 0)
- [ ] `last_reset_source` still shows 'webhook'
- [ ] No duplicate reset occurred

---

### Test C3: Celery Fallback (Webhook Failed)

**Setup:**
1. Set `last_reset_at = NULL` to simulate missed webhook:
   ```sql
   UPDATE users
   SET last_reset_at = NULL,
       last_reset_source = NULL,
       parses_this_month = 5000
   WHERE email = 'YOUR_TEST_EMAIL';
   ```

2. Trigger Celery task:
   ```bash
   celery -A app.core.celery_app call app.workers.cleanup.reset_monthly_usage
   ```

**Verify:**
- [ ] Celery logs show: `celery_fallback_reset_triggered`
- [ ] `parses_this_month` reset to 0
- [ ] `last_reset_source = 'celery'`
- [ ] `last_reset_at` updated

---

## Phase 5: Invoice Preview Accuracy 💰

### Test D1: Standard User with No Overage

**Setup:**
```sql
UPDATE users
SET parses_this_month = 50000
WHERE email = 'YOUR_TEST_EMAIL';
```

**Test:**
1. Navigate to `/dashboard`
2. Check "Next Invoice" card

**Verify:**
- [ ] Invoice preview card appears
- [ ] Shows: `$99.00` (base subscription only)
- [ ] Days remaining shows correct countdown
- [ ] No overage warning displayed
- [ ] Card has normal styling (not warning colors)

---

### Test D2: Standard User with Overage

**Setup:**
```sql
UPDATE users
SET parses_this_month = 150000
WHERE email = 'YOUR_TEST_EMAIL';
```

**Test:**
1. Refresh dashboard
2. Check "Next Invoice" card

**Verify:**
- [ ] Invoice preview shows: `$599.00`
  - Base: $99.00
  - Overage: $500.00 (50,000 × $0.01)
  - Total: $599.00
- [ ] Shows overage breakdown: "+$500.00 overage"
- [ ] Card has warning styling (yellow/orange border)
- [ ] Days remaining accurate

**API Test:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/billing/invoice-preview
```

**Expected JSON:**
```json
{
  "base_subscription_cost": 99.0,
  "current_overage_amount": 50000,
  "current_overage_cost": 500.0,
  "estimated_total": 599.0,
  "days_until_invoice": 28,
  "billing_period_end": "2025-01-02T00:00:00Z",
  "has_overage": true,
  "plan_name": "STANDARD",
  "billing_period": "monthly"
}
```

---

## Phase 6: Stripe Usage Report Retry Queue 🔄

### Test E1: Simulated API Failure

**Setup:**
1. Temporarily break Stripe API (wrong API key or network issue)
2. Upload file with 100 rows

**Verify:**
- [ ] Upload succeeds
- [ ] Backend logs show: `stripe_usage_report_failed`
- [ ] Backend logs show: `stripe_usage_queued_for_retry`
- [ ] Entry created in `failed_stripe_reports` table

**Database Check:**
```sql
SELECT * FROM failed_stripe_reports
WHERE user_id = (SELECT id FROM users WHERE email = 'YOUR_TEST_EMAIL')
ORDER BY created_at DESC LIMIT 1;
```

**Expected:**
- `retry_count = 0`
- `quantity = 100`
- `next_retry_at` is ~5 minutes in future

---

### Test E2: Retry Success

**Setup:**
1. Fix Stripe API connection
2. Wait for Celery beat to trigger retry (5 minutes) OR manually run:
   ```bash
   celery -A app.core.celery_app call app.workers.webhook_retry.retry_failed_stripe_reports
   ```

**Verify:**
- [ ] Celery logs show: `stripe_usage_retry_success`
- [ ] `succeeded_at` timestamp updated in database
- [ ] Usage visible in Stripe Dashboard → Meters

**Database Check:**
```sql
SELECT
  retry_count,
  succeeded_at,
  last_error
FROM failed_stripe_reports
WHERE id = 'REPORT_ID';
```

**Expected:**
- `retry_count = 1`
- `succeeded_at` is NOT NULL
- `last_error` is NULL or empty

---

## Phase 7: Dashboard Design Validation 🎨

### Visual Checklist

**Desktop (1920px):**
- [ ] All cards aligned properly
- [ ] Spacing consistent (16px/24px grid)
- [ ] Icons properly sized and colored
- [ ] Invoice preview card fits in 4-column grid
- [ ] No text overflow or truncation
- [ ] Shadows and borders render correctly

**Tablet (768px):**
- [ ] Cards stack to 2 columns
- [ ] Invoice preview moves to second row
- [ ] Touch targets ≥ 44px
- [ ] No horizontal scroll

**Mobile (375px):**
- [ ] Cards stack to 1 column
- [ ] Text remains readable
- [ ] Buttons full-width
- [ ] Stats cards properly scaled

**Dark Mode:**
- [ ] All text readable
- [ ] Contrast ratios maintained
- [ ] Gradients visible but subtle
- [ ] Invoice preview warning colors work

---

## Phase 8: Critical Edge Cases 🔬

### Test F1: Concurrent Uploads

**Steps:**
1. Open 3 browser tabs
2. Upload files simultaneously

**Verify:**
- [ ] All uploads process correctly
- [ ] `parses_this_month` accurate (no race condition)
- [ ] All usage reported to Stripe

---

### Test F2: Large File (10K+ rows)

**Steps:**
1. Upload CSV with 10,000 rows
2. Monitor processing

**Verify:**
- [ ] Processing completes without timeout
- [ ] All rows processed
- [ ] Stripe meter accepts large quantity
- [ ] No memory issues

---

### Test F3: Rapid Subscription Changes

**Steps:**
1. Subscribe to STANDARD
2. Immediately cancel
3. Immediately resubscribe

**Verify:**
- [ ] No orphaned subscriptions in Stripe
- [ ] Database state consistent
- [ ] No duplicate charges

---

## Success Criteria ✅

All tests must pass with:
- ✅ **Zero database inconsistencies**
- ✅ **All Stripe meter events recorded**
- ✅ **No failed reports after retry**
- ✅ **Accurate invoice previews**
- ✅ **No double resets**
- ✅ **WCAG AA contrast compliance**

---

## Post-Testing Cleanup

```sql
-- Reset test user
UPDATE users
SET parses_this_month = 0,
    custom_monthly_limit = NULL
WHERE email = 'YOUR_TEST_EMAIL';

-- Clear failed reports
DELETE FROM failed_stripe_reports
WHERE user_id = (SELECT id FROM users WHERE email = 'YOUR_TEST_EMAIL');
```

---

## Logs to Monitor

**Backend (FastAPI):**
```bash
tail -f backend/logs/app.log | grep -E "stripe_usage|billing_reset|overage"
```

**Celery Worker:**
```bash
celery -A app.core.celery_app worker --loglevel=info
```

**Celery Beat:**
```bash
celery -A app.core.celery_app beat --loglevel=info
```

**Stripe Webhooks:**
```bash
stripe listen --forward-to http://localhost:8000/api/billing/stripe/webhook
```

---

**Testing Started:** _____________
**Testing Completed:** _____________
**Tester:** _____________
**Result:** ✅ PASS / ❌ FAIL

**Notes:**
