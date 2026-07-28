"use client"

/**
 * Доступ к экспорту одного заказа: загрузка статуса, оплата через ЮKassa
 * и ожидание вебхука после возврата с платёжной страницы.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AccessAlreadyGrantedError,
  ORDER_PRICE_RUB,
  PACK_PRICE_RUB,
  clearCheckoutIntent,
  fetchOrderAccess,
  fetchPaymentBalance,
  reportCheckoutStarted,
  reportPaymentSucceeded,
  startOrderCheckout,
  startPackCheckout,
  type OrderAccess,
  type PaymentBalance,
  type PaymentRequiredError,
  type PurchaseKind,
} from '@/lib/payments'

/** Вебхук ЮKassa приходит не мгновенно: 15 попыток по 2 секунды = 30 секунд. */
const POLL_INTERVAL_MS = 2000
const POLL_ATTEMPTS = 15

export interface OrderAccessState {
  access: OrderAccess | null
  balance: PaymentBalance | null
  isLoading: boolean
  loadError: string | null
  isWaitingPayment: boolean
  waitTimedOut: boolean
  checkoutKind: PurchaseKind | null
  checkoutError: string | null
}

export interface UseOrderAccess extends OrderAccessState {
  buy: (kind: PurchaseKind) => void
  /** Перечитать доступ после экспорта: бэкенд мог списать бесплатный заказ или кредит. */
  reload: () => void
  markPaymentRequired: (error: PaymentRequiredError) => void
}

const INITIAL: OrderAccessState = {
  access: null,
  balance: null,
  isLoading: true,
  loadError: null,
  isWaitingPayment: false,
  waitTimedOut: false,
  checkoutKind: null,
  checkoutError: null,
}

/** Убрать ?payment из адреса, чтобы обновление страницы не запускало ожидание заново. */
function stripPaymentParam(): void {
  const url = new URL(window.location.href)
  if (!url.searchParams.has('payment')) return
  url.searchParams.delete('payment')
  window.history.replaceState(null, '', url.toString())
}

/** Пауза между опросами доступа. */
function nextPollTick(): Promise<void> {
  const { promise, resolve } = Promise.withResolvers<void>()
  setTimeout(resolve, POLL_INTERVAL_MS)
  return promise
}

export function useOrderAccess(orderId: string, returnedFromPayment: boolean): UseOrderAccess {
  const [state, setState] = useState<OrderAccessState>(INITIAL)
  const aliveRef = useRef(true)
  const pollStartedRef = useRef(false)
  const stateRef = useRef(state)
  stateRef.current = state

  useEffect(() => {
    aliveRef.current = true
    return () => {
      aliveRef.current = false
    }
  }, [])

  const load = useCallback(async (): Promise<OrderAccess | null> => {
    const [accessResult, balanceResult] = await Promise.allSettled([
      fetchOrderAccess(orderId),
      fetchPaymentBalance(),
    ])
    if (!aliveRef.current) return null

    const access = accessResult.status === 'fulfilled' ? accessResult.value : null
    const failure = accessResult.status === 'rejected' ? accessResult.reason : null
    setState((prev) => ({
      ...prev,
      access: access ?? prev.access,
      balance: balanceResult.status === 'fulfilled' ? balanceResult.value : prev.balance,
      isLoading: false,
      loadError: failure
        ? String(failure.message ?? 'Не удалось проверить доступ к заказу')
        : null,
    }))
    return access
  }, [orderId])

  const waitForWebhook = useCallback(async () => {
    setState((prev) => ({ ...prev, isWaitingPayment: true, waitTimedOut: false }))

    for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt += 1) {
      const access = await load()
      if (!aliveRef.current) return
      if (access?.access) {
        reportPaymentSucceeded(orderId, access)
        setState((prev) => ({ ...prev, isWaitingPayment: false }))
        stripPaymentParam()
        return
      }
      await nextPollTick()
    }

    if (!aliveRef.current) return
    setState((prev) => ({ ...prev, isWaitingPayment: false, waitTimedOut: true }))
    stripPaymentParam()
  }, [load, orderId])

  useEffect(() => {
    if (!orderId) return
    if (!returnedFromPayment) {
      void load()
      return
    }
    if (pollStartedRef.current) return
    pollStartedRef.current = true
    void waitForWebhook()
  }, [orderId, returnedFromPayment, load, waitForWebhook])

  const buy = useCallback(
    (kind: PurchaseKind) => {
      const { access, balance } = stateRef.current
      const amountRub =
        kind === 'pack'
          ? balance?.pack_price_rub ?? PACK_PRICE_RUB
          : access?.price_rub ?? balance?.price_rub ?? ORDER_PRICE_RUB

      setState((prev) => ({ ...prev, checkoutKind: kind, checkoutError: null }))
      reportCheckoutStarted(
        orderId,
        kind,
        amountRub,
        balance?.pack_credits ?? access?.pack_credits ?? 0
      )

      const checkout = kind === 'pack' ? startPackCheckout(orderId) : startOrderCheckout(orderId)
      checkout
        .then((session) => window.location.assign(session.confirmation_url))
        .catch((error: unknown) => {
          clearCheckoutIntent()
          if (!aliveRef.current) return
          if (error instanceof AccessAlreadyGrantedError) {
            setState((prev) => ({ ...prev, checkoutKind: null }))
            void load()
            return
          }
          setState((prev) => ({
            ...prev,
            checkoutKind: null,
            checkoutError: error instanceof Error ? error.message : 'Не удалось перейти к оплате',
          }))
        })
    },
    [orderId, load]
  )

  const markPaymentRequired = useCallback((error: PaymentRequiredError) => {
    setState((prev) => ({
      ...prev,
      isLoading: false,
      access: {
        access: false,
        reason: null,
        price_rub: error.priceRub,
        pack_credits: prev.access?.pack_credits ?? 0,
        free_first_available: false,
        beta_free: false,
      },
    }))
  }, [])

  const reload = useCallback(() => {
    void load()
  }, [load])

  return { ...state, buy, reload, markPaymentRequired }
}
