/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      /* Responsive Breakpoints - Extends defaults with ultrawide support */
      screens: {
        '3xl': '2560px',   // 27"+ displays, ultrawide monitors
      },
      /* Maximum Content Width - Prevents over-stretching on large displays */
      maxWidth: {
        'ultrawide': '1920px',  // Maximum content width for ultrawide displays
        'comfortable': '1440px', // Optimal reading width for text-heavy content
      },
      /* Apple HIG - Spacing additions (extends default, doesn't replace) */
      spacing: {
        '4.5': '1.125rem',  // 18px - between default values
        '11': '2.75rem',    // 44px - Apple minimum touch target
        '13': '3.25rem',    // 52px - comfortable touch target
        '15': '3.75rem',    // 60px - large touch target
        '17': '4.25rem',    // 68px
        '18': '4.5rem',     // 72px
        '19': '4.75rem',    // 76px
        '21': '5.25rem',    // 84px
        '22': '5.5rem',     // 88px
        '26': '6.5rem',     // 104px
        '30': '7.5rem',     // 120px
      },
      /* Apple HIG - Border radius (references CSS custom properties) */
      borderRadius: {
        // Base tokens from CSS custom properties
        'sm': 'var(--radius-sm)',        // 4px - subtle corners
        'DEFAULT': 'var(--radius-md)',   // 8px - standard (FIX: was 6px hardcoded)
        'md': 'var(--radius-md)',        // 8px - standard
        'lg': 'var(--radius-lg)',        // 12px - cards (FIX: was 10px hardcoded)
        'xl': 'var(--radius-xl)',        // 16px - modals (FIX: was 14px hardcoded)
        '2xl': 'var(--radius-2xl)',      // 24px - hero sections (FIX: was 18px hardcoded)
        'full': '9999px',                // Pills, avatars, circles

        // Semantic aliases for Apple HIG component hierarchy
        'button': 'var(--radius-md)',    // 8px - buttons, toggles
        'input': 'var(--radius-md)',     // 8px - text inputs, selects, textareas
        'card': 'var(--radius-lg)',      // 12px - cards, panels, containers
        'modal': 'var(--radius-xl)',     // 16px - dialogs, modals, sheets
        'dropdown': 'var(--radius-md)',  // 8px - dropdowns, menus, tooltips, popovers
        'badge': 'var(--radius-sm)',     // 4px - badges, chips, tags
      },
      /* Apple HIG - Z-Index Layering (references CSS custom properties) */
      zIndex: {
        // Base tokens from CSS custom properties
        '0': 'var(--z-base)',           // Default layer
        '10': 'var(--z-dropdown)',      // Dropdowns, navigation menus
        '20': 'var(--z-sticky)',        // Sticky headers
        '30': 'var(--z-overlay)',       // Modal backdrops
        '40': 'var(--z-sidebar)',       // Sidebars, drawers
        '50': 'var(--z-modal)',         // Modals, dialogs, tooltips

        // Semantic aliases for clarity
        'base': 'var(--z-base)',
        'dropdown': 'var(--z-dropdown)',
        'sticky': 'var(--z-sticky)',
        'overlay': 'var(--z-overlay)',
        'sidebar': 'var(--z-sidebar)',
        'modal': 'var(--z-modal)',
      },
      /* Apple HIG - Opacity Scale (references CSS custom properties) */
      opacity: {
        '0': 'var(--opacity-0)',
        '50': 'var(--opacity-50)',
        '60': 'var(--opacity-60)',
        '70': 'var(--opacity-70)',
        '75': 'var(--opacity-75)',
        '90': 'var(--opacity-90)',
        '95': 'var(--opacity-95)',
        '100': 'var(--opacity-100)',

        // Semantic aliases for interaction states
        'hover': 'var(--opacity-hover)',
        'active': 'var(--opacity-active)',
        'disabled': 'var(--opacity-disabled)',
      },
      /* Apple HIG - Touch target utilities */
      minHeight: {
        'touch': '2.75rem',      // 44px - minimum
        'touch-comfortable': '3rem', // 48px - comfortable
      },
      minWidth: {
        'touch': '2.75rem',      // 44px - minimum
        'touch-comfortable': '3rem', // 48px - comfortable
      },
      /* Apple HIG - Elevation/Shadow system (references CSS custom properties) */
      boxShadow: {
        '0': 'var(--shadow-0)',         // none
        '1': 'var(--shadow-1)',         // Card resting
        '2': 'var(--shadow-2)',         // Card hover, Dropdown
        '3': 'var(--shadow-3)',         // Modal
        '4': 'var(--shadow-4)',         // Popover
        '5': 'var(--shadow-5)',         // Drawer
        // Semantic aliases for clarity
        'none': 'var(--shadow-0)',
        'card': 'var(--shadow-1)',
        'dropdown': 'var(--shadow-2)',
        'modal': 'var(--shadow-3)',
        'popover': 'var(--shadow-4)',
        'drawer': 'var(--shadow-5)',
      },
      /* Apple HIG - Transition durations (references CSS custom properties) */
      transitionDuration: {
        'instant': 'var(--duration-instant)',   // 100ms - Hover, focus
        'fast': 'var(--duration-fast)',         // 150ms - Dropdowns, tooltips
        'normal': 'var(--duration-normal)',     // 200ms - Modals, dialogs
        'slow': 'var(--duration-slow)',         // 300ms - Page transitions
        'slower': 'var(--duration-slower)',     // 400ms - Complex animations
      },
      /* Apple HIG - Easing curves (references CSS custom properties) */
      transitionTimingFunction: {
        'apple': 'var(--ease-in-out)',          // cubic-bezier(0.4, 0, 0.2, 1) - Apple's standard
        'ease-in': 'var(--ease-in)',            // cubic-bezier(0.4, 0, 1, 1)
        'ease-out': 'var(--ease-out)',          // cubic-bezier(0, 0, 0.2, 1)
        'ease-in-out': 'var(--ease-in-out)',    // cubic-bezier(0.4, 0, 0.2, 1)
      },
      /* Apple HIG - Typography Hierarchy (semantic naming) */
      fontSize: {
        // Apple HIG Typography Scale - Use these for semantic meaning
        'display': ['4rem', { lineHeight: '1.1', letterSpacing: '-0.03em', fontWeight: '900' }],                                                                      // 64px - Hero headlines (modern SaaS)
        'display-sm': ['3rem', { lineHeight: '1.15', letterSpacing: '-0.025em', fontWeight: '800' }],                                                                 // 48px - Secondary heroes
        'hero': ['var(--font-size-large-title)', { lineHeight: 'var(--line-height-tight)', letterSpacing: '-0.02em', fontWeight: 'var(--font-weight-bold)' }],      // 34px - Hero sections only
        'title-1': ['var(--font-size-title-1)', { lineHeight: 'var(--line-height-tight)', letterSpacing: '-0.015em', fontWeight: 'var(--font-weight-bold)' }],      // 28px - Page titles (h1)
        'title-2': ['var(--font-size-title-2)', { lineHeight: 'var(--line-height-snug)', letterSpacing: '-0.01em', fontWeight: 'var(--font-weight-bold)' }],        // 22px - Section headings (h2), card titles
        'title-3': ['var(--font-size-title-3)', { lineHeight: 'var(--line-height-snug)', fontWeight: 'var(--font-weight-semibold)' }],                                  // 20px - Subsection headings (h3)
        'headline': ['var(--font-size-headline)', { lineHeight: 'var(--line-height-snug)', fontWeight: 'var(--font-weight-medium)' }],                                // 17px - Prominent text, dialog titles
        'body': ['var(--font-size-body)', { lineHeight: 'var(--line-height-normal)', fontWeight: 'var(--font-weight-normal)' }],                                      // 17px - Body paragraphs
        'callout': ['var(--font-size-callout)', { lineHeight: 'var(--line-height-normal)', fontWeight: 'var(--font-weight-normal)' }],                                // 16px - Emphasized body text
        'subhead': ['var(--font-size-subhead)', { lineHeight: 'var(--line-height-normal)', fontWeight: 'var(--font-weight-normal)' }],                                // 15px - Secondary descriptive text
        'footnote': ['var(--font-size-footnote)', { lineHeight: 'var(--line-height-snug)', fontWeight: 'var(--font-weight-normal)' }],                                // 13px - Metadata, form labels, captions
        'caption': ['var(--font-size-caption)', { lineHeight: 'var(--line-height-snug)', fontWeight: 'var(--font-weight-normal)' }],                                  // 12px - Tiny labels, legal text
      },
      fontWeight: {
        normal: 'var(--font-weight-normal)',     // 400
        medium: 'var(--font-weight-medium)',     // 500
        semibold: 'var(--font-weight-semibold)', // 600
        bold: 'var(--font-weight-bold)',         // 700
        black: 'var(--font-weight-black)',       // 900 - for stats, large numbers
      },
      colors: {
        /* Brand Colors with Full Ramps */
        'primary': {
          50: 'hsl(var(--color-primary-50))',
          100: 'hsl(var(--color-primary-100))',
          200: 'hsl(var(--color-primary-200))',
          300: 'hsl(var(--color-primary-300))',
          400: 'hsl(var(--color-primary-400))',
          500: 'hsl(var(--color-primary-500))',
          600: 'hsl(var(--color-primary-600))',
          700: 'hsl(var(--color-primary-700))',
          800: 'hsl(var(--color-primary-800))',
          900: 'hsl(var(--color-primary-900))',
          DEFAULT: 'hsl(var(--color-primary))',
          foreground: 'hsl(var(--color-primary-foreground))',
        },
        'secondary': {
          50: 'hsl(var(--color-secondary-50))',
          100: 'hsl(var(--color-secondary-100))',
          200: 'hsl(var(--color-secondary-200))',
          300: 'hsl(var(--color-secondary-300))',
          400: 'hsl(var(--color-secondary-400))',
          500: 'hsl(var(--color-secondary-500))',
          600: 'hsl(var(--color-secondary-600))',
          700: 'hsl(var(--color-secondary-700))',
          800: 'hsl(var(--color-secondary-800))',
          900: 'hsl(var(--color-secondary-900))',
          DEFAULT: 'hsl(var(--color-secondary))',
          foreground: 'hsl(var(--color-secondary-foreground))',
        },
        /* Semantic Colors with Ramps */
        'success': {
          50: 'hsl(var(--color-success-50))',
          100: 'hsl(var(--color-success-100))',
          500: 'hsl(var(--color-success-500))',
          600: 'hsl(var(--color-success-600))',
          DEFAULT: 'hsl(var(--color-success))',
          foreground: 'hsl(var(--color-success-foreground))',
        },
        'warning': {
          50: 'hsl(var(--color-warning-50))',
          100: 'hsl(var(--color-warning-100))',
          500: 'hsl(var(--color-warning-500))',
          600: 'hsl(var(--color-warning-600))',
          DEFAULT: 'hsl(var(--color-warning))',
          foreground: 'hsl(var(--color-warning-foreground))',
        },
        'destructive': {
          50: 'hsl(var(--color-destructive-50))',
          100: 'hsl(var(--color-destructive-100))',
          500: 'hsl(var(--color-destructive-500))',
          600: 'hsl(var(--color-destructive-600))',
          DEFAULT: 'hsl(var(--color-destructive))',
          foreground: 'hsl(var(--color-destructive-foreground))',
        },
        /* Status Colors for Consistency */
        'status': {
          success: 'hsl(var(--color-status-success))',
          'success-bg': 'hsl(var(--color-status-success-bg))',
          'success-border': 'hsl(var(--color-status-success-border))',
          warning: 'hsl(var(--color-status-warning))',
          'warning-bg': 'hsl(var(--color-status-warning-bg))',
          'warning-border': 'hsl(var(--color-status-warning-border))',
          error: 'hsl(var(--color-status-error))',
          'error-bg': 'hsl(var(--color-status-error-bg))',
          'error-border': 'hsl(var(--color-status-error-border))',
          info: 'hsl(var(--color-status-info))',
          'info-bg': 'hsl(var(--color-status-info-bg))',
          'info-border': 'hsl(var(--color-status-info-border))',
          processing: 'hsl(var(--color-status-processing))',
          'processing-bg': 'hsl(var(--color-status-processing-bg))',
          'processing-border': 'hsl(var(--color-status-processing-border))',
        },
      },
      /* Enhanced Border System - Three-tier hierarchy for nested elements */
      borderColor: {
        subtle: 'hsl(var(--color-border-subtle))',
        DEFAULT: 'hsl(var(--color-border-default))',
        strong: 'hsl(var(--color-border-strong))',
      },
    },
  },
}