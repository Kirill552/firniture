"use client";

import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Check, Pencil, AlertTriangle } from "lucide-react";
import type { ExtractedFurnitureParams } from "@/types/api";

// Упрощённые параметры для UI (плоская структура)
interface SimpleParams {
  product_type?: string;
  width?: number;
  height?: number;
  depth?: number;
  material?: string;
  thickness?: number;
  door_count?: number;
  drawer_count?: number;
  shelf_count?: number;
}

interface ExtractedParamsCardProps {
  params: ExtractedFurnitureParams;
  confidence: number;
  onConfirm: (params: SimpleParams) => void;
  isLoading?: boolean;
}

const PRODUCT_TYPES: Record<string, string> = {
  wall: "Навесной шкаф",
  base: "Напольная тумба",
  base_sink: "Тумба под мойку",
  drawer: "Тумба с ящиками",
  tall: "Пенал",
};

// Конвертер из ExtractedFurnitureParams в SimpleParams
function toSimpleParams(params: ExtractedFurnitureParams): SimpleParams {
  return {
    product_type: params.furniture_type?.subcategory || params.furniture_type?.category || undefined,
    width: params.dimensions?.width_mm ?? undefined,
    height: params.dimensions?.height_mm ?? undefined,
    depth: params.dimensions?.depth_mm ?? undefined,
    material: params.body_material?.type || "ЛДСП",
    thickness: params.dimensions?.thickness_mm ?? 16,
    door_count: params.door_count ?? undefined,
    drawer_count: params.drawer_count ?? undefined,
    shelf_count: params.shelf_count ?? undefined,
  };
}

export function ExtractedParamsCard({
  params: apiParams,
  confidence,
  onConfirm,
  isLoading,
}: ExtractedParamsCardProps) {
  // Конвертируем вложенную структуру в плоскую для UI
  const initialParams = useMemo(() => toSimpleParams(apiParams), [apiParams]);

  const [isEditing, setIsEditing] = useState(false);
  const [params, setParams] = useState<SimpleParams>(initialParams);

  const confidencePercent = Math.round(confidence * 100);
  const isLowConfidence = confidence < 0.8;

  const updateParam = (key: keyof SimpleParams, value: string | number) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleConfirm = () => {
    onConfirm(params);
  };

  return (
    <Card className={isLowConfidence ? "border-amber-500/50" : "border-green-500/50"}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Распознанные параметры</CardTitle>
          <Badge variant={isLowConfidence ? "outline" : "default"}>
            {isLowConfidence && <AlertTriangle className="mr-1 h-3 w-3" />}
            Уверенность: {confidencePercent}%
          </Badge>
        </div>
        {isLowConfidence && (
          <CardDescription className="text-amber-600">
            Рекомендуем проверить параметры перед продолжением
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {isEditing ? (
          // Режим редактирования
          <>
            <div className="space-y-2">
              <Label>Тип изделия</Label>
              <Select
                value={params.product_type || ""}
                onValueChange={(v) => updateParam("product_type", v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Выберите тип" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PRODUCT_TYPES).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label>Ширина, мм</Label>
                <Input
                  type="number"
                  value={params.width || ""}
                  onChange={(e) => updateParam("width", parseInt(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-2">
                <Label>Высота, мм</Label>
                <Input
                  type="number"
                  value={params.height || ""}
                  onChange={(e) => updateParam("height", parseInt(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-2">
                <Label>Глубина, мм</Label>
                <Input
                  type="number"
                  value={params.depth || ""}
                  onChange={(e) => updateParam("depth", parseInt(e.target.value) || 0)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Материал</Label>
                <Select
                  value={params.material || "ЛДСП"}
                  onValueChange={(v) => updateParam("material", v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ЛДСП">ЛДСП</SelectItem>
                    <SelectItem value="МДФ">МДФ</SelectItem>
                    <SelectItem value="Фанера">Фанера</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Толщина, мм</Label>
                <Select
                  value={String(params.thickness || 16)}
                  onValueChange={(v) => updateParam("thickness", parseInt(v))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="16">16 мм</SelectItem>
                    <SelectItem value="18">18 мм</SelectItem>
                    <SelectItem value="22">22 мм</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditing(false)}>
                Отмена
              </Button>
              <Button onClick={handleConfirm} disabled={isLoading}>
                <Check className="mr-2 h-4 w-4" />
                {isLoading ? "Создаём..." : "Подтвердить"}
              </Button>
            </div>
          </>
        ) : (
          // Режим просмотра
          <>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Тип:</span>{" "}
                <span className="font-medium">
                  {PRODUCT_TYPES[params.product_type || ""] || params.product_type || "—"}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Материал:</span>{" "}
                <span className="font-medium">{params.material || "ЛДСП"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Размеры:</span>{" "}
                <span className="font-medium">
                  {params.width || "—"} × {params.height || "—"} × {params.depth || "—"} мм
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Толщина:</span>{" "}
                <span className="font-medium">{params.thickness || 16} мм</span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditing(true)}>
                <Pencil className="mr-2 h-4 w-4" />
                Редактировать
              </Button>
              <Button onClick={handleConfirm} disabled={isLoading} className="flex-1">
                <Check className="mr-2 h-4 w-4" />
                {isLoading ? "Создаём заказ..." : "Подтвердить и продолжить"}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
