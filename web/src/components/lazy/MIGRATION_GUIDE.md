# Руководство по миграции на Lazy Loading

Этот документ содержит конкретные примеры замены компонентов в существующих файлах проекта.

## Файлы для обновления

### 1. `web/src/app/viewer/page.tsx` - ThreeViewer

**Текущий код:**
```tsx
'use client'

import { ThreeViewer } from "@/components/three-viewer"

export default function ViewerPage() {
  return (
    <div className="w-full h-screen">
      <ThreeViewer />
    </div>
  )
}
```

**После миграции:**
```tsx
'use client'

import { LazyThreeViewer } from "@/components/lazy"

export default function ViewerPage() {
  return (
    <div className="w-full h-screen">
      <LazyThreeViewer />
    </div>
  )
}
```

**Экономия:** ~2MB начального бандла

---

### 2. `web/src/app/orders/page.tsx` - DataTable

**Текущий код (первые строки):**
```tsx
"use client"

import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { DateRangeFilter, DateRange } from "@/components/date-range-filter"
import * as React from "react"

// ... остальной код

export default function OrdersPage() {
  // ...
  return (
    <div className="container mx-auto py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Заказы</h1>
        <DateRangeFilter
          value={dateRange}
          onChange={setDateRange}
        />
      </div>
      <DataTable columns={columns} data={filteredOrders} tableId="orders" />
    </div>
  )
}
```

**После миграции:**
```tsx
"use client"

import { LazyDataTable } from "@/components/lazy"
import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { DateRangeFilter, DateRange } from "@/components/date-range-filter"
import * as React from "react"

// ... остальной код

export default function OrdersPage() {
  // ...
  return (
    <div className="container mx-auto py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Заказы</h1>
        <DateRangeFilter
          value={dateRange}
          onChange={setDateRange}
        />
      </div>
      <LazyDataTable columns={columns} data={filteredOrders} tableId="orders" />
    </div>
  )
}
```

**Экономия:** ~200KB начального бандла

---

### 3. `web/src/app/dashboard/page.tsx` - DataTable

**Замена аналогична orders/page.tsx:**
```tsx
// Было:
import { DataTable } from "@/components/data-table"

// Стало:
import { LazyDataTable } from "@/components/lazy"

// И в JSX:
// Было: <DataTable columns={columns} data={data} />
// Стало: <LazyDataTable columns={columns} data={data} />
```

---

### 4. `web/src/app/orders/new/bom/page.tsx` - DataTable

**Замена аналогична:**
```tsx
// Было:
import { DataTable } from "@/components/data-table"

// Стало:
import { LazyDataTable } from "@/components/lazy"
```

---

### 5. `web/src/components/app-bar.tsx` - GlobalSearch

**Текущий код (первые строки):**
```tsx
import * as React from "react"
import { Button } from "@/components/ui/button"
import { GlobalSearch } from "@/components/global-search"
import {
  DropdownMenu,
  // ... остальные импорты
} from "@/components/ui/dropdown-menu"

export function AppBar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="w-full flex h-14 items-center px-6">
        <div className="flex w-full flex-1 items-center justify-between space-x-4">
          <div className="flex-1"></div>
          <div className="flex-1 max-w-md">
            <GlobalSearch />
          </div>
          {/* ... остальной код */}
        </div>
      </div>
    </header>
  )
}
```

**После миграции:**
```tsx
import * as React from "react"
import { Button } from "@/components/ui/button"
import { LazyGlobalSearch } from "@/components/lazy"
import {
  DropdownMenu,
  // ... остальные импорты
} from "@/components/ui/dropdown-menu"

export function AppBar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="w-full flex h-14 items-center px-6">
        <div className="flex w-full flex-1 items-center justify-between space-x-4">
          <div className="flex-1"></div>
          <div className="flex-1 max-w-md">
            <LazyGlobalSearch />
          </div>
          {/* ... остальной код */}
        </div>
      </div>
    </header>
  )
}
```

**Экономия:** ~200KB начального бандла

---

### 6. `web/src/app/orders/new/dialogue/page.tsx` - AiChat

**Найти файл и заменить:**
```tsx
// Было:
import { AiChat } from "@/components/ai-chat"

// Стало:
import { LazyAiChat } from "@/components/lazy"

// И в JSX:
// Было: <AiChat orderId={orderId} />
// Стало: <LazyAiChat orderId={orderId} />
```

