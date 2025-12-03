import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { isInPaymentGracePeriod, clearPaymentGracePeriod } from '@/utils/gracePeriodManager';
import { processingService } from '@/services/processingService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Upload,
  FileText,
  Activity,
  CheckCircle,
  AlertCircle,
  PartyPopper,
  ArrowRight,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ProcessingJob } from '@/types/processing';
import { StatusIndicator } from '@/components/shared/StatusIndicator';
import { ProgressBar } from '@/components/shared/ProgressBar';
import { formatDate } from '@/utils/format';
import { UI } from '@/config/constants';

type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export default function DashboardHome() {
  const { user, refreshUser, hasActiveSubscription } = useAuth();
  const navigate = useNavigate();
  const [recentJobs, setRecentJobs] = useState<ProcessingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [showWelcomeModal, setShowWelcomeModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [inGracePeriod, setInGracePeriod] = useState(isInPaymentGracePeriod());

  // Show welcome modal for users who just completed payment (grace period active)
  // Also poll subscription status during grace period and clear it when active
  useEffect(() => {
    const checkGracePeriod = isInPaymentGracePeriod();
    setInGracePeriod(checkGracePeriod);
    const hasSeenWelcome = localStorage.getItem('welcome_modal_shown');

    if (checkGracePeriod && !hasSeenWelcome) {
      setShowWelcomeModal(true);
      localStorage.setItem('welcome_modal_shown', 'true');
    }

    // Poll subscription status during grace period to auto-clear when activated
    if (checkGracePeriod) {
      logger.debug('DashboardHome: Grace period active, starting subscription status polling');

      const pollInterval = setInterval(async () => {
        try {
          // Refresh user data to check if subscription is now active
          await refreshUser();

          // If subscription is now active, clear grace period
          if (hasActiveSubscription) {
            logger.debug('DashboardHome: Subscription confirmed active, clearing grace period');
            clearPaymentGracePeriod();
            setInGracePeriod(false);
            clearInterval(pollInterval);
          } else {
            // Check if grace period expired
            setInGracePeriod(isInPaymentGracePeriod());
          }
        } catch (error) {
          logger.error('DashboardHome: Error polling subscription status', error);
        }
      }, 5000); // Poll every 5 seconds

      // Clear polling when component unmounts or grace period expires
      return () => {
        clearInterval(pollInterval);
      };
    }
  }, [hasActiveSubscription, refreshUser]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [jobs] = await Promise.all([
          processingService.getJobs().catch(() => {
            logger.debug('Jobs endpoint not available yet, using empty array');
            return [];
          })
        ]);

        setRecentJobs(Array.isArray(jobs) ? jobs.slice(0, UI.MAX_RECENT_JOBS) : []); // Show only recent jobs
      } catch (error) {
        logger.error('Error fetching dashboard data:', error);
        // Set fallback data instead of showing errors
        setRecentJobs([]);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [user]);

  const handleRefreshSubscription = async () => {
    setRefreshing(true);
    try {
      await refreshUser();
      toast.success('Subscription status updated successfully');
    } catch {
      toast.error('Failed to refresh subscription status. Please try again.');
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-muted rounded w-24"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-muted rounded w-16"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Modal for New Users */}
      <Dialog open={showWelcomeModal} onOpenChange={setShowWelcomeModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex justify-center mb-4">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                <PartyPopper className="h-8 w-8 text-primary" />
              </div>
            </div>
            <DialogTitle className="text-center text-2xl">
              Welcome to TidyFrame!
            </DialogTitle>
            <DialogDescription className="text-center">
              Your account is now active with 100,000 monthly parses. Let's process your first file!
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-4">
            <div className="flex items-start space-x-3 p-3 rounded-lg bg-muted/50">
              <CheckCircle className="h-5 w-5 text-success mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium">95%+ Accuracy</p>
                <p className="text-xs text-muted-foreground">AI-powered name parsing with entity detection</p>
              </div>
            </div>
            <div className="flex items-start space-x-3 p-3 rounded-lg bg-muted/50">
              <CheckCircle className="h-5 w-5 text-success mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium">Lightning Fast</p>
                <p className="text-xs text-muted-foreground">Process 1000 names in under 1 minute</p>
              </div>
            </div>
            <div className="flex items-start space-x-3 p-3 rounded-lg bg-muted/50">
              <CheckCircle className="h-5 w-5 text-success mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium">Easy Export</p>
                <p className="text-xs text-muted-foreground">Download results in CSV or Excel format</p>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              className="w-full"
              size="lg"
              onClick={() => {
                setShowWelcomeModal(false);
                navigate('/dashboard/upload');
              }}
            >
              Upload Your First File
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Welcome Section with Gradient */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary/15 via-primary/5 to-secondary/15 p-8 border border-primary/20 shadow-xl shadow-primary/5">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-secondary/10" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-secondary/20 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-primary/20 to-transparent rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
        <div className="relative flex flex-col gap-3">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/80 bg-clip-text">
            Welcome back{user?.fullName ? `, ${user.fullName.split(' ')[0]}` : ''}! 👋
          </h1>
          <p className="text-foreground/70 text-lg max-w-xl">
            Here's what's happening with your name parsing projects today.
          </p>
        </div>
      </div>

      {/* Activation Banner - Show during grace period */}
      {inGracePeriod && (
        <Card className="border-success/50 bg-success/5">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <Loader2 className="h-6 w-6 text-success animate-spin" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-sm mb-1">Activating Your Subscription</h3>
                <p className="text-sm text-muted-foreground">
                  Your payment was successful! We're processing your subscription and updating your account.
                  This usually takes just a few seconds.
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  You can start using the dashboard - your subscription will be activated automatically.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Subscription Status Refresh - Show for FREE plan users who may have just paid (but not in grace period) */}
      {user?.plan === 'FREE' && !inGracePeriod && (
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-sm">Subscription Status</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    If you just completed payment, click refresh to update your subscription status.
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefreshSubscription}
                disabled={refreshing}
                className="flex-shrink-0"
              >
                {refreshing ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Refreshing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Refresh Status
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="group relative overflow-hidden hover:shadow-xl hover:shadow-primary/10 hover:border-primary/30 transition-all duration-normal">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative">
            <CardTitle className="text-sm font-semibold text-foreground/80">Parses This Month</CardTitle>
            <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/25 group-hover:scale-110 transition-transform">
              <FileText className="h-6 w-6 text-primary-foreground" />
            </div>
          </CardHeader>
          <CardContent className="relative">
            <div className="text-4xl font-black tracking-tight bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
              {(user?.parsesThisMonth || 0).toLocaleString()}
            </div>
            <p className="text-sm text-muted-foreground mt-1.5">
              of {user?.monthlyLimit === -1 ? '∞' : (user?.monthlyLimit || 100000).toLocaleString()} limit
            </p>
          </CardContent>
        </Card>

        <Card className="group relative overflow-hidden hover:shadow-xl hover:shadow-secondary/10 hover:border-secondary/30 transition-all duration-normal">
          <div className="absolute inset-0 bg-gradient-to-br from-secondary/5 via-transparent to-secondary/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative">
            <CardTitle className="text-sm font-semibold text-foreground/80">Active Jobs</CardTitle>
            <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-br from-secondary to-secondary/80 shadow-lg shadow-secondary/25 group-hover:scale-110 transition-transform">
              <Activity className="h-6 w-6 text-secondary-foreground" />
            </div>
          </CardHeader>
          <CardContent className="relative">
            <div className="text-4xl font-black tracking-tight bg-gradient-to-r from-secondary to-secondary/70 bg-clip-text text-transparent">
              {recentJobs.filter(job => job.status === 'processing' || job.status === 'pending').length}
            </div>
            <p className="text-sm text-muted-foreground mt-1.5">
              Currently processing
            </p>
          </CardContent>
        </Card>

        <Card className="group relative overflow-hidden hover:shadow-xl hover:shadow-success/10 hover:border-success/30 transition-all duration-normal">
          <div className="absolute inset-0 bg-gradient-to-br from-success/5 via-transparent to-success/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative">
            <CardTitle className="text-sm font-semibold text-foreground/80">Completed Today</CardTitle>
            <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-br from-success to-success/80 shadow-lg shadow-success/25 group-hover:scale-110 transition-transform">
              <CheckCircle className="h-6 w-6 text-success-foreground" />
            </div>
          </CardHeader>
          <CardContent className="relative">
            <div className="text-4xl font-black tracking-tight bg-gradient-to-r from-success to-success/70 bg-clip-text text-transparent">
              {recentJobs.filter(job =>
                job.status === 'completed' &&
                new Date(job.completedAt!).toDateString() === new Date().toDateString()
              ).length}
            </div>
            <p className="text-sm text-muted-foreground mt-1.5">
              Files processed
            </p>
          </CardContent>
        </Card>

      </div>

      {/* Usage Progress */}
      {user && user.monthlyLimit !== -1 && (
        <Card className="relative overflow-hidden border-primary/20 shadow-lg shadow-primary/5">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5" />
          <CardHeader className="relative bg-gradient-to-r from-primary/10 via-primary/5 to-secondary/10 border-b border-primary/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/25">
                  <Activity className="h-6 w-6 text-primary-foreground" />
                </div>
                <div>
                  <CardTitle className="text-lg font-bold">Monthly Usage</CardTitle>
                  <CardDescription className="text-foreground/60">
                    Your parsing usage for this billing period
                  </CardDescription>
                </div>
              </div>
              <div className="text-right">
                <p className="text-3xl font-black bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                  {Math.round((user.parsesThisMonth / user.monthlyLimit) * 100)}%
                </p>
                <p className="text-xs text-muted-foreground font-medium">used</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6 relative">
            <ProgressBar
              value={user.parsesThisMonth}
              max={user.monthlyLimit}
              showLabel
              label={`${user.parsesThisMonth.toLocaleString()} / ${user.monthlyLimit.toLocaleString()} parses`}
              dangerZone={80}
              size="md"
            />
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Quick Actions */}
        <Card className="relative overflow-hidden border-primary/10 shadow-md hover:shadow-lg transition-shadow">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/3 via-transparent to-secondary/3" />
          <CardHeader className="relative bg-gradient-to-r from-primary/10 via-transparent to-secondary/10 border-b border-primary/10">
            <CardTitle className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-gradient-to-br from-primary to-primary/80 shadow-md shadow-primary/20">
                <Activity className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="font-bold">Quick Actions</span>
            </CardTitle>
            <CardDescription className="text-foreground/60">
              Get started with common tasks
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 pt-6 relative">
            <Link to="/dashboard/upload">
              <Button className="w-full justify-start h-14 bg-gradient-to-r from-primary via-primary to-primary/90 hover:from-primary/95 hover:via-primary/90 hover:to-primary/85 shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 hover:scale-[1.02] transition-all duration-normal" size="lg">
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-white/20 mr-4">
                  <Upload className="h-5 w-5" />
                </div>
                <span className="font-semibold">Upload New File</span>
                <ArrowRight className="ml-auto h-5 w-5 opacity-70" />
              </Button>
            </Link>
            <Link to="/dashboard/results">
              <Button className="w-full justify-start h-14 border-2 border-secondary/40 hover:border-secondary/60 hover:bg-secondary/10 hover:scale-[1.02] transition-all duration-normal" variant="outline" size="lg">
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-secondary/15 mr-4">
                  <FileText className="h-5 w-5 text-secondary" />
                </div>
                <span className="font-semibold text-foreground/80">View Results</span>
                <ArrowRight className="ml-auto h-5 w-5 opacity-50" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card className="relative overflow-hidden border-info/10 shadow-md hover:shadow-lg transition-shadow">
          <div className="absolute inset-0 bg-gradient-to-br from-info/3 via-transparent to-secondary/3" />
          <CardHeader className="relative bg-gradient-to-r from-info/10 via-transparent to-secondary/10 border-b border-info/10">
            <CardTitle className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-gradient-to-br from-info to-info/80 shadow-md shadow-info/20">
                <FileText className="h-5 w-5 text-info-foreground" />
              </div>
              <span className="font-bold">Recent Jobs</span>
            </CardTitle>
            <CardDescription className="text-foreground/60">
              Your latest file processing jobs
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6 relative">
            {recentJobs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <div className="flex items-center justify-center h-16 w-16 rounded-2xl bg-gradient-to-br from-muted to-muted/50 mb-4">
                  <FileText className="h-8 w-8 text-muted-foreground/60" />
                </div>
                <p className="text-foreground/70 text-sm font-semibold">
                  No jobs yet
                </p>
                <p className="text-muted-foreground text-xs mt-1">
                  Upload your first file to get started!
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentJobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-4 rounded-xl border border-border/50 bg-gradient-to-r from-muted/30 to-muted/10 hover:from-muted/50 hover:to-muted/30 hover:border-primary/20 transition-all duration-normal"
                    role="article"
                    aria-label={`Job ${job.filename}, ${job.status}`}
                  >
                    <div className="flex items-center gap-3">
                      <StatusIndicator
                        status={job.status as JobStatus}
                        mode="icon"
                        iconSize="sm"
                        animate
                      />
                      <div>
                        <p className="text-sm font-semibold truncate max-w-32 text-foreground/90">
                          {job.filename}
                        </p>
                        <p className="text-caption text-muted-foreground">
                          {formatDate(job.createdAt)}
                        </p>
                      </div>
                    </div>
                    <StatusIndicator
                      status={job.status as JobStatus}
                      mode="badge"
                    />
                  </div>
                ))}
                <Link to="/dashboard/processing">
                  <Button variant="outline" size="sm" className="w-full mt-3 border-dashed border-primary/30 hover:border-solid hover:border-primary/50 hover:bg-primary/5 font-semibold transition-all duration-normal">
                    View All Jobs
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}