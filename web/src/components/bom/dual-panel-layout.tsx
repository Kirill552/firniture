"use client"

import { cn } from "@/lib/utils"

interface DualPanelLayoutProps {
  leftColumn: React.ReactNode
  rightColumn: React.ReactNode
  className?: string
}

export function DualPanelLayout({
  leftColumn,
  rightColumn,
  className,
}: DualPanelLayoutProps) {
  return (
    <div
      className={cn(
        "grid gap-6",
        // Desktop: 60/40
        "lg:grid-cols-[3fr_2fr]",
        // Tablet: 50/50
        "md:grid-cols-2",
        // Mobile: stack
        "grid-cols-1",
        className
      )}
    >
      {/* Левая колонка: редактирование */}
      <div className="space-y-4 min-w-0">
        {leftColumn}
      </div>

      {/* Правая колонка: визуализация + файлы */}
      <div className="space-y-4 min-w-0 lg:sticky lg:top-6 lg:self-start">
        {rightColumn}
      </div>
    </div>
  )
}
