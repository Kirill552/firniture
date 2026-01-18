"use client"

import { useState } from "react"
import { Pencil, Save, RefreshCw } from "lucide-react"
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
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Название изделия */}
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Заказ:</span>
            {isEditingName ? (
              <div className="flex items-center gap-2">
                <Input
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  className="h-8 w-64"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleNameSave()
                    if (e.key === "Escape") {
                      setEditedName(furnitureType)
                      setIsEditingName(false)
                    }
                  }}
                />
                <Button size="sm" onClick={handleNameSave}>
                  OK
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold">{furnitureType || "Новое изделие"}</span>
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

          {/* Габариты и материал */}
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
                  <SelectContent>
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
                  <SelectContent>
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

            {/* Кнопки действий */}
            {!readOnly && (
              <div className="flex items-center gap-2 ml-auto">
                {onRecalculate && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onRecalculate}
                    disabled={isLoading}
                  >
                    <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? "animate-spin" : ""}`} />
                    Пересчитать
                  </Button>
                )}
                {onSave && (
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
        </div>
      </CardContent>
    </Card>
  )
}
