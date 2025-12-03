import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import { AlertCircle, AlertTriangle, Info, RefreshCw, ExternalLink } from 'lucide-react';

export type ErrorCategory =
  | 'network'
  | 'auth'
  | 'validation'
  | 'server'
  | 'not_found'
  | 'permission'
  | 'rate_limit'
  | 'unknown';

export interface ErrorStateProps {
  /** Error title */
  title?: string;
  /** Error message/description */
  message: string;
  /** Error severity level */
  severity?: 'warning' | 'error' | 'critical';
  /** Error category for better handling */
  category?: ErrorCategory;
  /** Error code (e.g., HTTP status code, custom error code) */
  errorCode?: string | number;
  /** Technical error details (hidden by default, expandable) */
  technicalDetails?: string;
  /** Retry function */
  onRetry?: () => void | Promise<void>;
  /** Retry button label */
  retryLabel?: string;
  /** Enable automatic retry with exponential backoff */
  autoRetry?: boolean;
  /** Maximum number of auto-retry attempts */
  maxRetries?: number;
  /** Show contact support link */
  showSupport?: boolean;
  /** Support link URL */
  supportUrl?: string;
  /** Is retry in progress */
  isRetrying?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional className */
  className?: string;
  /** Children for custom content */
  children?: React.ReactNode;
}

/**
 * ErrorState component for unified error handling with retry functionality
 *
 * Features:
 * - Severity variants (warning, error, critical)
 * - Error categorization (network, auth, validation, etc.)
 * - Auto-retry with exponential backoff
 * - Offline detection and handling
 * - Error codes and technical details (expandable)
 * - Retry button with loading state
 * - Optional contact support link
 * - Consistent error messaging patterns
 * - Accessible error announcements
 *
 * @example
 * ```tsx
 * // Basic error with retry
 * <ErrorState
 *   title="Failed to load data"
 *   message="Unable to fetch job results. The file may have expired."
 *   category="network"
 *   errorCode={404}
 *   onRetry={fetchData}
 *   isRetrying={loading}
 * />
 *
 * // Critical error with auto-retry
 * <ErrorState
 *   severity="critical"
 *   category="server"
 *   errorCode={500}
 *   title="Server Error"
 *   message="Internal server error occurred."
 *   technicalDetails="TypeError: Cannot read property 'data' of undefined\n  at processingService.ts:45"
 *   onRetry={reconnect}
 *   autoRetry
 *   maxRetries={3}
 *   showSupport
 * />
 *
 * // Network error with categorization
 * <ErrorState
 *   category="network"
 *   message="Failed to connect"
 *   onRetry={retry}
 *   autoRetry
 * />
 * ```
 */
