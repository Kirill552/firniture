"use client";

import { useRef, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface DrillPoint {
  x: number;
  y: number;
  diameter: number;
  depth: number;
  layer: string;
  hardware_id: string;
  hardware_type: "hinge_cup" | "hinge_mount" | "slide";
  notes: string;
}

interface DrillPreviewProps {
  panelWidth: number;
  panelHeight: number;
  drillPoints: DrillPoint[];
  highlightedHardwareId?: string;
  onPointHover?: (point: DrillPoint | null) => void;
  className?: string;
}

// Цвета по типу отверстия (соответствуют AutoCAD ACI)
const LAYER_COLORS: Record<string, string> = {
  DRILL_V_35: "#0000FF", // Синий — чашка петли
  DRILL_V_5: "#00FFFF",  // Циан — крепёж петли
  DRILL_H_4: "#00FF00",  // Зелёный — направляющие
  DRILLING: "#0000FF",   // Legacy
};

const HARDWARE_TYPE_LABELS: Record<string, string> = {
  hinge_cup: "Чашка петли",
  hinge_mount: "Крепёж петли",
  slide: "Направляющая",
};

export function DrillPreview({
  panelWidth,
  panelHeight,
  drillPoints,
  highlightedHardwareId,
  onPointHover,
  className,
}: DrillPreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Масштаб для вписывания панели в canvas
  const getScale = useCallback(() => {
    if (!containerRef.current) return 1;
    const containerWidth = containerRef.current.clientWidth - 40; // padding
    const containerHeight = 300; // фиксированная высота
    const scaleX = containerWidth / panelWidth;
    const scaleY = containerHeight / panelHeight;
    return Math.min(scaleX, scaleY, 1); // Не увеличивать больше 1:1
  }, [panelWidth, panelHeight]);

  // Отрисовка
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const scale = getScale();
    const scaledWidth = panelWidth * scale;
    const scaledHeight = panelHeight * scale;

    // Размер canvas
    canvas.width = scaledWidth + 60; // место для размеров
    canvas.height = scaledHeight + 60;

    // Очистка
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Смещение для центрирования
    const offsetX = 30;
    const offsetY = 30;

    // Фон панели
    ctx.fillStyle = "#F5F5DC"; // Бежевый (цвет ЛДСП)
    ctx.fillRect(offsetX, offsetY, scaledWidth, scaledHeight);

    // Контур панели
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 2;
    ctx.strokeRect(offsetX, offsetY, scaledWidth, scaledHeight);

    // Отрисовка отверстий
    for (const point of drillPoints) {
      const x = offsetX + point.x * scale;
      // Y инвертируем (canvas Y вниз, DXF Y вверх)
      const y = offsetY + scaledHeight - point.y * scale;
      const radius = (point.diameter * scale) / 2;

      // Цвет по слою
      const color = LAYER_COLORS[point.layer] || "#0000FF";

      // Подсветка при hover
      const isHighlighted = highlightedHardwareId &&
        point.hardware_id.startsWith(highlightedHardwareId);

      ctx.beginPath();
      ctx.arc(x, y, Math.max(radius, 3), 0, Math.PI * 2);

      if (isHighlighted) {
        ctx.fillStyle = "#FFD700"; // Золотой для highlight
        ctx.strokeStyle = "#FF0000";
        ctx.lineWidth = 3;
      } else {
        ctx.fillStyle = color;
        ctx.strokeStyle = "#000";
        ctx.lineWidth = 1;
      }

      ctx.fill();
      ctx.stroke();
    }

    // Размеры панели
    ctx.fillStyle = "#333";
    ctx.font = "12px Arial";
    ctx.textAlign = "center";

    // Ширина (снизу)
    ctx.fillText(
      `${panelWidth} мм`,
      offsetX + scaledWidth / 2,
      offsetY + scaledHeight + 20
    );

    // Высота (слева, повёрнуто)
    ctx.save();
    ctx.translate(15, offsetY + scaledHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(`${panelHeight} мм`, 0, 0);
    ctx.restore();
  }, [panelWidth, panelHeight, drillPoints, highlightedHardwareId, getScale]);

  // Перерисовка при изменении данных
  useEffect(() => {
    draw();
  }, [draw]);

  // Обработка hover
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!onPointHover || !canvasRef.current) return;

      const canvas = canvasRef.current;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const scale = getScale();
      const offsetX = 30;
      const offsetY = 30;
      const scaledHeight = panelHeight * scale;

      // Найти точку под курсором
      for (const point of drillPoints) {
        const px = offsetX + point.x * scale;
        const py = offsetY + scaledHeight - point.y * scale;
        const radius = Math.max((point.diameter * scale) / 2, 5);

        const distance = Math.sqrt((x - px) ** 2 + (y - py) ** 2);
        if (distance <= radius + 5) {
          onPointHover(point);
          return;
        }
      }

      onPointHover(null);
    },
    [drillPoints, panelHeight, getScale, onPointHover]
  );

  return (
    <Card className={className}>
      <CardHeader className="py-3">
        <CardTitle className="text-sm font-medium">Превью присадки</CardTitle>
      </CardHeader>
      <CardContent className="p-4" ref={containerRef}>
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => onPointHover?.(null)}
          className="border rounded cursor-crosshair"
        />

        {/* Легенда */}
        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: LAYER_COLORS.DRILL_V_35 }}
            />
            <span>Чашка петли ø35</span>
          </div>
          <div className="flex items-center gap-1">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: LAYER_COLORS.DRILL_V_5 }}
            />
            <span>Крепёж ø5</span>
          </div>
          <div className="flex items-center gap-1">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: LAYER_COLORS.DRILL_H_4 }}
            />
            <span>Направляющие ø4</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
