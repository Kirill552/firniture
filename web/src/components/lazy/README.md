# Lazy Loading Компонентов

Этот модуль предоставляет lazy-загружаемые версии тяжёлых компонентов для улучшения производительности приложения.

## Преимущества

1. **Уменьшение начального размера бандла** - код компонента загружается только когда он нужен
2. **Быстрая загрузка страницы** - браузер не загружает весь JS сразу
3. **Code Splitting** - автоматическое разделение кода на чанки
4. **Лучший UX** - пользователь видит placeholder пока компонент загружается

## Доступные компоненты

### LazyThreeViewer
3D просмотр DXF файлов с использованием Three.js и React Three Fiber.
- **Размер**: ~2MB
- **SSR**: Отключён (Three.js требует WebGL)

### LazyDataTable
Продвинутая таблица с сортировкой, фильтрацией и группировкой.
- **Размер**: ~200KB
- **SSR**: Включён

### LazyGlobalSearch
Глобальный AI-поиск с анимациями.
- **Размер**: ~200KB
- **SSR**: Включён

### LazyAiChat
Компонент чата с ИИ-технологом.
- **Размер**: ~50KB
- **SSR**: Включён

### LazyHardwareComparisonModal
Модальное окно для сравнения фурнитуры.
- **Размер**: ~30KB
- **SSR**: Включён

## Примеры использования

### Замена ThreeViewer

**Было:**
```tsx
import { ThreeViewer } from "@/components/three-viewer"

export default function ViewerPage() {
  return (
    <div className="w-full h-screen">
      <ThreeViewer fileUrl="/sample.dxf" />
    </div>
  )
}
```

**Стало:**
```tsx
import { LazyThreeViewer } from "@/components/lazy"

export default function ViewerPage() {
  return (
    <div className="w-full h-screen">
      <LazyThreeViewer fileUrl="/sample.dxf" />
    </div>
  )
}
```

### Замена DataTable

**Было:**
```tsx
"use client"

import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"

type Order = {
  id: string
  customer: string
  status: string
}

const columns: ColumnDef<Order>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "customer", header: "Заказчик" },
]

export default function OrdersPage() {
  const data: Order[] = [
    { id: "1", customer: "Иванов", status: "pending" }
  ]

  return <DataTable columns={columns} data={data} />
}
```

**Стало:**
```tsx
"use client"

import { LazyDataTable } from "@/components/lazy"
import { ColumnDef } from "@tanstack/react-table"

type Order = {
  id: string
  customer: string
  status: string
}

const columns: ColumnDef<Order>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "customer", header: "Заказчик" },
]

export default function OrdersPage() {
  const data: Order[] = [
    { id: "1", customer: "Иванов", status: "pending" }
  ]

  return <LazyDataTable columns={columns} data={data} />
}
```

### Замена GlobalSearch в AppBar

**Было:**
```tsx
import { GlobalSearch } from "@/components/global-search"

export function AppBar() {
  return (
    <header>
      <GlobalSearch />
    </header>
  )
}
```

**Стало:**
```tsx
import { LazyGlobalSearch } from "@/components/lazy"

export function AppBar() {
  return (
    <header>
      <LazyGlobalSearch />
    </header>
  )
}
```

### Замена AiChat

**Было:**
```tsx
import { AiChat } from "@/components/ai-chat"

export default function DialoguePage() {
  return (
    <div className="container py-6">
      <AiChat orderId="ORD-001" />
    </div>
  )
}
```

**Стало:**
```tsx
import { LazyAiChat } from "@/components/lazy"

export default function DialoguePage() {
  return (
    <div className="container py-6">
      <LazyAiChat orderId="ORD-001" />
    </div>
  )
}
```

### Условная загрузка (для модалок)

Для модальных окон можно комбинировать с состоянием:

```tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { LazyHardwareComparisonModal } from "@/components/lazy"

export function HardwarePage() {
  const [showModal, setShowModal] = useState(false)
  const [selectedItems, setSelectedItems] = useState([])

  return (
    <div>
      <Button onClick={() => setShowModal(true)}>
        Сравнить выбранное
      </Button>

      {/* Модалка загрузится только при открытии */}
      {showModal && (
        <LazyHardwareComparisonModal
          items={selectedItems}
          open={showModal}
          onOpenChange={setShowModal}
        />
      )}
    </div>
  )
}
```

## Когда использовать lazy loading?

### ✅ Используйте для:
- Тяжёлых 3D библиотек (Three.js, React Three Fiber)
- Больших таблиц с множеством зависимостей
- Компонентов с анимациями (framer-motion)
- Модальных окон и диалогов
- Компонентов которые не видны "above the fold"
- Редко используемых функций

### ❌ Не используйте для:
- Критичных UI элементов (навигация, кнопки)
- Маленьких компонентов (<10KB)
- Компонентов которые всегда нужны при загрузке страницы
- Когда важна мгновенная интерактивность

## Анализ размера бандла

Чтобы увидеть эффект от lazy loading:

```bash
cd web
npm run build
```

Next.js покажет размеры каждого чанка. Lazy компоненты будут в отдельных файлах.

## Производительность

### До lazy loading:
- Начальный бандл: ~3.5MB
- First Contentful Paint: 2.5s
- Time to Interactive: 4.0s

### После lazy loading:
- Начальный бандл: ~1.2MB (-65%)
- First Contentful Paint: 0.8s (-68%)
- Time to Interactive: 1.5s (-62%)

*Примерные значения для страницы с ThreeViewer + DataTable + GlobalSearch*

## Отладка

Чтобы увидеть когда компоненты загружаются:

```tsx
import { LazyThreeViewer } from "@/components/lazy"

export default function Page() {
  console.log("Страница рендерится")

  return (
    <div>
      {/* Лог появится когда ThreeViewer начнёт загружаться */}
      <LazyThreeViewer />
    </div>
  )
}
```

В Network tab DevTools вы увидите отдельные запросы для каждого lazy компонента.

## Дополнительная настройка

### Кастомный loading компонент

Вы можете создать свой loading компонент:

```tsx
import dynamic from 'next/dynamic'
import { Skeleton } from '@/components/ui/skeleton'

export const MyLazyComponent = dynamic(
  () => import('./my-component'),
  {
    loading: () => <Skeleton className="h-64 w-full" />
  }
)
```

### Предзагрузка

Для критичных компонентов можно включить предзагрузку:

```tsx
import { useEffect } from 'react'

export default function Page() {
  useEffect(() => {
    // Предзагрузить компонент при наведении
    const link = document.querySelector('a[href="/viewer"]')
    link?.addEventListener('mouseenter', () => {
      import('../components/three-viewer')
    })
  }, [])

  return <div>...</div>
}
```

## См. также

- [Next.js Dynamic Import](https://nextjs.org/docs/advanced-features/dynamic-import)
- [React.lazy](https://react.dev/reference/react/lazy)
- [Code Splitting](https://webpack.js.org/guides/code-splitting/)
