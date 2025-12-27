# API Hooks для Мебель-ИИ

Этот файл содержит TanStack Query hooks для всех API эндпоинтов проекта Мебель-ИИ.

## Установка

TanStack Query уже установлен в проекте:
```bash
npm install @tanstack/react-query
```

## Использование

### 1. Создание заказа

```tsx
import { useCreateOrder } from '@/hooks/use-api'

function OrderForm() {
  const createOrder = useCreateOrder()

  const handleSubmit = () => {
    createOrder.mutate({
      customer_ref: 'ИП Иванов',
      notes: 'Срочный заказ'
    }, {
      onSuccess: (data) => {
        console.log('Заказ создан:', data.id)
      },
      onError: (error) => {
        console.error('Ошибка:', error.message)
      }
    })
  }

  return (
    <button onClick={handleSubmit} disabled={createOrder.isPending}>
      {createOrder.isPending ? 'Создание...' : 'Создать заказ'}
    </button>
  )
}
```

### 2. Извлечение параметров из ТЗ

```tsx
import { useExtractSpec } from '@/hooks/use-api'

function SpecExtractor() {
  const extractSpec = useExtractSpec()

  const handleExtract = (text: string) => {
    extractSpec.mutate({
      input_type: 'text',
      content: text
    }, {
      onSuccess: (data) => {
        console.log('Параметры:', data.parameters)
        console.log('Product Config ID:', data.product_config_id)
      }
    })
  }

  return (
    <div>
      {extractSpec.data && (
        <pre>{JSON.stringify(extractSpec.data.parameters, null, 2)}</pre>
      )}
    </div>
  )
}
```

### 3. Подбор фурнитуры (RAG)

```tsx
import { useSelectHardware } from '@/hooks/use-api'

function HardwareSelector() {
  const selectHardware = useSelectHardware()

  const handleSelect = (productConfigId: string) => {
    selectHardware.mutate({
      product_config_id: productConfigId,
      criteria: {
        material: 'ЛДСП',
        thickness: 18
      }
    }, {
      onSuccess: (data) => {
        console.log('BOM ID:', data.bom_id)
        console.log('Позиции:', data.items)
      }
    })
  }

  return (
    <div>
      {selectHardware.data?.items.map(item => (
        <div key={item.hardware_item_id}>
          {item.name} - {item.quantity} шт. ({item.supplier})
        </div>
      ))}
    </div>
  )
}
```

### 4. Генерация CAM файлов

```tsx
import { useGenerateDXF, useGenerateGCode, useCAMJobStatus } from '@/hooks/use-api'

function CAMGenerator() {
  const generateDXF = useGenerateDXF()
  const generateGCode = useGenerateGCode()
  const jobStatus = useCAMJobStatus(generateDXF.data?.dxf_job_id || '')

  const handleGenerateDXF = (productConfigId: string) => {
    generateDXF.mutate({ product_config_id: productConfigId })
  }

  return (
    <div>
      <button onClick={() => handleGenerateDXF('uuid')}>
        Сгенерировать DXF
      </button>

      {jobStatus.data && (
        <div>
          Статус: {jobStatus.data.status}
          {jobStatus.data.artifact_id && (
            <a href={`/download/${jobStatus.data.artifact_id}`}>
              Скачать артефакт
            </a>
          )}
        </div>
      )}
    </div>
  )
}
```

### 5. Мониторинг статуса CAM задачи

Hook `useCAMJobStatus` автоматически обновляет статус каждые 2 секунды, пока задача в процессе:

```tsx
import { useCAMJobStatus } from '@/hooks/use-api'

function JobMonitor({ jobId }: { jobId: string }) {
  const { data, isLoading } = useCAMJobStatus(jobId)

  if (isLoading) return <div>Загрузка...</div>

  return (
    <div>
      <p>Статус: {data?.status}</p>
      <p>Тип: {data?.job_kind}</p>
      {data?.error && <p className="text-red-500">Ошибка: {data.error}</p>}
      {data?.artifact_id && <p>Артефакт готов: {data.artifact_id}</p>}
    </div>
  )
}
```

### 6. Валидация и подтверждение

