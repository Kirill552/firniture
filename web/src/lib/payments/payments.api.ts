/**
 * Клиент платежей ЮKassa.
 *
 * Единица тарификации — заказ целиком, сколько бы изделий в нём ни было.
 * Цены приходят с бэкенда; константы ниже нужны только для первого рендера
 * и для сообщений об ошибке, когда ответ ещё не получен.
 */

import type {
  BalanceResponse,
  CheckoutResponse,
  OrderAccessResponse,
  PackCheckoutRequest,
} from '@/lib/api/generated'
import { getAuthHeader } from '@/lib/auth'

export const ORDER_PRICE_RUB = 890
export const PACK_PRICE_RUB = 7900
export const PACK_SIZE = 10

/** Почему доступ к экспорту заказа открыт. */
export type AccessReason = 'free_first' | 'payment' | 'pack' | null

/** Что покупаем: доступ к одному заказу или пакет из 10 заказов. */
export type PurchaseKind = 'order' | 'pack'

/** Доступ к экспорту заказа. Отличие от контракта — сужённый reason. */
export interface OrderAccess extends Omit<OrderAccessResponse, 'reason'> {
  reason: AccessReason
}

export type PaymentBalance = BalanceResponse
export type CheckoutSession = CheckoutResponse

/** 402 от экспортных эндпоинтов: доступ к заказу не оплачен. */
export class PaymentRequiredError extends Error {
  readonly orderId: string
  readonly priceRub: number

  constructor(orderId: string, priceRub: number = ORDER_PRICE_RUB) {
    super('Экспорт этого заказа не оплачен')
    this.name = 'PaymentRequiredError'
    this.orderId = orderId
    this.priceRub = priceRub
  }
}

/** 409 на checkout: доступ к заказу уже есть, платить второй раз не нужно. */
export class AccessAlreadyGrantedError extends Error {
  constructor() {
    super('Доступ к заказу уже открыт')
    this.name = 'AccessAlreadyGrantedError'
  }
}

export function isPaymentRequiredError(error: unknown): error is PaymentRequiredError {
  return error instanceof PaymentRequiredError
}

interface ErrorBody {
  detail?: string | { code?: string; order_id?: string; price_rub?: number }
}

/** Достать типизированный 402 из ответа экспортного эндпоинта. */
export async function readPaymentRequired(
  response: Response,
  fallbackOrderId: string
): Promise<PaymentRequiredError> {
  const body = (await response.json().catch(() => null)) as ErrorBody | null
  const detail = typeof body?.detail === 'object' ? body.detail : null
  return new PaymentRequiredError(
    detail?.order_id ?? fallbackOrderId,
    detail?.price_rub ?? ORDER_PRICE_RUB
  )
}

function readErrorMessage(body: ErrorBody | null, status: number): string {
  if (status >= 500) return 'Сервис оплаты временно недоступен. Попробуйте через минуту'
  if (status === 401 || status === 403) return 'Войдите в аккаунт, чтобы оплатить заказ'
  if (typeof body?.detail === 'string') return body.detail
  return `Не удалось связаться с сервисом оплаты (код ${status})`
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...init?.headers,
    },
  })

  if (response.status === 409) throw new AccessAlreadyGrantedError()

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null
    throw new Error(readErrorMessage(body, response.status))
  }

  return (await response.json()) as T
}

/** Есть ли у фабрики доступ к экспорту конкретного заказа. */
export function fetchOrderAccess(orderId: string): Promise<OrderAccess> {
  return requestJson<OrderAccess>(
    `/api/v1/payments/orders/${encodeURIComponent(orderId)}/access`
  )
}

/** Остаток кредитов пакета и доступность бесплатного первого заказа. */
export function fetchPaymentBalance(): Promise<PaymentBalance> {
  return requestJson<PaymentBalance>('/api/v1/payments/balance')
}

/** Платёж за доступ к одному заказу. Бросает AccessAlreadyGrantedError на 409. */
export function startOrderCheckout(orderId: string): Promise<CheckoutSession> {
  return requestJson<CheckoutSession>(
    `/api/v1/payments/orders/${encodeURIComponent(orderId)}/checkout`,
    { method: 'POST' }
  )
}

/**
 * Платёж за пакет из 10 заказов. order_id нужен только для return_url —
 * бэкенд вернёт пользователя на страницу того заказа, откуда он ушёл платить.
 */
export function startPackCheckout(orderId: string): Promise<CheckoutSession> {
  const body: PackCheckoutRequest = { order_id: orderId }
  return requestJson<CheckoutSession>('/api/v1/payments/packs/checkout', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
