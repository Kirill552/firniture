'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Settings, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type SettingsData = {
  settings: Record<string, unknown>
  defaults_used: string[]
}

type SettingsIndicatorProps = {
  /** Поля которые нужно показать */
  fields: string[]
  /** Вкладка настроек куда вести ссылку */
  targetTab?: 'factory' | 'machine' | 'materials' | 'generation'
  /** Кастомный className */
  className?: string
}

const FIELD_LABELS: Record<string, string> = {
  machine_profile: 'Станок',
  sheet_width_mm: 'Ширина листа',
  sheet_height_mm: 'Высота листа',
  thickness_mm: 'Толщина',
  edge_thickness_mm: 'Кромка',
  decor: 'Декор',
  gap_mm: 'Зазор',
  spindle_speed: 'Шпиндель',
  feed_rate_cutting: 'Подача резки',
  feed_rate_plunge: 'Подача врезания',
  cut_depth: 'Глубина',
  safe_height: 'Безопасная высота',
  tool_diameter: 'Фреза',
}

const MACHINE_LABELS: Record<string, string> = {
  weihong: 'Weihong',
  syntec: 'Syntec',
  fanuc: 'FANUC',
  dsp: 'DSP',
  homag: 'HOMAG',
}

function formatValue(field: string, value: unknown): string {
  if (value === null || value === undefined) return '—'

  if (field === 'machine_profile') {
    return MACHINE_LABELS[value as string] || String(value)
  }

  if (typeof value === 'number') {
    // Размеры листа — показываем как WxH
    if (field === 'sheet_width_mm') return `${value}`
    if (field === 'sheet_height_mm') return `${value}`
    // Остальные числа с единицами измерения
    if (field.includes('_mm')) return `${value} мм`
    if (field === 'spindle_speed') return `${value} об/мин`
    if (field.includes('feed_rate')) return `${value} мм/мин`
    return String(value)
  }

  return String(value)
}

export function SettingsIndicator({ fields, targetTab = 'generation', className }: SettingsIndicatorProps) {
  const [data, setData] = useState<SettingsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/settings')
        if (response.ok) {
          const result = await response.json()
          setData(result)
        } else {
          setError(true)
        }
      } catch {
        setError(true)
      } finally {
        setIsLoading(false)
      }
    }

    loadSettings()
  }, [])

  if (isLoading || error || !data) {
    return null
  }

  // Проверяем сколько полей из списка используют дефолты
  const fieldsWithDefaults = fields.filter(f => data.defaults_used.includes(f))
  const hasAllDefaults = fieldsWithDefaults.length === fields.length
  const hasPartialDefaults = fieldsWithDefaults.length > 0 && fieldsWithDefaults.length < fields.length
  const hasNoDefaults = fieldsWithDefaults.length === 0

  // Формируем отображаемые значения
  const displayValues: string[] = []

  // Специальная обработка для размера листа
  const hasSheetWidth = fields.includes('sheet_width_mm')
  const hasSheetHeight = fields.includes('sheet_height_mm')
  if (hasSheetWidth && hasSheetHeight) {
    const w = data.settings.sheet_width_mm
    const h = data.settings.sheet_height_mm
    displayValues.push(`Лист: ${w}×${h}`)
  } else {
    if (hasSheetWidth) displayValues.push(`Ширина: ${formatValue('sheet_width_mm', data.settings.sheet_width_mm)}`)
    if (hasSheetHeight) displayValues.push(`Высота: ${formatValue('sheet_height_mm', data.settings.sheet_height_mm)}`)
  }

  // Остальные поля
  for (const field of fields) {
    if (field === 'sheet_width_mm' || field === 'sheet_height_mm') continue
    const label = FIELD_LABELS[field] || field
    const value = formatValue(field, data.settings[field])
    displayValues.push(`${label}: ${value}`)
  }

  return (
    <div
      className={cn(
        'rounded-lg border p-3 text-sm',
        hasAllDefaults && 'bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-800',
        hasPartialDefaults && 'bg-blue-50 border-blue-200 dark:bg-blue-950/20 dark:border-blue-800',
        hasNoDefaults && 'bg-muted/50 border-border',
        className
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2 min-w-0 flex-1">
          {hasAllDefaults ? (
            <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
          ) : (
            <Settings className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          )}
          <div className="min-w-0">
            <p className={cn(
              'font-medium',
              hasAllDefaults && 'text-amber-700 dark:text-amber-400',
              hasPartialDefaults && 'text-blue-700 dark:text-blue-400',
            )}>
              {hasAllDefaults && 'Используются значения по умолчанию'}
              {hasPartialDefaults && 'Настройки фабрики + значения по умолчанию'}
              {hasNoDefaults && 'Применены настройки фабрики'}
            </p>
            <p className="text-muted-foreground truncate">
              {displayValues.join(' • ')}
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" asChild className="flex-shrink-0">
          <Link href={`/settings?tab=${targetTab}`}>
            {hasAllDefaults ? 'Настроить' : 'Изменить'}
          </Link>
        </Button>
      </div>
    </div>
  )
}
