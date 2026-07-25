"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { FileText, Plus, Settings, type LucideIcon } from "lucide-react"

export type ProductNavItemVariant = "default" | "accent"

export interface ProductNavItem {
  title: string
  url: string
  icon: LucideIcon
  variant?: ProductNavItemVariant
}

export const productNavItems: ProductNavItem[] = [
  {
    title: "Новый заказ",
    url: "/new",
    icon: Plus,
    variant: "accent",
  },
  {
    title: "Заказы",
    url: "/orders",
    icon: FileText,
  },
  {
    title: "Настройки",
    url: "/settings",
    icon: Settings,
  },
]

export interface ProductNavigationProps {
  onNavigate?: () => void
  className?: string
}

export function ProductNavigation({
  onNavigate,
  className,
}: ProductNavigationProps) {
  const pathname = usePathname()

  return (
    <nav
      aria-label="Основная навигация"
      className={cn("w-full", className)}
    >
      <ul className="flex flex-col gap-1">
        {productNavItems.map((item) => {
          const Icon = item.icon
          const isAccent = item.variant === "accent"
          const isActive =
            pathname === item.url || pathname.startsWith(`${item.url}/`)

          return (
            <li key={item.url}>
              <Link
                href={item.url}
                onClick={onNavigate}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background motion-reduce:transition-none motion-reduce:duration-0",
                  isAccent
                    ? "bg-[var(--brand-lime)] text-[var(--brand-ink)] font-semibold hover:bg-[var(--brand-lime-strong)] active:scale-[0.98] motion-reduce:scale-100"
                    : isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                )}
              >
                {isActive && !isAccent && (
                  <span
                    aria-hidden="true"
                    className="absolute left-0 top-1/2 h-4 w-1 -translate-y-1/2 rounded-r-full bg-[var(--brand-lime)]"
                  />
                )}
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0",
                    isActive || isAccent
                      ? "text-[var(--brand-ink)]"
                      : "text-muted-foreground"
                  )}
                  aria-hidden="true"
                />
                <span>{item.title}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
