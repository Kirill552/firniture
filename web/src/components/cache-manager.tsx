'use client'

import { useForceRefresh } from '@/hooks/use-force-refresh'

export function CacheManager() {
  useForceRefresh()
  
  // В development режиме добавляем кнопку для ручного обновления
  if (process.env.NODE_ENV === 'development') {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => {
            if (typeof window !== 'undefined') {
              sessionStorage.clear()
              localStorage.clear()
              window.location.reload()
            }
          }}
          className="bg-red-500 text-white px-3 py-1 rounded text-xs opacity-50 hover:opacity-100 transition-opacity"
          title="Принудительное обновление (очистка кеша)"
        >
          🔄 Cache Clear
        </button>
      </div>
    )
  }
  
  return null
}