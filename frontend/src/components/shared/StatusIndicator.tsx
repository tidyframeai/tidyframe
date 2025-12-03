import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  getStatusColor,
  getStatusIcon,
  getStatusBadgeVariant,
  getStatusLabel,
  type JobStatus
} from '@/utils/status';

export interface StatusIndicatorProps {
  /** Job status */
  status: JobStatus;
  /** Display mode */
  mode?: 'icon' | 'badge' | 'both';
  /** Icon size */
  iconSize?: 'sm' | 'md' | 'lg';
  /** Show label text next to icon */
  showLabel?: boolean;
  /** Animate processing state */
  animate?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Custom aria-label for accessibility */
  ariaLabel?: string;
}

/**
 * StatusIndicator - Unified component for displaying job status
 *
 * Replaces duplicated status icon and badge logic across components.
 * Provides consistent status visualization with accessibility.
 *
 * @example
 * ```tsx
 * <StatusIndicator status="processing" mode="both" animate />
 * <StatusIndicator status="completed" mode="icon" showLabel />
 * <StatusIndicator status="failed" mode="badge" />
 * ```
 */
export const StatusIndicator = React.forwardRef<HTMLDivElement, StatusIndicatorProps>(
  (
    {
      status,
      mode = 'icon',
      iconSize = 'md',
      showLabel = false,
      animate = false,
      className,
      ariaLabel,
      ...props
    },
    ref
  ) => {
    const Icon = getStatusIcon(status);
    const colorClass = getStatusColor(status);
    const badgeVariant = getStatusBadgeVariant(status);
    const label = getStatusLabel(status);

    const iconSizeClasses = {
      sm: 'h-4 w-4',
      md: 'h-5 w-5',
      lg: 'h-6 w-6'
    };

    // Apply animation only to processing status if animate is true
    const shouldAnimate = animate && status === 'processing';

    // Generate aria-label if not provided
    const accessibleLabel = ariaLabel || `Status: ${label}`;

    const renderIcon = () => (
      <Icon
        className={cn(
          iconSizeClasses[iconSize],
          colorClass,
          shouldAnimate && 'animate-pulse'
        )}
        aria-hidden={!showLabel} // Hide from screen readers if label is shown
      />
    );

    const renderBadge = () => (
      <Badge variant={badgeVariant} aria-label={accessibleLabel}>
        {label}
      </Badge>
    );

    if (mode === 'badge') {
      return (
        <div ref={ref} className={className} {...props}>
          {renderBadge()}
        </div>
      );
    }

    if (mode === 'both') {
      return (
        <div
          ref={ref}
          className={cn('flex items-center gap-2', className)}
          role="status"
          aria-label={accessibleLabel}
          {...props}
        >
          {renderIcon()}
          {renderBadge()}
        </div>
      );
    }

    // mode === 'icon' (default)
    return (
      <div
        ref={ref}
        className={cn('flex items-center gap-2', className)}
        role="status"
        aria-label={accessibleLabel}
        {...props}
      >
        {renderIcon()}
        {showLabel && (
          <span className={cn('text-sm font-medium', colorClass)}>
            {label}
          </span>
        )}
      </div>
    );
  }
);

StatusIndicator.displayName = 'StatusIndicator';
