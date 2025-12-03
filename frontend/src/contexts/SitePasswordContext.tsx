import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { logger } from '@/utils/logger';
import { sitePasswordService } from '@/services/sitePasswordService';

interface SitePasswordContextType {
  isEnabled: boolean;
  isAuthenticated: boolean;
  loading: boolean;
  authenticate: (password: string) => Promise<boolean>;
  checkStatus: () => Promise<void>;
}

const SitePasswordContext = createContext<SitePasswordContextType | undefined>(undefined);

interface SitePasswordProviderProps {
  children: ReactNode;
}

export function SitePasswordProvider({ children }: SitePasswordProviderProps) {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkStatus = async () => {
    try {
      logger.debug('🔍 SitePasswordContext: Starting status check...');
      setLoading(true);
      const status = await sitePasswordService.getStatus();
      logger.debug('📋 SitePasswordContext: Setting state:', {
        enabled: status.enabled,
        authenticated: status.authenticated
      });
      setIsEnabled(status.enabled);
      setIsAuthenticated(status.authenticated);
      logger.debug('✅ Site password status loaded:', status);
    } catch (error) {
      logger.error('❌ Failed to check site password status:', error);
      // Default to enabled and not authenticated if check fails for safety
      logger.debug('🛡️ Defaulting to enabled=true, authenticated=false for safety');
      setIsEnabled(true);
      setIsAuthenticated(false);
    } finally {
      logger.debug('🏁 SitePasswordContext: Setting loading=false');
      setLoading(false);
    }
  };

  const authenticate = async (password: string): Promise<boolean> => {
    try {
      const response = await sitePasswordService.authenticate(password);
      if (response.success) {
        setIsAuthenticated(true);
        return true;
      }
      return false;
    } catch (error) {
      logger.error('Site password authentication failed:', error);
      return false;
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const value: SitePasswordContextType = {
    isEnabled,
    isAuthenticated,
    loading,
    authenticate,
    checkStatus
  };

  return (
    <SitePasswordContext.Provider value={value}>
      {children}
    </SitePasswordContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSitePassword() {
  const context = useContext(SitePasswordContext);
  if (context === undefined) {
    throw new Error('useSitePassword must be used within a SitePasswordProvider');
  }
  return context;
}