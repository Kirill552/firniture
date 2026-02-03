"use client"

import { useState } from "react"
import { Pencil, Save, RefreshCw, Loader2, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { BOMDimensions, BOMBodyMaterial } from "@/types/api"

interface BOMHeaderProps {
  furnitureType: string
  dimensions: BOMDimensions
  bodyMaterial: BOMBodyMaterial
  onUpdate?: (updates: {
    furniture_type?: string
    dimensions?: Partial<BOMDimensions>
    body_material?: Partial<BOMBodyMaterial>
  }) => void
  onRecalculate?: () => void
  onSave?: () => void
  readOnly?: boolean
  isLoading?: boolean
  hasChanges?: boolean
  // Новые props для компактного режима
  compact?: boolean
  panelCount?: number
  totalCost?: number
  saveStatus?: "idle" | "saving" | "saved" | "error"
}

const MATERIAL_TYPES = ["ЛДСП", "МДФ", "Фанера", "Массив", "ДВП"]
const THICKNESS_OPTIONS = [10, 12, 16, 18, 19, 22, 25, 28, 32]

export function BOMHeader({
  furnitureType,
  dimensions,
  bodyMaterial,
  onUpdate,
  onRecalculate,
  onSave,
  readOnly = false,
  isLoading = false,
  hasChanges = false,
  compact = false,
  panelCount,
  totalCost,
  saveStatus = "idle",
}: BOMHeaderProps) {
  const [isEditingName, setIsEditingName] = useState(false)
  const [editedName, setEditedName] = useState(furnitureType)

  const handleNameSave = () => {
    if (onUpdate && editedName !== furnitureType) {
      onUpdate({ furniture_type: editedName })
    }
    setIsEditingName(false)
  }

  const handleDimensionChange = (field: keyof BOMDimensions, value: number) => {
    if (!onUpdate) return
    onUpdate({ dimensions: { [field]: value } })
  }

  const handleMaterialChange = (field: keyof BOMBodyMaterial, value: string | number) => {
    if (!onUpdate) return
    onUpdate({ body_material: { [field]: value } })
  }

  return (
    <Card className={compact ? "border-0 shadow-none bg-transparent" : ""}>
      <CardContent className={compact ? "px-0 py-3" : "pt-6"}>
        <div className={compact ? "flex flex-wrap items-center gap-4 min-h-[40px]" : "space-y-4"}>
          {/* Название изделия */}
          <div className="flex items-center gap-2">
            {!compact && <span className="text-muted-foreground">Заказ:</span>}
            {isEditingName ? (
              <div className="flex items-center gap-2">
                <Input
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  className="h-8 w-48"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleNameSave()
                    if (e.key === "Escape") {
                      setEditedName(furnitureType)
                      setIsEditingName(false)
                    }
                  }}
                />
                <Button size="sm" variant="ghost" onClick={handleNameSave}>
                  OK
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-1">
                <span className={compact ? "font-semibold" : "text-lg font-semibold"}>
                  {furnitureType || "Новое изделие"}
                </span>
                {!readOnly && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => setIsEditingName(true)}
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                )}
              </div>
            )}
          </div>

          {compact && <span className="text-muted-foreground">|</span>}

          {/* Габариты + Материал + Толщина + Цвет (Compact) */}
          {compact && (
            <>
              <div className="flex items-center gap-1">
                <Input
                  type="number"
                  value={dimensions.width_mm}
                  onChange={(e) => handleDimensionChange("width_mm", parseInt(e.target.value) || 0)}
                  className="h-7 w-16 text-center text-sm"
                />
                <span className="text-muted-foreground text-sm">×</span>
                <Input
                  type="number"
                  value={dimensions.height_mm}
                  onChange={(e) => handleDimensionChange("height_mm", parseInt(e.target.value) || 0)}
                  className="h-7 w-16 text-center text-sm"
                />
                <span className="text-muted-foreground text-sm">×</span>
                <Input
                  type="number"
                  value={dimensions.depth_mm}
                  onChange={(e) => handleDimensionChange("depth_mm", parseInt(e.target.value) || 0)}
                  className="h-7 w-14 text-center text-sm"
                />
              </div>

              <span className="text-muted-foreground">|</span>

              <div className="flex items-center gap-1">
                <Select
                  value={bodyMaterial.type}
                  onValueChange={(value) => handleMaterialChange("type", value)}
                >
                  <SelectTrigger className="h-7 w-20 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent position="popper" sideOffset={4}>
                    {MATERIAL_TYPES.map((mat) => (
                      <SelectItem key={mat} value={mat}>
                        {mat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select
                  value={String(bodyMaterial.thickness_mm)}
                  onValueChange={(value) => handleMaterialChange("thickness_mm", parseInt(value))}
                >
                  <SelectTrigger className="h-7 w-16 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent position="popper" sideOffset={4}>
                    {THICKNESS_OPTIONS.map((t) => (
                      <SelectItem key={t} value={String(t)}>
                        {t}мм
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {/* Габариты + Материал + Толщина + Цвет (Full — всё в одном flex-wrap) */}
          {!compact && (
            <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
              {/* Габариты */}
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Габариты:</span>
                {readOnly ? (
                  <span className="font-medium">
                    {dimensions.width_mm} × {dimensions.height_mm} × {dimensions.depth_mm} мм
                  </span>
                ) : (
                  <div className="flex items-center gap-1">
                    <Input
                      type="number"
                      value={dimensions.width_mm}
                      onChange={(e) => handleDimensionChange("width_mm", parseInt(e.target.value) || 0)}
                      className="h-8 w-20 text-center"
                    />
                    <span className="text-muted-foreground">×</span>
                    <Input
                      type="number"
                      value={dimensions.height_mm}
                      onChange={(e) => handleDimensionChange("height_mm", parseInt(e.target.value) || 0)}
                      className="h-8 w-20 text-center"
                    />
                    <span className="text-muted-foreground">×</span>
                    <Input
                      type="number"
                      value={dimensions.depth_mm}
                      onChange={(e) => handleDimensionChange("depth_mm", parseInt(e.target.value) || 0)}
                      className="h-8 w-20 text-center"
                    />
                    <span className="text-muted-foreground ml-1">мм</span>
                  </div>
                )}
              </div>

              {/* Материал */}
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Материал:</span>
                {readOnly ? (
                  <span className="font-medium">{bodyMaterial.type}</span>
                ) : (
                  <Select
                    value={bodyMaterial.type}
                    onValueChange={(value) => handleMaterialChange("type", value)}
                  >
                    <SelectTrigger className="h-8 w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent position="popper" sideOffset={4}>
                      {MATERIAL_TYPES.map((mat) => (
                        <SelectItem key={mat} value={mat}>
                          {mat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Толщина */}
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Толщина:</span>
                {readOnly ? (
                  <span className="font-medium">{bodyMaterial.thickness_mm} мм</span>
                ) : (
                  <Select
                    value={String(bodyMaterial.thickness_mm)}
                    onValueChange={(value) => handleMaterialChange("thickness_mm", parseInt(value))}
                  >
                    <SelectTrigger className="h-8 w-20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent position="popper" sideOffset={4}>
                      {THICKNESS_OPTIONS.map((t) => (
                        <SelectItem key={t} value={String(t)}>
                          {t} мм
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Цвет */}
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Цвет:</span>
                {readOnly ? (
                  <span className="font-medium">{bodyMaterial.color || "—"}</span>
                ) : (
                  <Input
                    value={bodyMaterial.color || ""}
                    onChange={(e) => handleMaterialChange("color", e.target.value)}
                    placeholder="белый"
                    className="h-8 w-24"
                  />
                )}
              </div>
            </div>
          )}

          {/* Счётчик панелей и стоимость (только в compact) */}
          {compact && panelCount !== undefined && (
            <>
              <span className="text-muted-foreground">|</span>
              <span className="text-sm">{panelCount} пан.</span>
            </>
          )}
          {compact && totalCost !== undefined && (
            <>
              <span className="text-muted-foreground">|</span>
              <span className="font-medium">
                {new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", minimumFractionDigits: 0 }).format(totalCost)}
              </span>
            </>
          )}

          {/* Статус сохранения */}
          {compact && saveStatus !== "idle" && (
            <>
              <span className="text-muted-foreground">|</span>
              {saveStatus === "saving" && (
                <span className="text-sm text-blue-600 flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Сохранение...
                </span>
              )}
              {saveStatus === "saved" && (
                <span className="text-sm text-green-600 flex items-center gap-1">
                  <Check className="h-3 w-3" />
                  Сохранено
                </span>
              )}
              {saveStatus === "error" && (
                <span className="text-sm text-destructive">Ошибка</span>
              )}
            </>
          )}

          {/* Кнопки действий */}
          {!readOnly && (
            <div className="flex items-center gap-2 ml-auto">
              {onRecalculate && (
                <Button
                  variant={hasChanges ? "default" : "outline"}
                  size="sm"
                  onClick={onRecalculate}
                  disabled={isLoading}
                  className={compact ? "ml-auto" : ""}
                >
                  <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? "animate-spin" : ""}`} />
                  Пересчитать
                </Button>
              )}
              {onSave && !compact && (
                <Button
                  size="sm"
                  onClick={onSave}
                  disabled={isLoading || !hasChanges}
                >
                  <Save className="h-4 w-4 mr-1" />
                  Сохранить
                </Button>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}