"use client"

import { useState, FormEvent, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { parseAiResponse } from "@/lib/ai-response";
import { Loader2 } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  buttons?: string[];
  toolCalls?: { tool: string; arguments: Record<string, unknown>; result: unknown }[];
}

interface AiChatProps {
  orderId: string;
  initialMessages?: Message[];
  extractedContext?: string;
}


// Парсинг [SPEC_JSON]...[/SPEC_JSON] из текста
function parseSpecJson(text: string): { cleanText: string; spec: Record<string, unknown> | null } {
  const specMatch = text.match(/\[SPEC_JSON\]([\s\S]*?)\[\/SPEC_JSON\]/);
  if (!specMatch) {
    return { cleanText: text, spec: null };
  }

  try {
    // Очищаем JSON от бэктиков, переносов и лишних пробелов
    const jsonStr = specMatch[1]
      .replace(/```json?/gi, '')  // Убираем ```json или ```
      .replace(/```/g, '')         // Убираем оставшиеся ```
      .replace(/\n/g, ' ')         // Заменяем переносы на пробелы
      .replace(/\s+/g, ' ')        // Схлопываем множественные пробелы
      .trim();

    const spec = JSON.parse(jsonStr);
    const cleanText = text.replace(/\[SPEC_JSON\][\s\S]*?\[\/SPEC_JSON\]/, '').trim();
    return { cleanText, spec };
  } catch (e) {
    console.error('Failed to parse SPEC_JSON:', e);
    return { cleanText: text, spec: null };
  }
}

// Проверка наличия [COMPLETE] в тексте
function hasCompleteMarker(text: string): boolean {
  return text.includes('[COMPLETE]');
}

// Удаление маркера [COMPLETE] из текста для отображения
function removeCompleteMarker(text: string): string {
  return text.replace('[COMPLETE]', '').trim();
}


