import { useState, useEffect } from 'react';
import { Link, useSearchParams, Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

export default function EmailVerificationPage() {
  const { user, verifyEmail } = useAuth();
  const [searchParams] = useSearchParams();
  const [verifying, setVerifying] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const token = searchParams.get('token');

  useEffect(() => {
    const handleVerification = async () => {
      if (!token) {
        setError('Verification token is missing');
        setVerifying(false);
        return;
      }

      try {
        await verifyEmail(token);
        setSuccess(true);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error && 'response' in err && 
          err.response && typeof err.response === 'object' && 
          'data' in err.response && 
          err.response.data && typeof err.response.data === 'object' && 
          'message' in err.response.data && 
          typeof err.response.data.message === 'string'
          ? err.response.data.message
          : 'Email verification failed';
        setError(errorMessage);
      } finally {
        setVerifying(false);
      }
    };

    handleVerification();
  }, [token, verifyEmail]);

  // Redirect if user is already logged in and verified
  if (user && user.emailVerified) {
    return <Navigate to="/dashboard" replace />;
  }

  if (verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-6">
              <Link to="/">
                <img src="/logo-with-name.png" alt="TidyFrame" className="h-12" />
              </Link>
            </div>
            <div className="flex justify-center mb-4">
              <Loader2 className="h-12 w-12 text-primary animate-spin" />
            </div>
            <CardTitle className="text-2xl font-bold">Verifying your email</CardTitle>
            <CardDescription>
              Please wait while we verify your email address...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-6">
              <Link to="/">
                <img src="/logo-with-name.png" alt="TidyFrame" className="h-12" />
              </Link>
            </div>
            <div className="flex justify-center mb-4">
              <CheckCircle className="h-12 w-12 text-status-success" />
            </div>
            <CardTitle className="text-2xl font-bold text-status-success">
              Email verified successfully!
            </CardTitle>
            <CardDescription>
              Your email address has been verified. You can now access all features.
            </CardDescription>
          </CardHeader>
          
          <CardFooter className="flex flex-col space-y-4">
            <Link to="/dashboard" className="w-full">
              <Button className="w-full">
                Go to Dashboard
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-6">
            <Link to="/">
              <img src="/logo-with-name.png" alt="TidyFrame" className="h-12" />
            </Link>
          </div>
          <div className="flex justify-center mb-4">
            <XCircle className="h-12 w-12 text-status-error" />
          </div>
          <CardTitle className="text-2xl font-bold text-status-error">
            Email verification failed
          </CardTitle>
          <CardDescription>
            We couldn't verify your email address
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
        
        <CardFooter className="flex flex-col space-y-4">
          <p className="text-sm text-muted-foreground text-center">
            The verification link may have expired or is invalid. 
            Please request a new verification email from your account settings.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-2 w-full">
            <Link to="/auth/login" className="flex-1">
              <Button variant="outline" className="w-full">
                Sign In
              </Button>
            </Link>
            <Link to="/dashboard" className="flex-1">
              <Button className="w-full">
                Go to Dashboard
              </Button>
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}