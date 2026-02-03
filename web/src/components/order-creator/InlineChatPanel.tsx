// web/src/components/order-creator/InlineChatPanel.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Send, Loader2, Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage, OrderCreatorParams } from "@/types/api";

interface InlineChatPanelProps {
  messages: ChatMessage[];
  suggestedPrompt: string | null;
  currentParams: Partial<OrderCreatorParams>;
  orderId: string | null;
  onSendMessage: (message: string) => void;
  onParamUpdate: (updates: Partial<OrderCreatorParams>) => void;
  onClose: () => void;
  isOpen: boolean;
  isLoading?: boolean;
}

export function InlineChatPanel({
  messages,
  suggestedPrompt,
  currentParams,
  orderId,
  onSendMessage,
  onParamUpdate,
  onClose,
  isOpen,
  isLoading = false,
}: InlineChatPanelProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll на новые сообщения
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Показать suggested prompt при открытии
  useEffect(() => {
    if (isOpen && suggestedPrompt && messages.length === 0) {
      // Автоматически отправить suggested prompt от системы
      onSendMessage(suggestedPrompt);
    }
  }, [isOpen, suggestedPrompt, messages.length, onSendMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");

    // Делегировать отправку сообщения родительскому компоненту
    onSendMessage(userMessage);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-[400px] bg-background border-l shadow-lg flex flex-col z-50 lg:relative lg:w-[350px]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <span className="font-medium">AI-уточнение</span>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        <div ref={scrollRef} className="space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex gap-2",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {msg.role === "assistant" && (
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              )}
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                {msg.content}
              </div>
              {msg.role === "user" && (
                <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-2">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
              </div>
              <div className="bg-muted rounded-lg px-3 py-2">
                <span className="text-sm text-muted-foreground">Думаю...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Уточните параметры..."
            disabled={isLoading}
          />
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
