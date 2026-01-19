'use client'

import { useState, useEffect, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Search, Loader2, Package } from "lucide-react"

type HardwareItem = {
  sku: string
  name: string | null
  description: string | null
  brand: string | null
  type: string
  category: string | null
  price_rub: number | null
  params: Record<string, any>
  score: number
}

type HardwareSearchResponse = {
  items: HardwareItem[]
  total: number
  query: string
}

async function searchHardware(query: string, limit: number = 20): Promise<HardwareSearchResponse> {
  if (!query.trim()) {
    return { items: [], total: 0, query: "" }
  }
  const res = await fetch(`/api/v1/hardware/search?q=${encodeURIComponent(query)}&limit=${limit}`)
  if (!res.ok) throw new Error("Ошибка поиска")
  return res.json()
}

export default function HardwarePage() {
  const [query, setQuery] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")
  const [selectedItems, setSelectedItems] = useState<HardwareItem[]>([])
  const [savedQueries, setSavedQueries] = useState<string[]>([])

  // Debounce поиска (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  // Загрузка сохранённых запросов
  useEffect(() => {
    try {
      const raw = localStorage.getItem('hardware:savedQueries')
      if (raw) setSavedQueries(JSON.parse(raw))
    } catch {}
  }, [])

  // Поиск через API
  const { data, isLoading, error } = useQuery({
    queryKey: ['hardware-search', debouncedQuery],
    queryFn: () => searchHardware(debouncedQuery),
    enabled: debouncedQuery.length > 0,
    staleTime: 60_000, // 1 минута кэширования
  })

  const saveCurrentQuery = useCallback(() => {
    if (!query.trim()) return
    setSavedQueries(prev => {
      const next = Array.from(new Set([query.trim(), ...prev])).slice(0, 10)
      try { localStorage.setItem('hardware:savedQueries', JSON.stringify(next)) } catch {}
      return next
    })
  }, [query])

  const removeQuery = useCallback((q: string) => {
    setSavedQueries(prev => {
      const next = prev.filter(x => x !== q)
      try { localStorage.setItem('hardware:savedQueries', JSON.stringify(next)) } catch {}
      return next
    })
  }, [])

  const handleSelectItem = useCallback((item: HardwareItem) => {
    setSelectedItems(prev =>
      prev.find(i => i.sku === item.sku)
        ? prev.filter(i => i.sku !== item.sku)
        : [...prev, item]
    )
  }, [])

  const isSelected = useCallback((item: HardwareItem) => !!selectedItems.find(i => i.sku === item.sku), [selectedItems])

  const items = data?.items || []

  return (
    <div className="p-6 w-full">
      <div className="flex justify-between items-center mb-6 flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold">Каталог фурнитуры</h1>
          <p className="text-muted-foreground mt-1">1305 позиций Boyard • RAG-поиск</p>
        </div>
        {selectedItems.length > 0 && (
          <Button variant="outline" onClick={() => setSelectedItems([])}>
            Очистить выбор ({selectedItems.length})
          </Button>
        )}
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Поиск: петля 110, направляющие 450, подъёмник..."
          className="pl-10 pr-24"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
          {isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          <Button size="sm" variant="outline" onClick={saveCurrentQuery} disabled={!query.trim()}>
            Сохранить
          </Button>
        </div>
      </div>

      {savedQueries.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2 text-xs">
          {savedQueries.map(q => (
            <button
              key={q}
              onClick={() => setQuery(q)}
              className="px-2 py-1 rounded border bg-background hover:bg-muted transition relative group"
            >
              {q}
              <span
                onClick={(e) => { e.stopPropagation(); removeQuery(q) }}
                className="ml-2 opacity-0 group-hover:opacity-100 text-muted-foreground cursor-pointer"
              >
                ×
              </span>
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-4 p-4 rounded border border-destructive bg-destructive/10 text-destructive">
          Ошибка поиска: {(error as Error).message}
        </div>
      )}

      {!query && (
        <div className="text-center py-16 text-muted-foreground">
          <Package className="h-16 w-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">Введите запрос для поиска фурнитуры</p>
          <p className="text-sm mt-2">Например: &quot;петля 110&quot;, &quot;направляющие 450&quot;, &quot;подъёмник авентос&quot;</p>
        </div>
      )}

      {query && items.length === 0 && !isLoading && (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg">Ничего не найдено по запросу &quot;{query}&quot;</p>
          <p className="text-sm mt-2">Попробуйте изменить запрос</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map((item) => (
          <Card
            key={item.sku}
            className={`flex flex-col cursor-pointer transition-colors ${isSelected(item) ? 'border-primary ring-1 ring-primary' : 'hover:border-muted-foreground/50'}`}
            onClick={() => handleSelectItem(item)}
          >
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start gap-2">
                <div>
                  <CardTitle className="text-base">{item.name || item.sku}</CardTitle>
                  <CardDescription className="font-mono text-xs">{item.sku}</CardDescription>
                </div>
                <Badge variant="secondary" className="shrink-0">
                  {Math.round(item.score * 100)}%
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="flex-grow">
              {item.description && (
                <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{item.description}</p>
              )}
              <div className="flex flex-wrap gap-2 text-xs">
                {item.type && <Badge variant="outline">{item.type}</Badge>}
                {item.category && <Badge variant="outline">{item.category}</Badge>}
                {item.brand && <Badge variant="outline">{item.brand}</Badge>}
              </div>
              {item.price_rub && (
                <p className="text-sm font-medium mt-3">{item.price_rub.toLocaleString('ru-RU')} ₽</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {data && data.total > 0 && (
        <div className="mt-6 text-center text-sm text-muted-foreground">
          Найдено: {data.total} позиций
        </div>
      )}
    </div>
  )
}