export const ErrorState = React.forwardRef<HTMLDivElement, ErrorStateProps>(
  (
    {
      title,
      message,
      severity = 'error',
      category,
      errorCode,
      technicalDetails,
      onRetry,
      retryLabel = 'Try Again',
      autoRetry = false,
      maxRetries = 3,
      showSupport = false,
      supportUrl = '/contact',
      isRetrying = false,
      size = 'md',
      className,
      children,
    },
    ref
  ) => {
    const [retryCount, setRetryCount] = React.useState(0);
    const [showDetails, setShowDetails] = React.useState(false);
    const [isOffline, setIsOffline] = React.useState(!navigator.onLine);

    // Monitor online/offline status
    React.useEffect(() => {
      const handleOnline = () => setIsOffline(false);
      const handleOffline = () => setIsOffline(true);

      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);

      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }, []);

    // Auto-retry with exponential backoff
    React.useEffect(() => {
      if (!autoRetry || !onRetry || retryCount >= maxRetries || isOffline || isRetrying) {
        return;
      }

      // Exponential backoff: 1s, 2s, 4s, 8s...
      const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);

      const timeoutId = setTimeout(() => {
        setRetryCount((prev) => prev + 1);
        onRetry();
      }, delay);

      return () => clearTimeout(timeoutId);
    }, [autoRetry, onRetry, retryCount, maxRetries, isOffline, isRetrying]);

    // Category-based messaging
    const getCategoryMessage = (): string | null => {
      if (isOffline) return 'You appear to be offline. Please check your internet connection.';

      switch (category) {
        case 'network':
          return 'Unable to reach the server. Please check your internet connection.';
        case 'auth':
          return 'Your session may have expired. Please sign in again.';
        case 'permission':
          return 'You don\'t have permission to perform this action.';
        case 'rate_limit':
          return 'Too many requests. Please wait a moment and try again.';
        case 'not_found':
          return 'The requested resource could not be found.';
        default:
          return null;
      }
    };

    // Severity-based configuration
    const severityConfig = {
      warning: {
        icon: AlertTriangle,
        variant: 'default' as const,
        defaultTitle: 'Warning',
        iconColor: 'text-status-warning',
      },
      error: {
        icon: AlertCircle,
        variant: 'destructive' as const,
        defaultTitle: 'Error',
        iconColor: 'text-status-error',
      },
      critical: {
        icon: AlertCircle,
        variant: 'destructive' as const,
        defaultTitle: 'Critical Error',
        iconColor: 'text-status-error',
      },
    };

    const config = severityConfig[severity];
    const Icon = config.icon;
    const displayTitle = title || config.defaultTitle;
    const categoryMessage = getCategoryMessage();

    // Size-based styling
    const sizeClasses = {
      sm: 'p-4 text-sm',
      md: 'p-6 text-base',
      lg: 'p-8 text-base',
    };

    return (
      <div
        ref={ref}
        className={cn(sizeClasses[size], className)}
        role="alert"
        aria-live="assertive"
      >
        <Alert variant={config.variant} className="space-y-4">
          <div className="flex items-start gap-3">
            <Icon className={cn('h-5 w-5 mt-0.5', config.iconColor)} aria-hidden="true" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <AlertTitle className="font-semibold">{displayTitle}</AlertTitle>
                {errorCode && (
                  <span className="text-caption text-muted-foreground font-mono">
                    Error {errorCode}
                  </span>
                )}
              </div>

              <AlertDescription className="text-sm space-y-2">
                <p>{categoryMessage || message}</p>
                {categoryMessage && categoryMessage !== message && (
                  <p className="text-muted-foreground">{message}</p>
                )}
              </AlertDescription>

              {/* Offline indicator */}
              {isOffline && (
                <div className="flex items-center gap-2 text-caption text-status-warning">
                  <div className="h-2 w-2 rounded-full bg-status-warning animate-pulse" />
                  Offline - Waiting for connection...
                </div>
              )}

              {/* Auto-retry status */}
              {autoRetry && retryCount > 0 && retryCount < maxRetries && (
                <p className="text-caption text-muted-foreground">
                  Auto-retry attempt {retryCount} of {maxRetries}...
                </p>
              )}

              {/* Technical details (expandable) */}
              {technicalDetails && (
                <div className="mt-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDetails(!showDetails)}
                    className="h-auto p-0 text-caption text-muted-foreground hover:text-foreground"
                  >
                    {showDetails ? 'Hide' : 'Show'} technical details
                  </Button>
                  {showDetails && (
                    <pre className="mt-2 p-2 bg-muted rounded text-caption font-mono overflow-x-auto">
                      {technicalDetails}
                    </pre>
                  )}
                </div>
              )}

              {children}

              {/* Action buttons */}
              {(onRetry || showSupport) && (
                <div className="flex flex-wrap gap-2 mt-4">
                  {onRetry && (
                    <Button
                      onClick={() => {
                        setRetryCount(0);
                        onRetry();
                      }}
                      disabled={isRetrying || isOffline}
                      variant="outline"
                      size="sm"
                      aria-label={isRetrying ? 'Retrying...' : retryLabel}
                    >
                      <RefreshCw
                        className={cn('h-4 w-4 mr-2', isRetrying && 'animate-spin')}
                      />
                      {isRetrying ? 'Retrying...' : retryLabel}
                    </Button>
                  )}

                  {showSupport && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(supportUrl, '_blank')}
                      aria-label="Contact support"
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Contact Support
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        </Alert>
      </div>
    );
  }
);

ErrorState.displayName = 'ErrorState';

/**
 * Simple inline error message (non-blocking)
 *
 * @example
 * ```tsx
 * <InlineError message="Invalid input" />
 * ```
 */
export const InlineError: React.FC<{
  message: string;
  className?: string;
}> = ({ message, className }) => {
  return (
    <p
      className={cn('text-sm text-status-error flex items-center gap-1', className)}
      role="alert"
    >
      <Info className="h-3 w-3" aria-hidden="true" />
      {message}
    </p>
  );
};

InlineError.displayName = 'InlineError';
