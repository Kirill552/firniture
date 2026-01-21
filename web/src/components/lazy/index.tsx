/**
 * Lazy-загружаемые версии тяжёлых компонентов
 *
 * Используется dynamic import из Next.js для code splitting и улучшения производительности.
 * Компоненты загружаются только когда они действительно нужны на странице.
 */

import dynamic from 'next/dynamic'

/**
 * ThreeViewer - 3D просмотр DXF файлов
 *
 * Зависимости:
 * - @react-three/fiber (~800KB)
 * - @react-three/drei (~400KB)
 * - three (~600KB)
 * - three-dxf-loader
 *
 * Итого: ~2MB кода
 *
 * SSR отключён потому что Three.js требует WebGL и не работает на сервере
 */
export const LazyThreeViewer = dynamic(
  () => import('../three-viewer').then(mod => ({ default: mod.ThreeViewer })),
  {
    loading: () => (
      <div className="w-full h-full bg-gray-100 dark:bg-gray-900 animate-pulse flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-16 h-16 mx-auto rounded-lg bg-gray-200 dark:bg-gray-800" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Загрузка 3D-просмотра...</p>
        </div>
      </div>
    ),
    ssr: false // Three.js не работает на сервере
  }
)

/**
 * DataTable - Продвинутая таблица с фильтрами, сортировкой, группировкой
 *
 * Зависимости:
 * - @tanstack/react-table (~150KB)
 * - множество UI компонентов
 *
 * Итого: ~200KB кода
 */
export const LazyDataTable = dynamic(
  () => import('../data-table').then(mod => ({ default: mod.DataTable })),
  {
    loading: () => (
      <div className="w-full space-y-4">
        <div className="flex items-center gap-2 py-4">
          <div className="h-10 w-64 bg-muted animate-pulse rounded-md" />
          <div className="h-10 w-32 bg-muted animate-pulse rounded-md ml-auto" />
        </div>
        <div className="rounded-md border">
          <div className="h-96 bg-muted animate-pulse" />
        </div>
        <div className="flex justify-end gap-2 py-4">
          <div className="h-9 w-24 bg-muted animate-pulse rounded-md" />
          <div className="h-9 w-24 bg-muted animate-pulse rounded-md" />
        </div>
      </div>
    )
  }
)

/**
 * GlobalSearch - Глобальный поиск с AI
 *
 * Зависимости:
 * - framer-motion (~100KB)
 * - cmdk (~50KB)
 * - множество UI компонентов и иконок
 *
 * Итого: ~200KB кода
 */
export const LazyGlobalSearch = dynamic(
  () => import('../global-search').then(mod => ({ default: mod.GlobalSearch })),
  {
    loading: () => (
      <div className="w-[280px] h-10 bg-muted animate-pulse rounded-md" />
    )
  }
)

/**
 * AiChat - Компонент чата с ИИ-технологом
 *
 * Зависимости:
 * - Streaming API
 * - UI компоненты для чата
 *
 * Итого: ~50KB кода
 *
 * Менее критичен чем другие, но всё равно полезно грузить лениво
 */
export const LazyAiChat = dynamic(
  () => import('../ai-chat').then(mod => ({ default: mod.AiChat })),
  {
    loading: () => (
      <div className="w-full rounded-lg border bg-card">
        <div className="space-y-4 p-6">
          <div className="h-6 w-48 bg-muted animate-pulse rounded" />
          <div className="h-96 bg-muted animate-pulse rounded" />
          <div className="flex gap-2">
            <div className="h-10 flex-1 bg-muted animate-pulse rounded" />
            <div className="h-10 w-24 bg-muted animate-pulse rounded" />
          </div>
        </div>
      </div>
    )
  }
)

/**
 * HardwareComparisonModal - Модальное окно сравнения фурнитуры
 *
 * Зависимости:
 * - Dialog компонент
 * - Таблица
 *
 * Итого: ~30KB кода
 *
 * Загружается только при открытии модального окна
 */
export const LazyHardwareComparisonModal = dynamic(
  () => import('../hardware-comparison-modal').then(mod => ({ default: mod.HardwareComparisonModal })),
  {
    loading: () => (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
        <div className="w-full max-w-4xl rounded-lg border bg-card p-6 shadow-lg">
          <div className="space-y-4">
            <div className="h-6 w-64 bg-muted animate-pulse rounded" />
            <div className="h-96 bg-muted animate-pulse rounded" />
          </div>
        </div>
      </div>
    )
  }
)

/**
 * BlueprintAnimation - Анимированный чертёж кухни на фоне
 *
 * Зависимости:
 * - framer-motion
 * - Множество SVG path анимаций
 *
 * Итого: ~20KB кода + framer-motion
 *
 * Используется для декоративных целей, не критичен для функциональности
 */
export const LazyBlueprintAnimation = dynamic(
  () => import('../blueprint-animation').then(mod => ({ default: mod.BlueprintAnimation })),
  {
    loading: () => null, // Не показываем placeholder - это декоративный элемент
    ssr: false // Анимации не нужны на сервере
  }
)

/**
 * AnimatedLayout - Анимация переходов между страницами
 *
 * Зависимости:
 * - framer-motion
 *
 * Итого: ~5KB кода + framer-motion
 *
 * Можно использовать для улучшения UX при навигации
 */
export const LazyAnimatedLayout = dynamic(
  () => import('../animated-layout').then(mod => ({ default: mod.AnimatedLayout })),
  {
    loading: () => <div />,
    ssr: false // Анимации переходов не нужны на сервере
  }
)
