export interface SubscriptionStatus {
  id?: string;
  status?: 'active' | 'canceled' | 'past_due' | 'unpaid' | 'incomplete' | 'trialing' | 'inactive' | 'unknown';
  plan: string; // Plan type: FREE, ANONYMOUS, STANDARD, ENTERPRISE
  current_period_start?: number; // Unix timestamp
  current_period_end?: number; // Unix timestamp
  cancel_at_period_end?: boolean;
  // Usage and billing info
  current_usage?: number;
  usage_limit?: number;
  usage_percentage?: number;
  overage?: number;
  overage_cost?: number; // in cents
  estimated_next_invoice?: number; // in cents
  days_until_renewal?: number;
}

export interface UsageStats {
  current_month: {
    parses: number;
    limit: number;
    percentage: number;
    overage: number;
    overage_cost: number; // in cents
    period_start: string;
    period_end: string;
  };
  previous_month: {
    parses: number;
    limit: number;
    percentage: number;
    overage: number;
    overage_cost: number;
    period_start: string;
    period_end: string;
  };
  all_time_parses: number;
  average_parse_size: number;
  peak_usage_day: {
    date: string;
    parses: number;
  };
}

export interface BillingHistory {
  id: string;
  amount: number;
  currency: string;
  status: 'paid' | 'pending' | 'failed' | 'draft' | 'open' | 'void' | 'uncollectible';
  description: string;
  invoice_url?: string;
  invoice_pdf?: string;
  created_at: string;
  paid_at?: string;
  line_items: {
    subscription: number; // in cents
    overage: number; // in cents
    other: number; // in cents
  };
}

export interface PaymentMethod {
  id: string;
  type: 'card' | 'bank_account';
  card?: {
    brand: string;
    last4: string;
    expMonth: number;
    expYear: number;
  };
  bankAccount?: {
    bankName: string;
    last4: string;
  };
  isDefault: boolean;
}

export interface CheckoutSessionRequest {
  priceId: string;
  successUrl?: string;
  cancelUrl?: string;
}

export interface CheckoutSessionByPlanRequest {
  plan: 'STANDARD' | 'ENTERPRISE';
  billing_period: 'monthly' | 'yearly';
}

export interface CheckoutSessionResponse {
  checkout_url?: string;
  sessionId?: string;
  url?: string;
}

export interface CustomerPortalResponse {
  url: string;
}

export interface PricingPlan {
  id: string;
  name: string;
  description: string;
  amount?: number; // null for custom/enterprise plans
  currency: string;
  interval: string; // 'month' | 'year' | 'custom'
  features: string[];
  popular: boolean;
  price_id?: string;
}

export interface BillingConfig {
  monthly_price: number; // In dollars
  yearly_price: number; // In dollars
  overage_rate: number; // Per unit in dollars
  standard_limit: number; // Monthly parse limit
  enterprise_limit: number; // Monthly parse limit
  currency: string;
  standard_features: string[];
  standard_yearly_features: string[];
  enterprise_features: string[];
}