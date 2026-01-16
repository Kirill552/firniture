"use client"

import * as React from "react"
import { CalendarIcon, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export interface DateRange {
  from: string | undefined // формат YYYY-MM-DD
  to: string | undefined
}

interface DateRangeFilterProps {
  value: DateRange | undefined
  onChange: (value: DateRange | undefined) => void
  placeholder?: string
}

export function DateRangeFilter({ value, onChange, placeholder = "Фильтр по дате" }: DateRangeFilterProps) {
  const [open, setOpen] = React.useState(false)
  const [tempFrom, setTempFrom] = React.useState("")
  const [tempTo, setTempTo] = React.useState("")

  // Синхронизируем temp значения при открытии
  React.useEffect(() => {
    if (open) {
      setTempFrom(value?.from ?? "")
      setTempTo(value?.to ?? "")
    }
  }, [open, value?.from, value?.to])

  const handleApply = () => {
    onChange({
      from: tempFrom || undefined,
      to: tempTo || undefined,
    })
    setOpen(false)
  }

  const handleClear = () => {
    onChange(undefined)
    setTempFrom("")
    setTempTo("")
    setOpen(false)
  }

  const formatDisplayDate = () => {
    if (!value?.from && !value?.to) return placeholder
    if (value?.from && value?.to) return `${value.from} — ${value.to}`
    if (value?.from) return `с ${value.from}`
    if (value?.to) return `до ${value.to}`
    return placeholder
  }

  const hasValue = value?.from || value?.to

  return (
    <div className="flex items-center gap-1">
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className={hasValue ? "text-foreground" : "text-muted-foreground"}
          >
            <CalendarIcon className="h-4 w-4 mr-2" />
            {formatDisplayDate()}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="p-4 w-auto">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">От</label>
              <input
                type="date"
                value={tempFrom}
                onChange={(e) => setTempFrom(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">До</label>
              <input
                type="date"
                value={tempTo}
                onChange={(e) => setTempTo(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleClear}
                className="flex-1"
              >
                Сбросить
              </Button>
              <Button
                size="sm"
                onClick={handleApply}
                className="flex-1"
              >
                Применить
              </Button>
            </div>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      {hasValue && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onChange(undefined)}
          aria-label="Сбросить дату"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}
