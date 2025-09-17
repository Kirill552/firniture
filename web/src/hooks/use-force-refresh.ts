import { useEffect } from 'react'

export function useForceRefresh() {
  useEffect(() => {
    // В режиме разработки только очищаем кеш, но не перезагружаем автоматически
    if (process.env.NODE_ENV === 'development') {
      if (typeof window !== 'undefined' && 'caches' in window) {
        caches.keys().then(names => {
          names.forEach(name => {
            caches.delete(name)
          })
        })
      }
    }
  }, [])

  // Функция для ручного принудительного обновления
  const forceRefresh = () => {
    if (typeof window !== 'undefined') {
      // Очищаем все виды кеша
      sessionStorage.clear()
      localStorage.removeItem('force-refreshed')
      
      if ('caches' in window) {
        caches.keys().then(names => {
          names.forEach(name => {
            caches.delete(name)
          })
        })
      }
      
      // Принудительное обновление с добавлением timestamp
      const url = new URL(window.location.href)
      url.searchParams.set('_t', Date.now().toString())
      window.location.href = url.toString()
    }
  }

  return { forceRefresh }
}