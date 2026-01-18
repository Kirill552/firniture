"use client"

import { useState } from "react"
import { Trash2, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { BOMEdgeBand } from "@/types/api"

interface EdgeBandTableProps {
  edgeBands: BOMEdgeBand[]
  onEdgeBandUpdate?: (id: string, updates: Partial<BOMEdgeBand>) => void
  onEdgeBandDelete?: (id: string) => void
  readOnly?: boolean
}

export function EdgeBandTable({
  edgeBands,
  onEdgeBandUpdate,
  onEdgeBandDelete,
  readOnly = false,
}: EdgeBandTableProps) {
  const [editingCell, setEditingCell] = useState<{
    id: string
    field: keyof BOMEdgeBand
  } | null>(null)
  const [editValue, setEditValue] = useState("")

  // Расчёт общей стоимости
  const totalCost = edgeBands.reduce((sum, eb) => {
    return sum + eb.length_m * (eb.unit_price || 0)
  }, 0)

  const totalLength = edgeBands.reduce((sum, eb) => sum + eb.length_m, 0)

  const handleCellClick = (id: string, field: keyof BOMEdgeBand, value: string | number) => {
    if (readOnly) return
    setEditingCell({ id, field })
    setEditValue(String(value))
  }

  const handleCellBlur = () => {
    if (!editingCell || !onEdgeBandUpdate) {
      setEditingCell(null)
      return
    }

    const { id, field } = editingCell
    let parsedValue: string | number = editValue

    if (field === "length_m" || field === "unit_price") {
      parsedValue = parseFloat(editValue) || 0
    }

    onEdgeBandUpdate(id, { [field]: parsedValue })
    setEditingCell(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleCellBlur()
    } else if (e.key === "Escape") {
      setEditingCell(null)
    }
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: "RUB",
      minimumFractionDigits: 0,
    }).format(price)
  }

  const renderEditableCell = (
    id: string,
    field: keyof BOMEdgeBand,
    value: string | number,
    suffix?: string,
    isNumber = false
  ) => {
    const isEditing = editingCell?.id === id && editingCell?.field === field

    if (isEditing) {
      return (
        <Input
          type={isNumber ? "number" : "text"}
          step={isNumber ? "0.1" : undefined}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleCellBlur}
          onKeyDown={handleKeyDown}
          autoFocus
          className="h-8 w-20"
        />
      )
    }

    return (
      <span
        onClick={() => handleCellClick(id, field, value)}
        className={!readOnly ? "cursor-pointer hover:bg-muted/50 px-1 rounded" : ""}
      >
        {value}
        {suffix}
      </span>
    )
  }

  const getEdgeTypeColor = (type: string) => {
    if (type.toLowerCase().includes("пвх")) return "default"
    if (type.toLowerCase().includes("меламин")) return "secondary"
    if (type.toLowerCase().includes("abs")) return "outline"
    return "secondary"
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">Кромка</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Тип</TableHead>
              <TableHead>Цвет</TableHead>
              <TableHead className="text-right">Длина</TableHead>
              <TableHead>Назначение</TableHead>
              <TableHead className="text-right">Цена/м</TableHead>
              <TableHead className="text-right">Сумма</TableHead>
              {!readOnly && <TableHead className="w-[50px]"></TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {edgeBands.length === 0 ? (
              <TableRow>
                <TableCell colSpan={readOnly ? 6 : 7} className="text-center text-muted-foreground py-8">
                  Нет кромки. Кромка будет рассчитана автоматически при финализации заказа.
                </TableCell>
              </TableRow>
            ) : (
              edgeBands.map((item) => {
                const sum = item.length_m * (item.unit_price || 0)

                return (
                  <TableRow key={item.id}>
                    <TableCell>
                      <Badge variant={getEdgeTypeColor(item.type)} className="text-xs">
                        {item.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{item.color}</TableCell>
                    <TableCell className="text-right">
                      {renderEditableCell(item.id, "length_m", item.length_m, " м", true)}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {item.purpose}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {formatPrice(item.unit_price || 0)}/м
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatPrice(sum)}
                    </TableCell>
                    {!readOnly && (
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => onEdgeBandDelete?.(item.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>

        {/* Итого */}
        {edgeBands.length > 0 && (
          <div className="flex items-center justify-between mt-4 pt-3 border-t text-sm">
            <div className="flex gap-6">
              <div>
                <span className="text-muted-foreground">Всего длина: </span>
                <span className="font-medium">{totalLength.toFixed(1)} м</span>
              </div>
              <div>
                <span className="text-muted-foreground">Типов: </span>
                <span className="font-medium">{edgeBands.length}</span>
              </div>
            </div>
            <div>
              <span className="text-muted-foreground">Итого: </span>
              <span className="font-bold">{formatPrice(totalCost)}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
