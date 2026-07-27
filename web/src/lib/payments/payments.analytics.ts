/**
 * Аналитика оплат: старт checkout и подтверждённый доступ после возврата с ЮKassa.
 * Логика повторной покупки живёт здесь, чтобы пейволл о ней не знал.
 */

import { track } from '@/lib/analytics'
import type { OrderAccess, PurchaseKind } from './payments.api'
import {
  clearCheckoutIntent,
  hasPreviousPayment,
  readCheckoutIntent,
  rememberCheckoutIntent,
  rememberPayment,
} from './payments.history'

export function reportCheckoutStarted(
  orderId: string,
  kind: PurchaseKind,
  amountRub: number,
  packCreditsBefore: number
): void {
  rememberCheckoutIntent({ orderId, kind, packCreditsBefore })
  track({
    name: 'payment_started',
    properties: { order_id: orderId, purchase_kind: kind, amount_rub: amountRub },
  })
}

/**
 * Отчитаться об успешной оплате ровно один раз: намерение живёт до первого
 * успеха, поэтому перезагрузка страницы события не дублирует.
 */
export function reportPaymentSucceeded(orderId: string, access: OrderAccess): void {
  const intent = readCheckoutIntent()
  if (!intent || access.reason === 'free_first') return

  const isRepeat = hasPreviousPayment() || intent.packCreditsBefore > 0
  track({
    name: 'payment_succeeded',
    properties: {
      order_id: orderId,
      purchase_kind: intent.kind,
      access_reason: access.reason ?? 'unknown',
    },
  })
  if (isRepeat) {
    track({
      name: 'payment_second_succeeded',
      properties: {
        order_id: orderId,
        purchase_kind: intent.kind,
        pack_credits: access.pack_credits,
      },
    })
  }
  rememberPayment()
  clearCheckoutIntent()
}
