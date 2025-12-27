# Примеры интеграции API Hooks в существующие страницы

## Пример 1: Интеграция в страницу загрузки ТЗ

Файл: `web/src/app/orders/new/tz-upload/page.tsx`

### Было (mock):
```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault()
  if (!orderId) return

  setIsLoading(true)
  // Mock upload
  await new Promise(resolve => setTimeout(resolve, 1000))
  router.push(`/orders/new/dialogue?orderId=${orderId}`)
}
```

### Стало (с API hooks):
```tsx
'use client'

import { useExtractSpec } from '@/hooks/use-api'
import { useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'
import { useToast } from '@/hooks/use-toast'

export default function TzUploadPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('orderId')
  const { toast } = useToast()

  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])

  // Используем hook для извлечения спецификации
  const extractSpec = useExtractSpec({
    onSuccess: (data) => {
      toast({
        title: "Параметры извлечены",
        description: `Создана конфигурация ${data.product_config_id}`,
      })

      // Сохраняем product_config_id для следующих шагов
      router.push(`/orders/new/dialogue?orderId=${orderId}&configId=${data.product_config_id}`)
    },
    onError: (error) => {
      toast({
        title: "Ошибка извлечения",
        description: error.message,
        variant: "destructive",
      })
    }
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orderId) return

    // Если есть текст - используем его
    if (text.trim()) {
      extractSpec.mutate({
        input_type: 'text',
        content: text
      })
    }
    // Если есть файлы - загружаем первый файл как изображение/эскиз
    else if (files.length > 0) {
      const file = files[0]
      const reader = new FileReader()

      reader.onloadend = () => {
        const base64 = reader.result as string
        extractSpec.mutate({
          input_type: file.type.startsWith('image/') ? 'image' : 'sketch',
          content: base64
        })
      }

      reader.readAsDataURL(file)
    }
  }

  return (
    // ... JSX остается прежним
    <Button
      type="submit"
      className="w-full"
      disabled={extractSpec.isPending || !orderId}
    >
      {extractSpec.isPending ? "Извлечение параметров..." : "Продолжить к диалогу с ИИ"}
    </Button>
  )
}
```

## Пример 2: Страница диалога с ИИ-технологом

Файл: `web/src/app/orders/new/dialogue/page.tsx`

