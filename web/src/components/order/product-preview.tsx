"use client"

import { Minus, Plus } from "lucide-react"
import { ModuleDrawing, type ModuleShape } from "./module-drawing"
import { WallStrip } from "./wall-strip"

/**
 * «Пирог» — что получится, до того как считать технологию.
 *
 * Технолог просил показывать сборку перед генерацией: шкаф с размерами,
 * полками и ножками, и возможность добавить недостающее прямо здесь.
 */

interface ProductPreviewProps {
  modules: ModuleShape[]
  wallWidth: number
  selectedIndex: number
  onSelect: (index: number) => void
  onChange: (index: number, patch: Partial<ModuleShape>) => void
}

interface CounterProps {
  label: string
  value: number
  min?: number
  max?: number
  step?: number
  suffix?: string
  onChange: (value: number) => void
}

function Counter({ label, value, min = 0, max = 12, step = 1, suffix, onChange }: CounterProps) {
  const dec = () => onChange(Math.max(min, value - step))
  const inc = () => onChange(Math.min(max, value + step))
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[#d7dde2] bg-white px-3 py-2">
      <span className="text-xs font-medium text-[#171a1d]">{label}</span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={dec}
          disabled={value <= min}
          aria-label={`${label}: убрать`}
          className="flex h-7 w-7 items-center justify-center rounded-md border border-[#d7dde2] text-[#171a1d] transition-colors duration-150 hover:border-[#66707a] disabled:opacity-40 disabled:hover:border-[#d7dde2] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#171a1d]"
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <span className="min-w-[3.5rem] text-center text-xs tabular-nums text-[#171a1d]">
          {value}
          {suffix ? ` ${suffix}` : ""}
        </span>
        <button
          type="button"
          onClick={inc}
          disabled={value >= max}
          aria-label={`${label}: добавить`}
          className="flex h-7 w-7 items-center justify-center rounded-md border border-[#d7dde2] text-[#171a1d] transition-colors duration-150 hover:border-[#66707a] disabled:opacity-40 disabled:hover:border-[#d7dde2] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#171a1d]"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}

export function ProductPreview({
  modules,
  wallWidth,
  selectedIndex,
  onSelect,
  onChange,
}: ProductPreviewProps) {
  if (modules.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#d7dde2] bg-[#f3f6f8] px-4 py-8 text-center">
        <p className="text-sm font-medium text-[#171a1d]">Пока нечего показывать</p>
        <p className="mt-1 text-xs text-[#66707a]">
          Добавьте модуль — покажем сборку с размерами до расчёта
        </p>
      </div>
    )
  }

  const index = Math.min(selectedIndex, modules.length - 1)
  const current = modules[index]
  const isFloor = current.type !== "wall"

  return (
    <div className="space-y-4" data-testid="product-preview">
      {modules.length > 1 && (
        <WallStrip
          modules={modules}
          wallWidth={wallWidth}
          selectedIndex={index}
          onSelect={onSelect}
        />
      )}

      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_260px]">
        <div className="rounded-lg border border-[#d7dde2] bg-white p-4">
          <div className="mb-2 flex items-baseline justify-between">
            <span className="text-sm font-semibold text-[#171a1d]">{current.label}</span>
            {modules.length > 1 && (
              <span className="text-xs text-[#66707a]">
                модуль {index + 1} из {modules.length}
              </span>
            )}
          </div>
          <div className="flex justify-center">
            <ModuleDrawing module={current} className="h-[340px] w-auto max-w-full" />
          </div>
        </div>

        <div className="space-y-2">
          <Counter
            label="Полки"
            value={current.shelves}
            max={8}
            onChange={(v) => onChange(index, { shelves: v })}
          />
          <Counter
            label="Фасады"
            value={current.doors}
            max={4}
            onChange={(v) => onChange(index, { doors: v })}
          />
          {isFloor && (
            <Counter
              label="Ножки"
              value={current.legs}
              max={200}
              step={10}
              suffix="мм"
              onChange={(v) => onChange(index, { legs: v })}
            />
          )}
          <p className="px-1 pt-1 text-[11px] leading-relaxed text-[#66707a]">
            {isFloor
              ? `Высота до столешницы ${current.height + current.legs} мм`
              : "Навесной модуль — ножек нет"}
          </p>
        </div>
      </div>
    </div>
  )
}
