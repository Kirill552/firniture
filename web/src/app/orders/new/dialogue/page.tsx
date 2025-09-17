"use client"

import { AiChat } from "@/components/ai-chat";

export default function NewOrderDialoguePage() {
  // In a real app, the orderId would be retrieved from the URL or state management
  const orderId = "dev-order-123";

  return (
    <div className="p-6 w-full">
      <AiChat orderId={orderId} />
    </div>
  );
}
