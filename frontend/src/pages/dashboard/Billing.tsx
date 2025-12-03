import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { useSearchParams, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CreditCard,
  Download,
  Calendar,
  TrendingUp,
  Activity,
  AlertCircle,
  CheckCircle2,
  Receipt,
  BarChart3,
  DollarSign,
  Zap,
  ArrowUp,
  ArrowDown,
  AlertTriangle
} from 'lucide-react';
import { SubscriptionCard } from '@/components/billing/SubscriptionCard';
import { PaymentModal } from '@/components/billing/PaymentModal';
import { SubscriptionStatus, UsageStats, BillingHistory, BillingConfig } from '@/types/billing';
import { billingService } from '@/services/billingService';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';
import { format } from 'date-fns';

export default function Billing() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [billingHistory, setBillingHistory] = useState<BillingHistory[]>([]);
  const [billingConfig, setBillingConfig] = useState<BillingConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  useEffect(() => {
    loadBillingData();
    
    // Check for success/cancel params from Stripe redirect
    const success = searchParams.get('success');
    const canceled = searchParams.get('canceled');
    
    if (success === 'true') {
      toast.success('Subscription created successfully!');
      setSearchParams({}, { replace: true }); // Clear params
    } else if (canceled === 'true') {
      toast.error('Payment was cancelled.');
      setSearchParams({}, { replace: true }); // Clear params
    }
  }, [searchParams, setSearchParams]);

  const loadBillingData = async () => {
    try {
      setIsLoading(true);

      const [subscriptionData, usageData, historyData, configData] = await Promise.allSettled([
        billingService.getSubscriptionStatus(),
        billingService.getUsageStats(),
        billingService.getBillingHistory(10),
        billingService.getBillingConfig()
      ]);

      if (subscriptionData.status === 'fulfilled') {
        setSubscription(subscriptionData.value);
      }

      if (usageData.status === 'fulfilled') {
        setUsage(usageData.value);
      }

      if (historyData.status === 'fulfilled') {
        setBillingHistory(historyData.value);
      }

      if (configData.status === 'fulfilled') {
        setBillingConfig(configData.value);
      }
    } catch (error) {
      logger.error('Error loading billing data:', error);
      toast.error('Failed to load billing information');
    } finally {
      setIsLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    try {
      const { url } = await billingService.createCustomerPortalSession();
      window.location.href = url;
    } catch {
      toast.error('Failed to open billing portal');
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  };

  const getPaymentStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'bg-success/10 text-success border-success/20';
      case 'pending':
        return 'bg-warning/10 text-warning border-warning/20';
      case 'failed':
        return 'bg-destructive/10 text-destructive border-destructive/20';
      default:
        return 'bg-muted/10 text-muted-foreground border-muted/20';
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="space-y-2">
          <div className="h-8 bg-muted rounded w-64 animate-pulse"></div>
          <div className="h-4 bg-muted rounded w-96 animate-pulse"></div>
        </div>

        {/* Content skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Subscription card skeleton */}
            <Card className="animate-pulse">
              <CardHeader>
                <div className="h-6 bg-muted rounded w-40"></div>
                <div className="h-4 bg-muted rounded w-full mt-2"></div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-20 bg-muted rounded"></div>
                <div className="h-16 bg-muted rounded"></div>
              </CardContent>
            </Card>

            {/* Usage stats skeleton */}
            <Card className="animate-pulse">
              <CardHeader>
                <div className="h-6 bg-muted rounded w-48"></div>
              </CardHeader>
              <CardContent>
                <div className="h-32 bg-muted rounded"></div>
              </CardContent>
            </Card>
          </div>

          {/* Billing history skeleton */}
          <div className="space-y-4">
            <Card className="animate-pulse">
              <CardHeader>
                <div className="h-6 bg-muted rounded w-40"></div>
              </CardHeader>
              <CardContent className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-16 bg-muted rounded"></div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <CreditCard className="h-6 w-6" />
            Billing & Subscription
          </h1>
          <p className="text-muted-foreground">
            Manage your subscription, view usage statistics, and billing history.
          </p>
        </div>
        
        {(!subscription || subscription.status !== 'active') && user?.plan !== 'ENTERPRISE' && (
          <Button onClick={() => setShowPaymentModal(true)}>
            <Zap className="h-4 w-4 mr-2" />
            Upgrade Plan
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Subscription & Usage */}
        <div className="lg:col-span-2 space-y-6">
          {/* Subscription Card */}
          {usage && (
            <SubscriptionCard
              subscription={subscription}
              usage={usage}
              billingConfig={billingConfig}
              onManageSubscription={handleManageSubscription}
              onUpgrade={() => setShowPaymentModal(true)}
            />
          )}

          {/* Usage Warning Alerts - 80% and 95% thresholds */}
          {usage && usage.current_month.percentage >= 80 && usage.current_month.percentage < 100 && (
            <Card className={`border-warning/50 ${usage.current_month.percentage >= 95 ? 'bg-destructive/5 border-destructive/50' : 'bg-warning/5'}`}>
              <CardHeader>
                <CardTitle className={`flex items-center gap-2 ${usage.current_month.percentage >= 95 ? 'text-destructive' : 'text-warning'}`}>
                  <AlertTriangle className="h-5 w-5" />
                  {usage.current_month.percentage >= 95 ? 'Critical Usage Alert' : 'High Usage Warning'}
                </CardTitle>
                <CardDescription>
                  {usage.current_month.percentage >= 95
                    ? "You're approaching your monthly limit. Consider upgrading to avoid overages."
                    : "You've used a significant portion of your monthly allocation."}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Current usage</span>
                    <span className={`text-2xl font-bold ${usage.current_month.percentage >= 95 ? 'text-destructive' : 'text-warning'}`}>
                      {usage.current_month.percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Remaining parses</span>
                    <span className="font-medium">
                      {(usage.current_month.limit - usage.current_month.parses).toLocaleString()}
                    </span>
                  </div>
                  {subscription?.current_period_end && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Resets in</span>
                      <span className="font-medium">
                        {Math.ceil((new Date(subscription.current_period_end * 1000).getTime() - Date.now()) / (1000 * 60 * 60 * 24))} days
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Overage Alert */}
          {usage && usage.current_month.overage > 0 && (
            <Card className="border-warning/50 bg-warning/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-warning">
                  <AlertCircle className="h-5 w-5" />
                  Overage Usage Detected
                </CardTitle>
                <CardDescription>
                  You've exceeded your monthly parse limit. Additional charges will apply.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Overage parses</p>
                    <p className="text-2xl font-bold text-warning">
                      {usage.current_month.overage.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Overage cost</p>
                    <p className="text-2xl font-bold text-warning">
                      {formatCurrency(usage.current_month.overage_cost, 'usd')}
                    </p>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground bg-background/50 p-3 rounded-md">
                  <p>
                    <strong>Note:</strong> Overage charges are billed at {billingConfig ? `$${billingConfig.overage_rate.toFixed(2)}` : '$0.01'} per parse beyond your {usage.current_month.limit.toLocaleString()} monthly limit.
                    This amount will be added to your next invoice on{' '}
                    {subscription?.current_period_end && format(new Date(subscription.current_period_end * 1000), 'MMM dd, yyyy')}.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Usage Statistics */}
          {usage && (() => {
            const monthOverMonthChange = usage.previous_month.parses > 0
              ? ((usage.current_month.parses - usage.previous_month.parses) / usage.previous_month.parses) * 100
              : 0;
            const isIncreasing = monthOverMonthChange > 0;

            return (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    Usage Statistics
                  </CardTitle>
                  <CardDescription>
                    Detailed breakdown of your account usage.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Month-over-Month Trend */}
                  {usage.previous_month.parses > 0 && (
                    <div className="p-4 rounded-lg border bg-muted/50">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Month-over-month trend</span>
                        <div className={`flex items-center gap-1 ${isIncreasing ? 'text-info' : 'text-success'}`}>
                          {isIncreasing ? (
                            <ArrowUp className="h-4 w-4" />
                          ) : (
                            <ArrowDown className="h-4 w-4" />
                          )}
                          <span className="font-bold">
                            {Math.abs(monthOverMonthChange).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {isIncreasing
                          ? `Usage increased by ${Math.abs(monthOverMonthChange).toFixed(1)}% compared to last month`
                          : `Usage decreased by ${Math.abs(monthOverMonthChange).toFixed(1)}% compared to last month`}
                      </p>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">This month</span>
                        <span className="font-medium">{usage.current_month.parses.toLocaleString()}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Last month</span>
                        <span className="font-medium">{usage.previous_month.parses.toLocaleString()}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">All time</span>
                        <span className="font-medium">{usage.all_time_parses.toLocaleString()}</span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Average parse size</span>
                        <span className="font-medium">{(usage.average_parse_size / 1024).toFixed(1)}KB</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Peak usage day</span>
                        <span className="font-medium">{usage.peak_usage_day.parses}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Peak date</span>
                        <span className="font-medium">
                          {format(new Date(usage.peak_usage_day.date), 'MMM dd')}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })()}

          {/* Billing History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Receipt className="h-5 w-5" />
                Billing History
              </CardTitle>
              <CardDescription>
                Your recent invoices and payments.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {billingHistory.length === 0 ? (
                <div className="text-center py-8">
                  <Receipt className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No billing history available.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {billingHistory.map((item) => (
                    <div key={item.id} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <DollarSign className="h-4 w-4" />
                          <div>
                            <p className="font-medium">{item.description}</p>
                            <p className="text-sm text-muted-foreground">
                              {format(new Date(item.created_at), 'MMM dd, yyyy')}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <p className="font-medium">
                              {formatCurrency(item.amount, item.currency)}
                            </p>
                            <Badge className={getPaymentStatusColor(item.status)}>
                              {item.status === 'paid' && <CheckCircle2 className="h-3 w-3 mr-1" />}
                              {item.status === 'pending' && <Activity className="h-3 w-3 mr-1" />}
                              {item.status === 'failed' && <AlertCircle className="h-3 w-3 mr-1" />}
                              {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                            </Badge>
                          </div>

                          {item.invoice_pdf && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => window.open(item.invoice_pdf, '_blank')}
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Line Item Breakdown */}
                      {(item.line_items.subscription > 0 || item.line_items.overage > 0) && (
                        <div className="pl-7 space-y-1 text-sm border-t pt-2">
                          {item.line_items.subscription > 0 && (
                            <div className="flex justify-between text-muted-foreground">
                              <span>Subscription</span>
                              <span>{formatCurrency(item.line_items.subscription, item.currency)}</span>
                            </div>
                          )}
                          {item.line_items.overage > 0 && (
                            <div className="flex justify-between text-warning">
                              <span>Overage charges</span>
                              <span>{formatCurrency(item.line_items.overage, item.currency)}</span>
                            </div>
                          )}
                          {item.line_items.other > 0 && (
                            <div className="flex justify-between text-muted-foreground">
                              <span>Other charges</span>
                              <span>{formatCurrency(item.line_items.other, item.currency)}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Quick Stats */}
        <div className="space-y-6">
          {/* Quick Stats */}
          {usage && (
            <div className="space-y-4">
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-success" />
                    <div>
                      <p className="text-2xl font-bold">{usage.current_month.parses.toLocaleString()}</p>
                      <p className="text-sm text-muted-foreground">Parses this month</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-info" />
                    <div>
                      <p className="text-2xl font-bold">{usage.current_month.percentage.toFixed(1)}%</p>
                      <p className="text-sm text-muted-foreground">Of monthly limit used</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Estimated Next Invoice */}
              {subscription?.estimated_next_invoice !== undefined && subscription.estimated_next_invoice > 0 && (
                <Card className="border-primary/20">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2">
                      <DollarSign className="h-5 w-5 text-primary" />
                      <div>
                        <p className="text-2xl font-bold">
                          {formatCurrency(subscription.estimated_next_invoice, 'usd')}
                        </p>
                        <p className="text-sm text-muted-foreground">Estimated next invoice</p>
                        {subscription.days_until_renewal !== undefined && (
                          <p className="text-xs text-muted-foreground mt-1">
                            In {subscription.days_until_renewal} days
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-secondary" />
                    <div>
                      <p className="text-2xl font-bold">{usage.peak_usage_day.parses}</p>
                      <p className="text-sm text-muted-foreground">Peak daily usage</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Support Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Need Help?</CardTitle>
              <CardDescription>
                Contact our support team for billing assistance.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full" asChild>
                <Link to="/contact">
                  Contact Support
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Payment Modal */}
      <PaymentModal
        isOpen={showPaymentModal}
        onClose={() => {
          setShowPaymentModal(false);
          loadBillingData();
        }}
      />
    </div>
  );
}