import * as React from "react"
import { motion, HTMLMotionProps } from "framer-motion"
import { Slot } from "@radix-ui/react-slot"

import { cn } from "@/lib/utils"
import { buttonVariants, type ButtonVariantProps } from "./button-variants"

export interface ButtonProps
  extends Omit<HTMLMotionProps<"button">, "ref">,
    ButtonVariantProps {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    if (asChild) {
      const { whileHover: _whileHover, whileTap: _whileTap, transition: _transition, ...slotProps } = props;
      return (
        <Slot
          className={cn(buttonVariants({ variant, size, className }))}
          {...(slotProps as React.ComponentPropsWithoutRef<typeof Slot>)}
        />
      )
    }
    
    return (
      <motion.button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        whileTap={{ scale: 0.98 }}
        transition={{ type: "spring", stiffness: 400, damping: 17 }}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
