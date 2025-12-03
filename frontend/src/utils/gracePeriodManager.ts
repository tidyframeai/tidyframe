/**
 * Grace Period Manager
 *
 * Manages a grace period for users who have just completed payment but whose
 * subscription hasn't been activated yet via Stripe webhook. This prevents
 * users from being redirected to the pricing page immediately after payment.
 *
 * Uses sessionStorage so the grace period persists across navigation but not
 * across browser sessions (intentional - if user closes tab, they'll need to
 * wait for webhook or manually refresh subscription status).
 */

import { logger } from './logger';

const GRACE_PERIOD_KEY = 'payment_grace_period_timestamp';
const GRACE_PERIOD_DURATION_MS = 180000; // 180 seconds (3 minutes)

/**
 * Set the grace period timestamp (call this immediately after payment success)
 */
export function setPaymentGracePeriod(): void {
  const timestamp = Date.now();
  sessionStorage.setItem(GRACE_PERIOD_KEY, timestamp.toString());
  logger.debug('Grace period activated', {
    timestamp,
    durationMs: GRACE_PERIOD_DURATION_MS,
    expiresAt: new Date(timestamp + GRACE_PERIOD_DURATION_MS).toISOString()
  });
}

/**
 * Check if user is currently within the payment grace period
 * @returns true if within 90 seconds of payment completion
 */
export function isInPaymentGracePeriod(): boolean {
  const timestampStr = sessionStorage.getItem(GRACE_PERIOD_KEY);

  if (!timestampStr) {
    return false;
  }

  const timestamp = parseInt(timestampStr, 10);
  const now = Date.now();
  const elapsedMs = now - timestamp;

  // Check if still within grace period
  if (elapsedMs < GRACE_PERIOD_DURATION_MS) {
    return true;
  }

  // Grace period expired - clean up and log
  logger.debug('Grace period expired', {
    timestamp,
    elapsedMs,
    durationMs: GRACE_PERIOD_DURATION_MS
  });
  clearPaymentGracePeriod();
  return false;
}

/**
 * Clear the grace period (call this when subscription is confirmed active)
 */
export function clearPaymentGracePeriod(): void {
  const timestampStr = sessionStorage.getItem(GRACE_PERIOD_KEY);

  if (timestampStr) {
    const timestamp = parseInt(timestampStr, 10);
    const elapsedMs = Date.now() - timestamp;

    logger.debug('Grace period cleared', {
      timestamp,
      elapsedMs,
      reason: 'Subscription confirmed active or grace period expired'
    });
  }

  sessionStorage.removeItem(GRACE_PERIOD_KEY);
}

/**
 * Get remaining grace period time in milliseconds
 * @returns milliseconds remaining, or 0 if expired/not set
 */
export function getRemainingGracePeriodMs(): number {
  const timestampStr = sessionStorage.getItem(GRACE_PERIOD_KEY);

  if (!timestampStr) {
    return 0;
  }

  const timestamp = parseInt(timestampStr, 10);
  const now = Date.now();
  const elapsedMs = now - timestamp;
  const remainingMs = Math.max(0, GRACE_PERIOD_DURATION_MS - elapsedMs);

  return remainingMs;
}