```tsx
'use client'

import { useDialogueClarify, readDialogueStream } from '@/hooks/use-api'
import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function DialoguePage() {
  const searchParams = useSearchParams()
  const orderId = searchParams.get('orderId')

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const dialogue = useDialogueClarify()

  // Автоматическая прокрутка при добавлении сообщений
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || !orderId || isStreaming) return

    const userMessage = { role: 'user' as const, content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)

    try {
      const stream = await dialogue.mutateAsync({
        order_id: orderId,
        messages: [userMessage]
      })

      // Создаем временное сообщение для потокового ответа
      const tempMessage = { role: 'assistant' as const, content: '' }
      setMessages(prev => [...prev, tempMessage])

      await readDialogueStream(stream, (chunk) => {
        setMessages(prev => {
          const newMessages = [...prev]
          const lastMessage = newMessages[newMessages.length - 1]
          if (lastMessage.role === 'assistant') {
            lastMessage.content += chunk
          }
          return newMessages
        })
      })
    } catch (error) {
      console.error('Ошибка диалога:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Извините, произошла ошибка при получении ответа.'
      }])
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Диалог с ИИ-технологом</h1>

      <ScrollArea className="flex-1 border rounded-lg p-4 mb-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`mb-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}
          >
            <div
              className={`inline-block max-w-[80%] p-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        <div ref={scrollRef} />
      </ScrollArea>

      <div className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="Задайте вопрос технологу..."
          className="flex-1"
          disabled={isStreaming}
        />
        <Button onClick={handleSend} disabled={isStreaming || !input.trim()}>
          {isStreaming ? 'Отправка...' : 'Отправить'}
        </Button>
      </div>
    </div>
  )
}
```

## Пример 3: Страница подбора фурнитуры

Файл: `web/src/app/orders/new/bom/page.tsx`

```tsx
'use client'

import { useSelectHardware } from '@/hooks/use-api'
import { useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'

export default function BOMPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const configId = searchParams.get('configId')
  const orderId = searchParams.get('orderId')
  const { toast } = useToast()

  const [material, setMaterial] = useState('ЛДСП')
  const [thickness, setThickness] = useState(18)

  const selectHardware = useSelectHardware({
    onSuccess: (data) => {
      toast({
        title: "Фурнитура подобрана",
        description: `BOM ID: ${data.bom_id}, позиций: ${data.items.length}`,
      })

      // Переходим к следующему шагу
      router.push(`/orders/new/cam?orderId=${orderId}&configId=${configId}&bomId=${data.bom_id}`)
    },
    onError: (error) => {
      toast({
        title: "Ошибка подбора фурнитуры",
        description: error.message,
        variant: "destructive",
      })
    }
  })

  const handleSelect = () => {
    if (!configId) return

    selectHardware.mutate({
      product_config_id: configId,
      criteria: {
        material,
        thickness
      }
    })
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Подбор фурнитуры</h1>

      <Card className="p-6 mb-6">
        <div className="space-y-4">
          <div>
            <Label htmlFor="material">Материал</Label>
            <Input
              id="material"
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
              placeholder="ЛДСП, МДФ и т.д."
            />
          </div>

          <div>
            <Label htmlFor="thickness">Толщина (мм)</Label>
            <Input
              id="thickness"
              type="number"
              value={thickness}
              onChange={(e) => setThickness(Number(e.target.value))}
            />
          </div>

          <Button
            onClick={handleSelect}
            disabled={selectHardware.isPending || !configId}
            className="w-full"
          >
            {selectHardware.isPending ? 'Подбор фурнитуры...' : 'Подобрать фурнитуру (RAG)'}
          </Button>
        </div>
      </Card>

      {selectHardware.data && (
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Результаты подбора</h2>
          <p className="text-sm text-muted-foreground mb-4">
            BOM ID: {selectHardware.data.bom_id}
          </p>

          <div className="space-y-2">
            {selectHardware.data.items.map((item) => (
              <div
                key={item.hardware_item_id}
                className="flex justify-between items-center p-3 border rounded"
              >
                <div>
                  <p className="font-medium">{item.name || item.sku}</p>
                  <p className="text-sm text-muted-foreground">
                    Поставщик: {item.supplier || 'Не указан'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{item.quantity} шт.</p>
                  <p className="text-sm text-muted-foreground">{item.sku}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
```

## Пример 4: Страница генерации CAM файлов

Файл: `web/src/app/orders/new/cam/page.tsx`

```tsx
'use client'

import { useGenerateDXF, useGenerateGCode, useCAMJobStatus, useCreateZIP } from '@/hooks/use-api'
import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'

export default function CAMPage() {
  const searchParams = useSearchParams()
  const configId = searchParams.get('configId')
  const orderId = searchParams.get('orderId')

  const [dxfJobId, setDxfJobId] = useState<string>('')
  const [gcodeJobId, setGcodeJobId] = useState<string>('')

  const generateDXF = useGenerateDXF({
    onSuccess: (data) => {
      if (data.dxf_job_id) {
        setDxfJobId(data.dxf_job_id)
      }
    }
  })

  const generateGCode = useGenerateGCode({
    onSuccess: (data) => {
      if (data.gcode_job_id) {
        setGcodeJobId(data.gcode_job_id)
      }
    }
  })

  const createZIP = useCreateZIP()

  const dxfStatus = useCAMJobStatus(dxfJobId)
  const gcodeStatus = useCAMJobStatus(gcodeJobId)

  const handleGenerateDXF = () => {
    if (!configId) return
    generateDXF.mutate({ product_config_id: configId })
  }

  const handleGenerateGCode = () => {
    if (!configId || !dxfJobId) return
    generateGCode.mutate({
      product_config_id: configId,
      dxf_job_id: dxfJobId
    })
  }

  const handleCreateZIP = () => {
    if (!orderId || !dxfJobId || !gcodeJobId) return
    createZIP.mutate({
      order_id: orderId,
      job_ids: [dxfJobId, gcodeJobId]
    })
  }

  const renderJobStatus = (status: typeof dxfStatus) => {
    if (!status.data) return null

    const { status: jobStatus, error, artifact_id } = status.data

    return (
      <div className="flex items-center gap-2">
        {jobStatus === 'Created' && <Loader2 className="h-4 w-4 animate-spin" />}
        {jobStatus === 'Processing' && <Loader2 className="h-4 w-4 animate-spin" />}
        {jobStatus === 'Completed' && <CheckCircle2 className="h-4 w-4 text-green-500" />}
        {jobStatus === 'Failed' && <XCircle className="h-4 w-4 text-red-500" />}

        <span>{jobStatus}</span>

        {artifact_id && (
          <Button size="sm" variant="link">
            Скачать
          </Button>
        )}

        {error && (
          <span className="text-sm text-red-500">{error}</span>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold">Генерация CAM файлов</h1>

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">DXF Чертежи</h2>

        <Button
          onClick={handleGenerateDXF}
          disabled={generateDXF.isPending || !configId || !!dxfJobId}
        >
          {generateDXF.isPending ? 'Создание задачи...' : 'Сгенерировать DXF'}
        </Button>

        {dxfStatus.data && (
          <div className="mt-4">
            {renderJobStatus(dxfStatus)}
          </div>
        )}
      </Card>

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">G-Code</h2>

        <Button
          onClick={handleGenerateGCode}
          disabled={
            generateGCode.isPending ||
            !configId ||
            !dxfJobId ||
            dxfStatus.data?.status !== 'Completed' ||
            !!gcodeJobId
          }
        >
          {generateGCode.isPending ? 'Создание задачи...' : 'Сгенерировать G-Code'}
        </Button>

        {gcodeStatus.data && (
          <div className="mt-4">
            {renderJobStatus(gcodeStatus)}
          </div>
        )}
      </Card>

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Упаковка артефактов</h2>

        <Button
          onClick={handleCreateZIP}
          disabled={
            createZIP.isPending ||
            dxfStatus.data?.status !== 'Completed' ||
            gcodeStatus.data?.status !== 'Completed'
          }
        >
          {createZIP.isPending ? 'Создание ZIP...' : 'Создать ZIP архив'}
        </Button>
      </Card>
    </div>
  )
}
```

## Пример 5: Экспорт в 1С

```tsx
'use client'

import { useExport1C } from '@/hooks/use-api'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

export function Export1CButton({ orderId }: { orderId: string }) {
  const { toast } = useToast()

  const export1C = useExport1C({
    onSuccess: (data) => {
      toast({
        title: "Экспорт успешен",
        description: `Заказ экспортирован в 1С. ID: ${data.one_c_order_id}`,
      })
    },
    onError: (error) => {
      toast({
        title: "Ошибка экспорта",
        description: error.message,
        variant: "destructive",
      })
    }
  })

  return (
    <Button
      onClick={() => export1C.mutate({ order_id: orderId })}
      disabled={export1C.isPending}
      variant="outline"
    >
      {export1C.isPending ? 'Экспорт...' : 'Экспортировать в 1С'}
    </Button>
  )
}
```

## Общие рекомендации

1. **Обработка ошибок**: Всегда используйте `useToast` для отображения ошибок пользователю
2. **Loading состояния**: Используйте `isPending` для отключения кнопок во время запросов
3. **Инвалидация кэша**: Hooks автоматически инвалидируют связанные запросы при успешных мутациях
4. **Типизация**: В production замените `any` типы на конкретные типы из OpenAPI схемы
5. **Streaming**: Для диалога с ИИ используйте `readDialogueStream` для обработки потоковых ответов
6. **Polling**: `useCAMJobStatus` автоматически обновляется каждые 2 секунды для активных задач
