'use client'

import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"

/**
 * Страница создания нового заказа.
 * Автоматически создаёт заказ через API и редиректит на загрузку ТЗ.
 */
export default function NewOrderPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const createOrder = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })

        if (!response.ok) {
          throw new Error('Не удалось создать заказ')
        }

        const data = await response.json()
        router.replace(`/orders/new/tz-upload?orderId=${data.id}`)
      } catch (err) {
        console.error("Failed to create order:", err)
        setError('Не удалось создать заказ. Попробуйте ещё раз.')
      }
    }

    createOrder()
  }, [router])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6">
        <div className="text-destructive mb-4">{error}</div>
        <button
          onClick={() => window.location.reload()}
          className="text-primary hover:underline"
        >
          Повторить
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-6">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
      <p className="text-muted-foreground">Создаём заказ...</p>
    </div>
  )
}
