'use client'

import { ReactNode } from 'react'
import { Card } from '@/components/ui/card'

interface AuthShellProps {
  children: ReactNode
}

/**
 * Общая оболочка экранов входа/регистрации/verify: центрированная карточка
 * на спокойном studio-фоне. Использует существующие theme tokens
 * (brand-система придёт в Task 6/7).
 */
export function AuthShell({ children }: AuthShellProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-10">
      <Card className="w-full max-w-[420px] p-8">{children}</Card>
    </div>
  )
}
