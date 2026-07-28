"use client"

import { wallFit } from "@/lib/order/module-geometry"
import type { ModuleShape } from "./module-drawing"

/**
 * Ряд модулей в масштабе стены. Ширина блока пропорциональна ширине модуля,
 * поэтому мастер видит компоновку, а не список. Остаток по габариту показан
 * тем же масштабом — это место под щелевую планку.
 */

interface WallStripProps {
  modules: ModuleShape[]
  wallWidth: number
  selectedIndex: number
  onSelect: (index: number) => void
}

const SHORT_LABEL: Record<string, string> = {
  wall: "Навесной",
  base: "Тумба",
  base_sink: "Мойка",
  drawer: "Ящики",
  tall: "Пенал",
}

export function WallStrip({ modules, wallWidth, selectedIndex, onSelect }: WallStripProps) {
  const { modulesWidth, remainder } = wallFit(modules.map((m) => m.width), wallWidth)
  const scaleBase = Math.max(wallWidth, modulesWidth) || 1
  const tallest = Math.max(...modules.map((m) => m.height), 1)
  return (
    <div className="space-y-2">
      <div
        className="flex items-end gap-1 rounded-lg border border-[#d7dde2] bg-[#f3f6f8] p-3"
        style={{ minHeight: 128 }}
      >
        {modules.map((module, index) => {
          const isSelected = index === selectedIndex
          return (
            <button
              key={`${module.type}-${index}`}
              type="button"
              onClick={() => onSelect(index)}
              aria-pressed={isSelected}
              title={`${module.label} ${module.width} мм`}
              className={[
                "group relative flex flex-col justify-end overflow-hidden rounded-sm border text-left",
                "transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2",
                "focus-visible:ring-[#171a1d] focus-visible:ring-offset-1",
                isSelected
                  ? "border-[#171a1d] bg-white shadow-[inset_0_-3px_0_0_#c7ff00]"
                  : "border-[#d7dde2] bg-white/70 hover:border-[#66707a]",
              ].join(" ")}
              style={{
                flexGrow: module.width,
                flexBasis: `${(module.width / scaleBase) * 100}%`,
                height: `${Math.max((module.height / tallest) * 96, 44)}px`,
              }}
              data-testid={`wall-module-${index}`}
            >
              <span
                className={[
                  "truncate px-1.5 text-[11px] font-medium leading-tight",
                  isSelected ? "text-[#171a1d]" : "text-[#66707a]",
                ].join(" ")}
              >
                {SHORT_LABEL[module.type] ?? module.label}
              </span>
              <span className="truncate px-1.5 pb-1.5 text-[11px] tabular-nums leading-tight text-[#66707a]">
                {module.width}
              </span>
            </button>
          )
        })}

        {remainder > 0 && (
          <div
            className="flex h-9 items-center justify-center rounded-sm border border-dashed border-[#66707a] bg-white/60 px-1"
            style={{ flexGrow: remainder, flexBasis: `${(remainder / scaleBase) * 100}%` }}
            data-testid="wall-remainder"
          >
            <span className="truncate text-[10px] text-[#66707a]">{remainder}</span>
          </div>
        )}
      </div>

      <div className="flex items-baseline justify-between text-xs">
        <span className="text-[#66707a]">
          Стена {wallWidth} мм · занято {modulesWidth} мм
        </span>
        {remainder > 0 && (
          <span className="font-medium text-[#171a1d]">
            Остаток {remainder} мм — закройте щелевой планкой
          </span>
        )}
        {remainder < 0 && (
          <span className="font-medium text-red-600">
            Не влезает на {Math.abs(remainder)} мм
          </span>
        )}
        {remainder === 0 && <span className="font-medium text-[#171a1d]">Стена заполнена</span>}
      </div>
    </div>
  )
}
