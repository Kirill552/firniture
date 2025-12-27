# Быстрый старт: Lazy Loading

## 1. Импортируй lazy-версию

```tsx
// ❌ Старый способ
import { ThreeViewer } from "@/components/three-viewer"
import { DataTable } from "@/components/data-table"
import { GlobalSearch } from "@/components/global-search"
import { AiChat } from "@/components/ai-chat"

// ✅ Новый способ
import {
  LazyThreeViewer,
  LazyDataTable,
  LazyGlobalSearch,
  LazyAiChat
} from "@/components/lazy"
```

## 2. Используй с теми же пропсами

```tsx
// API идентичен, просто добавь "Lazy" в начало
<LazyThreeViewer fileUrl="/sample.dxf" />
<LazyDataTable columns={columns} data={data} />
<LazyGlobalSearch />
<LazyAiChat orderId="ORD-001" />
```

## 3. Готово!

Компонент автоматически:
- Загрузится только когда нужен
- Покажет красивый placeholder
- Уменьшит начальный размер бандла

---

## Все доступные компоненты

| Компонент | Lazy версия | Экономия |
|-----------|-------------|----------|
| ThreeViewer | LazyThreeViewer | ~2MB |
| DataTable | LazyDataTable | ~200KB |
| GlobalSearch | LazyGlobalSearch | ~200KB |
| AiChat | LazyAiChat | ~50KB |
| HardwareComparisonModal | LazyHardwareComparisonModal | ~30KB |
| BlueprintAnimation | LazyBlueprintAnimation | ~20KB |
| AnimatedLayout | LazyAnimatedLayout | ~5KB |

---

## Файлы для замены

### Высокий приоритет (большой эффект):
- ✅ `web/src/app/viewer/page.tsx` → LazyThreeViewer
- ✅ `web/src/components/app-bar.tsx` → LazyGlobalSearch

### Средний приоритет:
- ✅ `web/src/app/orders/page.tsx` → LazyDataTable
- ✅ `web/src/app/dashboard/page.tsx` → LazyDataTable
- ✅ `web/src/app/orders/new/bom/page.tsx` → LazyDataTable
- ✅ `web/src/app/orders/new/dialogue/page.tsx` → LazyAiChat

---

## Для модальных окон

```tsx
// Загружай только при открытии
const [open, setOpen] = useState(false)

return (
  <>
    <Button onClick={() => setOpen(true)}>Открыть</Button>

    {open && (
      <LazyHardwareComparisonModal
        items={items}
        open={open}
        onOpenChange={setOpen}
      />
    )}
  </>
)
```

---

## Проверка работы

```bash
cd web
npm run build
```

Ищи строки типа:
```
+ Chunks:
  ├ three-viewer-[hash].js     1.9 MB  ← Отдельный чанк!
```

---

📖 **Детали:** `README.md`
🚀 **Миграция:** `MIGRATION_GUIDE.md`
