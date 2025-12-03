import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  User,
  CreditCard,
  Key,
  Save,
  Crown
} from 'lucide-react';
import { toast } from 'sonner';

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    fullName: user?.fullName || '',
    email: user?.email || '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await updateProfile(formData);
      toast.success('Profile updated successfully');
    } catch {
      toast.error('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Profile Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile Information
            </CardTitle>
            <CardDescription>
              Update your personal information
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fullName">Full Name</Label>
                <Input
                  id="fullName"
                  value={formData.fullName}
                  onChange={(e) => handleInputChange('fullName', e.target.value)}
                  placeholder="Enter your full name"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    placeholder="Enter your email"
                  />
                  {user?.emailVerified ? (
                    <Badge className="absolute right-2 top-2 h-6 text-caption">
                      Verified
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="absolute right-2 top-2 h-6 text-caption">
                      Unverified
                    </Badge>
                  )}
                </div>
              </div>

              <Button type="submit" disabled={loading}>
                <Save className="h-4 w-4 mr-2" />
                {loading ? 'Saving...' : 'Save Changes'}
              </Button>
            </CardContent>
          </form>
        </Card>

        {/* Account Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Crown className="h-5 w-5" />
              Account Details
            </CardTitle>
            <CardDescription>
              Your account information and plan
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Plan</span>
              <Badge variant={user?.plan === 'ENTERPRISE' ? 'default' : 'secondary'}>
                {user?.plan || 'Standard'}
              </Badge>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Monthly Parses</span>
              <span className="text-sm">
                {user?.parsesThisMonth || 0} / {user?.monthlyLimit === -1 ? '∞' : user?.monthlyLimit || 100000}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Member Since</span>
              <span className="text-sm">
                {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : 'Unknown'}
              </span>
            </div>

            <Separator />

            <div className="space-y-2">
              <h4 className="text-sm font-medium">Account Status</h4>
              <div className="flex gap-2">
                <Badge variant={user?.isActive ? 'default' : 'destructive'}>
                  {user?.isActive ? 'Active' : 'Inactive'}
                </Badge>
                <Badge variant={user?.emailVerified ? 'default' : 'destructive'}>
                  {user?.emailVerified ? 'Email Verified' : 'Email Unverified'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Subscription Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Subscription
            </CardTitle>
            <CardDescription>
              Manage your billing and subscription
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertDescription>
                Subscription management is handled through Stripe's customer portal for security.
              </AlertDescription>
            </Alert>
            
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1">
                <CreditCard className="h-4 w-4 mr-2" />
                Billing Portal
              </Button>
              {user?.plan !== 'ENTERPRISE' && (
                <Button className="flex-1">
                  Upgrade Plan
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* API Keys Link */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Access
            </CardTitle>
            <CardDescription>
              Manage your API keys for programmatic access
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Generate and manage API keys for accessing TidyFrame programmatically
              </span>
            </div>
            
            <Button variant="outline" asChild>
              <a href="/dashboard/api-keys">
                <Key className="h-4 w-4 mr-2" />
                Manage API Keys
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}