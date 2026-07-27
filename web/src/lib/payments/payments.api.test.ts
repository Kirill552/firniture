import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  AccessAlreadyGrantedError,
  ORDER_PRICE_RUB,
  fetchOrderAccess,
  isPaymentRequiredError,
  readPaymentRequired,
  startOrderCheckout,
  startPackCheckout,
} from './payments.api'

const SESSION = { payment_id: 'pay-1', confirmation_url: 'https://yoomoney', amount_rub: 7900, status: 'pending' }

beforeEach(() => {
  vi.stubGlobal('window', {})
  vi.stubGlobal('localStorage', { getItem: () => null })
})

describe('readPaymentRequired', () => {
  it('разбирает 402 по контракту экспортных эндпоинтов', async () => {
    const response = new Response(
      JSON.stringify({ detail: { code: 'payment_required', price_rub: 890, order_id: 'ord-9' } }),
      { status: 402 }
    )

    const error = await readPaymentRequired(response, 'fallback')

    expect(isPaymentRequiredError(error)).toBe(true)
    expect(error.orderId).toBe('ord-9')
    expect(error.priceRub).toBe(890)
  })

  it('без разбираемого тела берёт заказ вызова и базовую цену', async () => {
    const error = await readPaymentRequired(new Response('', { status: 402 }), 'fallback')

    expect(error.orderId).toBe('fallback')
    expect(error.priceRub).toBe(ORDER_PRICE_RUB)
  })
})

describe('checkout', () => {
  it('409 означает уже открытый доступ, а не сбой оплаты', async () => {
    vi.stubGlobal('fetch', async () => new Response('', { status: 409 }))

    await expect(startOrderCheckout('ord-1')).rejects.toBeInstanceOf(AccessAlreadyGrantedError)
  })

  it('пакет уходит с order_id, чтобы ЮKassa вернула на страницу заказа', async () => {
    let sentBody: string | undefined
    vi.stubGlobal('fetch', async (_url: string, init: RequestInit) => {
      sentBody = String(init.body)
      return new Response(JSON.stringify(SESSION), { status: 200 })
    })

    const session = await startPackCheckout('ord-7')

    expect(JSON.parse(sentBody ?? '{}')).toEqual({ order_id: 'ord-7' })
    expect(session.confirmation_url).toBe('https://yoomoney')
  })
})

describe('ошибки сервиса оплаты', () => {
  it('5xx показывает русское сообщение, а не текст бэкенда', async () => {
    vi.stubGlobal(
      'fetch',
      async () => new Response(JSON.stringify({ detail: 'Payments service unavailable' }), { status: 503 })
    )

    await expect(fetchOrderAccess('ord-1')).rejects.toThrow('Сервис оплаты временно недоступен')
  })

  it('401 зовёт войти в аккаунт', async () => {
    vi.stubGlobal('fetch', async () => new Response('', { status: 401 }))

    await expect(fetchOrderAccess('ord-1')).rejects.toThrow('Войдите в аккаунт')
  })
})
