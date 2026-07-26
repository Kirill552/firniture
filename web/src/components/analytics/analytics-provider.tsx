'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { getConsent, setConsent, registerSink, unregisterSink, type ConsentStatus, type AnalyticsEvent } from '@/lib/analytics'
import { YM_COUNTER_ID } from './yandex-metrika'

interface AnalyticsContextType {
  consent: ConsentStatus
  updateConsent: (status: 'granted' | 'denied') => void
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined)

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const [consent, setConsentState] = useState<ConsentStatus>('pending')

  useEffect(() => {
    const initialConsent = getConsent()
    setConsentState(initialConsent)
  }, [])

  useEffect(() => {
    if (consent === 'granted') {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''
      const targetUrl = `${API_BASE_URL}/api/v1/product-analytics/events`

      registerSink((event: AnalyticsEvent) => {
        try {
          fetch(targetUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(event),
            keepalive: true,
          }).catch((err) => {
            console.error('Failed to send analytics event', err)
          })

          // Дублируем событие целью Метрики: воронка считается без ручной разметки
          window.ym?.(YM_COUNTER_ID, 'reachGoal', event.name)
        } catch (e) {
          console.error('Error in analytics sink', e)
        }
      })
    } else {
      unregisterSink()
    }

    return () => {
      unregisterSink()
    }
  }, [consent])

  const updateConsent = (status: 'granted' | 'denied') => {
    setConsent(status)
    setConsentState(status)
  }

  return (
    <AnalyticsContext.Provider value={{ consent, updateConsent }}>
      {children}
    </AnalyticsContext.Provider>
  )
}

export function useAnalytics() {
  const context = useContext(AnalyticsContext)
  if (!context) {
    throw new Error('useAnalytics must be used within an AnalyticsProvider')
  }
  return context
}
