import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-base font-medium transition-all duration-normal focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/50 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90 hover:brightness-110 shadow-sm hover:shadow-md",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:brightness-110 shadow-sm hover:shadow-md",
        outline:
          "border-2 border-input bg-background hover:bg-accent hover:text-accent-foreground hover:border-primary/70 hover:shadow-sm",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 hover:brightness-105 shadow-sm hover:shadow-md",
        ghost: "hover:bg-accent hover:text-accent-foreground hover:shadow-sm",
        link: "text-primary underline-offset-4 hover:underline hover:brightness-110",
        prominent: "text-white shadow-lg hover:shadow-2xl transition-all duration-normal font-semibold hover:scale-[1.02] hover:brightness-110" + " [background:var(--gradient-brand)]",
        success: "bg-success text-success-foreground hover:bg-success/90 hover:brightness-110 shadow-md hover:shadow-lg transition-all duration-normal",
      },
      size: {
        default: "h-11 px-4 py-2",     // 44px height - Apple HIG minimum
        sm: "h-10 px-3 py-2",          // 40px - compact (8px vertical)
        lg: "h-12 px-6 py-3",          // 48px - comfortable
        icon: "h-11 w-11",             // 44px square - Apple HIG minimum
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

// eslint-disable-next-line react-refresh/only-export-components
export { Button, buttonVariants }
