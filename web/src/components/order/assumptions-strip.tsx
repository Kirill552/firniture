"use client"

import Link from "next/link"
import { Info } from "lucide-react"

/**
 * Из чего посчитано. Строка стоит под чертежом, до генерации технологии.
 *
 * Часть значений — отраслевая норма, часть — привычка цеха, на котором мы
 * обкатываем расчёт. Мастер должен увидеть чужое до того, как получит
 * спецификацию, а не после. Страницу настроек открывают единицы, пирог видят все.
 */

export interface ShopStandards {
  bottom_mount?: string
  tie_beam_height_mm?: number
  shelf_gap_mm?: number
  facade_gap_mm?: number
  fastener_type?: string
  hardware_mount?: string
}

const BOTTOM_MOUNT_LABEL: Record<string, string> = {
  on_bottom: "Боковины на дне",
  inset: "Дно вкладное",
}

const FASTENER_LABEL: Record<string, string> = {
  confirmat: "Конфирмат",
  dowel: "Шкант",
}

export function AssumptionsStrip({ standards }: { standards: ShopStandards | null }) {
  if (!standards) return null

  const chips = [
    BOTTOM_MOUNT_LABEL[standards.bottom_mount ?? "on_bottom"],
    standards.tie_beam_height_mm ? `Планка ${standards.tie_beam_height_mm} мм` : null,
    standards.shelf_gap_mm != null
      ? `Полка −${String(standards.shelf_gap_mm).replace(".", ",")} мм на сторону`
      : null,
    standards.facade_gap_mm ? `Зазор фасада ${standards.facade_gap_mm} мм` : null,
    FASTENER_LABEL[standards.fastener_type ?? "confirmat"],
    standards.hardware_mount === "euro_screw" ? "Планки на евровинт" : "Планки на саморезы",
  ].filter(Boolean) as string[]

  return (
    <div className="rounded-lg border border-[#d7dde2] bg-[#f3f6f8] px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
        <Info className="h-3.5 w-3.5 shrink-0 text-[#66707a]" aria-hidden />
        <span className="text-xs font-medium text-[#171a1d]">Считаем так:</span>
        {chips.map((chip) => (
          <span
            key={chip}
            className="rounded-md border border-[#d7dde2] bg-white px-2 py-0.5 text-[11px] text-[#171a1d]"
          >
            {chip}
          </span>
        ))}
      </div>
      <p className="mt-1.5 text-[11px] leading-relaxed text-[#66707a]">
        Это типовая практика, а не единственно верный способ.{" "}
        <Link
          href="/settings"
          className="font-medium text-[#171a1d] underline underline-offset-2 hover:text-[#66707a]"
        >
          Поменяйте под свой цех
        </Link>{" "}
        — расчёт пересчитается по вашим правилам.
      </p>
    </div>
  )
}
