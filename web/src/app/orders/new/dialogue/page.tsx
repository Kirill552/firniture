"use client"

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { LazyAiChat } from "@/components/lazy";

export default function NewOrderDialoguePage() {
  const searchParams = useSearchParams();
  const orderIdParam = searchParams.get('orderId');
  const extractedContext = searchParams.get('context'); // Закодированный контекст из Vision OCR

  const [orderId, setOrderId] = useState<string | null>(orderIdParam);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Если orderId уже передан в URL — используем его
    if (orderIdParam) {
      setOrderId(orderIdParam);
      return;
    }

    // Иначе создаём новый заказ
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
  }, [orderIdParam]);

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

  // Декодируем контекст если есть
  const decodedContext = extractedContext
    ? decodeURIComponent(extractedContext)
    : undefined;

  return (
    <div className="p-6 w-full">
      <LazyAiChat orderId={orderId} extractedContext={decodedContext} />
    </div>
  );
}
