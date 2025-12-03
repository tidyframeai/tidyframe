import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-badge border px-3 py-1 text-xs font-semibold transition-colors duration-[var(--duration-fast)] focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/90 hover:text-white shadow-sm",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/90 hover:text-white",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:text-white shadow-sm",
        success:
          "border-transparent bg-success text-success-foreground hover:bg-success/90 hover:text-white shadow-sm",
        warning:
          "border-transparent bg-warning text-warning-foreground hover:bg-warning/90 hover:text-white shadow-sm",
        info:
          "border-transparent bg-info text-info-foreground hover:bg-info/90 hover:text-white shadow-sm",
        outline: "text-foreground border-border hover:bg-muted",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export { Badge, badgeVariants }
