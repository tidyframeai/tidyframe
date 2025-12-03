import React, { useState } from 'react';
import { logger } from '@/utils/logger';
import { useSitePassword } from '@/contexts/SitePasswordContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Lock, Eye, EyeOff } from 'lucide-react';

interface SitePasswordGateProps {
  children: React.ReactNode;
}

export function SitePasswordGate({ children }: SitePasswordGateProps) {
  const { isEnabled, isAuthenticated, loading, authenticate } = useSitePassword();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Admin routes that bypass site password protection
  // Using window.location since we're outside Router context
  const isAdminRoute = window.location.pathname.startsWith('/admin') || 
                      window.location.pathname.startsWith('/auth');

  logger.debug('SitePasswordGate:', {
    isEnabled,
    isAuthenticated,
    isAdminRoute,
    pathname: window.location.pathname,
    loading
  });

  // If site password is not enabled, user is authenticated, or accessing admin routes, show the content
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isEnabled || isAuthenticated || isAdminRoute) {
    return <>{children}</>;
  }

  // Show password form
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError('Please enter a password');
      return;
    }

    setIsAuthenticating(true);
    setError('');

    try {
      const success = await authenticate(password);
      if (!success) {
        setError('Invalid password. Please try again.');
      }
      // If successful, the context will update and the component will re-render
    } catch {
      setError('Authentication failed. Please try again.');
    } finally {
      setIsAuthenticating(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
      <div className="w-full max-w-md">
        <Card className="border-slate-200 dark:border-slate-700 shadow-xl bg-white dark:bg-slate-900">
          <CardHeader className="space-y-1 text-center">
            <div className="flex justify-center mb-6">
              <img src="/logo-with-name.png" alt="TidyFrame" className="h-16" />
            </div>
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Lock className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl font-semibold">
              Welcome to tidyframe.com
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              This site is currently in pre-launch mode. Please enter the access password to continue.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              
              <div className="space-y-2">
                <Label htmlFor="password" className="font-medium">
                  Access Password
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter access password"
                    className="pr-10"
                    disabled={isAuthenticating}
                    autoFocus
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={isAuthenticating}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground hover:text-foreground transition-colors" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground hover:text-foreground transition-colors" />
                    )}
                  </button>
                </div>
              </div>
              
              <Button
                type="submit"
                className="w-full font-medium"
                disabled={isAuthenticating || !password.trim()}
              >
                {isAuthenticating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Authenticating...
                  </>
                ) : (
                  'Access Site'
                )}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm">
              <p className="text-muted-foreground">
                Need help? Contact support at{' '}
                <a
                  href="mailto:tidyframeai@gmail.com"
                  className="text-primary hover:text-primary/80 underline transition-colors"
                >
                  tidyframeai@gmail.com
                </a>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Optional: Add branding footer */}
        <div className="mt-8 text-center">
          <p className="text-xs text-muted-foreground">
            © 2025 TidyFrame. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
}