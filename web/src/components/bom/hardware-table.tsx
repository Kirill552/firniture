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
import type { BOMHardware, BOMFastener } from "@/types/api"

interface HardwareTableProps {
  hardware: BOMHardware[]
  fasteners: BOMFastener[]
  onHardwareUpdate?: (sku: string, updates: Partial<BOMHardware>) => void
  onHardwareDelete?: (sku: string) => void
  onFastenerUpdate?: (id: string, updates: Partial<BOMFastener>) => void
  onFastenerDelete?: (id: string) => void
  readOnly?: boolean
}

export function HardwareTable({
  hardware,
  fasteners,
  onHardwareUpdate,
  onHardwareDelete,
  onFastenerUpdate,
  onFastenerDelete,
  readOnly = false,
}: HardwareTableProps) {
  const [editingCell, setEditingCell] = useState<{
    type: "hardware" | "fastener"
    id: string
    field: string
  } | null>(null)
  const [editValue, setEditValue] = useState("")

  // Расчёт общей стоимости
  const hardwareTotal = hardware.reduce((sum, h) => {
    const qty = h.quantity || h.qty || 0
    const price = h.unit_price || 0
    return sum + qty * price
  }, 0)

  const fastenersTotal = fasteners.reduce((sum, f) => {
    return sum + f.quantity * (f.unit_price || 0)
  }, 0)

  const totalCost = hardwareTotal + fastenersTotal

  const handleCellClick = (
    type: "hardware" | "fastener",
    id: string,
    field: string,
    value: string | number
  ) => {
    if (readOnly) return
    setEditingCell({ type, id, field })
    setEditValue(String(value))
  }

  const handleCellBlur = () => {
    if (!editingCell) {
      return
    }

    const { type, id, field } = editingCell
    let parsedValue: string | number = editValue

    if (field === "quantity" || field === "unit_price") {
      parsedValue = parseFloat(editValue) || 0
    }

    if (type === "hardware" && onHardwareUpdate) {
      onHardwareUpdate(id, { [field]: parsedValue })
    } else if (type === "fastener" && onFastenerUpdate) {
      onFastenerUpdate(id, { [field]: parsedValue })
    }

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
    type: "hardware" | "fastener",
    id: string,
    field: string,
    value: string | number,
    suffix?: string,
    isNumber = false
  ) => {
    const isEditing =
      editingCell?.type === type &&
      editingCell?.id === id &&
      editingCell?.field === field

    if (isEditing) {
      return (
        <Input
          type={isNumber ? "number" : "text"}
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
        onClick={() => handleCellClick(type, id, field, value)}
        className={!readOnly ? "cursor-pointer hover:bg-muted/50 px-1 rounded" : ""}
      >
        {value}
        {suffix}
      </span>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">Фурнитура и крепёж</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Артикул</TableHead>
              <TableHead className="w-[250px]">Наименование</TableHead>
              <TableHead>Тип</TableHead>
              <TableHead className="text-right">Кол-во</TableHead>
              <TableHead className="text-right">Цена</TableHead>
              <TableHead className="text-right">Сумма</TableHead>
              {!readOnly && <TableHead className="w-[50px]"></TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Фурнитура (петли, направляющие, ручки) */}
            {hardware.length === 0 && fasteners.length === 0 ? (
              <TableRow>
                <TableCell colSpan={readOnly ? 6 : 7} className="text-center text-muted-foreground py-8">
                  Нет фурнитуры и крепежа
                </TableCell>
              </TableRow>
            ) : (
              <>
                {hardware.map((item) => {
                  const qty = item.quantity || item.qty || 0
                  const price = item.unit_price || 0
                  const sum = qty * price
                  const id = item.id || item.sku

                  return (
                    <TableRow key={id}>
                      <TableCell className="font-mono text-sm">{item.sku}</TableCell>
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">
                          {item.category || "Фурнитура"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {renderEditableCell("hardware", id, "quantity", qty, " шт", true)}
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        {formatPrice(price)}
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
                            onClick={() => onHardwareDelete?.(item.sku)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}

                {/* Крепёж (конфирматы, заглушки, полкодержатели) */}
                {fasteners.map((item) => {
                  const sum = item.quantity * (item.unit_price || 0)

                  return (
                    <TableRow key={item.id} className="bg-muted/20">
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        —
                      </TableCell>
                      <TableCell>
                        <div>
                          <span className="font-medium">{item.name}</span>
                          {item.size && (
                            <span className="text-muted-foreground ml-1">({item.size})</span>
                          )}
                        </div>
                        {item.purpose && (
                          <div className="text-xs text-muted-foreground">{item.purpose}</div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          Крепёж
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {renderEditableCell("fastener", item.id, "quantity", item.quantity, " шт", true)}
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        {formatPrice(item.unit_price || 0)}
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
                            onClick={() => onFastenerDelete?.(item.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}
              </>
            )}
          </TableBody>
        </Table>

        {/* Итого */}
        {(hardware.length > 0 || fasteners.length > 0) && (
          <div className="flex items-center justify-between mt-4 pt-3 border-t text-sm">
            <div className="flex gap-6">
              <div>
                <span className="text-muted-foreground">Фурнитура: </span>
                <span className="font-medium">{hardware.length} поз.</span>
              </div>
              <div>
                <span className="text-muted-foreground">Крепёж: </span>
                <span className="font-medium">{fasteners.length} поз.</span>
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
