/**
 * Token Manager - Handles JWT token refresh and expiration
 * Ensures users stay logged in and tokens are refreshed before expiration
 */

import { logger } from '@/utils/logger';
import { apiService } from '@/services/api';

interface TokenPayload {
  exp: number;
  sub: string;
  email: string;
}

class TokenManager {
  private refreshTimer: NodeJS.Timeout | null = null;
  private isRefreshing = false;

  /**
   * Initialize token manager - call this on app startup
   */
  init() {
    // Check and schedule refresh on startup
    this.scheduleTokenRefresh();

    // Check token every minute
    setInterval(() => {
      this.checkAndRefreshToken();
    }, 60000); // 1 minute
  }

  /**
   * Decode JWT token to get payload
   */
  private decodeToken(token: string): TokenPayload | null {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      logger.error('Failed to decode token:', error);
      return null;
    }
  }

  /**
   * Check if token needs refresh (within 1 hour of expiry)
   */
  private shouldRefreshToken(token: string): boolean {
    const payload = this.decodeToken(token);
    if (!payload) return true;

    const now = Date.now() / 1000;
    const timeUntilExpiry = payload.exp - now;

    // Refresh if less than 1 hour remaining
    return timeUntilExpiry < 3600;
  }

  /**
   * Schedule token refresh before expiration
   */
  private scheduleTokenRefresh() {
    // Clear existing timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }

    const token = localStorage.getItem('token');
    if (!token) return;

    const payload = this.decodeToken(token);
    if (!payload) return;

    const now = Date.now() / 1000;
    const timeUntilExpiry = payload.exp - now;

    // Schedule refresh 5 minutes before expiry (or immediately if less than 5 minutes)
    const refreshIn = Math.max(0, (timeUntilExpiry - 300) * 1000);

    if (refreshIn > 0) {
      this.refreshTimer = setTimeout(() => {
        this.refreshToken();
      }, refreshIn);
    } else {
      // Token expired or about to expire, refresh immediately
      this.refreshToken();
    }
  }

  /**
   * Check and refresh token if needed
   */
  async checkAndRefreshToken() {
    const token = localStorage.getItem('token');
    if (!token) return;

    if (this.shouldRefreshToken(token) && !this.isRefreshing) {
      await this.refreshToken();
    }
  }

  /**
   * Refresh the access token
   */
  async refreshToken(): Promise<boolean> {
    if (this.isRefreshing) return false;

    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) return false;

    this.isRefreshing = true;

    try {
      const response = await apiService.post<{
        access_token: string;
        refresh_token?: string;
        expires_in: number;
      }>('/api/auth/refresh', {
        refresh_token: refreshToken,
      });

      // Update tokens
      localStorage.setItem('token', response.access_token);
      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token);
      }

      // Schedule next refresh
      this.scheduleTokenRefresh();

      logger.debug('Token refreshed successfully');
      return true;
    } catch (error) {
      logger.error('Failed to refresh token:', error);
      
      // Clear tokens and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      
      // Only redirect if we're not already on the login page
      if (!window.location.pathname.includes('/auth/login')) {
        window.location.href = '/auth/login';
      }
      
      return false;
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * Clear tokens and timers (for logout)
   */
  clear() {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    this.isRefreshing = false;
  }

  /**
   * Get remaining time until token expiry in seconds
   */
  getTokenTimeRemaining(): number {
    const token = localStorage.getItem('token');
    if (!token) return 0;

    const payload = this.decodeToken(token);
    if (!payload) return 0;

    const now = Date.now() / 1000;
    return Math.max(0, payload.exp - now);
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = localStorage.getItem('token');
    if (!token) return false;

    const payload = this.decodeToken(token);
    if (!payload) return false;

    const now = Date.now() / 1000;
    return payload.exp > now;
  }
}

export const tokenManager = new TokenManager();