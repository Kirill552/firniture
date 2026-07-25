'use client'

import React, { useEffect, useState } from 'react'
import { useAnalytics } from './analytics-provider'

export function AnalyticsConsent() {
  const { consent, updateConsent } = useAnalytics()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted || consent !== 'pending') return null

  return (
    <div 
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-md p-4 rounded-xl border border-[#d7dde2] bg-white shadow-lg z-50 transition-all duration-300 ease-out"
      role="alert"
      aria-label="Согласие на сбор аналитики"
    >
      <div className="flex flex-col gap-3">
        <p className="text-xs text-[#66707a] leading-relaxed">
          Мы собираем обезличенные данные (без почты и эскизов), чтобы улучшить процесс распознавания мебели и качество чертежей.
        </p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => updateConsent('denied')}
            className="px-3 py-1.5 rounded-lg text-xs font-medium border border-[#d7dde2] text-[#171a1d] hover:bg-[#f3f6f8] active:scale-[0.97] transition-all duration-150 cursor-pointer"
          >
            Не разрешать
          </button>
          <button
            onClick={() => updateConsent('granted')}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#c7ff00] hover:bg-[#aee600] text-[#171a1d] active:scale-[0.97] transition-all duration-150 cursor-pointer"
          >
            Разрешить аналитику
          </button>
        </div>
      </div>
    </div>
  )
}
