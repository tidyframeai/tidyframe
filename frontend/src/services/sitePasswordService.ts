// Removed unused ApiResponse import
import { logger } from '@/utils/logger';

// Always use relative path - vite proxy handles it in dev, nginx in prod
const API_BASE = '';

interface SitePasswordStatus {
  enabled: boolean;
  authenticated: boolean;
}

interface SitePasswordResponse {
  success: boolean;
  message: string;
}

export const sitePasswordService = {
  async getStatus(): Promise<SitePasswordStatus> {
    try {
      logger.debug('Making site password status request', { url: `${API_BASE}/api/site-password/status` });

      const response = await fetch(`${API_BASE}/api/site-password/status`, {
        method: 'GET',
        credentials: 'include', // Include cookies
        headers: {
          'Content-Type': 'application/json',
        },
      });

      logger.debug('Site password status response', {
        ok: response.ok,
        status: response.status,
        statusText: response.statusText,
        url: response.url
      });

      if (!response.ok) {
        // Handle 401 gracefully - means site password is enabled and user not authenticated
        if (response.status === 401) {
          logger.debug('Site password required (401 response)');
          return {
            enabled: true,
            authenticated: false
          };
        }

        // For other errors, log but assume enabled/not authenticated for safety
        logger.warn('Site password status check failed', { status: response.status, statusText: response.statusText });
        return {
          enabled: true,
          authenticated: false
        };
      }

      const result = await response.json();
      logger.debug('Site password status received', result);
      return result;
    } catch (error) {
      logger.warn('Site password status check network error', error);
      // If we can't connect to backend, assume protection is enabled for safety
      return {
        enabled: true,
        authenticated: false
      };
    }
  },

  async authenticate(password: string): Promise<SitePasswordResponse> {
    logger.debug('Authenticating with site password', { apiBase: API_BASE || '(same origin)' });

    const response = await fetch(`${API_BASE}/api/site-password/authenticate`, {
      method: 'POST',
      credentials: 'include', // Include cookies
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    logger.debug('Authentication response received', { status: response.status });

    if (!response.ok) {
      if (response.status === 401) {
        logger.debug('Invalid password (401 response)');
        return {
          success: false,
          message: 'Invalid password'
        };
      }
      throw new Error('Authentication request failed');
    }

    const result = await response.json();
    logger.debug('Authentication successful', result);
    return result;
  },

  async checkPassword(password: string): Promise<SitePasswordResponse> {
    const response = await fetch(`${API_BASE}/api/site-password/check`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      throw new Error('Password check failed');
    }

    return response.json();
  },
};