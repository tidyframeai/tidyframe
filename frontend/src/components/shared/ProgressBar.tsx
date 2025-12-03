import * as React from 'react';
import * as ProgressPrimitive from '@radix-ui/react-progress';
import { cn } from '@/lib/utils';
import { formatPercent } from '@/utils/format';

export interface ProgressBarProps extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  /** Current value */
  value?: number;
  /** Maximum value */
  max?: number;
  /** Threshold at which bar turns to danger/error color (percentage 0-100) */
  dangerZone?: number;
  /** Optional target marker to show on the bar */
  target?: number;
  /** Show animated stripes for active/processing state */
  animated?: boolean;
  /** Show label with percentage */
  showLabel?: boolean;
  /** Custom label text (overrides percentage) */
  label?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Color variant */
  variant?: 'primary' | 'success' | 'warning' | 'error';
  /** Additional className */
  className?: string;
}

/**
 * Enhanced ProgressBar component with danger zones, targets, and better accessibility
 *
 * Features:
 * - Danger zone highlighting (automatically turns red when threshold exceeded)
 * - Target markers
 * - Animated stripes for active states
 * - Labels and percentages
 * - ARIA live region for screen readers
 *
 * @example
 * ```tsx
 * <ProgressBar
 *   value={75}
 *   max={100}
 *   dangerZone={80}
 *   showLabel
 *   animated={isProcessing}
 * />
 * ```
 */
export const ProgressBar = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressBarProps
>(
  (
    {
      value = 0,
      max = 100,
      dangerZone,
      target,
      animated = false,
      showLabel = false,
      label,
      size = 'md',
      variant = 'primary',
      className,
      ...props
    },
    ref
  ) => {
    const percentage = Math.min(100, Math.max(0, (value / max) * 100));

    // Determine if we're in danger zone
    const isInDangerZone = dangerZone !== undefined && percentage >= dangerZone;

    // Determine color based on danger zone or variant
    const colorClass = isInDangerZone
      ? 'bg-status-error'
      : variant === 'success'
      ? 'bg-status-success'
      : variant === 'warning'
      ? 'bg-status-warning'
      : variant === 'error'
      ? 'bg-status-error'
      : 'bg-primary';

    const sizeClasses = {
      sm: 'h-2',
      md: 'h-4',
      lg: 'h-6'
    };

    const displayLabel = label || formatPercent(percentage, 0);

    return (
      <div className="space-y-2">
        {/* Label */}
        {showLabel && (
          <div className="flex justify-between text-sm">
            <span className="font-medium">{displayLabel}</span>
            {max !== 100 && (
              <span className="text-muted-foreground">
                {value} / {max}
              </span>
            )}
          </div>
        )}

        {/* Progress Bar Container */}
        <div className="relative">
          <ProgressPrimitive.Root
            ref={ref}
            className={cn(
              'relative w-full overflow-hidden rounded-full bg-muted',
              sizeClasses[size],
              className
            )}
            aria-valuemin={0}
            aria-valuemax={max}
            aria-valuenow={value}
            aria-valuetext={displayLabel}
            aria-live="polite"
            aria-label="Progress"
            {...props}
          >
            <ProgressPrimitive.Indicator
              className={cn(
                'h-full w-full flex-1 transition-all duration-[var(--duration-normal)]',
                colorClass,
                animated && 'animate-progress-stripes bg-gradient-to-r from-transparent via-white/20 to-transparent bg-[length:200%_100%]'
              )}
              style={{ transform: `translateX(-${100 - percentage}%)` }}
            />
          </ProgressPrimitive.Root>

          {/* Target Marker */}
          {target !== undefined && target > 0 && target <= max && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-foreground/50"
              style={{ left: `${(target / max) * 100}%` }}
              aria-label={`Target: ${target}`}
            >
              <div className="absolute -top-1 -left-1 w-2 h-2 rounded-full bg-foreground/50" />
            </div>
          )}
        </div>

        {/* Danger Zone Warning */}
        {isInDangerZone && (
          <p className="text-caption text-status-error flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-status-error animate-pulse" />
            High usage detected
          </p>
        )}
      </div>
    );
  }
);

ProgressBar.displayName = 'ProgressBar';

// Add keyframes for animated stripes
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes progress-stripes {
      0% { background-position: 200% 0; }
      100% { background-position: 0% 0; }
    }
    .animate-progress-stripes {
      animation: progress-stripes 2s linear infinite;
    }
  `;
  document.head.appendChild(style);
}
