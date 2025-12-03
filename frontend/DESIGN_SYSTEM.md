# TidyFrame Design System

## Overview
TidyFrame follows Apple's Human Interface Guidelines (HIG) with brand-specific customizations. All design tokens are defined as CSS custom properties in `src/index.css` and exposed through Tailwind utilities in `tailwind.config.js`.

---

## Color System

### Brand Colors
Our color system is **brand-derived** - all colors share the same hue relationship for visual cohesion.

#### Primary Blue (#1420bf)
```css
--color-primary-50: 228 93% 97%;   /* Lightest tint */
--color-primary-100: 228 93% 92%;
--color-primary-200: 228 93% 82%;
--color-primary-300: 228 93% 72%;
--color-primary-400: 228 93% 57%;
--color-primary-500: 228 93% 42%;  /* Base color */
--color-primary-600: 228 93% 35%;
--color-primary-700: 228 93% 28%;
--color-primary-800: 228 85% 22%;
--color-primary-900: 228 75% 16%;  /* Darkest shade */
```

**Usage:**
```tsx
<div className="bg-primary text-primary-foreground">Primary Button</div>
<div className="bg-primary-50 border-primary-200">Light background with border</div>
<span className="text-primary-600">Darker text</span>
```

#### Secondary Cyan (#8deaff)
```css
--color-secondary-500: 191 93% 77%;  /* Base color */
```

Full ramp (50-900) available. Use for accents, secondary actions, and highlights.

### Semantic Colors
Semantic colors are **hue-shifted** from the primary brand color, maintaining consistent saturation:

- **Success:** Primary blue shifted to green (150° hue)
- **Warning:** Primary blue shifted to amber (38° hue)
- **Destructive:** Primary blue shifted to red (0° hue)

**Usage:**
```tsx
<Badge className="bg-success text-success-foreground">Success</Badge>
<Alert className="border-warning-200 bg-warning-50">Warning</Alert>
<Button variant="destructive">Delete</Button>
```

### Status Colors
Purpose-built colors for UI feedback with background and border variants:

```tsx
// Success states
text-status-success           // Text
bg-status-success-bg         // Background
border-status-success-border // Border

// Warning states
text-status-warning
bg-status-warning-bg
border-status-warning-border

// Error states
text-status-error
bg-status-error-bg
border-status-error-border

// Info states
text-status-info
bg-status-info-bg
border-status-info-border

// Processing states
text-status-processing
bg-status-processing-bg
border-status-processing-border
```

**Example:**
```tsx
<div className="bg-status-success-bg border border-status-success-border rounded-card p-4">
  <p className="text-status-success font-semibold">95% Success Rate</p>
</div>
```

---

## Typography

### Apple HIG Scale
TidyFrame uses Apple's semantic typography scale. Font sizes are defined with built-in line heights, letter spacing, and font weights.

| Token | Size | Usage | Weight | Class |
|-------|------|-------|--------|-------|
| `hero` | 34px | Hero sections only | 700 (bold) | `text-hero` |
| `title-1` | 28px | Page titles (h1) | 700 (bold) | `text-title-1` |
| `title-2` | 22px | Section headings (h2), card titles | 700 (bold) | `text-title-2` |
| `title-3` | 20px | Subsection headings (h3) | 600 (semibold) | `text-title-3` |
| `headline` | 17px | Prominent text, dialog titles | 500 (medium) | `text-headline` |
| `body` | 17px | Body paragraphs | 400 (normal) | `text-body` |
| `callout` | 16px | Emphasized body text, buttons | 400 (normal) | `text-callout` |
| `subhead` | 15px | Secondary descriptive text | 400 (normal) | `text-subhead` |
| `footnote` | 13px | Metadata, form labels, captions | 400 (normal) | `text-footnote` |
| `caption` | 12px | Tiny labels, legal text | 400 (normal) | `text-caption` |

### Font Weight Hierarchy
Global rules ensure consistency:

```css
/* Headings are ALWAYS bold */
h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
}

/* Buttons are ALWAYS medium weight */
button, .button {
  font-weight: 500;
}

/* Labels are ALWAYS medium weight */
label {
  font-weight: 500;
}

/* Body text is normal weight */
body {
  font-weight: 400;
}
```

**Utility Classes:**
```tsx
<p className="font-normal">400 - body text</p>
<p className="font-medium">500 - buttons, labels</p>
<p className="font-semibold">600 - subheadings</p>
<p className="font-bold">700 - headings</p>
<p className="font-black">900 - stats, large numbers</p>
```

---

## Spacing (8pt Grid)

All spacing **MUST** use multiples of 8px for vertical rhythm.

### Tailwind Spacing Scale
| Class | Value | Usage |
|-------|-------|-------|
| `space-0` | 0px | No spacing |
| `space-2` | 8px | Tight spacing, icon gaps |
| `space-4` | 16px | Default spacing, cards |
| `space-6` | 24px | Medium spacing, sections |
| `space-8` | 32px | Large spacing, major sections |
| `space-12` | 48px | XL spacing, page sections |
| `space-16` | 64px | XXL spacing, hero sections |
| `space-20` | 80px | Hero sections |

### Apple HIG Touch Targets
Minimum sizes for interactive elements:

```tsx
<Button className="h-11">Default button (44px height)</Button>
<Button size="icon" className="h-11 w-11">Icon button (44px square)</Button>
```

Custom utilities:
- `min-h-touch` = 44px
- `min-w-touch` = 44px
- `min-h-touch-comfortable` = 48px
- `min-w-touch-comfortable` = 48px

