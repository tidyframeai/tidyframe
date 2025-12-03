import * as React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

export interface EmptyStateProps {
  /** Icon to display (Lucide icon component) */
  icon?: LucideIcon;
  /** Illustration image URL or React element (optional, overrides icon) */
  illustration?: string | React.ReactNode;
  /** Primary title text */
  title: string;
  /** Supporting description text */
  description?: string;
  /** Call-to-action button label */
  actionLabel?: string;
  /** Call-to-action button click handler */
  onAction?: () => void;
  /** CTA button variant */
  actionVariant?: 'default' | 'secondary' | 'outline' | 'ghost';
  /** Secondary action button label */
  secondaryActionLabel?: string;
  /** Secondary action button click handler */
  onSecondaryAction?: () => void;
  /** Help link text */
  helpLink?: {
    label: string;
    href: string;
  };
  /** Enable fade-in animation */
  animate?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional className */
  className?: string;
  /** Children for custom content */
  children?: React.ReactNode;
  /** Show subtle branding watermark at bottom */
  showBranding?: boolean;
}

/**
 * EmptyState component for consistent empty state patterns
 *
 * Features:
 * - Optional icon or illustration display
 * - Title and description with typography
 * - Primary and secondary CTA buttons
 * - Help links for documentation
 * - Fade-in animation for smooth appearance
 * - Size variants for different contexts
 * - Semantic HTML with proper ARIA labels
 *
 * @example
 * ```tsx
 * // Simple empty state with icon
 * <EmptyState
 *   icon={FileText}
 *   title="No files yet"
 *   description="Upload your first file to get started"
 *   animate
 * />
 *
 * // With illustration and dual CTAs
 * <EmptyState
 *   illustration="/images/empty-state.svg"
 *   title="No processing jobs"
 *   description="Upload a file to start processing names"
 *   actionLabel="Upload File"
 *   onAction={() => navigate('/upload')}
 *   secondaryActionLabel="View Tutorial"
 *   onSecondaryAction={() => navigate('/help')}
 *   helpLink={{ label: "Learn more about processing", href: "/docs" }}
 *   size="lg"
 *   animate
 * />
 *
 * // With custom React illustration
 * <EmptyState
 *   illustration={<CustomIllustration />}
 *   title="Empty inbox"
 *   description="All caught up!"
 * />
 * ```
 */
export const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  (
    {
      icon: Icon,
      illustration,
      title,
      description,
      actionLabel,
      onAction,
      actionVariant = 'default',
      secondaryActionLabel,
      onSecondaryAction,
      helpLink,
      animate = false,
      size = 'md',
      className,
      children,
      showBranding = false,
    },
    ref
  ) => {
    // Size-based styling
    const sizeClasses = {
      sm: {
        container: 'p-6',
        icon: 'h-10 w-10 mb-3',
        illustration: 'h-32 w-32 mb-4',
        title: 'text-base font-semibold',
        description: 'text-sm',
      },
      md: {
        container: 'p-12',
        icon: 'h-12 w-12 mb-4',
        illustration: 'h-40 w-40 mb-6',
        title: 'text-xl font-semibold',
        description: 'text-base',
      },
      lg: {
        container: 'p-16',
        icon: 'h-16 w-16 mb-6',
        illustration: 'h-48 w-48 mb-8',
        title: 'text-2xl font-semibold',
        description: 'text-base',
      },
    };

    const classes = sizeClasses[size];

    return (
      <div
        ref={ref}
        className={cn(
          'text-center',
          classes.container,
          animate && 'animate-in fade-in duration-500',
          className
        )}
        role="status"
        aria-label={`Empty state: ${title}`}
      >
        {/* Illustration (if provided, overrides icon) */}
        {illustration && (
          <div className={cn(classes.illustration, 'mx-auto')}>
            {typeof illustration === 'string' ? (
              <img
                src={illustration}
                alt=""
                className="w-full h-full object-contain"
                aria-hidden="true"
              />
            ) : (
              illustration
            )}
          </div>
        )}

        {/* Icon (only if no illustration) */}
        {!illustration && Icon && (
          <Icon
            className={cn(classes.icon, 'text-muted-foreground mx-auto')}
            aria-hidden="true"
          />
        )}

        <h3 className={cn(classes.title, 'mb-2')}>{title}</h3>

        {description && (
          <p className={cn(classes.description, 'text-muted-foreground mb-4')}>
            {description}
          </p>
        )}

        {children}

        {/* Action buttons */}
        {(actionLabel || secondaryActionLabel) && (
          <div className="flex items-center justify-center gap-2 mt-4">
            {actionLabel && onAction && (
              <Button
                onClick={onAction}
                variant={actionVariant}
                aria-label={actionLabel}
              >
                {actionLabel}
              </Button>
            )}
            {secondaryActionLabel && onSecondaryAction && (
              <Button
                onClick={onSecondaryAction}
                variant="outline"
                aria-label={secondaryActionLabel}
              >
                {secondaryActionLabel}
              </Button>
            )}
          </div>
        )}

        {/* Help link */}
        {helpLink && (
          <a
            href={helpLink.href}
            className="inline-block mt-4 text-sm text-primary hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {helpLink.label}
          </a>
        )}

        {/* Subtle branding watermark */}
        {showBranding && (
          <div className="mt-8 opacity-30">
            <Link to="/">
              <img
                src="/logo-with-name.png"
                alt="TidyFrame"
                className="h-12 mx-auto"
              />
            </Link>
          </div>
        )}
      </div>
    );
  }
);

EmptyState.displayName = 'EmptyState';
