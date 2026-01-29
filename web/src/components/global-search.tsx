"use client"

import * as React from "react"
import { Search, FileText, Package, Wrench, History, Shield, Settings, Users, Hash, User, ArrowRight, Clock } from "lucide-react"
import { Command as CommandComponent, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command"
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { motion, AnimatePresence } from "framer-motion"

import Link from 'next/link'
import { useRouter } from 'next/navigation'

interface SearchResult {
  id: string
  title: string
  description: string
  url: string
  type: "page" | "order" | "user" | "setting" | "document" | "component"
  category: string
  keywords: string[]
  icon: React.ComponentType<{ className?: string }>
  timestamp?: string
  score?: number
}

const mockSearchResults: SearchResult[] = [
  {
    id: "1",
    title: "Создать новый заказ",
    description: "Начать процесс создания нового заказа мебели через wizard",
    url: "/new",
    type: "page",
    category: "Заказы",
    keywords: ["создать", "новый", "заказ", "мебель", "wizard"],
    icon: FileText,
    score: 95
  },
  {
    id: "2",
    title: "Спецификация материалов (BOM)",
    description: "Просмотр и управление спецификациями материалов и компонентов",
    url: "/bom",
    type: "page",
    category: "Производство",
    keywords: ["bom", "спецификация", "материалы", "компоненты", "детали"],
    icon: Package,
    score: 90
  },
  {
    id: "3",
    title: "CAM обработка",
    description: "Управление CAM задачами, генерация G-code и предпросмотр DXF",
    url: "/cam",
    type: "page",
    category: "Производство",
    keywords: ["cam", "dxf", "gcode", "обработка", "чпу", "станок"],
    icon: Wrench,
    score: 88
  },
  {
    id: "4",
    title: "Заказ КУХ-2025-001",
    description: "Кухонный гарнитур 3.2м • Статус: В производстве • Клиент: Иванов И.И.",
    url: "/orders/КУХ-2025-001",
    type: "order",
    category: "Заказы",
    keywords: ["кухня", "гарнитур", "производство", "иванов"],
    icon: Hash,
    timestamp: "2025-01-15",
    score: 85
  },
  {
    id: "5",
    title: "Настройки интеграции 1С",
    description: "Конфигурация подключения к системе 1С:Предприятие",
    url: "/integrations",
    type: "setting",
    category: "Настройки",
    keywords: ["1с", "интеграция", "erp", "настройки", "подключение"],
    icon: Settings,
    score: 80
  },
  {
    id: "6",
    title: "Пользователь: technologist@furniture.ru",
    description: "Технолог-конструктор • Последняя активность: 2 часа назад",
    url: "/users/technologist",
    type: "user",
    category: "Пользователи",
    keywords: ["технолог", "пользователь", "активность", "конструктор"],
    icon: User,
    score: 75
  },
  {
    id: "7",
    title: "История заказов",
    description: "Архив всех выполненных заказов с расширенной фильтрацией",
    url: "/orders",
    type: "page",
    category: "Отчеты",
    keywords: ["история", "архив", "заказы", "отчеты", "фильтр"],
    icon: History,
    score: 70
  },
  {
    id: "9",
    title: "Заказ ШКАФ-2025-015",
    description: "Встроенный шкаф-купе • Статус: CAM обработка • Срок: 3 дня",
    url: "/orders/ШКАФ-2025-015",
    type: "order",
    category: "Заказы",
    keywords: ["шкаф", "купе", "встроенный", "cam"],
    icon: Hash,
    timestamp: "2025-01-14",
    score: 60
  },
  {
    id: "10",
    title: "Подбор фурнитуры",
    description: "AI-powered подбор фурнитуры с анализом совместимости",
    url: "/bom",
    type: "page",
    category: "Каталог",
    keywords: ["фурнитура", "подбор", "ai", "искусственный", "интеллект"],
    icon: Package,
    score: 55
  }
]

export function GlobalSearch() {
  const [open, setOpen] = React.useState(false)
  const [value, setValue] = React.useState("")
  const [results, setResults] = React.useState<SearchResult[]>([])
  const [loading, setLoading] = React.useState(false)
  const [selectedIndex, setSelectedIndex] = React.useState(0)
  const router = useRouter()

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }

    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const performSearch = React.useCallback(async (query: string) => {
    if (!query.trim()) {
      setResults([])
      setSelectedIndex(0)
      return
    }

    setLoading(true)

    // Simulate AI-powered search with delay
    await new Promise(resolve => setTimeout(resolve, 300))

    try {
      // Smart fuzzy search with AI-like scoring
      const searchTerms = query.toLowerCase().split(' ').filter(term => term.length > 1)
      const scoredResults = mockSearchResults.map(item => {
        let score = 0
        const searchableText = [
          item.title,
          item.description,
          item.category,
          ...item.keywords
        ].join(' ').toLowerCase()

        // Exact title match gets highest score
        if (item.title.toLowerCase().includes(query.toLowerCase())) {
          score += 50
        }

        // Category match
        if (item.category.toLowerCase().includes(query.toLowerCase())) {
          score += 30
        }

        // Description match
        if (item.description.toLowerCase().includes(query.toLowerCase())) {
          score += 20
        }

        // Keywords match
        searchTerms.forEach(term => {
          if (searchableText.includes(term)) {
            score += 10
          }
        })

        // Recent items get boost
        if (item.timestamp) {
          score += 5
        }

        return { ...item, searchScore: score }
      })
        .filter(item => item.searchScore > 0)
        .sort((a, b) => b.searchScore - a.searchScore)
        .slice(0, 8)

      setResults(scoredResults)
      setSelectedIndex(0)
    } catch (error) {
      console.error('Search error:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    const timeoutId = setTimeout(() => {
      performSearch(value)
    }, 150) // Debounce search

    return () => clearTimeout(timeoutId)
  }, [value, performSearch])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => Math.min(prev + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (results[selectedIndex]) {
        handleResultSelect(results[selectedIndex])
      }
    }
  }

  const handleResultSelect = (result: SearchResult) => {
    router.push(result.url)
    setOpen(false)
    setValue("")
    setResults([])
  }

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      "Заказы": "bg-blue-50 text-blue-700 border-blue-200",
      "Производство": "bg-green-50 text-green-700 border-green-200",
      "Настройки": "bg-gray-50 text-gray-700 border-gray-200",
      "Пользователи": "bg-purple-50 text-purple-700 border-purple-200",
      "Отчеты": "bg-orange-50 text-orange-700 border-orange-200",
      "Безопасность": "bg-red-50 text-red-700 border-red-200",
      "Каталог": "bg-teal-50 text-teal-700 border-teal-200"
    }
    return colors[category] || "bg-gray-50 text-gray-700 border-gray-200"
  }

  const popularPages = [
    { title: "Создать заказ", url: "/new", icon: FileText, description: "Новый заказ мебели" },
    { title: "Спецификации", url: "/bom", icon: Package, description: "BOM материалов" },
    { title: "CAM обработка", url: "/cam", icon: Wrench, description: "Генерация G-code" },
    { title: "История", url: "/orders", icon: History, description: "Архив заказов" }
  ]

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="w-[280px] justify-start space-x-2 text-muted-foreground hover:text-foreground"
          aria-label="Открыть глобальный поиск (⌘K)"
        >
          <Search className="mr-2 h-4 w-4" />
          <span className="hidden sm:inline-flex">Поиск по всему приложению...</span>
          <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground ml-auto">
            <span className="hidden sm:inline-flex">⌘</span> K
          </kbd>
        </Button>
      </DialogTrigger>
      <DialogContent className="overflow-hidden p-0 max-w-2xl">
        <DialogTitle className="sr-only">Глобальный поиск</DialogTitle>
        <DialogDescription className="sr-only">
          Поиск по страницам, заказам, материалам и настройкам. Используйте стрелки для навигации, Enter для выбора и Esc для закрытия.
        </DialogDescription>
        <CommandComponent className="p-0" onKeyDown={handleKeyDown}>
          <div className="relative">
            <CommandInput
              placeholder="Поиск заказов, материалов, пользователей..."
              value={value}
              onValueChange={setValue}
              className="pr-14"
              aria-label="Быстрый поиск"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                <span className="text-xs">⌘</span>K
              </kbd>
            </div>
          </div>
          <CommandList className="max-h-[400px]">
            <AnimatePresence>
              {loading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-2 px-4 py-3"
                >
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-600"></div>
                  <span className="text-sm text-muted-foreground">Поиск с помощью ИИ...</span>
                </motion.div>
              )}

              {!loading && results.length === 0 && value && (
                <CommandEmpty>
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="py-6 text-center"
                  >
                    <Search className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Нет результатов для "{value}"</p>
                    <p className="text-xs text-muted-foreground mt-1">Попробуйте другие ключевые слова</p>
                  </motion.div>
                </CommandEmpty>
              )}

              {!loading && results.length === 0 && !value && (
                <CommandGroup heading="Популярные разделы">
                  {popularPages.map((page, index) => (
                    <CommandItem
                      key={page.url}
                      onSelect={() => handleResultSelect({
                        ...page,
                        id: page.url,
                        type: "page",
                        category: "",
                        keywords: []
                      })}
                      className="flex items-center gap-3 px-4 py-3"
                    >
                      <page.icon className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">{page.title}</p>
                        <p className="text-xs text-muted-foreground">{page.description}</p>
                      </div>
                      <ArrowRight className="h-3 w-3 text-muted-foreground" />
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}

              {!loading && results.length > 0 && (
                <CommandGroup heading={`${results.length} результатов`}>
                  {results.map((result, index) => (
                    <motion.div
                      key={result.id}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.02 }}
                    >
                      <CommandItem
                        onSelect={() => handleResultSelect(result)}
                        className={`flex items-center gap-3 px-4 py-3 ${index === selectedIndex ? "bg-accent" : ""
                          }`}
                      >
                        <result.icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-sm font-medium truncate">{result.title}</p>
                            <Badge
                              variant="outline"
                              className={`text-xs px-2 py-0 ${getCategoryColor(result.category)}`}
                            >
                              {result.category}
                            </Badge>
                          </div>

                          <p className="text-xs text-muted-foreground truncate">
                            {result.description}
                          </p>

                          {result.timestamp && (
                            <div className="flex items-center gap-1 mt-1">
                              <Clock className="h-3 w-3 text-muted-foreground" />
                              <span className="text-xs text-muted-foreground">
                                {result.timestamp}
                              </span>
                            </div>
                          )}
                        </div>

                        <ArrowRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                      </CommandItem>
                    </motion.div>
                  ))}
                </CommandGroup>
              )}
            </AnimatePresence>
          </CommandList>

          {(results.length > 0 || (!loading && !value)) && (
            <div className="border-t px-4 py-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-4">
                  <span>↑↓ навигация</span>
                  <span>Enter выбор</span>
                  <span>Esc закрыть</span>
                </div>
                {results.length > 0 && (
                  <span>{results.length} из {mockSearchResults.length}</span>
                )}
              </div>
            </div>
          )}
        </CommandComponent>
      </DialogContent>
    </Dialog>
  )
}