**Экономия:** ~50KB начального бандла

---

## Дополнительные оптимизации

### 7. Декоративные элементы - BlueprintAnimation

Если `BlueprintAnimation` используется где-то (например, на главной странице):

```tsx
// Было:
import { BlueprintAnimation } from "@/components/blueprint-animation"

// Стало:
import { LazyBlueprintAnimation } from "@/components/lazy"

// Использование:
<div className="relative">
  <LazyBlueprintAnimation />
  {/* Основной контент */}
</div>
```

### 8. AnimatedLayout для переходов

Если используется `AnimatedLayout`:

```tsx
// Было:
import { AnimatedLayout } from "@/components/animated-layout"

// Стало:
import { LazyAnimatedLayout } from "@/components/lazy"

// Использование:
<LazyAnimatedLayout>
  <YourPageContent />
</LazyAnimatedLayout>
```

---

## План миграции (рекомендуемый порядок)

### Фаза 1: Критичные компоненты (наибольший эффект)
1. ✅ `web/src/app/viewer/page.tsx` - ThreeViewer (~2MB)
2. ✅ `web/src/components/app-bar.tsx` - GlobalSearch (~200KB)

### Фаза 2: Таблицы
3. ✅ `web/src/app/orders/page.tsx` - DataTable
4. ✅ `web/src/app/dashboard/page.tsx` - DataTable
5. ✅ `web/src/app/orders/new/bom/page.tsx` - DataTable

### Фаза 3: Остальное
6. ✅ `web/src/app/orders/new/dialogue/page.tsx` - AiChat
7. ✅ Любые страницы с декоративными анимациями

---

## Проверка результата

После миграции проверьте размеры бандлов:

```bash
cd web
npm run build
```

Вы должны увидеть что-то вроде:

```
Route (app)                              Size     First Load JS
┌ ○ /                                    5.2 kB         120 kB
├ ○ /orders                              8.1 kB         130 kB
├ ○ /viewer                              3.5 kB         118 kB  ← Основной JS уменьшился!
└ ○ /dashboard                           6.8 kB         125 kB

+ Chunks:
  ├ three-viewer-[hash].js               1.9 MB         ← Загружается отдельно
  ├ data-table-[hash].js                 180 KB         ← Загружается отдельно
  └ global-search-[hash].js              195 KB         ← Загружается отдельно
```

---

## Тестирование

После миграции протестируйте:

1. **Функциональность**
   - Все компоненты работают как раньше
   - Placeholder'ы показываются корректно
   - Нет ошибок в консоли

2. **Производительность**
   - Используйте Chrome DevTools → Performance
   - Проверьте FCP (First Contentful Paint)
   - Проверьте LCP (Largest Contentful Paint)
   - Убедитесь что компоненты загружаются когда нужно

3. **Network**
   - Откройте DevTools → Network
   - Обновите страницу
   - Убедитесь что тяжёлые компоненты загружаются отдельными чанками

---

## Откат изменений

Если что-то пошло не так, откатить просто:

```tsx
// Откат:
import { ThreeViewer } from "@/components/three-viewer"
// вместо:
import { LazyThreeViewer } from "@/components/lazy"
```

---

## FAQ

**Q: Можно ли использовать LazyDataTable с теми же пропсами?**
A: Да, API полностью совместим. Все пропсы работают так же.

**Q: Будет ли "мигание" при загрузке?**
A: Нет, мы используем placeholder'ы которые выглядят как skeleton screens.

**Q: Нужно ли менять что-то в тестах?**
A: Зависит от тестов. Unit тесты должны работать, но в E2E тестах может понадобиться `waitFor` для ожидания загрузки компонента.

**Q: Как это влияет на SEO?**
A: Положительно! Более быстрая загрузка улучшает Core Web Vitals, что учитывается Google.

**Q: Можно ли lazy-загружать компоненты условно?**
A: Да! Например:
```tsx
{showComparison && <LazyHardwareComparisonModal {...props} />}
```

---

## Дополнительные ресурсы

- [Next.js Dynamic Import](https://nextjs.org/docs/advanced-features/dynamic-import)
- [Web.dev - Code Splitting](https://web.dev/code-splitting-suspense/)
- [React - Suspense](https://react.dev/reference/react/Suspense)
