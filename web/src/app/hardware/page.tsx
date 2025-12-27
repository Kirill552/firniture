'use client'

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Search, Sparkles } from "lucide-react"
import { AiExplanation } from "@/components/ai-explanation"
import { HardwareComparisonModal } from "@/components/hardware-comparison-modal"
import { HardwareAdvancedFilters } from "@/components/hardware-advanced-filters"

// This is a placeholder for the actual hardware item type
type HardwareItem = {
  sku: string;
  name: string;
  description: string;
  imageUrl: string;
  aiExplanation: {
    pros: string[];
    cons: string[];
    confidence: number;
  };
  [key: string]: any; // Allow other properties
};

const hardwareItems: HardwareItem[] = [
  {
    sku: "HFL-001",
    name: "Петля накладная, 110°",
    description: "Стандартная петля для большинства фасадов. Простая установка.",
    imageUrl: "/placeholder.svg",
    aiExplanation: {
      pros: ["Надежная", "Низкая стоимость"],
      cons: ["Не для толстых фасадов"],
      confidence: 0.95,
    },
  },
  {
    sku: "HFL-002",
    name: "Петля для фальш-панелей, 90°",
    description: "Используется для угловых шкафов и фальш-панелей.",
    imageUrl: "/placeholder.svg",
    aiExplanation: {
      pros: ["Решает проблему угловых соединений"],
      cons: ["Сложнее в установке"],
      confidence: 0.88,
    },
  },
  {
    sku: "DRS-010",
    name: "Направляющие шариковые, 450мм",
    description: "Плавное и тихое выдвижение ящиков. Полное выдвижение.",
    imageUrl: "/placeholder.svg",
    aiExplanation: {
      pros: ["Плавный ход", "Высокая нагрузка"],
      cons: ["Требуют точной установки"],
      confidence: 0.92,
    },
  },
]

export default function HardwarePage() {
  const [selectedItems, setSelectedItems] = useState<HardwareItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [query, setQuery] = useState("")
  const [confidenceRange, setConfidenceRange] = useState<[number, number]>([0,1])
  const [aiSuggestion, setAiSuggestion] = useState<string | undefined>()
  const [savedQueries, setSavedQueries] = useState<string[]>([])

  useEffect(() => {
    // Stub имитация AI подсказки по вводу
    if (!query) {
      setAiSuggestion("петля 110 плавное закрытие")
    } else if (query.length > 12) {
      setAiSuggestion(undefined)
    } else {
      setAiSuggestion("добавить мягкое закрывание")
    }
  }, [query])

  useEffect(() => {
    try {
      const raw = localStorage.getItem('hardware:savedQueries')
      if (raw) setSavedQueries(JSON.parse(raw))
    } catch {}
  }, [])

  const saveCurrentQuery = () => {
    if (!query.trim()) return
    setSavedQueries(prev => {
      const next = Array.from(new Set([query.trim(), ...prev])).slice(0,10)
      try { localStorage.setItem('hardware:savedQueries', JSON.stringify(next)) } catch {}
      return next
    })
  }

  const removeQuery = (q: string) => {
    setSavedQueries(prev => {
      const next = prev.filter(x => x !== q)
      try { localStorage.setItem('hardware:savedQueries', JSON.stringify(next)) } catch {}
      return next
    })
  }

  const handleSelectItem = (item: HardwareItem) => {
    setSelectedItems(prev => 
      prev.find(i => i.sku === item.sku) 
        ? prev.filter(i => i.sku !== item.sku) 
        : [...prev, item]
    );
  };

  const isSelected = (item: HardwareItem) => !!selectedItems.find(i => i.sku === item.sku);

  const filtered = hardwareItems.filter(item => {
    const c = item.aiExplanation.confidence
    if (c < confidenceRange[0] || c > confidenceRange[1]) return false
    if (query) {
      const q = query.toLowerCase()
      if (!(
        item.name.toLowerCase().includes(q) ||
        item.sku.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q)
      )) return false
    }
    return true
  })

  return (
    <div className="p-6 w-full">
      <div className="flex justify-between items-center mb-6 flex-wrap gap-4">
        <h1 className="text-3xl font-bold">Подбор фурнитуры</h1>
        <div className="flex items-center gap-2">
          <Button onClick={() => setIsModalOpen(true)} disabled={selectedItems.length < 2}>
            Сравнить выбранное ({selectedItems.length})
          </Button>
        </div>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="Поиск по названию, SKU или параметрам..." className="pl-10" />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={saveCurrentQuery}>Сохранить</Button>
        </div>
      </div>

      {savedQueries.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2 text-xs">
          {savedQueries.map(q => (
            <button key={q} onClick={()=>setQuery(q)} className="px-2 py-1 rounded border bg-background hover:bg-muted transition relative group">
              {q}
              <span onClick={(e)=>{e.stopPropagation(); removeQuery(q)}} className="ml-2 opacity-0 group-hover:opacity-100 text-muted-foreground cursor-pointer">×</span>
            </button>
          ))}
        </div>
      )}

      <div className="mb-8">
        <HardwareAdvancedFilters
          confidenceRange={confidenceRange}
          onConfidenceChange={setConfidenceRange}
          query={query}
          onQueryChange={setQuery}
          aiSuggestion={aiSuggestion}
          onApplySuggestion={() => aiSuggestion && setQuery(q => q ? `${q} ${aiSuggestion}` : aiSuggestion)}
        />
      </div>

      {aiSuggestion && (
        <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground"><Sparkles className="h-4 w-4 text-primary"/> AI подсказка активна</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((item) => (
          <Card key={item.sku} className={`flex flex-col ${isSelected(item) ? 'border-primary' : ''}`}>
            <CardHeader>
              <img src={item.imageUrl} alt={item.name} className="rounded-lg mb-4 h-40 w-full object-cover" />
              <CardTitle>{item.name}</CardTitle>
              <CardDescription>{item.sku}</CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="mb-4 text-sm">{item.description}</p>
              <AiExplanation {...item.aiExplanation} />
            </CardContent>
            <div className="p-6 pt-0">
                <Button variant={isSelected(item) ? "secondary" : "outline"} className="w-full" onClick={() => handleSelectItem(item)}>
                  {isSelected(item) ? "Убрать из сравнения" : "Добавить к сравнению"}
                </Button>
            </div>
          </Card>
        ))}
      </div>
      <HardwareComparisonModal items={selectedItems} open={isModalOpen} onOpenChange={setIsModalOpen} />
    </div>
  )
}

