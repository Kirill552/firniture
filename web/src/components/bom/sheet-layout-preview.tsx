"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertTriangle, Lightbulb, Layers } from "lucide-react"
import type { BOMPanel } from "@/types/api"

interface SheetLayoutPreviewProps {
  panels: BOMPanel[]
  sheetWidth?: number // мм
  sheetHeight?: number // мм
  showCombineSuggestion?: boolean
}

interface PlacedPanel {
  panel: BOMPanel
  x: number
  y: number
  rotated: boolean
}

// Простой жадный алгоритм раскладки панелей
function packPanels(
  panels: BOMPanel[],
  sheetWidth: number,
  sheetHeight: number
): PlacedPanel[] {
  const placed: PlacedPanel[] = []
  const remaining = [...panels].sort(
    (a, b) => b.width_mm * b.height_mm - a.width_mm * a.height_mm
  )

  // Простая раскладка: слева направо, снизу вверх
  let currentX = 0
  let currentY = 0
  let rowHeight = 0

  for (const panel of remaining) {
    const w = panel.width_mm
    const h = panel.height_mm

    // Пробуем разместить без поворота
    if (currentX + w <= sheetWidth && currentY + h <= sheetHeight) {
      placed.push({ panel, x: currentX, y: currentY, rotated: false })
      currentX += w + 5 // 5мм зазор
      rowHeight = Math.max(rowHeight, h)
    }
    // Пробуем с поворотом
    else if (currentX + h <= sheetWidth && currentY + w <= sheetHeight) {
      placed.push({ panel, x: currentX, y: currentY, rotated: true })
      currentX += h + 5
      rowHeight = Math.max(rowHeight, w)
    }
    // Переходим на новый ряд
    else if (currentX > 0) {
      currentX = 0
      currentY += rowHeight + 5
      rowHeight = 0

      if (currentX + w <= sheetWidth && currentY + h <= sheetHeight) {
        placed.push({ panel, x: currentX, y: currentY, rotated: false })
        currentX += w + 5
        rowHeight = Math.max(rowHeight, h)
      } else if (currentX + h <= sheetWidth && currentY + w <= sheetHeight) {
        placed.push({ panel, x: currentX, y: currentY, rotated: true })
        currentX += h + 5
        rowHeight = Math.max(rowHeight, w)
      }
    }
  }

  return placed
}

// Генерируем цвет для панели (пастельные тона)
const panelColors = [
  "rgb(219, 234, 254)", // blue-100
  "rgb(220, 252, 231)", // green-100
  "rgb(254, 249, 195)", // yellow-100
  "rgb(254, 226, 226)", // red-100
  "rgb(233, 213, 255)", // purple-100
  "rgb(254, 215, 170)", // orange-100
  "rgb(204, 251, 241)", // teal-100
  "rgb(252, 231, 243)", // pink-100
]