export function AiChat({ orderId, initialMessages = [], extractedContext }: AiChatProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFirstMessage, setIsFirstMessage] = useState(true);
  const [isFinishing, setIsFinishing] = useState(false);
  const hasAutoStarted = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Прокрутка к последнему сообщению
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Финализация заказа и редирект на BOM
  const finalizeAndRedirect = async (spec: Record<string, unknown>) => {
    setIsFinishing(true);
    try {
      const response = await fetch(`/api/v1/orders/${orderId}/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spec),
      });

      const data = await response.json();

      if (data.success) {
        // Небольшая задержка чтобы пользователь увидел финальное сообщение
        setTimeout(() => {
          router.push(`/bom?orderId=${orderId}`);
        }, 1500);
      } else {
        console.error('Finalize failed:', data);
        setIsFinishing(false);
      }
    } catch (error) {
      console.error('Finalize error:', error);
      setIsFinishing(false);
    }
  };

  // Отправка сообщения через /clarify-with-tools (с function calling)
  const sendMessage = useCallback(async (userMessage: Message | null, includeContext: boolean) => {
    setIsLoading(true);

    try {
      const requestBody: {
        order_id: string;
        messages: { role: string; content: string }[];
        extracted_context?: string;
      } = {
        order_id: orderId,
        messages: userMessage ? [{ role: userMessage.role, content: userMessage.content }] : [],
      };

      if (includeContext && extractedContext) {
        requestBody.extracted_context = extractedContext;
      }

      const response = await fetch('/api/v1/dialogue/clarify-with-tools', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();

      if (!data.success && data.error) {
        throw new Error('Не удалось получить уточнение. Проверьте параметры и попробуйте снова.');
      }

      // После получения ответа от API
      if (data.success && data.response) {
        let responseText = data.response;

        // Парсим SPEC_JSON
        const { cleanText: textWithoutSpec, spec } = parseSpecJson(responseText);
        if (spec) {
          responseText = textWithoutSpec;
        }

        // Проверяем на [COMPLETE]
        const isComplete = hasCompleteMarker(responseText);
        if (isComplete) {
          responseText = removeCompleteMarker(responseText);
        }

        // Парсим кнопки и удаляем служебные блоки
        const { cleanText, buttons } = parseAiResponse(responseText);
        // Добавляем сообщение в список
        const assistantMessage: Message = {
          role: 'assistant',
          content: cleanText,
          buttons: buttons.length > 0 ? buttons : undefined,
          toolCalls: data.tool_calls,
        };
        setMessages(prev => [...prev, assistantMessage]);

        // Если диалог завершён — финализируем
        if (isComplete && spec) {
          await finalizeAndRedirect(spec);
        }
      }

    } catch (error) {
      console.error('Error fetching AI response:', error);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Не удалось получить ответ. Проверьте параметры и попробуйте снова.'
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [orderId, extractedContext, router]);

  // Автостарт диалога при наличии контекста
  useEffect(() => {
    if (extractedContext && isFirstMessage && !hasAutoStarted.current && !isLoading) {
      hasAutoStarted.current = true;
      setIsFirstMessage(false);

      (async () => {
        setIsLoading(true);
        try {
          const response = await fetch('/api/v1/dialogue/clarify-with-tools', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              order_id: orderId,
              messages: [],
              extracted_context: extractedContext,
            }),
          });
          const data = await response.json();

          if (data.success !== false) {
            const { cleanText, buttons } = parseAiResponse(data.response || '');
            setMessages([{
              role: 'assistant',
              content: cleanText,
              buttons: buttons.length > 0 ? buttons : undefined,
              toolCalls: data.tool_calls?.length > 0 ? data.tool_calls : undefined,
            }]);
          }
        } catch (error) {
          console.error('Auto-start error:', error);
        } finally {
          setIsLoading(false);
        }
      })();
    }
  }, [extractedContext, isFirstMessage, isLoading, orderId]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    const shouldIncludeContext = isFirstMessage;
    if (isFirstMessage) {
      setIsFirstMessage(false);
    }

    await sendMessage(userMessage, shouldIncludeContext);
  };

  const handleButtonClick = async (buttonText: string) => {
    if (isLoading) return;

    const userMessage: Message = { role: 'user', content: buttonText };
    setMessages((prev) => [...prev, userMessage]);

    await sendMessage(userMessage, false);
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
          {messages.map((m, i) => {
            const displayContent = m.content;

            // Пропускаем пустые сообщения ассистента (только function_call)
            if (m.role === 'assistant' && !displayContent && !m.buttons?.length && !m.toolCalls?.length) {
              return null;
            }

            return (
              <div key={i} className="space-y-2">
                {/* Показываем текст только если он не пустой */}
                {displayContent && (
                  <div className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
                    {m.role !== 'user' && (
                      <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold shrink-0">
                        AI
                      </div>
                    )}
                    <div className={`rounded-lg px-4 py-2 max-w-[80%] ${
                      m.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}>
                      {displayContent}
                    </div>
                  </div>
                )}

                {/* Кнопки быстрых ответов */}
                {m.buttons && m.role === 'assistant' && (
                  <div className="flex flex-wrap gap-2 ml-10">
                    {m.buttons.map((btn, btnIndex) => (
                      <Button
                        key={btnIndex}
                        size="sm"
                        variant="outline"
                        onClick={() => handleButtonClick(btn)}
                        disabled={isLoading}
                      >
                        {btn}
                      </Button>
                    ))}
                  </div>
                )}

                {/* Показываем использованные инструменты */}
                {m.toolCalls && m.toolCalls.length > 0 && (
                  <div className="ml-10 text-xs text-muted-foreground bg-muted/50 rounded p-2">
                    🔧 Использовано: {m.toolCalls.map(tc => tc.tool).join(', ')}
                  </div>
                )}
              </div>
            );
          })}

          {/* Индикатор загрузки */}
          {isLoading && (
            <div className="flex gap-2">
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold shrink-0">
                AI
              </div>
              <div className="rounded-lg px-4 py-2 bg-muted flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
                <span className="text-muted-foreground">Технолог-GPT думает...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Индикатор финализации */}
        {isFinishing && (
          <div className="flex items-center justify-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800 mx-4 mb-4">
            <Loader2 className="h-5 w-5 animate-spin text-green-600 mr-2" />
            <span className="text-green-800 dark:text-green-200">
              Переходим к спецификации...
            </span>
          </div>
        )}
      </CardContent>
      <CardFooter>
        <form onSubmit={handleSubmit} className="flex w-full items-center space-x-2">
          <Input
            value={input}
            placeholder="Задайте уточняющий вопрос..."
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            aria-label="Сообщение для ИИ-технолога"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            Отправить
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
}
