"use client"

import * as React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Sparkles, SlidersHorizontal, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AdvancedFiltersProps {
  confidenceRange: [number, number]
  onConfidenceChange: (range: [number, number]) => void
  query: string
  onQueryChange: (q: string) => void
  aiSuggestion?: string
  onApplySuggestion: () => void
}

export function HardwareAdvancedFilters({
  confidenceRange,
  onConfidenceChange,
  query,
  onQueryChange,
  aiSuggestion,
  onApplySuggestion
}: AdvancedFiltersProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [minVal, setMinVal] = React.useState(Math.round(confidenceRange[0] * 100))
  const [maxVal, setMaxVal] = React.useState(Math.round(confidenceRange[1] * 100))

  React.useEffect(() => {
    setMinVal(Math.round(confidenceRange[0] * 100))
    setMaxVal(Math.round(confidenceRange[1] * 100))
  }, [confidenceRange])

  const applyRange = () => {
    const min = Math.min(Math.max(0, minVal), 100)
    const max = Math.min(Math.max(min, maxVal), 100)
    onConfidenceChange([min / 100, max / 100])
  }

  const hasActiveFilters = confidenceRange[0] > 0 || confidenceRange[1] < 1 || query.length > 0

  const handleReset = () => {
    onConfidenceChange([0, 1])
    onQueryChange('')
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Toggle button */}
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full justify-between"
      >
        <span className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4" />
          Расширенные фильтры
          {hasActiveFilters && (
            <span className="ml-1 rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
              активны
            </span>
          )}
        </span>
        {isOpen ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </Button>

      {/* Collapsible content */}
      <div
        className={cn(
          "overflow-hidden transition-all duration-200 ease-in-out",
          isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
        )}
      >
        <div className="p-4 border rounded-lg bg-muted/30 mt-2">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Поиск */}
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase text-muted-foreground">Поиск</label>
              <Input
                value={query}
                onChange={e => onQueryChange(e.target.value)}
                placeholder="Например: петля 110 мягкое закрывание"
              />
              {aiSuggestion && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="justify-start gap-2"
                  onClick={onApplySuggestion}
                >
                  <Sparkles className="h-4 w-4 text-primary" />
                  Подсказка: {aiSuggestion}
                </Button>
              )}
            </div>

            {/* Уверенность ИИ */}
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase text-muted-foreground">Уверенность ИИ (%)</label>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={minVal}
                  onChange={e => setMinVal(Number(e.target.value))}
                  className="w-20"
                />
                <span>—</span>
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={maxVal}
                  onChange={e => setMaxVal(Number(e.target.value))}
                  className="w-20"
                />
                <Button size="sm" variant="secondary" onClick={applyRange}>
                  OK
                </Button>
              </div>
              <div className="text-xs text-muted-foreground">
                Текущий диапазон: {confidenceRange.map(v => Math.round(v * 100)).join('%–')}%
              </div>
            </div>
          </div>

          {/* Кнопка сброса */}
          {hasActiveFilters && (
            <div className="mt-4 pt-4 border-t">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleReset}
              >
                Сбросить все фильтры
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
