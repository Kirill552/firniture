import { describe, it, expect, beforeEach, vi } from 'vitest'
import { registerSink, setConsent, unregisterSink, type AnalyticsEvent } from '../analytics'
import { reportCheckoutStarted, reportPaymentSucceeded } from './payments.analytics'
import { readCheckoutIntent, rememberPayment } from './payments.history'
import type { OrderAccess } from './payments.api'

const local = new Map<string, string>()
const session = new Map<string, string>()
const captured: AnalyticsEvent[] = []

function storage(map: Map<string, string>) {
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => {
      map.set(key, value)
    },
    removeItem: (key: string) => {
      map.delete(key)
    },
  }
}

const PAID: OrderAccess = {
  access: true,
  reason: 'payment',
  price_rub: 890,
  pack_credits: 0,
  free_first_available: false,
  beta_free: false,
}

beforeEach(() => {
  local.clear()
  session.clear()
  captured.length = 0
  unregisterSink()
  vi.stubGlobal('window', { localStorage: storage(local), sessionStorage: storage(session) })
  vi.stubGlobal('localStorage', storage(local))
  setConsent('granted')
  registerSink((event) => captured.push(event))
})

describe('reportCheckoutStarted', () => {
  it('шлёт payment_started и запоминает намерение до возврата с ЮKassa', () => {
    reportCheckoutStarted('order-5', 'pack', 7900, 2)

    expect(captured).toEqual([
      {
        name: 'payment_started',
        properties: { order_id: 'order-5', purchase_kind: 'pack', amount_rub: 7900 },
      },
    ])
    expect(readCheckoutIntent()).toEqual({
      orderId: 'order-5',
      kind: 'pack',
      packCreditsBefore: 2,
    })
  })
})

describe('reportPaymentSucceeded', () => {
  it('молчит без намерения: перезагрузка страницы не дублирует событие', () => {
    reportPaymentSucceeded('order-1', PAID)

    expect(captured).toHaveLength(0)
  })

  it('первая оплата шлёт только payment_succeeded и гасит намерение', () => {
    reportCheckoutStarted('order-1', 'order', 890, 0)
    captured.length = 0

    reportPaymentSucceeded('order-1', PAID)

    expect(captured.map((event) => event.name)).toEqual(['payment_succeeded'])
    expect(captured[0].properties).toMatchObject({
      order_id: 'order-1',
      purchase_kind: 'order',
      access_reason: 'payment',
    })
    expect(readCheckoutIntent()).toBeNull()
  })

  it('повторная оплата в том же браузере добавляет payment_second_succeeded', () => {
    rememberPayment()
    reportCheckoutStarted('order-2', 'order', 890, 0)
    captured.length = 0

    reportPaymentSucceeded('order-2', PAID)

    expect(captured.map((event) => event.name)).toEqual([
      'payment_succeeded',
      'payment_second_succeeded',
    ])
  })

  it('остаток пакета до оплаты тоже означает повторную покупку', () => {
    reportCheckoutStarted('order-3', 'pack', 7900, 4)
    captured.length = 0

    reportPaymentSucceeded('order-3', { ...PAID, reason: 'pack', pack_credits: 14 })

    expect(captured.map((event) => event.name)).toEqual([
      'payment_succeeded',
      'payment_second_succeeded',
    ])
    expect(captured[1].properties).toMatchObject({ purchase_kind: 'pack', pack_credits: 14 })
  })

  it('бесплатный первый заказ оплатой не считается', () => {
    reportCheckoutStarted('order-4', 'order', 890, 0)
    captured.length = 0

    reportPaymentSucceeded('order-4', { ...PAID, reason: 'free_first' })

    expect(captured).toHaveLength(0)
  })
})

describe('readCheckoutIntent', () => {
  it('игнорирует мусор в sessionStorage вместо падения', () => {
    session.set('payments_checkout_intent', '{ сломано')

    expect(readCheckoutIntent()).toBeNull()
  })
})
