'use client'

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useRouter } from "next/navigation"
import { useState } from "react"

export default function NewOrderPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

  const handleCreateOrder = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/orders', { method: 'POST' })
      const data = await response.json()
      router.push(`/orders/new/tz-upload?orderId=${data.orderId}`)
    } catch (error) {
      console.error("Failed to create order:", error)
      // TODO: Show an error message to the user
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Новый заказ</CardTitle>
          <CardDescription>Нажмите кнопку ниже, чтобы начать процесс создания нового заказа.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleCreateOrder} className="w-full" disabled={isLoading}>
            {isLoading ? "Создание..." : "Начать"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
