import * as React from 'react';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';

export type LogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
export type LogoVariant = 'full' | 'icon';

export interface LogoProps {
  /** Size of the logo */
  size?: LogoSize;
  /** Logo variant - full (with text) or icon only */
  variant?: LogoVariant;
  /** Make logo a link to home */
  asLink?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Show animated hover effect */
  animated?: boolean;
}

const logoSizes: Record<LogoSize, string> = {
  xs: 'h-8',    // 32px - Mobile nav, compact spaces
  sm: 'h-10',   // 40px - Footer, small headers
  md: 'h-12',   // 48px - Default, dashboard
  lg: 'h-16',   // 64px - Auth pages
  xl: 'h-20',   // 80px - Hero sections
  '2xl': 'h-24' // 96px - Landing page hero
};

/**
 * Logo component for consistent branding across the app
 *
 * @example
 * // Default logo with text
 * <Logo />
 *
 * // Small icon only
 * <Logo size="sm" variant="icon" />
 *
 * // Large animated logo with link
 * <Logo size="xl" animated asLink />
 */
export const Logo = React.forwardRef<HTMLImageElement, LogoProps>(
  ({
    size = 'md',
    variant = 'full',
    asLink = false,
    className,
    animated = false,
    ...props
  }, ref) => {
    const sizeClass = logoSizes[size];

    // Choose the right logo file
    const getSrc = () => {
      if (variant === 'icon') {
        return '/logo-only.png';
      }
      return '/logo-with-name.png';
    };

    const logoElement = (
      <img
        ref={ref}
        src={getSrc()}
        alt="TidyFrame"
        className={cn(
          sizeClass,
          'object-contain',
          animated && 'transition-transform duration-300 hover:scale-105',
          className
        )}
        {...props}
      />
    );

    if (asLink) {
      return (
        <Link
          to="/"
          className={cn(
            'inline-flex items-center',
            animated && 'group'
          )}
        >
          {logoElement}
        </Link>
      );
    }

    return logoElement;
  }
);

Logo.displayName = 'Logo';