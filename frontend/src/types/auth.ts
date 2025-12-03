export interface User {
  id: string;
  email: string;
  fullName?: string;
  firstName?: string;
  lastName?: string;
  companyName?: string;
  googleId?: string;
  plan: 'FREE' | 'STANDARD' | 'ENTERPRISE';
  parsesThisMonth: number;     // Now in camelCase from backend
  monthlyLimit: number;         // Now in camelCase from backend
  monthResetDate?: string;      // Now in camelCase from backend
  createdAt: string;
  updatedAt?: string;
  isActive: boolean;
  emailVerified: boolean;
  isAdmin: boolean;            // Admin flag for admin panel access
  stripeCustomerId?: string;
  stripeSubscriptionId?: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  checkout_url?: string;      // Stripe checkout URL for payment
  requires_payment?: boolean;  // True if user needs to pay
  requires_subscription?: boolean; // True if subscription needed (login)
  message?: string;           // Optional message about payment
}

export interface ConsentData {
  age_verified: boolean;
  terms_accepted: boolean;
  privacy_accepted: boolean;
  arbitration_acknowledged: boolean;
  location_confirmed: boolean;
  consent_timestamp: string;
  user_agent: string;
  billing_period?: string;  // Optional billing period for Stripe checkout
}

export interface RegisterRequest {
  email: string;
  password: string;
  fullName?: string;
  consent?: ConsentData;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ResetPasswordRequest {
  email: string;
}

export interface VerifyEmailRequest {
  token: string;
}