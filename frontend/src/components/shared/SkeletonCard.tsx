import * as React from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export interface SkeletonCardProps {
  /** Skeleton variant based on content type */
  variant?: 'metric' | 'table' | 'card' | 'list';
  /** Number of rows for table/list variants */
  rows?: number;
  /** Show header skeleton */
  showHeader?: boolean;
  /** Enable shimmer animation (left-to-right gradient sweep) */
  shimmer?: boolean;
  /** Enable stagger loading (progressive delay between items) */
  stagger?: boolean;
  /** Additional className */
  className?: string;
}

/**
 * Skeleton loading placeholder component for consistent loading states
 *
 * Variants:
 * - metric: For stat/metric cards (used in dashboards)
 * - table: For data tables with rows
 * - card: For content cards with title and body
 * - list: For list items
 *
 * Features:
 * - Shimmer animation: Left-to-right gradient sweep for polished loading effect
 * - Stagger loading: Progressive delay between items for smooth appearance
 * - Pulse fallback: Standard pulse animation when shimmer is disabled
 *
 * @example
 * ```tsx
 * // Metric skeleton (dashboard stats)
 * <SkeletonCard variant="metric" shimmer />
 *
 * // Table skeleton with shimmer and stagger
 * <SkeletonCard variant="table" rows={5} showHeader shimmer stagger />
 *
 * // Card skeleton (job cards)
 * <SkeletonCard variant="card" showHeader shimmer />
 *
 * // List with progressive loading
 * <SkeletonCard variant="list" rows={4} shimmer stagger />
 * ```
 */
export const SkeletonCard = React.forwardRef<HTMLDivElement, SkeletonCardProps>(
  ({ variant = 'card', rows = 3, showHeader = false, shimmer = false, stagger = false, className }, ref) => {
    // Base skeleton animation class - shimmer or pulse
    const skeletonClass = cn(
      'rounded',
      shimmer ? 'animate-shimmer' : 'animate-pulse bg-muted'
    );

    // Metric variant - compact stats display
    if (variant === 'metric') {
      return (
        <Card ref={ref} className={cn('animate-pulse', className)}>
          <CardHeader className="pb-2">
            <div className={cn(skeletonClass, 'h-4 w-24')} />
          </CardHeader>
          <CardContent>
            <div className={cn(skeletonClass, 'h-8 w-16 mb-2')} />
            <div className={cn(skeletonClass, 'h-3 w-20')} />
          </CardContent>
        </Card>
      );
    }

    // Table variant - data table with multiple rows
    if (variant === 'table') {
      return (
        <Card ref={ref} className={className}>
          {showHeader && (
            <CardHeader>
              <div className={cn(skeletonClass, 'h-6 w-1/3 mb-2')} />
              <div className={cn(skeletonClass, 'h-4 w-1/2')} />
            </CardHeader>
          )}
          <CardContent className={cn('space-y-3', showHeader ? '' : 'pt-6')}>
            {[...Array(rows)].map((_, i) => (
              <div
                key={i}
                className="space-y-2"
                style={stagger ? { animationDelay: `${i * 75}ms` } : undefined}
              >
                <div className="flex gap-4">
                  <div className={cn(skeletonClass, 'h-4 flex-1')} />
                  <div className={cn(skeletonClass, 'h-4 w-24')} />
                  <div className={cn(skeletonClass, 'h-4 w-16')} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      );
    }

    // List variant - simple list items
    if (variant === 'list') {
      return (
        <div ref={ref} className={cn('space-y-3', className)}>
          {[...Array(rows)].map((_, i) => (
            <div
              key={i}
              className={cn(
                'flex items-center gap-4 p-4 rounded-lg border',
                skeletonClass
              )}
              style={stagger ? { animationDelay: `${i * 75}ms` } : undefined}
            >
              <div className={cn(skeletonClass, 'h-10 w-10 rounded-full')} />
              <div className="flex-1 space-y-2">
                <div className={cn(skeletonClass, 'h-4 w-1/3')} />
                <div className={cn(skeletonClass, 'h-3 w-1/2')} />
              </div>
            </div>
          ))}
        </div>
      );
    }

    // Card variant (default) - content card with title and body
    return (
      <Card ref={ref} className={className}>
        {showHeader && (
          <CardHeader>
            <div className={cn(skeletonClass, 'h-6 w-1/3 mb-2')} />
            <div className={cn(skeletonClass, 'h-4 w-1/2')} />
          </CardHeader>
        )}
        <CardContent className={cn('space-y-4', showHeader ? '' : 'p-6')}>
          <div className={cn(skeletonClass, 'h-4 w-full')} />
          <div className={cn(skeletonClass, 'h-4 w-5/6')} />
          <div className={cn(skeletonClass, 'h-4 w-4/6')} />
          {rows > 3 && (
            <>
              <div className={cn(skeletonClass, 'h-4 w-full')} />
              <div className={cn(skeletonClass, 'h-4 w-3/4')} />
            </>
          )}
        </CardContent>
      </Card>
    );
  }
);

SkeletonCard.displayName = 'SkeletonCard';

/**
 * Grid of skeleton metric cards (for dashboard stats)
 *
 * @example
 * ```tsx
 * <SkeletonMetricGrid count={4} />
 * ```
 */
export const SkeletonMetricGrid: React.FC<{ count?: number; className?: string }> = ({
  count = 4,
  className,
}) => {
  return (
    <div className={cn('grid gap-4 md:grid-cols-2 lg:grid-cols-4', className)}>
      {[...Array(count)].map((_, i) => (
        <SkeletonCard key={i} variant="metric" />
      ))}
    </div>
  );
};

SkeletonMetricGrid.displayName = 'SkeletonMetricGrid';
