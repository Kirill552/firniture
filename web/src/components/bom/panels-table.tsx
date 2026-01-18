"use client"

import { useState } from "react"
import { Trash2, Plus, Pencil } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { BOMPanel } from "@/types/api"

interface PanelsTableProps {
  panels: BOMPanel[]
  onPanelUpdate?: (panelId: string, updates: Partial<BOMPanel>) => void
  onPanelDelete?: (panelId: string) => void
  onPanelAdd?: (panel: Omit<BOMPanel, "id">) => void
  readOnly?: boolean
  sheetArea?: number // Площадь листа в м²
}

export function PanelsTable({
  panels,
  onPanelUpdate,
  onPanelDelete,
  onPanelAdd,
  readOnly = false,
  sheetArea = 5.8, // Стандартный лист 2800×2070 мм
}: PanelsTableProps) {
  const [editingCell, setEditingCell] = useState<{
    panelId: string
    field: keyof BOMPanel
  } | null>(null)
  const [editValue, setEditValue] = useState("")
  const [showAddRow, setShowAddRow] = useState(false)
  const [newPanel, setNewPanel] = useState({
    name: "",
    width_mm: 0,
    height_mm: 0,
    thickness_mm: 16,
    material: "ЛДСП",
  })

  // Расчёт площади всех панелей
  const totalArea = panels.reduce((sum, p) => {
    return sum + (p.width_mm * p.height_mm) / 1_000_000
  }, 0)
  const utilizationPercent = sheetArea > 0 ? (totalArea / sheetArea) * 100 : 0

  const handleCellClick = (panelId: string, field: keyof BOMPanel, value: string | number) => {
    if (readOnly) return
    setEditingCell({ panelId, field })
    setEditValue(String(value))
  }

  const handleCellBlur = () => {
    if (!editingCell || !onPanelUpdate) {
      setEditingCell(null)
      return
    }

    const { panelId, field } = editingCell
    let parsedValue: string | number = editValue

    // Парсим числовые поля
    if (["width_mm", "height_mm", "thickness_mm"].includes(field)) {
      parsedValue = parseFloat(editValue) || 0
    }

    onPanelUpdate(panelId, { [field]: parsedValue })
    setEditingCell(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleCellBlur()
    } else if (e.key === "Escape") {
      setEditingCell(null)
    } else if (e.key === "Tab") {
      // Tab navigation between cells
      e.preventDefault()
      handleCellBlur()
    }
  }

  const handleAddPanel = () => {
    if (!onPanelAdd || !newPanel.name || !newPanel.width_mm || !newPanel.height_mm) return
    onPanelAdd(newPanel)
    setNewPanel({
      name: "",
      width_mm: 0,
      height_mm: 0,
      thickness_mm: 16,
      material: "ЛДСП",
    })
    setShowAddRow(false)
  }

  const renderEditableCell = (
    panelId: string,
    field: keyof BOMPanel,
    value: string | number,
    suffix?: string,
    alignRight?: boolean
  ) => {
    const isEditing = editingCell?.panelId === panelId && editingCell?.field === field
    const isNumeric = ["width_mm", "height_mm", "thickness_mm"].includes(field)

    return (
      <div className={`relative min-h-[32px] flex items-center ${alignRight ? "justify-end" : ""}`}>
        {isEditing ? (
          <Input
            type={isNumeric ? "number" : "text"}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleCellBlur}
            onKeyDown={handleKeyDown}
            autoFocus
            className={`h-8 ${alignRight ? "text-right" : ""}`}
            style={{ width: isNumeric ? "80px" : "120px" }}
          />
        ) : (
          <span
            onClick={() => handleCellClick(panelId, field, value)}
            className={!readOnly ? "cursor-pointer hover:bg-muted/50 px-1 rounded whitespace-nowrap" : "whitespace-nowrap"}
          >
            {value}{suffix}
          </span>
        )}
      </div>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">Панели</CardTitle>
          {!readOnly && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAddRow(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              Добавить
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px] min-w-[180px]">Название</TableHead>
              <TableHead className="text-right w-[100px] min-w-[100px]">Ширина</TableHead>
              <TableHead className="text-right w-[100px] min-w-[100px]">Высота</TableHead>
              <TableHead className="text-right w-[90px] min-w-[90px]">Толщина</TableHead>
              <TableHead className="w-[100px] min-w-[100px]">Материал</TableHead>
              <TableHead className="min-w-[80px]">Кромка</TableHead>
              {!readOnly && <TableHead className="w-[50px]"></TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {panels.length === 0 && !showAddRow ? (
              <TableRow>
                <TableCell colSpan={readOnly ? 6 : 7} className="text-center text-muted-foreground py-8">
                  Нет панелей. Панели будут рассчитаны автоматически при финализации заказа.
                </TableCell>
              </TableRow>
            ) : (
              panels.map((panel) => (
                <TableRow key={panel.id}>
                  <TableCell className="font-medium">
                    {renderEditableCell(panel.id, "name", panel.name)}
                  </TableCell>
                  <TableCell className="text-right">
                    {renderEditableCell(panel.id, "width_mm", panel.width_mm, " мм", true)}
                  </TableCell>
                  <TableCell className="text-right">
                    {renderEditableCell(panel.id, "height_mm", panel.height_mm, " мм", true)}
                  </TableCell>
                  <TableCell className="text-right">
                    {renderEditableCell(panel.id, "thickness_mm", panel.thickness_mm, " мм", true)}
                  </TableCell>
                  <TableCell>
                    {renderEditableCell(panel.id, "material", panel.material)}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {panel.edge_front || panel.edge_back
                      ? [
                          panel.edge_front && "спереди",
                          panel.edge_back && "сзади",
                        ]
                          .filter(Boolean)
                          .join(", ")
                      : "—"}
                  </TableCell>
                  {!readOnly && (
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => onPanelDelete?.(panel.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
            {showAddRow && (
              <TableRow className="bg-muted/30">
                <TableCell>
                  <Input
                    placeholder="Название"
                    value={newPanel.name}
                    onChange={(e) => setNewPanel({ ...newPanel, name: e.target.value })}
                    className="h-8"
                  />
                </TableCell>
                <TableCell>
                  <Input
                    type="number"
                    placeholder="мм"
                    value={newPanel.width_mm || ""}
                    onChange={(e) => setNewPanel({ ...newPanel, width_mm: parseFloat(e.target.value) || 0 })}
                    className="h-8 w-20"
                  />
                </TableCell>
                <TableCell>
                  <Input
                    type="number"
                    placeholder="мм"
                    value={newPanel.height_mm || ""}
                    onChange={(e) => setNewPanel({ ...newPanel, height_mm: parseFloat(e.target.value) || 0 })}
                    className="h-8 w-20"
                  />
                </TableCell>
                <TableCell>
                  <Input
                    type="number"
                    value={newPanel.thickness_mm}
                    onChange={(e) => setNewPanel({ ...newPanel, thickness_mm: parseFloat(e.target.value) || 16 })}
                    className="h-8 w-16"
                  />
                </TableCell>
                <TableCell>
                  <Input
                    value={newPanel.material}
                    onChange={(e) => setNewPanel({ ...newPanel, material: e.target.value })}
                    className="h-8 w-24"
                  />
                </TableCell>
                <TableCell>—</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button size="sm" onClick={handleAddPanel}>
                      OK
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowAddRow(false)}
                    >
                      ✕
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Сводка по площади */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t text-sm">
          <div className="flex gap-6">
            <div>
              <span className="text-muted-foreground">Площадь: </span>
              <span className="font-medium">{totalArea.toFixed(2)} м²</span>
            </div>
            <div>
              <span className="text-muted-foreground">Лист: </span>
              <span className="font-medium">{sheetArea} м²</span>
            </div>
            <div>
              <span className="text-muted-foreground">Использование: </span>
              <span className={`font-medium ${utilizationPercent < 50 ? "text-amber-600" : "text-green-600"}`}>
                {utilizationPercent.toFixed(1)}%
              </span>
            </div>
          </div>
          <div className="text-muted-foreground">
            {panels.length} {panels.length === 1 ? "панель" : panels.length < 5 ? "панели" : "панелей"}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
