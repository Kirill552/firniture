"use client"
import * as React from "react"
import { CalendarIcon, X } from "lucide-react"
import { Button } from "@/components/ui/button"

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
  const from = value?.from ?? ""
  const to = value?.to ?? ""

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" onClick={() => setOpen(o => !o)} className="flex items-center gap-2">
        <CalendarIcon className="h-4 w-4" />
        {from ? (
          to ? `${from} – ${to}` : from
        ) : <span className="text-muted-foreground">{placeholder}</span>}
      </Button>
      {value && (
        <Button variant="ghost" size="icon" onClick={() => onChange(undefined)} aria-label="Сбросить дату">
            <X className="h-4 w-4" />
        </Button>
      )}
      {open && (
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={from}
            onChange={(e) => onChange({ from: e.target.value || undefined, to })}
            className="border rounded px-2 py-1 text-sm"
          />
          <span className="text-muted-foreground">—</span>
          <input
            type="date"
            value={to}
            onChange={(e) => onChange({ from, to: e.target.value || undefined })}
            className="border rounded px-2 py-1 text-sm"
          />
          <Button size="sm" variant="secondary" onClick={() => setOpen(false)}>OK</Button>
        </div>
      )}
    </div>
  )
}
