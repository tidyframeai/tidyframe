import { useEffect } from 'react';
import { logger } from '@/utils/logger';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { XCircle, ArrowRight, Home } from 'lucide-react';

export default function PaymentCancelledPage() {
  useEffect(() => {
    // Clean up any pending registration state
    localStorage.removeItem('pending_user');
    localStorage.removeItem('registration_complete');

    // Note: User's plan will be reset to FREE by backend on checkout.session.expired webhook
    logger.debug('Payment cancelled - cleaning up local state');
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
              <XCircle className="h-8 w-8 text-muted-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">
            Payment Cancelled
          </CardTitle>
          <CardDescription className="text-base">
            No charges were made to your account
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="space-y-3 text-center">
            <p className="text-sm text-muted-foreground">
              You cancelled the checkout process. Your account remains active with the free trial limits.
            </p>
            <p className="text-sm text-muted-foreground">
              You can try 5 anonymous name parses without signing up, or subscribe anytime to unlock unlimited processing.
            </p>
          </div>

          <div className="space-y-3">
            <Link to="/pricing" className="block">
              <Button className="w-full" size="lg">
                View Pricing Plans
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>

            <Link to="/" className="block">
              <Button variant="outline" className="w-full" size="lg">
                <Home className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </div>

          <div className="pt-4 border-t text-center">
            <p className="text-xs text-muted-foreground mb-3">
              Have questions? We're here to help!
            </p>
            <Link to="/contact">
              <Button variant="link" size="sm" className="text-xs">
                Contact Support
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
