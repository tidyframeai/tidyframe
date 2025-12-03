import { useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LoginResponse } from '@/types/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import ConsentCheckboxes from '@/components/legal/ConsentCheckboxes';
import { Loader2, Mail, Lock, Eye, EyeOff, User } from 'lucide-react';
import { toast } from 'sonner';
import { isInPaymentGracePeriod } from '@/utils/gracePeriodManager';

export default function RegisterPage() {
  const { user, register, hasActiveSubscription } = useAuth();
  const [searchParams] = useSearchParams();
  const billingPeriod = (searchParams.get('billing') as 'monthly' | 'yearly') || 'monthly';
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Legal compliance state - simplified (age, location, arbitration now in ToS Article 2.4)
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Redirect if already authenticated (but not during registration loading)
  if (user && !loading) {
    // Check grace period in addition to subscription (handles post-payment period)
    const inGracePeriod = isInPaymentGracePeriod();

    if (user.plan === 'ENTERPRISE' || hasActiveSubscription || inGracePeriod) {
      return <Navigate to="/dashboard" replace />;
    } else {
      // No active subscription AND not in grace period, redirect to pricing
      return <Navigate to="/pricing" replace />;
    }
  }

  const validateForm = () => {
    if (!formData.fullName.trim()) {
      setError('Full name is required');
      return false;
    }
    if (!formData.email.trim()) {
      setError('Email is required');
      return false;
    }
    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }
    // Enhanced password validation
    if (formData.password.length < 12) {
      setError('Password must be at least 12 characters');
      return false;
    }
    const hasUpper = /[A-Z]/.test(formData.password);
    const hasLower = /[a-z]/.test(formData.password);
    const hasNumber = /\d/.test(formData.password);
    const hasSymbol = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(formData.password);
    
    if (!hasUpper || !hasLower || !hasNumber || !hasSymbol) {
      setError('Password must contain uppercase, lowercase, number, and symbol');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    // Legal compliance validation - CRITICAL FOR LAWSUIT PROTECTION
    // Age, location, and arbitration are now attestations in Terms of Service Article 2.4
    if (!termsAccepted) {
      setError('You must accept the Terms of Service (which includes attestations for age 18+, US location, and arbitration agreement)');
      return false;
    }
    if (!privacyAccepted) {
      setError('You must accept the Privacy Policy');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      // Include consent data and billing period in registration (attestations in ToS Article 2.4)
      const response: LoginResponse = await register(
        formData.email,
        formData.password,
        formData.fullName,
        {
          age_verified: true,              // Attested via ToS acceptance
          terms_accepted: termsAccepted,
          privacy_accepted: privacyAccepted,
          arbitration_acknowledged: true,   // Attested via ToS acceptance
          location_confirmed: true,         // Attested via ToS acceptance
          consent_timestamp: new Date().toISOString(),
          user_agent: navigator.userAgent,
          billing_period: billingPeriod     // Pass selected billing period for Stripe checkout
        }
      );

      // Only show success toast if not redirecting to checkout
      if (!response?.checkout_url) {
        toast.success('Account created successfully! Please complete your subscription to access all features.');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error && 'response' in err && 
        err.response && typeof err.response === 'object' && 
        'data' in err.response && 
        err.response.data && typeof err.response.data === 'object' && 
        'message' in err.response.data && 
        typeof err.response.data.message === 'string'
        ? err.response.data.message
        : 'Registration failed. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };


  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-8">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Link to="/">
              <img src="/logo-with-name.png" alt="TidyFrame" className="h-50" />
            </Link>
          </div>
          <CardTitle className="text-2xl font-bold">Create your account</CardTitle>
          <CardDescription>
            Get started with tidyframe.com today
          </CardDescription>
        </CardHeader>
        
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="fullName"
                  type="text"
                  placeholder="Enter your full name"
                  value={formData.fullName}
                  onChange={(e) => handleInputChange('fullName', e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Create a password"
                  value={formData.password}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                  className="pl-9 pr-9"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-caption text-muted-foreground">
                Must be at least 12 characters with mixed case, numbers, and symbols
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm your password"
                  value={formData.confirmPassword}
                  onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                  className="pl-9 pr-9"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            
            {/* Legal Compliance Checkboxes - CRITICAL FOR LEGAL PROTECTION */}
            <ConsentCheckboxes
              termsAccepted={termsAccepted}
              onTermsAcceptedChange={setTermsAccepted}
              privacyAccepted={privacyAccepted}
              onPrivacyAcceptedChange={setPrivacyAccepted}
            />
          </CardContent>
          
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create account'
              )}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link to="/auth/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}