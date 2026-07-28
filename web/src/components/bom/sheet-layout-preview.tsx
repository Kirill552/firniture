"use client"

import { useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertTriangle, Layers, Loader2, Sparkles } from "lucide-react"
import type { BOMPanel, PlacedPanelInfo } from "@/types/api"
import { useLayoutPreview } from "@/hooks/use-api"

interface SheetLayoutPreviewProps {
  panels: BOMPanel[]
  sheetWidth?: number // мм
  sheetHeight?: number // мм
  gap?: number // мм — зазор на пропил
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
  gap = 4,
}: SheetLayoutPreviewProps) {

  // Вызываем API для раскладки
  const layoutMutation = useLayoutPreview()

  // Запрашиваем раскладку при изменении панелей
  useEffect(() => {
    if (panels.length === 0) return

    layoutMutation.mutate({
      panels: panels.map((p) => ({
        name: p.name,
        width_mm: p.width_mm,
        height_mm: p.height_mm,
      })),
      sheet_width_mm: sheetWidth,
      sheet_height_mm: sheetHeight,
      gap_mm: gap,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [panels, sheetWidth, sheetHeight, gap])

  // Прокручиваем контейнер вправо при загрузке

  // Данные из API или fallback
  const placedPanels: PlacedPanelInfo[] = layoutMutation.data?.placed_panels ?? []
  const unplacedPanels: string[] = layoutMutation.data?.unplaced_panels ?? []
  const utilization = layoutMutation.data?.utilization_percent ?? 0
  const layoutMethod = layoutMutation.data?.layout_method ?? "—"

  // Расчёт площадей
  const totalPanelArea = panels.reduce(
    (sum, p) => sum + (p.width_mm * p.height_mm) / 1_000_000,
    0
  )
  const sheetArea = (sheetWidth * sheetHeight) / 1_000_000

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Layers className="h-4 w-4" />
          Раскладка на листе
          {layoutMutation.isPending && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Визуализация — flex column на мобильных, row на десктопе */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Лист с панелями */}
          <div className="flex-1 min-w-0">
            <div className="relative border-2 border-stone-300 dark:border-stone-600 bg-stone-100 dark:bg-stone-800 w-full overflow-hidden">
              {panels.length === 0 ? (
                <div className="flex items-center justify-center text-muted-foreground text-sm h-[300px]">
                  Нет панелей
                </div>
              ) : (
                <svg
                  viewBox={`0 0 ${sheetWidth} ${sheetHeight}`}
                  preserveAspectRatio="xMidYMid meet"
                  className="w-full h-auto"
                >
                  {/* Панели */}
                  {placedPanels.map((placed, index) => {
                    const x = placed.x
                    const y = sheetHeight - placed.y - placed.height_mm
                    const w = placed.width_mm
                    const h = placed.height_mm
                    const color = panelColors[index % panelColors.length]
                    const fontSize = Math.min(w / (placed.name.length * 0.6), h * 0.3, 50)

                    return (
                      <g key={`${placed.name}-${index}`}>
                        <title>{`${placed.name}: ${placed.width_mm}×${placed.height_mm} мм${placed.rotated ? " (повёрнута)" : ""}`}</title>
                        <rect
                          x={x}
                          y={y}
                          width={w}
                          height={h}
                          fill={color}
                          stroke="rgb(120, 113, 108)" // stone-500
                          strokeWidth="1.5"
                        />
                        {w > 120 && h > 80 && fontSize >= 16 && (
                          <text
                            x={x + w / 2}
                            y={y + h / 2}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={fontSize}
                            className="fill-stone-700 dark:fill-stone-200 font-medium select-none pointer-events-none"
                          >
                            {placed.name}
                          </text>
                        )}
                      </g>
                    )
                  })}
                </svg>
              )}

              {/* Индикатор загрузки */}
              {layoutMutation.isPending && panels.length > 0 && (
                <div className="absolute inset-0 flex items-center justify-center bg-stone-100/50 dark:bg-stone-800/50">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>
            {/* Текстовая подпись габаритов листа */}
            <div className="text-center text-xs text-muted-foreground mt-2 font-medium">
              Лист ЛДСП: {sheetWidth} × {sheetHeight} мм
            </div>
          </div>

          {/* Статистика */}
          <div className="flex-1 min-w-[180px] space-y-3">
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
                <div className="text-muted-foreground">Заполнение</div>
                <div className="font-medium">{utilization.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-muted-foreground">Размещено</div>
                <div className="font-medium">
                  {placedPanels.length} / {panels.length} шт
                </div>
              </div>
            </div>

            {/* Метод раскладки */}
            <div className="text-xs text-muted-foreground">
              Алгоритм: {layoutMethod === "guillotine" ? "Гильотина" : layoutMethod}
            </div>

            {/* Неразмещённые панели */}
            {unplacedPanels.length > 0 && (
              <Alert variant="destructive" className="py-2">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle className="text-sm">Не поместились</AlertTitle>
                <AlertDescription className="text-xs">
                  {unplacedPanels.join(", ")}
                </AlertDescription>
              </Alert>
            )}

            {/* Легенда */}
            {panels.length > 0 && panels.length <= 8 && (
              <div className="pt-2 border-t space-y-1">
                <div className="text-xs text-muted-foreground mb-1">Панели:</div>
                <div className="flex flex-wrap gap-1">
                  {panels.map((panel, index) => (
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
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Информация о пакетном раскрое */}
        {panels.length > 0 && !layoutMutation.isPending && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground border rounded-md p-3 bg-muted/30">
            <Sparkles className="h-4 w-4 shrink-0" />
            <span>
              Пакетный раскрой нескольких заказов — <strong>скоро</strong>. Объединяйте заказы для экономии материала.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