### Common Patterns
```tsx
// Section spacing (hero, features, CTA)
<section className="py-20 px-4">

// Card padding
<Card className="p-6">

// Stack spacing
<div className="space-y-6">

// Grid gaps
<div className="grid gap-4 md:grid-cols-2">
```

---

## Border Radius

Semantic aliases reference CSS custom properties:

| Token | Value | Usage | Class |
|-------|-------|-------|-------|
| `badge` | 4px | Badges, chips, tags | `rounded-badge` |
| `sm` | 4px | Subtle corners | `rounded-sm` |
| `button` | 8px | Buttons, toggles | `rounded-button` |
| `input` | 8px | Text inputs, selects | `rounded-input` |
| `dropdown` | 8px | Dropdowns, menus, tooltips | `rounded-dropdown` |
| `md` | 8px | Standard | `rounded-md` |
| `card` | 12px | Cards, panels | `rounded-card` |
| `lg` | 12px | Cards | `rounded-lg` |
| `modal` | 16px | Dialogs, modals | `rounded-modal` |
| `xl` | 16px | Modals | `rounded-xl` |
| `2xl` | 24px | Hero sections | `rounded-2xl` |
| `full` | 9999px | Pills, avatars | `rounded-full` |

**Usage:**
```tsx
<Button className="rounded-button">Click me</Button>
<Card className="rounded-card">Content</Card>
<input className="rounded-input" />
<Dialog className="rounded-modal">Modal content</Dialog>
```

---

## Elevation (Shadows)

Apple-inspired shadow system for depth perception:

| Level | Usage | Class |
|-------|-------|-------|
| `shadow-0` / `shadow-none` | No shadow | No elevation |
| `shadow-1` / `shadow-card` | Card resting state | Cards, buttons |
| `shadow-2` / `shadow-dropdown` | Card hover, dropdowns | Dropdown menus |
| `shadow-3` / `shadow-modal` | Modals, dialogs | Modal overlays |
| `shadow-4` / `shadow-popover` | Popovers, tooltips | Floating content |
| `shadow-5` / `shadow-drawer` | Drawers, sidebars | Slide-out panels |

**Usage:**
```tsx
<Card className="shadow-card hover:shadow-dropdown transition-shadow">
  Card with hover effect
</Card>
```

---

## Transitions

Apple-inspired timing for smooth interactions:

### Durations
| Token | Value | Usage | Class |
|-------|-------|-------|-------|
| `instant` | 100ms | Hover, focus | `duration-instant` |
| `fast` | 150ms | Dropdowns, tooltips | `duration-fast` |
| `normal` | 200ms | Modals, dialogs | `duration-normal` |
| `slow` | 300ms | Page transitions | `duration-slow` |
| `slower` | 400ms | Complex animations | `duration-slower` |

### Easing
Apple's standard cubic-bezier curve:

```tsx
<div className="transition-all duration-instant ease-apple">
  Smooth Apple-style animation
</div>
```

---

## Accessibility

### Focus Indicators
All interactive elements have visible focus rings:

```css
*:focus-visible {
  outline: 2px solid hsl(var(--color-ring));
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

button:focus-visible {
  ring-2 ring-primary ring-offset-2
}
```

### Keyboard Navigation Testing Checklist
- [ ] Tab through all interactive elements
- [ ] Verify focus indicators are visible
- [ ] Test form submission with Enter key
- [ ] Verify modal/dialog focus trapping
- [ ] Test dropdown navigation with arrow keys
- [ ] Ensure no keyboard traps exist

---

## Component Patterns

### Cards
```tsx
<Card className="rounded-card shadow-card hover:shadow-dropdown transition-all duration-slow">
  <CardHeader>
    <CardTitle className="text-headline">Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent className="space-y-4">
    Content with consistent spacing
  </CardContent>
</Card>
```

### Buttons
```tsx
{/* Primary Action */}
<Button size="lg" variant="default">
  Get Started
</Button>

{/* Success Action */}
<Button variant="success">
  Download Results
</Button>

{/* Destructive Action */}
<Button variant="destructive">
  Delete
</Button>

{/* Secondary/Outline */}
<Button variant="outline">
  Cancel
</Button>
```

### Status Indicators
```tsx
{/* Success Badge */}
<Badge className="bg-status-success-bg text-status-success border-status-success-border">
  Completed
</Badge>

{/* Info Card */}
<div className="bg-status-info-bg border border-status-info-border rounded-card p-4">
  <p className="text-status-info font-semibold">Processing...</p>
</div>
```

---

## Migration Guide

### Replacing Hardcoded Colors
**Before:**
```tsx
<div className="text-green-500 bg-blue-50 border-red-200">
```

**After:**
```tsx
<div className="text-status-success bg-status-info-bg border-status-error-border">
```

### Fixing Non-8pt Spacing
**Before:**
```tsx
<div className="p-3 mb-3 gap-3">  {/* 12px - NOT on 8pt grid */}
```

**After:**
```tsx
<div className="p-4 mb-4 gap-4">  {/* 16px - ON 8pt grid */}
```

### Using Semantic Typography
**Before:**
```tsx
<h1 className="text-3xl font-bold">Page Title</h1>
```

**After:**
```tsx
<h1 className="text-title-1">Page Title</h1>  {/* Already has font-bold */}
```

---

## Tools & Resources

- **Tailwind Config:** `tailwind.config.js`
- **Design Tokens:** `src/index.css` (lines 1-450)
- **Component Library:** `src/components/ui/`
- **Apple HIG:** https://developer.apple.com/design/human-interface-guidelines/

---

## Version History

**v1.0.0** (2025-01-XX)
- Initial design system implementation
- Brand-derived color system
- Apple HIG typography scale
- 8pt grid spacing enforcement
- Focus-visible accessibility improvements
