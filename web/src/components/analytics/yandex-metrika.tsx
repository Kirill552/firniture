'use client'

import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { useAnalytics } from './analytics-provider'

declare global {
  interface Window {
    ym?: ((id: number, action: string, ...args: unknown[]) => void) & { a?: unknown[]; l?: number }
  }
}

/** ID счётчика Метрики (публичный, виден в исходнике страницы). */
const COUNTER_ID = Number(process.env.NEXT_PUBLIC_YM_COUNTER_ID) || 111048722

/** Загружает tag.js один раз. Вызов идёт только после согласия пользователя. */
function loadCounter(): void {
  if (window.ym) return

  const stub = ((...args: unknown[]) => {
    ;(stub.a = stub.a || []).push(args)
  }) as NonNullable<Window['ym']>
  stub.l = Date.now()
  window.ym = stub

  const script = document.createElement('script')
  script.src = 'https://mc.yandex.ru/metrika/tag.js'
  script.async = true
  document.head.appendChild(script)

  // defer: сервис сам шлёт hit при смене маршрута (App Router не перезагружает страницу)
  window.ym(COUNTER_ID, 'init', {
    defer: true,
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: true,
  })
}

/**
 * Яндекс.Метрика с привязкой к согласию (152-ФЗ: Вебвизор пишет поведение).
 * Счётчик грузится только при consent === 'granted', hit шлётся на каждый маршрут.
 */
export function YandexMetrika() {
  const { consent } = useAnalytics()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!COUNTER_ID || consent !== 'granted') return

    loadCounter()

    const query = searchParams.toString()
    window.ym?.(COUNTER_ID, 'hit', query ? `${pathname}?${query}` : pathname)
  }, [consent, pathname, searchParams])

  return null
}
