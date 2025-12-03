import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { logger } from '@/utils/logger';
import { isInPaymentGracePeriod, getRemainingGracePeriodMs } from '@/utils/gracePeriodManager';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireSubscription?: boolean;
}

export default function ProtectedRoute({ children, requireSubscription = true }: ProtectedRouteProps) {
  const { user, loading, hasActiveSubscription } = useAuth();
  const location = useLocation();

  // CRITICAL: Use lazy initialization to check grace period BEFORE first render
  // This prevents race condition where component redirects before useEffect sets gracePeriod
  const [gracePeriod, setGracePeriod] = useState(() => {
    const hasPaymentGrace = isInPaymentGracePeriod();
    const hasPendingUser = !!(
      localStorage.getItem('pending_user') &&
      localStorage.getItem('registration_complete')
    );
    const initialGracePeriod = hasPaymentGrace || hasPendingUser;

    if (initialGracePeriod) {
      logger.debug('ProtectedRoute: Initial grace period detected', {
        hasPaymentGrace,
        hasPendingUser
      });
    }

    return initialGracePeriod;
  });

  const [checkingPendingUser, setCheckingPendingUser] = useState(true);

  // Manage pending user grace period timer
  useEffect(() => {
    const managePendingUserTimer = () => {
      if (!user && !loading) {
        const hasPendingUser = !!(
          localStorage.getItem('pending_user') &&
          localStorage.getItem('registration_complete')
        );

        if (hasPendingUser) {
          logger.debug('ProtectedRoute: Managing pending user grace period timer');
          // State already set in lazy init, just manage timer
          // Extended grace period for pending users (60 seconds)
          const timer = setTimeout(() => {
            logger.debug('Pending user grace period timer expired, checking payment grace');
            // After pending user timer expires, check if payment grace period is still active
            setGracePeriod(isInPaymentGracePeriod());
            setCheckingPendingUser(false);
          }, 60000);
          setCheckingPendingUser(false);
          return () => clearTimeout(timer);
        }
      }
      setCheckingPendingUser(false);
    };

    managePendingUserTimer();
  }, [user, loading]);

  // Monitor payment grace period - state already set in lazy init
  useEffect(() => {
    const monitorGracePeriod = () => {
      if (isInPaymentGracePeriod()) {
        const remainingMs = getRemainingGracePeriodMs();
        logger.debug('Payment grace period active - monitoring expiry', { remainingMs });

        // Ensure state is true (should already be from lazy init)
        setGracePeriod(true);

        // Set timer to clear grace period when it expires
        const timer = setTimeout(() => {
          logger.debug('Payment grace period expired');
          setGracePeriod(false);
        }, remainingMs);

        return () => clearTimeout(timer);
      } else {
        // No payment grace period - check if pending user grace is active
        const hasPendingUser = !!(
          localStorage.getItem('pending_user') &&
          localStorage.getItem('registration_complete')
        );

        if (!hasPendingUser) {
          // No grace period at all
          setGracePeriod(false);
        }
      }
    };

    monitorGracePeriod();

    // Re-check every 5 seconds in case grace period is set mid-session
    const interval = setInterval(monitorGracePeriod, 5000);
    return () => clearInterval(interval);
  }, []);

  logger.debug('ProtectedRoute:', {
    user: user ? { id: user.id, email: user.email, plan: user.plan } : null,
    loading,
    hasActiveSubscription,
    gracePeriod,
    requireSubscription,
    path: location.pathname
  });

  if (loading || checkingPendingUser) {
    logger.debug('ProtectedRoute: Still loading, showing spinner');
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user && !gracePeriod) {
    logger.debug('ProtectedRoute: No user found and no grace period, redirecting to login');
    // Redirect to login page with return url
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  // Check subscription requirement
  if (requireSubscription && user) {
    // Enterprise users always have access
    // OR user in grace period after payment (webhook processing)
    // OR has active subscription
    if (user.plan !== 'ENTERPRISE' && !hasActiveSubscription && !gracePeriod) {
      logger.debug('ProtectedRoute: No active subscription and not in grace period, redirecting to pricing');
      return <Navigate to="/pricing" replace />;
    }

    if (gracePeriod) {
      logger.debug('ProtectedRoute: User in grace period after payment - allowing access');
    }
  }

  // If no user but in grace period, show activation loading UI instead of rendering null user
  if (!user && gracePeriod) {
    logger.debug('ProtectedRoute: No user but in grace period, showing activation UI');
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <Card className="w-full max-w-md mx-4">
          <CardContent className="pt-6 text-center space-y-4">
            <div className="flex justify-center">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
            <h3 className="text-lg font-semibold">Activating Your Account</h3>
            <p className="text-sm text-muted-foreground">
              Please wait while we process your subscription and set up your account...
            </p>
            <p className="text-xs text-muted-foreground">
              This usually takes just a few seconds.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  logger.debug('ProtectedRoute: User authenticated with valid subscription, rendering children');
  return <>{children}</>;
}