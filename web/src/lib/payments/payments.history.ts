/**
 * Локальная память об оплатах.
 *
 * Ответ /payments/balance не хранит историю платежей: по нему нельзя отличить
 * первую оплату от второй. Поэтому перед уходом на ЮKassa запоминаем намерение
 * (вкладка переживает редирект), а факт успешной оплаты — в localStorage,
 * чтобы отличить повторную покупку в аналитике.
 */

import type { PurchaseKind } from './payments.api'

const INTENT_KEY = 'payments_checkout_intent'
const PAID_ONCE_KEY = 'payments_paid_once'

export interface CheckoutIntent {
  orderId: string
  kind: PurchaseKind
  /** Остаток кредитов пакета на момент старта оплаты. */
  packCreditsBefore: number
}

export function rememberCheckoutIntent(intent: CheckoutIntent): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(INTENT_KEY, JSON.stringify(intent))
  } catch {
    // Приватный режим или переполненное хранилище — аналитика не критична
  }
}

export function readCheckoutIntent(): CheckoutIntent | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(INTENT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<CheckoutIntent>
    if (typeof parsed.orderId !== 'string') return null
    return {
      orderId: parsed.orderId,
      kind: parsed.kind === 'pack' ? 'pack' : 'order',
      packCreditsBefore: Number(parsed.packCreditsBefore) || 0,
    }
  } catch {
    return null
  }
}

export function clearCheckoutIntent(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(INTENT_KEY)
  } catch {
    // Нечего чистить
  }
}

/** Была ли у этого браузера успешная оплата раньше. */
export function hasPreviousPayment(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(PAID_ONCE_KEY) === '1'
  } catch {
    return false
  }
}

export function rememberPayment(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(PAID_ONCE_KEY, '1')
  } catch {
    // Аналитика повторных покупок деградирует, оплата не страдает
  }
}
