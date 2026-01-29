"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2 } from "lucide-react";
import dynamic from "next/dynamic";

const LazyAiChat = dynamic(
  () => import("@/components/ai-chat").then((mod) => mod.AiChat),
  {
    loading: () => (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    ),
    ssr: false,
  }
);

export default function DialoguePage() {
  const router = useRouter();
  const [orderId, setOrderId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(true);

  // Создать новый заказ при загрузке страницы
  useEffect(() => {
    const createOrder = async () => {
      try {
        const response = await fetch("/api/v1/orders/anonymous", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "Новый заказ (диалог)",
            description: "Создан через AI-диалог",
            spec: {},
          }),
        });

        if (!response.ok) {
          throw new Error("Ошибка создания заказа");
        }

        const order = await response.json();
        setOrderId(order.id);
      } catch (error) {
        console.error("Failed to create order:", error);
      } finally {
        setIsCreating(false);
      }
    };

    createOrder();
  }, []);

  // Callback когда диалог завершён
  const handleDialogueComplete = (completedOrderId: string) => {
    router.push(`/bom?orderId=${completedOrderId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto max-w-3xl px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/new">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Назад к выбору
            </Button>
          </Link>
        </div>

        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold tracking-tight">AI-технолог</h1>
          <p className="mt-1 text-muted-foreground">
            Опишите изделие, и я помогу составить спецификацию
          </p>
        </div>

        {/* Chat */}
        {isCreating ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Создаём заказ...</p>
          </div>
        ) : orderId ? (
          <div className="border rounded-lg bg-card">
            <LazyAiChat
              orderId={orderId}
              onComplete={handleDialogueComplete}
            />
          </div>
        ) : (
          <div className="text-center text-destructive">
            Не удалось создать заказ. Попробуйте обновить страницу.
          </div>
        )}
      </div>
    </div>
  );
}
