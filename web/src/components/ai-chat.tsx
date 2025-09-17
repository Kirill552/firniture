"use client"

import { useState, FormEvent } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

interface Message {
  role: 'user' | 'assistant';
  content: string;
  buttons?: { label: string; value: string }[];
}

interface AiChatProps {
  orderId: string;
  initialMessages?: Message[];
}

export function AiChat({ orderId, initialMessages = [] }: AiChatProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/v1/dialogue/clarify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ order_id: orderId, messages: [userMessage] }),
      });

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantResponse = '';

      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        assistantResponse += chunk;
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].content = assistantResponse;
          return newMessages;
        });
      }

      // Parse buttons from final response if present
      try {
        const lines = assistantResponse.split('\n');
        const lastLine = lines[lines.length - 1];
        if (lastLine.startsWith('[') && lastLine.endsWith(']')) {
          const buttonsData = JSON.parse(lastLine);
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1].buttons = buttonsData;
            newMessages[newMessages.length - 1].content = lines.slice(0, -1).join('\n');
            return newMessages;
          });
        }
      } catch (e) {
        console.log('No buttons in response');
      }
    } catch (error) {
      console.error('Error fetching AI response:', error);
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Ошибка получения ответа от ИИ.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const sendButtonClick = (value: string) => {
    setInput(value);
    const formEvent = { preventDefault: () => {} } as FormEvent;
    handleSubmit(formEvent);
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Диалог с ИИ-технологом</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 h-96 overflow-y-auto">
        <div
          role="log"
          aria-live="polite"
          aria-label="Диалог с ИИ-технологом"
          className="space-y-4"
        >
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role !== 'user' && (
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">AI</div>
            )}
            <div className={`rounded-lg px-4 py-2 max-w-[80%] ${m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
              {m.content}
            </div>
            {m.buttons && m.role === 'assistant' && (
              <div className="flex flex-wrap gap-2 mt-2">
                {m.buttons.map((btn, btnIndex) => (
                  <Button
                    key={btnIndex}
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const buttonValue = btn.value;
                      setInput(buttonValue);
                      // Auto-submit the button value
                      setTimeout(() => {
                        if (buttonValue.trim()) {
                          const formEvent = { preventDefault: () => {} } as FormEvent;
                          handleSubmit(formEvent);
                        }
                      }, 100);
                    }}
                    role="button"
                    aria-label={`Отправить: ${btn.label}`}
                  >
                    {btn.label}
                  </Button>
                ))}
              </div>
            )}
          </div>
        ))}
        {isLoading && messages[messages.length -1].role === 'user' && (
            <div className={`flex gap-2`}>
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">AI</div>
                <div className={`rounded-lg px-4 py-2 max-w-[80%] bg-muted`}>
                    ... печатает
                </div>
            </div>
        )}
        </div>
      </CardContent>
      <CardFooter>
        <form onSubmit={handleSubmit} className="flex w-full items-center space-x-2">
          <Input
            value={input}
            placeholder="Задайте уточняющий вопрос..."
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            aria-label="Сообщение для ИИ-технолога"
            aria-describedby="chat-submit"
          />
          <Button
            type="submit"
            disabled={isLoading}
            aria-label="Отправить сообщение"
            id="chat-submit"
          >
            Отправить
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
}