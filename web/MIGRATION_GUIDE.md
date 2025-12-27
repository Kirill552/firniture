# Руководство по миграции на централизованные TypeScript типы

## Обзор

В проекте созданы централизованные TypeScript типы для всех API эндпоинтов. Все типы находятся в файле `src/types/api.ts` и автоматически экспортируются через `src/types/index.ts`.

## Что изменилось

### До миграции
Типы были определены локально в каждом файле:

```typescript
// app/orders/page.tsx
type Order = {
  id: string
  customer: string
  product: string
  status: "pending" | "processing" | "completed" | "cancelled"
  price: number
  createdAt: string
}
```

### После миграции
Типы импортируются из централизованного хранилища:

```typescript
// app/orders/page.tsx
import { Order } from '@/types/api'

// Если нужны дополнительные поля для UI:
type OrderTableRow = Order & {
  customer: string
  product: string
  price: number
}
```

## Файлы, требующие обновления

Следующие файлы содержат локальные определения типов и должны быть обновлены:

1. **`src/app/orders/page.tsx`**
   - Локальный тип `Order` → импорт из `@/types/api`

2. **`src/app/dashboard/page.tsx`**
   - Локальный тип `Order` → импорт из `@/types/api`

3. **`src/app/history/page.tsx`**
   - Локальные типы `OrderStatus`, `HistoryOrder` → импорт из `@/types/api`

4. **`src/hooks/use-api.ts`** ✅ УЖЕ ОБНОВЛЕН
   - Все локальные типы заменены на импорты из `@/types/api`

## Пошаговая инструкция по миграции

### Шаг 1: Импортируйте типы

```typescript
// Вместо локальных определений
import {
  Order,
  JobStatus,
  ProductConfig,
  // ... другие нужные типы
} from '@/types/api'
```

### Шаг 2: Удалите локальные определения типов

Удалите все `type` и `interface` определения, которые дублируют типы из API.

### Шаг 3: Создайте расширенные типы для UI (если нужно)

Если компонент требует дополнительные поля, создайте расширенный тип:

```typescript
import { Order } from '@/types/api'

// Расширенный тип для таблицы
type OrderTableRow = Order & {
  customer: string      // Дополнительное поле
  product: string       // Дополнительное поле
  price: number         // Дополнительное поле
  displayStatus: string // Вычисляемое поле
}
```

### Шаг 4: Обновите использование типов

Замените все использования старых типов на новые импортированные типы.

## Примеры миграции

### Пример 1: Простая миграция (app/orders/page.tsx)

**До:**
```typescript
type Order = {
  id: string
  customer: string
  product: string
  status: "pending" | "processing" | "completed" | "cancelled"
  price: number
  createdAt: string
}

const orders: Order[] = [...]
```

**После:**
```typescript
import { Order } from '@/types/api'

// Расширяем Order для UI-специфичных полей
type OrderUIRow = Order & {
  customer: string
  product: string
  price: number
}

const orders: OrderUIRow[] = [...]
```

### Пример 2: Работа со статусами (app/history/page.tsx)

**До:**
```typescript
type OrderStatus = 'completed' | 'cancelled' | 'processing' | 'failed'

type HistoryOrder = {
  id: string
  date: string
  status: OrderStatus
  // ...
}
```

**После:**
```typescript
import { Order, JobStatus } from '@/types/api'
import { getJobStatusLabel } from '@/lib/api-utils'

type HistoryOrder = Order & {
  // Дополнительные поля
}
```

### Пример 3: API запросы

**До:**
```typescript
const createOrder = async (data: any) => {
  const response = await fetch('/api/v1/orders', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  return await response.json()
}
```

**После:**
```typescript
import { OrderCreateRequest, Order } from '@/types/api'
import { apiClient } from '@/lib/api-client'

// Вариант 1: Использование готового клиента
const order = await apiClient.createOrder({
  customer_ref: 'ООО "Рога и копыта"',
  notes: 'Срочный заказ'
})

// Вариант 2: Использование хука
import { useCreateOrder } from '@/hooks/use-api'

const mutation = useCreateOrder()
mutation.mutate({
  customer_ref: 'ООО "Рога и копыта"',
  notes: 'Срочный заказ'
})
```

