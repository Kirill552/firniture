# TypeScript типы для API проекта Мебель-ИИ

Этот файл содержит все TypeScript типы и интерфейсы для работы с API бэкенда проекта Мебель-ИИ.

## Структура файлов

- `api.ts` - основные типы для всех API эндпоинтов
- `three-dxf-loader.d.ts` - типы для загрузчика DXF в Three.js
- `index.ts` - главный файл экспорта всех типов

## Использование

### Импорт типов

```typescript
// Импорт конкретных типов
import { Order, OrderCreateRequest, JobStatus } from '@/types/api'

// Или импорт всех типов
import * as API from '@/types/api'
```

### Примеры использования

#### 1. Создание заказа

```typescript
import { OrderCreateRequest, Order } from '@/types/api'

const createOrder = async (data: OrderCreateRequest): Promise<Order> => {
  const response = await fetch('/api/v1/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return await response.json()
}

// Использование
const newOrder = await createOrder({
  customer_ref: 'ООО "Рога и копыта"',
  notes: 'Срочный заказ'
})
```

#### 2. Извлечение спецификации

```typescript
import { SpecExtractRequest, SpecExtractResponse } from '@/types/api'

const extractSpec = async (data: SpecExtractRequest): Promise<SpecExtractResponse> => {
  const response = await fetch('/api/v1/spec/extract', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return await response.json()
}

// Использование
const result = await extractSpec({
  input_type: 'text',
  content: 'Шкаф 2000x1000x600 мм из ЛДСП 18 мм'
})
```

#### 3. Работа с диалогом

```typescript
import { DialogueTurnRequest, DialogueMessageCreate } from '@/types/api'

const sendMessage = async (
  orderId: string,
  message: string
): Promise<ReadableStream> => {
  const messages: DialogueMessageCreate[] = [{
    role: 'user',
    content: message
  }]

  const response = await fetch('/api/v1/dialogue/clarify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      order_id: orderId,
      messages
    } as DialogueTurnRequest),
  })

  return response.body!
}
```

#### 4. Проверка статуса CAM задачи

```typescript
import { CAMJobStatusResponse, JobStatus } from '@/types/api'

const checkJobStatus = async (jobId: string): Promise<CAMJobStatusResponse> => {
  const response = await fetch(`/api/v1/cam/jobs/${jobId}/status`)
  return await response.json()
}

// Использование с type guard
const isJobCompleted = (status: JobStatus): boolean => {
  return status === 'Completed'
}

const job = await checkJobStatus('some-job-id')
if (isJobCompleted(job.status)) {
  console.log('Задача завершена!')
}
```

#### 5. Подбор фурнитуры

```typescript
import {
  HardwareSelectRequest,
  HardwareSelectResponse
} from '@/types/api'

const selectHardware = async (
  productConfigId: string,
  material: string,
  thickness: number
): Promise<HardwareSelectResponse> => {
  const request: HardwareSelectRequest = {
    product_config_id: productConfigId,
    criteria: {
      material,
      thickness
    }
  }

  const response = await fetch('/api/v1/hardware/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return await response.json()
}
```

#### 6. Работа с фильтрами (расширенные типы)

```typescript
import { OrderFilters, HardwareFilters } from '@/types/api'

// Фильтры для заказов
const orderFilters: OrderFilters = {
  customer_ref: 'ООО',
  created_from: '2025-01-01',
  sort_by: 'created_at',
  sort_order: 'desc'
}

// Фильтры для фурнитуры
const hardwareFilters: HardwareFilters = {
  search: 'петля',
  type: 'hinge',
  is_active: true,
  thickness_min: 16,
  thickness_max: 18
}
```

## Категории типов

### Enum типы
- `JobStatus` - статус CAM задачи
- `ValidationStatus` - статус валидации
- `InputType` - тип входных данных для извлечения спецификации
- `ValidationStage` - этап валидации спецификации
- `CAMJobKind` - тип CAM задачи
- `DialogueRole` - роль участника диалога

### Основные сущности
- `Order` - заказ
- `ProductConfig` - конфигурация изделия
- `Panel` - панель (деталь)
- `HardwareItem` - позиция фурнитуры
- `BOMItem` - позиция в спецификации
- `CAMJob` - CAM задача
- `Artifact` - артефакт (файл)
- `DialogueMessage` - сообщение в диалоге

### Request/Response типы
Для каждого API эндпоинта есть соответствующие типы запросов и ответов:
- `*Request` - типы для тела запроса
- `*Response` - типы для ответа сервера

### Расширенные типы
- `OrderWithProducts` - заказ с продуктами
- `ProductConfigWithPanels` - конфигурация с панелями
- `CAMJobWithArtifact` - задача с артефактом
- `OrderFilters` - фильтры для заказов
- `HardwareFilters` - фильтры для фурнитуры

## Миграция существующего кода

Если в вашем коде используются локальные определения типов (например, в `app/orders/page.tsx`), рекомендуется мигрировать на централизованные типы:

### До миграции:
```typescript
// В файле app/orders/page.tsx
type Order = {
  id: string
  customer: string
  product: string
  status: "pending" | "processing" | "completed" | "cancelled"
  price: number
  createdAt: string
}
```

### После миграции:
```typescript
// Импортируем типы из централизованного хранилища
import { Order } from '@/types/api'

// Если нужны дополнительные поля для UI, создаем расширенный тип
type OrderTableRow = Order & {
  customer: string  // Дополнительное поле для отображения
  product: string   // Дополнительное поле для отображения
  price: number     // Дополнительное поле для отображения
}
```

## Обработка ошибок

```typescript
import { APIError } from '@/types/api'

try {
  const response = await fetch('/api/v1/orders')
  if (!response.ok) {
    const error: APIError = await response.json()
    console.error('Ошибка API:', error.detail)
  }
} catch (error) {
  console.error('Ошибка сети:', error)
}
```

## Type Guards

Создавайте type guard функции для безопасной работы с типами:

```typescript
import { JobStatus, CAMJobStatusResponse } from '@/types/api'

function isJobCompleted(job: CAMJobStatusResponse): boolean {
  return job.status === 'Completed'
}

function isJobFailed(job: CAMJobStatusResponse): boolean {
  return job.status === 'Failed'
}

function canDownloadArtifact(job: CAMJobStatusResponse): boolean {
  return isJobCompleted(job) && job.artifact_id !== null
}
```

## Рекомендации

1. **Всегда импортируйте типы** из `@/types/api` вместо создания локальных типов
2. **Используйте расширение типов** когда нужны дополнительные поля для UI
3. **Создавайте type guards** для проверки состояний
4. **Документируйте кастомные типы** JSDoc комментариями на русском языке
5. **Обновляйте типы** при изменении API схем в `api/schemas.py`

## Синхронизация с бэкендом

При изменении Pydantic схем в `api/schemas.py` необходимо обновить соответствующие TypeScript типы в `api.ts`.

Для автоматизации этого процесса в будущем можно использовать:
- `pydantic-to-typescript` - автогенерация TypeScript типов из Pydantic моделей
- OpenAPI схема + генератор TypeScript клиента

## Вопросы и проблемы

Если вы обнаружили несоответствие между TypeScript типами и API, пожалуйста:
1. Проверьте актуальность схем в `api/schemas.py`
2. Обновите типы в `web/src/types/api.ts`
3. Запустите TypeScript проверку: `npm run type-check`
