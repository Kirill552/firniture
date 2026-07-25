"use client"

import * as React from "react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { ProductHeader } from "./product-header"
import { ProductNavigation } from "./product-navigation"

export interface ProductShellProps {
  children: React.ReactNode
  title: string
  description?: string
  headerActions?: React.ReactNode
  className?: string
}

function ProductLogo() {
  return (
    <Link href="/orders" className="flex items-center gap-3 select-none">
      <span className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)]">
        <span className="text-[14px] font-extrabold tracking-[-1px] text-[var(--brand-ink)]">
          АР
        </span>
        <span className="absolute -right-[2px] -top-[2px] h-2 w-2 rounded-full bg-[var(--brand-lime)]" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="text-[14px] font-bold tracking-[-0.6px] text-[var(--brand-ink)]">
          АвтоРаскрой
        </span>
        <span className="font-mono mt-0.5 text-[8.5px] uppercase tracking-[1.5px] text-[var(--brand-muted)]">
          заказы
        </span>
      </span>
    </Link>
  )
}

export function ProductShell({
  children,
  title,
  description,
  headerActions,
  className,
}: ProductShellProps) {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const closeMobile = React.useCallback(() => setMobileOpen(false), [])

  return (
    <div className={cn("flex min-h-svh w-full bg-background", className)}>
      <a
        href="#main-content"
        className="skip-link motion-reduce:transition-none"
      >
        Перейти к содержимому
      </a>

      {/* Desktop sidebar */}
      <aside
        className="sticky top-0 z-30 hidden h-svh w-60 shrink-0 flex-col border-r border-border bg-sidebar md:flex"
        aria-label="Боковая навигация"
      >
        <div className="flex h-14 items-center border-b border-border px-4">
          <ProductLogo />
        </div>
        <div className="flex-1 overflow-auto p-3">
          <ProductNavigation onNavigate={closeMobile} />
        </div>
      </aside>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        <ProductHeader
          title={title}
          description={description}
          actions={headerActions}
          menuOpen={mobileOpen}
          onMenuClick={() => setMobileOpen(true)}
        />
        <main
          id="main-content"
          className="flex-1 focus:outline-none"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>

      {/* Mobile navigation */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent
          id="mobile-nav-sheet"
          side="left"
          className="w-72 bg-sidebar p-0"
          aria-describedby="mobile-nav-description"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Навигация</SheetTitle>
            <SheetDescription id="mobile-nav-description">
              Меню приложения АвтоРаскрой
            </SheetDescription>
          </SheetHeader>
          <div className="flex h-full flex-col">
            <div className="flex h-14 items-center border-b border-border px-4">
              <ProductLogo />
            </div>
            <div className="flex-1 overflow-auto p-3">
              <ProductNavigation onNavigate={closeMobile} />
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