## Доступные утилиты

### API Client (`src/lib/api-client.ts`)

Готовый типизированный клиент для всех API эндпоинтов:

```typescript
import { apiClient } from '@/lib/api-client'

// Создание заказа
const order = await apiClient.createOrder({ ... })

// Извлечение спецификации
const spec = await apiClient.extractSpec({ ... })

// Подбор фурнитуры
const hardware = await apiClient.selectHardware({ ... })

// Создание CAM задачи
const job = await apiClient.createCAMJob({ ... })

// Получение статуса задачи
const status = await apiClient.getCAMJobStatus(jobId)

// Диалог с ИИ (потоковый ответ)
const stream = await apiClient.sendDialogueMessage({ ... })
```

### API Utils (`src/lib/api-utils.ts`)

Вспомогательные функции для работы с типами:

```typescript
import {
  isJobCompleted,
  getJobStatusLabel,
  formatDate,
  formatFileSize,
  calculateArea,
  readStreamAsText,
} from '@/lib/api-utils'

// Type guards
if (isJobCompleted(job.status)) {
  console.log('Задача завершена!')
}

// Форматирование
const label = getJobStatusLabel('Processing') // "Выполняется"
const date = formatDate('2025-09-03T10:00:00Z') // "3 сентября 2025 г., 10:00"

// Работа с потоками
await readStreamAsText(stream, (chunk) => {
  console.log('Получен чанк:', chunk)
})
```

### React Hooks (`src/hooks/use-api.ts`)

Готовые хуки для React Query:

```typescript
import {
  useCreateOrder,
  useExtractSpec,
  useSelectHardware,
  useCAMJobStatus,
  useDialogueClarify,
  useExport1C,
} from '@/hooks/use-api'

// В компоненте
const createOrderMutation = useCreateOrder()
const { data: jobStatus } = useCAMJobStatus(jobId)
```

## Проверка типов

После миграции выполните проверку типов:

```bash
cd web
npm run type-check
```

Если есть ошибки типов, исправьте их, обратившись к документации в `src/types/README.md`.

## Частые проблемы и решения

### Проблема 1: Несоответствие полей

**Ошибка:**
```
Property 'customer' does not exist on type 'Order'
```

**Решение:**
Создайте расширенный тип для UI:
```typescript
type OrderUIRow = Order & {
  customer: string
}
```

### Проблема 2: Различные названия статусов

**Ошибка:**
```
Type '"pending"' is not assignable to type 'JobStatus'
```

**Решение:**
Используйте правильные значения из типа `JobStatus`:
- `'pending'` → `'Created'`
- `'processing'` → `'Processing'`
- `'completed'` → `'Completed'`
- `'failed'` → `'Failed'`

### Проблема 3: UUID vs string ID

**Ошибка:**
```
Type 'string' is not assignable to type 'UUID'
```

**Решение:**
Все ID в API являются строками (string), так что просто используйте `string`:
```typescript
const orderId: string = order.id
```

## Контрольный список миграции

- [ ] Импортировать типы из `@/types/api`
- [ ] Удалить локальные определения типов
- [ ] Создать расширенные типы для UI (если нужно)
- [ ] Обновить API запросы на использование `apiClient`
- [ ] Заменить `fetch` на хуки из `use-api.ts`
- [ ] Использовать утилиты из `api-utils.ts`
- [ ] Запустить `npm run type-check`
- [ ] Протестировать функционал
- [ ] Обновить тесты (если есть)

## Дополнительная информация

- Полная документация по типам: `src/types/README.md`
- Примеры использования API: `src/lib/api-client.ts`
- Утилиты и хелперы: `src/lib/api-utils.ts`
- React хуки: `src/hooks/use-api.ts`

## Поддержка

Если возникли вопросы по миграции:
1. Проверьте документацию в `src/types/README.md`
2. Посмотрите примеры в `src/lib/api-client.ts`
3. Изучите существующие хуки в `src/hooks/use-api.ts`
