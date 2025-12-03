import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { logger } from '@/utils/logger';
import { authService } from '@/services/authService';
import { billingService } from '@/services/billingService';
import { clearPaymentGracePeriod } from '@/utils/gracePeriodManager';
import { User, LoginResponse, ConsentData } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  hasActiveSubscription: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, fullName?: string, consent?: ConsentData) => Promise<LoginResponse>;
  logout: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
  checkSubscriptionStatus: () => Promise<boolean>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasActiveSubscription, setHasActiveSubscription] = useState(false);

  const checkSubscriptionStatus = useCallback(async (): Promise<boolean> => {
    if (!user) return false;

    // PRIMARY CHECK: User's plan is the source of truth
    // The database is updated by Stripe webhook BEFORE the user needs access
    // This ensures payment status persists correctly across login/logout
    const hasPaidPlan = user.plan === 'STANDARD' || user.plan === 'ENTERPRISE';

    if (hasPaidPlan) {
      setHasActiveSubscription(true);
      logger.debug('User has paid plan, granting access', { plan: user.plan });
      return true;
    }

    // SECONDARY CHECK: For FREE users, optionally verify via Stripe API
    // This catches edge cases where user might have active subscription but plan not updated yet
    try {
      const isActive = await billingService.hasActiveSubscription();
      setHasActiveSubscription(isActive);
      return isActive;
    } catch (error) {
      logger.error('Error checking subscription status:', error);
      setHasActiveSubscription(false);
      return false;
    }
  }, [user]);

  useEffect(() => {
    // Check if user is already authenticated on app load
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('token');
        if (token) {
          const userData = await authService.getCurrentUser();

          // Set subscription status IMMEDIATELY based on plan (prevents race condition with ProtectedRoute)
          // This must happen BEFORE setUser to ensure ProtectedRoute sees correct subscription status
          const hasPaidPlan = userData.plan === 'STANDARD' || userData.plan === 'ENTERPRISE';
          setHasActiveSubscription(hasPaidPlan);

          setUser(userData);

          // Clean up stale registration flags after successful auth
          localStorage.removeItem('pending_user');
          localStorage.removeItem('registration_complete');
        }
      } catch (error) {
        logger.error('Auth initialization error:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Re-check subscription when user changes
  useEffect(() => {
    if (user) {
      checkSubscriptionStatus();
    } else {
      setHasActiveSubscription(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const login = async (email: string, password: string): Promise<boolean> => {
    const response = await authService.login(email, password);
    localStorage.setItem('token', response.access_token);
    localStorage.setItem('refreshToken', response.refresh_token);

    // Set subscription status IMMEDIATELY based on plan (prevents race condition with ProtectedRoute)
    // User's plan is the source of truth - DB is updated by webhook before user needs access
    const hasPaidPlan = response.user.plan === 'STANDARD' || response.user.plan === 'ENTERPRISE';
    setHasActiveSubscription(hasPaidPlan);

    setUser(response.user);

    // Reinitialize token manager after login
    const { tokenManager } = await import('@/utils/tokenManager');
    tokenManager.init();

    // Return subscription status to caller (avoids stale closure issues)
    return hasPaidPlan;
  };

  const register = async (email: string, password: string, fullName?: string, consent?: ConsentData) => {
    const response = await authService.register(email, password, fullName, consent);

    // CRITICAL: Check for checkout URL BEFORE setting user state
    // Setting user causes RegisterPage to re-render and redirect to /pricing
    if (response.checkout_url) {
      // Store tokens but DON'T set user yet (prevents premature re-render)
      localStorage.setItem('token', response.access_token);
      localStorage.setItem('refreshToken', response.refresh_token);
      localStorage.setItem('registration_complete', 'true');
      localStorage.setItem('pending_user', JSON.stringify(response.user));

      // Immediate redirect to Stripe - synchronous, no re-render
      window.location.href = response.checkout_url;
      return response; // Never reached but for TypeScript
    }

    // No checkout URL - normal registration flow
    localStorage.setItem('token', response.access_token);
    localStorage.setItem('refreshToken', response.refresh_token);
    setUser(response.user);

    return response;
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      logger.error('Logout error:', error);
    } finally {
      // Clear all auth-related tokens
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');

      // Clear registration flow state
      localStorage.removeItem('pending_user');
      localStorage.removeItem('registration_complete');

      // Clear welcome modal flag (so next login shows welcome)
      localStorage.removeItem('welcome_modal_shown');

      // Clear payment grace period to prevent stuck "Activating" state on re-login
      clearPaymentGracePeriod();

      // Reset auth state
      setUser(null);
      setHasActiveSubscription(false);
    }
  };

  const resetPassword = async (email: string) => {
    await authService.resetPassword(email);
  };

  const verifyEmail = async (token: string) => {
    await authService.verifyEmail(token);
    // Refresh user data after verification
    const userData = await authService.getCurrentUser();
    setUser(userData);
  };

  const updateProfile = async (data: Partial<User>) => {
    const updatedUser = await authService.updateProfile(data);
    setUser(updatedUser);
  };

  const refreshUser = async (): Promise<void> => {
    try {
      const userData = await authService.getCurrentUser();

      // Set subscription status IMMEDIATELY based on plan (consistent with login/initAuth)
      const hasPaidPlan = userData.plan === 'STANDARD' || userData.plan === 'ENTERPRISE';
      setHasActiveSubscription(hasPaidPlan);

      setUser(userData);

      logger.debug('User refreshed successfully:', userData.email);
    } catch (error) {
      logger.error('Failed to refresh user:', error);
      throw error;
    }
  };

  const value = {
    user,
    loading,
    hasActiveSubscription,
    login,
    register,
    logout,
    resetPassword,
    verifyEmail,
    updateProfile,
    checkSubscriptionStatus,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}