export function SheetLayoutPreview({
  panels,
  sheetWidth = 2800,
  sheetHeight = 2070,
  showCombineSuggestion = true,
}: SheetLayoutPreviewProps) {
  // Расчёт площадей
  const totalPanelArea = panels.reduce(
    (sum, p) => sum + (p.width_mm * p.height_mm) / 1_000_000,
    0
  )
  const sheetArea = (sheetWidth * sheetHeight) / 1_000_000
  const utilization = sheetArea > 0 ? (totalPanelArea / sheetArea) * 100 : 0

  // Раскладка панелей
  const placedPanels = useMemo(
    () => packPanels(panels, sheetWidth, sheetHeight),
    [panels, sheetWidth, sheetHeight]
  )

  // Масштаб для отображения (чтобы вписать в контейнер)
  const scale = 0.12 // ~336x248 px для стандартного листа
  const displayWidth = sheetWidth * scale
  const displayHeight = sheetHeight * scale

  // Определяем статус использования
  const isLowUtilization = utilization < 50
  const isVeryLowUtilization = utilization < 30

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Layers className="h-4 w-4" />
          Раскладка на листе
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Визуализация листа */}
        <div className="flex gap-10">
          {/* Лист с панелями */}
          <div className="relative">
            <div
              className="relative bg-stone-100 dark:bg-stone-800 border-2 border-stone-300 dark:border-stone-600 rounded"
              style={{
                width: displayWidth,
                height: displayHeight,
              }}
            >
              {/* Размеры листа */}
              <div className="absolute -top-5 left-0 right-0 text-center text-xs text-muted-foreground">
                {sheetWidth} мм
              </div>
              <div
                className="absolute top-1/2 -translate-y-1/2 -right-5 text-xs text-muted-foreground"
                style={{ writingMode: "vertical-rl" }}
              >
                {sheetHeight} мм
              </div>

              {/* Панели */}
              {placedPanels.map((placed, index) => {
                const w = placed.rotated
                  ? placed.panel.height_mm
                  : placed.panel.width_mm
                const h = placed.rotated
                  ? placed.panel.width_mm
                  : placed.panel.height_mm

                return (
                  <div
                    key={placed.panel.id || index}
                    className="absolute border border-stone-400 dark:border-stone-500 rounded-sm overflow-hidden flex items-center justify-center"
                    style={{
                      left: placed.x * scale,
                      top: placed.y * scale,
                      width: w * scale - 1,
                      height: h * scale - 1,
                      backgroundColor: panelColors[index % panelColors.length],
                    }}
                    title={`${placed.panel.name}: ${placed.panel.width_mm}×${placed.panel.height_mm} мм`}
                  >
                    {/* Название панели (если помещается) */}
                    {w * scale > 40 && h * scale > 20 && (
                      <span className="text-[8px] text-stone-600 dark:text-stone-300 truncate px-1">
                        {placed.panel.name}
                      </span>
                    )}
                  </div>
                )
              })}

              {/* Пустое место */}
              {panels.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
                  Нет панелей
                </div>
              )}
            </div>
          </div>

          {/* Статистика */}
          <div className="flex-1 space-y-3 ml-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-muted-foreground">Площадь панелей</div>
                <div className="font-medium">{totalPanelArea.toFixed(2)} м²</div>
              </div>
              <div>
                <div className="text-muted-foreground">Площадь листа</div>
                <div className="font-medium">{sheetArea.toFixed(2)} м²</div>
              </div>
              <div>
                <div className="text-muted-foreground">Использование</div>
                <div
                  className={`font-medium ${
                    isVeryLowUtilization
                      ? "text-red-600"
                      : isLowUtilization
                        ? "text-amber-600"
                        : "text-green-600"
                  }`}
                >
                  {utilization.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">Количество</div>
                <div className="font-medium">{panels.length} шт</div>
              </div>
            </div>

            {/* Легенда */}
            {panels.length > 0 && (
              <div className="pt-2 border-t space-y-1">
                <div className="text-xs text-muted-foreground mb-1">Панели:</div>
                <div className="flex flex-wrap gap-1">
                  {panels.slice(0, 6).map((panel, index) => (
                    <div
                      key={panel.id || index}
                      className="flex items-center gap-1 text-xs"
                    >
                      <div
                        className="w-3 h-3 rounded-sm border border-stone-400"
                        style={{
                          backgroundColor: panelColors[index % panelColors.length],
                        }}
                      />
                      <span className="truncate max-w-[80px]">{panel.name}</span>
                    </div>
                  ))}
                  {panels.length > 6 && (
                    <span className="text-xs text-muted-foreground">
                      +{panels.length - 6}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Предупреждение о низком использовании */}
        {showCombineSuggestion && isLowUtilization && panels.length > 0 && (
          <Alert variant={isVeryLowUtilization ? "destructive" : "default"}>
            {isVeryLowUtilization ? (
              <AlertTriangle className="h-4 w-4" />
            ) : (
              <Lightbulb className="h-4 w-4" />
            )}
            <AlertTitle>
              {isVeryLowUtilization
                ? "Очень низкое использование листа"
                : "Низкое использование листа"}
            </AlertTitle>
            <AlertDescription>
              {isVeryLowUtilization ? (
                <>
                  Используется только <strong>{utilization.toFixed(0)}%</strong>{" "}
                  листа. Рекомендуем объединить этот заказ с другими похожими
                  заказами для экономии материала. Остаток листа (
                  {((1 - utilization / 100) * sheetArea).toFixed(2)} м²) можно
                  использовать для небольших деталей.
                </>
              ) : (
                <>
                  Используется <strong>{utilization.toFixed(0)}%</strong> листа.
                  Если есть другие заказы из того же материала, можно объединить
                  раскрой для экономии.
                </>
              )}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