```tsx
import { useValidateSpec, useApproveValidation } from '@/hooks/use-api'

function SpecValidation() {
  const validateSpec = useValidateSpec()
  const approveValidation = useApproveValidation()

  const handleValidate = (productConfigId: string) => {
    validateSpec.mutate({
      product_config_id: productConfigId,
      stage: 'extraction_review',
      required_approvals: [
        {
          parameter: 'material',
          value: 'ЛДСП',
          confidence: 0.85,
          question: 'Подтвердите материал: ЛДСП'
        }
      ]
    })
  }

  const handleApprove = (validationId: string, itemId: string) => {
    approveValidation.mutate({
      validation_id: validationId,
      approvals: [
        {
          validation_item_id: itemId,
          approved: true,
          comment: 'Подтверждено'
        }
      ]
    })
  }

  return <div>...</div>
}
```

### 7. Диалог с ИИ-технологом (Streaming)

Для работы с потоковыми ответами:

```tsx
import { useDialogueClarify, readDialogueStream } from '@/hooks/use-api'
import { useState } from 'react'

function AIDialogue() {
  const [response, setResponse] = useState('')
  const dialogue = useDialogueClarify()

  const handleAsk = async (orderId: string, question: string) => {
    setResponse('')

    try {
      const stream = await dialogue.mutateAsync({
        order_id: orderId,
        messages: [{ role: 'user', content: question }]
      })

      await readDialogueStream(stream, (chunk) => {
        setResponse(prev => prev + chunk)
      })
    } catch (error) {
      console.error('Ошибка диалога:', error)
    }
  }

  return (
    <div>
      <button onClick={() => handleAsk('uuid', 'Какую фурнитуру использовать?')}>
        Спросить ИИ
      </button>
      <div className="whitespace-pre-wrap">{response}</div>
    </div>
  )
}
```

### 8. Экспорт в 1С

```tsx
import { useExport1C } from '@/hooks/use-api'

function Export1CButton({ orderId }: { orderId: string }) {
  const export1C = useExport1C()

  const handleExport = () => {
    export1C.mutate({ order_id: orderId }, {
      onSuccess: (data) => {
        if (data.success) {
          console.log('Экспортировано в 1С:', data.one_c_order_id)
        }
      }
    })
  }

  return (
    <button onClick={handleExport} disabled={export1C.isPending}>
      {export1C.isPending ? 'Экспорт...' : 'Экспортировать в 1С'}
    </button>
  )
}
```

### 9. Проверка доступности API

```tsx
import { useAPIHealth } from '@/hooks/use-api'

function APIStatus() {
  const { data, isLoading, error } = useAPIHealth()

  if (isLoading) return <div>Проверка...</div>
  if (error) return <div className="text-red-500">API недоступен</div>

  return <div className="text-green-500">API: {data?.status}</div>
}
```

## Query Keys

Для инвалидации кэша и ручного управления данными:

```tsx
import { apiKeys } from '@/hooks/use-api'
import { useQueryClient } from '@tanstack/react-query'

function Component() {
  const queryClient = useQueryClient()

  // Инвалидировать все заказы
  queryClient.invalidateQueries({ queryKey: apiKeys.orders })

  // Инвалидировать конкретный заказ
  queryClient.invalidateQueries({ queryKey: apiKeys.order('uuid') })

  // Инвалидировать статус CAM задачи
  queryClient.invalidateQueries({ queryKey: apiKeys.camJob('job-uuid') })
}
```

## Обработка ошибок

Все hooks поддерживают обработку ошибок через callbacks:

```tsx
const mutation = useCreateOrder({
  onError: (error) => {
    console.error('Ошибка:', error.message)
    // Показать уведомление пользователю
  },
  onSuccess: (data) => {
    console.log('Успешно:', data)
  }
})
```

## Переменные окружения

Убедитесь, что в `.env.local` указан правильный URL API:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Типизация

В будущем типы из `use-api.ts` следует заменить на типы, сгенерированные из OpenAPI схемы backend API.

## Дополнительно

- Все hooks используют автоматическую инвалидацию кэша при успешных мутациях
- `useCAMJobStatus` автоматически обновляется каждые 2 секунды для активных задач
- Streaming диалога с ИИ поддерживает чтение по чанкам для real-time обновлений UI
