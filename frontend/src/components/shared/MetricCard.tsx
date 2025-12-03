import * as React from 'react';
import { type LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/utils/format';
import { getStatusBackgroundColor, getStatusTextColor, type StatusVariant } from '@/utils/status';

export type TrendDirection = 'up' | 'down' | 'neutral';

export interface MetricCardProps {
  /** The metric value to display */
  value: number | string;
  /** Label describing the metric */
  label: string;
  /** Visual variant based on status colors */
  variant?: StatusVariant;
  /** Optional icon to display */
  icon?: LucideIcon;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Optional subtitle or description */
  subtitle?: string;
  /** Previous value for comparison */
  previousValue?: number;
  /** Trend direction (auto-calculated if previousValue provided) */
  trend?: TrendDirection;
  /** Show percentage change */
  showTrend?: boolean;
  /** Custom trend label (overrides percentage) */
  trendLabel?: string;
  /** Loading state - shows skeleton */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Format number values (default: true) */
  formatValue?: boolean;
  /** Optional click handler */
  onClick?: () => void;
  /** ARIA label for accessibility */
  ariaLabel?: string;
}

/**
 * MetricCard - Reusable component for displaying metrics
 *
 * Used for entity counts, quality scores, processing stats, etc.
 * Provides consistent styling and accessibility across the app.
 *
 * Features:
 * - Trend indicators with automatic calculation from previousValue
 * - Loading state with skeleton animation
 * - Comparison support for showing change percentages
 * - Size variants and status-based colors
 * - Optional click handlers for interactive metrics
 *
 * @example
 * ```tsx
 * // Simple metric
 * <MetricCard
 *   value={1234}
 *   label="People"
 *   variant="info"
 *   icon={Users}
 * />
 *
 * // With trend indicator
 * <MetricCard
 *   value={1500}
 *   previousValue={1234}
 *   label="Active Users"
 *   variant="success"
 *   showTrend
 *   icon={Users}
 * />
 *
 * // Loading state
 * <MetricCard
 *   value={0}
 *   label="Processing"
 *   isLoading
 *   icon={Activity}
 * />
 *
 * // Custom trend label
 * <MetricCard
 *   value={95}
 *   label="Quality Score"
 *   trend="up"
 *   showTrend
 *   trendLabel="+5 pts"
 *   variant="success"
 * />
 * ```
 */
export const MetricCard = React.forwardRef<HTMLDivElement, MetricCardProps>(
  (
    {
      value,
      label,
      variant = 'default',
      icon: Icon,
      size = 'md',
      subtitle,
      previousValue,
      trend,
      showTrend = false,
      trendLabel,
      isLoading = false,
      className,
      formatValue = true,
      onClick,
      ariaLabel,
      ...props
    },
    ref
  ) => {
    // Calculate trend direction and percentage if previousValue is provided
    const calculatedTrend = React.useMemo(() => {
      if (trend) return trend;
      if (previousValue === undefined || typeof value !== 'number') return undefined;

      if (value > previousValue) return 'up';
      if (value < previousValue) return 'down';
      return 'neutral';
    }, [trend, value, previousValue]);

    const trendPercentage = React.useMemo(() => {
      if (!previousValue || typeof value !== 'number' || previousValue === 0) return null;
      const change = ((value - previousValue) / previousValue) * 100;
      return Math.abs(change).toFixed(1);
    }, [value, previousValue]);

    const displayValue = typeof value === 'number' && formatValue
      ? formatNumber(value)
      : value;

    const sizeClasses = {
      sm: 'p-2',
      md: 'p-4',
      lg: 'p-6'
    };

    const textSizeClasses = {
      sm: 'text-xl',
      md: 'text-2xl',
      lg: 'text-hero'
    };

    const iconSizeClasses = {
      sm: 'h-4 w-4',
      md: 'h-6 w-6',
      lg: 'h-8 w-8'
    };

    const backgroundClasses = getStatusBackgroundColor(variant);
    const textColor = getStatusTextColor(variant);

    // Trend icon and color
    const getTrendIcon = () => {
      switch (calculatedTrend) {
        case 'up':
          return TrendingUp;
        case 'down':
          return TrendingDown;
        case 'neutral':
          return Minus;
        default:
          return null;
      }
    };

    const getTrendColor = () => {
      switch (calculatedTrend) {
        case 'up':
          return 'text-status-success';
        case 'down':
          return 'text-status-error';
        case 'neutral':
          return 'text-muted-foreground';
        default:
          return '';
      }
    };

    const TrendIcon = getTrendIcon();
    const trendColor = getTrendColor();

    // Generate ARIA label if not provided
    const trendText = trendLabel || (trendPercentage ? `${trendPercentage}%` : '');
    const accessibleLabel = ariaLabel || `${displayValue} ${label}${subtitle ? ` - ${subtitle}` : ''}${trendText ? ` - ${calculatedTrend} ${trendText}` : ''}`;

    // Loading state
    if (isLoading) {
      return (
        <div
          ref={ref}
          className={cn(
            'text-center rounded-lg border',
            backgroundClasses,
            sizeClasses[size],
            className
          )}
          role="status"
          aria-label="Loading metric"
        >
          <div className="animate-pulse space-y-2">
            {Icon && (
              <div className="flex justify-center mb-2">
                <div className={cn(iconSizeClasses[size], 'bg-muted rounded')} />
              </div>
            )}
            <div className={cn('h-8 bg-muted rounded mx-auto', size === 'sm' ? 'w-12' : size === 'lg' ? 'w-20' : 'w-16')} />
            <div className="h-3 bg-muted rounded mx-auto w-16" />
            {subtitle && <div className="h-2 bg-muted rounded mx-auto w-12" />}
          </div>
        </div>
      );
    }

    return (
      <div
        ref={ref}
        role="figure"
        aria-label={accessibleLabel}
        className={cn(
          'text-center rounded-lg border transition-all duration-fast',
          backgroundClasses,
          sizeClasses[size],
          onClick && 'cursor-pointer hover:shadow-dropdown',
          className
        )}
        onClick={onClick}
        {...props}
      >
        {Icon && (
          <div className="flex justify-center mb-2">
            <Icon className={cn(iconSizeClasses[size], textColor)} aria-hidden="true" />
          </div>
        )}

        <p className={cn(textSizeClasses[size], 'font-bold', textColor)}>
          {displayValue}
        </p>

        {/* Trend indicator */}
        {showTrend && TrendIcon && (
          <div className={cn('flex items-center justify-center gap-1 mt-1', trendColor)}>
            <TrendIcon className="h-3 w-3" aria-hidden="true" />
            <span className="text-caption font-medium">
              {trendLabel || (trendPercentage && `${trendPercentage}%`)}
            </span>
          </div>
        )}

        <p className={cn('text-caption text-muted-foreground', showTrend && TrendIcon ? 'mt-0.5' : 'mt-1')}>
          {label}
        </p>

        {subtitle && (
          <p className="text-caption text-muted-foreground opacity-75 mt-0.5">
            {subtitle}
          </p>
        )}
      </div>
    );
  }
);

MetricCard.displayName = 'MetricCard';
