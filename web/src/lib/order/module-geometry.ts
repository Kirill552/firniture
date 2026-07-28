/**
 * Геометрия пирога: как модули ложатся в габарит стены и как делится корпус.
 *
 * Вынесено из компонентов, потому что это арифметика цеха, а не отрисовка:
 * ошибка здесь означает неверную подсказку про щелевую планку или фасад,
 * который не встанет.
 */

export interface WallFit {
  /** Суммарная ширина модулей, мм */
  modulesWidth: number
  /** Свободное место по габариту: положительное — остаток, отрицательное — перелёт */
  remainder: number
  status: "fits" | "gap" | "overflow"
}

export function wallFit(moduleWidths: number[], wallWidth: number): WallFit {
  const modulesWidth = moduleWidths.reduce((sum, width) => sum + width, 0)
  const remainder = wallWidth - modulesWidth
  const status: WallFit["status"] = remainder === 0 ? "fits" : remainder > 0 ? "gap" : "overflow"
  return { modulesWidth, remainder, status }
}

/**
 * Ширина одной створки накладного фасада.
 *
 * Зазор общий на корпус: он же по краям, он же между створками. Корпус 600
 * при зазоре 4 даёт одну створку 596 или две по 298 — так же считает бэкенд.
 */
export function facadeWidth(bodyWidth: number, doors: number, gap: number): number {
  if (doors <= 0) return 0
  return (bodyWidth - gap) / doors
}

/**
 * Высоты полок внутри корпуса: делят внутреннее пространство поровну.
 * Возвращает смещения от верха внутреннего проёма.
 */
export function shelfOffsets(innerHeight: number, shelves: number): number[] {
  if (shelves <= 0 || innerHeight <= 0) return []
  return Array.from({ length: shelves }, (_, i) => (innerHeight * (i + 1)) / (shelves + 1))
}
