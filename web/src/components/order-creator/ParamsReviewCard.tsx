// web/src/components/order-creator/ParamsReviewCard.tsx
"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, MessageSquare, AlertTriangle } from "lucide-react";
import { FieldWithSource } from "./FieldWithSource";
import type { FieldSource, OrderCreatorParams } from "@/types/api";

const CABINET_TYPES = [
  { value: "wall", label: "Навесной шкаф" },
  { value: "base", label: "Напольная тумба" },
  { value: "base_sink", label: "Тумба под мойку" },
  { value: "drawer", label: "Тумба с ящиками" },
  { value: "tall", label: "Пенал" },
];

const MATERIALS = [
  { value: "ЛДСП", label: "ЛДСП" },
  { value: "МДФ", label: "МДФ" },
  { value: "Фанера", label: "Фанера" },
];

const THICKNESSES = [
  { value: "16", label: "16 мм" },
  { value: "18", label: "18 мм" },
  { value: "22", label: "22 мм" },
];

interface ParamsReviewCardProps {
  params: Partial<OrderCreatorParams>;
  fieldSources: Record<string, FieldSource>;
  recognizedCount: number;
  onUpdateParam: (key: keyof OrderCreatorParams, value: unknown) => void;
  onConfirm: () => void;
  onOpenClarify: () => void;
  isLoading: boolean;
}

export function ParamsReviewCard({
  params,
  fieldSources,
  recognizedCount,
  onUpdateParam,
  onConfirm,
  onOpenClarify,
  isLoading,
}: ParamsReviewCardProps) {
  const defaultCount = Object.values(fieldSources).filter((s) => s === "default").length;
  const hasDefaults = defaultCount > 0;

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Параметры изделия</CardTitle>
          <Badge variant={hasDefaults ? "outline" : "default"} className="gap-1">
            {hasDefaults && <AlertTriangle className="h-3 w-3" />}
            Распознано: {recognizedCount} полей
          </Badge>
        </div>
        {hasDefaults && (
          <p className="text-sm text-amber-600">
            {defaultCount} поле(й) не распознано — проверьте или уточните через AI
          </p>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Тип изделия */}
        <FieldWithSource
          label="Тип изделия"
          value={params.cabinet_type}
          source={fieldSources.furniture_type}
          onChange={(v) => onUpdateParam("cabinet_type", v)}
          type="select"
          options={CABINET_TYPES}
          placeholder="Выберите тип"
        />

        {/* Размеры */}
        <div className="grid grid-cols-3 gap-3">
          <FieldWithSource
            label="Ширина"
            value={params.width_mm}
            source={fieldSources.width_mm}
            onChange={(v) => onUpdateParam("width_mm", v)}
            type="number"
            unit="мм"
            min={100}
            max={3000}
          />
          <FieldWithSource
            label="Высота"
            value={params.height_mm}
            source={fieldSources.height_mm}
            onChange={(v) => onUpdateParam("height_mm", v)}
            type="number"
            unit="мм"
            min={100}
            max={3000}
          />
          <FieldWithSource
            label="Глубина"
            value={params.depth_mm}
            source={fieldSources.depth_mm}
            onChange={(v) => onUpdateParam("depth_mm", v)}
            type="number"
            unit="мм"
            min={100}
            max={1200}
          />
        </div>

        {/* Материал */}
        <div className="grid grid-cols-2 gap-3">
          <FieldWithSource
            label="Материал"
            value={params.material}
            source={fieldSources.material}
            onChange={(v) => onUpdateParam("material", v)}
            type="select"
            options={MATERIALS}
          />
          <FieldWithSource
            label="Толщина"
            value={String(params.thickness_mm)}
            source={fieldSources.thickness_mm}
            onChange={(v) => onUpdateParam("thickness_mm", parseInt(String(v)))}
            type="select"
            options={THICKNESSES}
          />
        </div>

        {/* Кнопки */}
        <div className="flex gap-2 pt-2">
          <Button
            variant="outline"
            onClick={onOpenClarify}
            className="gap-2"
          >
            <MessageSquare className="h-4 w-4" />
            Уточнить с AI
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isLoading}
            className="flex-1 gap-2"
          >
            <Check className="h-4 w-4" />
            {isLoading ? "Создаём заказ..." : "Рассчитать деталировку"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
