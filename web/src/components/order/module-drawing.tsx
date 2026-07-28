"use client"

/**
 * Фронтальная проекция модуля: корпус, полки, фасады, ножки и размеры.
 *
 * Чертёж, а не картинка: масштаб честный, толщина ЛДСП настоящая, размерные
 * линии как на бумаге. Мебельщик читает такую проекцию быстрее любого текста
 * и сразу видит, что программа поняла его не так.
 */

import { facadeWidth, shelfOffsets } from "@/lib/order/module-geometry"

export interface ModuleShape {
  type: string
  label: string
  width: number
  height: number
  depth: number
  shelves: number
  doors: number
  legs: number
  thickness: number
}

const INK = "#171a1d"
const MUTED = "#66707a"
const LINE = "#d7dde2"
const FACADE_FILL = "#f3f6f8"
const PAD_LEFT = 54
const PAD_BOTTOM = 40
const PAD_TOP = 22
const PAD_RIGHT = 16

/** Размерная линия со стрелками и подписью. */
function Dimension({
  x1, y1, x2, y2, label, vertical = false,
}: { x1: number; y1: number; x2: number; y2: number; label: string; vertical?: boolean }) {
  const tick = 7
  const midX = (x1 + x2) / 2
  const midY = (y1 + y2) / 2
  return (
    <g stroke={MUTED} strokeWidth={1} fill="none">
      <line x1={x1} y1={y1} x2={x2} y2={y2} />
      {vertical ? (
        <>
          <line x1={x1 - tick} y1={y1} x2={x1 + tick} y2={y1} />
          <line x1={x2 - tick} y1={y2} x2={x2 + tick} y2={y2} />
        </>
      ) : (
        <>
          <line x1={x1} y1={y1 - tick} x2={x1} y2={y1 + tick} />
          <line x1={x2} y1={y2 - tick} x2={x2} y2={y2 + tick} />
        </>
      )}
      <text
        x={vertical ? midX - 10 : midX}
        y={vertical ? midY : midY + 20}
        fill={MUTED}
        stroke="none"
        fontSize={13}
        textAnchor={vertical ? "end" : "middle"}
        dominantBaseline={vertical ? "middle" : "auto"}
        transform={vertical ? `rotate(-90 ${midX - 10} ${midY})` : undefined}
      >
        {label}
      </text>
    </g>
  )
}

export function ModuleDrawing({ module, className = "" }: { module: ModuleShape; className?: string }) {
  const { width, height, depth, shelves, doors, legs, thickness } = module
  const isFloor = module.type !== "wall"
  const legsHeight = isFloor ? legs : 0

  // Чертим не в миллиметрах: пенал 2200 мм ужал бы линии до невидимости.
  // Нормируем большую сторону в фиксированные единицы — тогда обводки,
  // размерные засечки и подписи читаются одинаково на любом модуле.
  const CANVAS = 320
  const k = CANVAS / Math.max(width, height + legsHeight)
  const mm = (value: number) => value * k

  const drawW = mm(width)
  const drawH = mm(height + legsHeight)
  const viewW = drawW + PAD_LEFT + PAD_RIGHT
  const viewH = drawH + PAD_TOP + PAD_BOTTOM

  const x0 = PAD_LEFT
  const y0 = PAD_TOP
  const wall = Math.max(mm(thickness), 3)
  const bodyW = drawW
  const bodyH = mm(height)
  const bodyBottom = y0 + bodyH

  const shelfInset = wall + Math.max(mm(12), 4)
  const innerTop = y0 + wall
  const innerHeight = bodyH - 2 * wall
  const shelfPositions = shelfOffsets(innerHeight, shelves).map((offset) => innerTop + offset)

  const facadeGap = Math.max(mm(4), 2)
  const facadeSpan = facadeWidth(bodyW, doors, facadeGap)

  return (
    <svg
      viewBox={`0 0 ${viewW} ${viewH}`}
      preserveAspectRatio="xMidYMid meet"
      className={className}
      role="img"
      aria-label={`${module.label} ${width} на ${height} на ${depth} миллиметров, полок ${shelves}, фасадов ${doors}`}
    >
      {/* Корпус: внешний контур, толщина стенки в масштабе материала */}
      <rect x={x0} y={y0} width={bodyW} height={bodyH} fill="#ffffff" stroke={INK} strokeWidth={2.5} />
      <rect
        x={x0 + wall}
        y={innerTop}
        width={bodyW - 2 * wall}
        height={innerHeight}
        fill="none"
        stroke={LINE}
        strokeWidth={1}
      />

      {/* Полки */}
      {shelfPositions.map((y, i) => (
        <line
          key={`shelf-${i}`}
          x1={x0 + shelfInset}
          y1={y}
          x2={x0 + bodyW - shelfInset}
          y2={y}
          stroke={INK}
          strokeWidth={2.5}
        />
      ))}

      {/* Фасады: штрихпунктир поверх корпуса. Створка закрывает нутро, но
          мастеру нужно видеть полки под ней, поэтому заливка почти прозрачная. */}
      {Array.from({ length: doors }, (_, i) => (
        <rect
          key={`facade-${i}`}
          x={x0 + facadeGap / 2 + i * (facadeSpan + facadeGap / Math.max(doors, 1))}
          y={y0 + facadeGap}
          width={facadeSpan - facadeGap / 2}
          height={bodyH - 2 * facadeGap}
          fill={FACADE_FILL}
          fillOpacity={0.25}
          stroke={MUTED}
          strokeWidth={1.5}
          strokeDasharray="8 4"
        />
      ))}

      {/* Ножки */}
      {legsHeight > 0 && (
        <>
          <rect x={x0 + mm(50)} y={bodyBottom} width={wall * 1.6} height={mm(legsHeight)} fill={MUTED} />
          <rect
            x={x0 + bodyW - mm(50) - wall * 1.6}
            y={bodyBottom}
            width={wall * 1.6}
            height={mm(legsHeight)}
            fill={MUTED}
          />
        </>
      )}

      {/* Размеры: ширина снизу, высота слева */}
      <Dimension
        x1={x0}
        y1={y0 + drawH + 20}
        x2={x0 + bodyW}
        y2={y0 + drawH + 20}
        label={`${width} мм`}
      />
      <Dimension
        x1={x0 - 24}
        y1={y0}
        x2={x0 - 24}
        y2={bodyBottom}
        label={`${height} мм`}
        vertical
      />
      <text x={x0 + bodyW} y={y0 - 9} fill={MUTED} fontSize={13} textAnchor="end">
        глубина {depth} мм
      </text>
    </svg>
  )
}
