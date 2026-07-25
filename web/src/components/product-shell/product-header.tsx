"use client"

import * as React from "react"
import { Menu } from "lucide-react"
import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"

export interface ProductHeaderProps {
  title: string
  description?: string
  actions?: React.ReactNode
  menuOpen?: boolean
  onMenuClick?: () => void
  className?: string
}

export function ProductHeader({
  title,
  description,
  actions,
  menuOpen,
  onMenuClick,
  className,
}: ProductHeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        className
      )}
    >
      <div className="flex h-14 items-center gap-3 px-4">
        <button
          type="button"
          className={cn(
            buttonVariants({ variant: "ghost", size: "icon" }),
            "shrink-0 md:hidden motion-reduce:transition-none motion-reduce:duration-0"
          )}
          aria-label="Открыть меню"
          aria-expanded={menuOpen}
          aria-controls="mobile-nav-sheet"
          onClick={onMenuClick}
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
          <span className="sr-only">Меню</span>
        </button>

        <div className="flex min-w-0 flex-col">
          <h1 className="truncate text-base font-semibold text-foreground">
            {title}
          </h1>
          {description && (
            <p className="truncate text-xs text-muted-foreground">
              {description}
            </p>
          )}
        </div>

        {actions && (
          <div className="ml-auto flex items-center gap-2">{actions}</div>
        )}
      </div>
    </header>
  )
}
