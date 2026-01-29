"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { ChevronRight, Home } from "lucide-react"
import { cn } from "@/lib/utils"

type Crumb = {
  href: string
  label: string
}

// Человеко-читаемые лейблы по маршрутам
const LABELS: Record<string, string> = {
  "": "Главная",
  "dashboard": "Обзор",
  "orders": "Заказы",
  "new": "Новый заказ",
  "manual": "Ручной ввод",
  "bom": "Спецификация",
  "cam": "Файлы для станка",
  "hardware": "Фурнитура",
  "integrations": "Интеграции",
  "settings": "Настройки",
  "history": "История заказов",
  "audit": "Аудит",
  "pricing": "Тарифы",
  "login": "Вход",
}

function normalizeSegment(segment: string) {
  // Сначала проверяем есть ли перевод
  if (LABELS[segment]) {
    return LABELS[segment]
  }
  // Если сегмент похож на UUID/ID — показываем сокращённо
  if (/^[0-9a-f-]{8,}$/i.test(segment)) {
    return segment.slice(0, 8) + "..."
  }
  return decodeURIComponent(segment)
}

export interface BreadcrumbsProps {
  className?: string
  rootHref?: string
}

export function Breadcrumbs({ className, rootHref = "/orders" }: BreadcrumbsProps) {
  const pathname = usePathname()
  const segments = React.useMemo(() => {
    const parts = pathname.split("/").filter(Boolean)
    const crumbs: Crumb[] = []
    let path = ""
    for (const part of parts) {
      path += `/${part}`
      crumbs.push({ href: path, label: normalizeSegment(part) })
    }
    return crumbs
  }, [pathname])

  // Публичные страницы — без хлебных крошек
  if (["/", "/login", "/pricing"].includes(pathname)) return null

  return (
    <nav aria-label="Хлебные крошки" className={cn("w-full", className)}>
      <ol className="flex items-center gap-1 text-sm text-muted-foreground">
        <li className="flex items-center">
          <Link href={rootHref} className="inline-flex items-center gap-1 transition-colors duration-200 hover:text-foreground focus-visible">
            <Home className="h-4 w-4" aria-hidden />
            <span className="sr-only">На главную</span>
          </Link>
        </li>
        {segments.map((crumb, idx) => {
          const isLast = idx === segments.length - 1
          return (
            <React.Fragment key={crumb.href}>
              <li aria-hidden className="px-1 text-muted-foreground">
                <ChevronRight className="h-4 w-4" />
              </li>
              <li>
                {isLast ? (
                  <span className="text-foreground font-medium" aria-current="page">{crumb.label}</span>
                ) : (
                  <Link href={crumb.href} className="transition-colors duration-200 hover:text-foreground focus-visible">
                    {crumb.label}
                  </Link>
                )}
              </li>
            </React.Fragment>
          )
        })}
      </ol>
    </nav>
  )
}

export default Breadcrumbs
