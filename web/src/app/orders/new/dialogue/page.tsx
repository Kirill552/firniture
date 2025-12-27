"use client"

import { useEffect, useState } from "react";
import { LazyAiChat } from "@/components/lazy";

export default function NewOrderDialoguePage() {
  const [orderId, setOrderId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Создаём новый заказ при загрузке страницы
    async function createOrder() {
      try {
        const response = await fetch('/api/v1/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            customer_ref: 'Новый заказ',
            notes: 'Создан через диалог с ИИ-технологом'
          })
        });

        if (!response.ok) {
          throw new Error('Не удалось создать заказ');
        }

        const data = await response.json();
        setOrderId(data.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ошибка');
      }
    }

    createOrder();
  }, []);

  if (error) {
    return (
      <div className="p-6 w-full">
        <div className="text-red-500">Ошибка: {error}</div>
      </div>
    );
  }

  if (!orderId) {
    return (
      <div className="p-6 w-full">
        <div className="text-muted-foreground">Создание заказа...</div>
      </div>
    );
  }

  return (
    <div className="p-6 w-full">
      <LazyAiChat orderId={orderId} />
    </div>
  );
}
