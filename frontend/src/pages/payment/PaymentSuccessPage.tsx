import { useEffect, useState } from 'react';
import { logger } from '@/utils/logger';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle, Loader2 } from 'lucide-react';
import { setPaymentGracePeriod } from '@/utils/gracePeriodManager';

export default function PaymentSuccessPage() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [activating, setActivating] = useState(true);
  const [activated, setActivated] = useState(false);

  useEffect(() => {
    const activateUser = async () => {
      try {
        // Set grace period immediately - protects user for 90 seconds while webhook processes
        setPaymentGracePeriod();
        logger.debug('Payment grace period activated');

        // Check if user is already activated
        if (user) {
          logger.debug('User already active, redirecting to dashboard');
          setActivated(true);
          setTimeout(() => {
            navigate('/dashboard', { replace: true });
          }, 1500);
          return;
        }

        // Extract pending user from localStorage
        const pendingUserStr = localStorage.getItem('pending_user');
        const registrationComplete = localStorage.getItem('registration_complete');

        if (!pendingUserStr || !registrationComplete) {
          logger.error('No pending user found, redirecting to login');
          navigate('/auth/login', { replace: true });
          return;
        }

        const pendingUser = JSON.parse(pendingUserStr);
        logger.debug('Activating pending user:', pendingUser.email);

        // Simulate activation delay for UX (webhook processing)
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Activate user by fetching current user data with stored token
        const token = localStorage.getItem('token');
        if (token) {
          logger.debug('Activating user with stored token');
          try {
            await refreshUser();
            logger.debug('User activated successfully');
          } catch (error) {
            logger.error('Failed to refresh user, continuing anyway:', error);
            // Continue even if refresh fails - user has valid token
          }
        }

        // Clean up localStorage
        localStorage.removeItem('pending_user');
        localStorage.removeItem('registration_complete');

        // Mark as activated
        setActivated(true);
        setActivating(false);

        // Redirect to dashboard - grace period manager protects access
        setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 1500);

      } catch (error) {
        logger.error('Error activating user:', error);
        // On error, still try to redirect - user has valid tokens and grace period
        setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 2000);
      }
    };

    activateUser();
  }, [user, navigate, refreshUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            {activated ? (
              <CheckCircle className="h-16 w-16 text-success animate-in zoom-in duration-500" />
            ) : (
              <Loader2 className="h-16 w-16 text-primary animate-spin" />
            )}
          </div>
          <CardTitle className="text-2xl font-bold">
            {activated ? 'Payment Successful!' : 'Processing Your Payment'}
          </CardTitle>
          <CardDescription>
            {activated
              ? 'Your account is now active. Redirecting you to start processing...'
              : 'Please wait while we activate your account...'}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 text-center">
          {!activated && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Thank you for subscribing to TidyFrame!
              </p>
              <p className="text-xs text-muted-foreground">
                We're setting up your account with 100,000 monthly name parses.
              </p>
            </div>
          )}

          {activated && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-success">
                ✓ Account activated
              </p>
              <p className="text-sm font-medium text-success">
                ✓ 100,000 monthly parses ready
              </p>
              <p className="text-sm font-medium text-success">
                ✓ Redirecting to dashboard...
              </p>
            </div>
          )}

          {activating && !activated && (
            <div className="flex items-center justify-center space-x-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>This may take a few seconds...</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
