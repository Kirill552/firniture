"use client"

import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { DateRangeFilter, DateRange } from "@/components/date-range-filter"
import * as React from "react"

// Определяем тип для данных заказа
type Order = {
  id: string
  customer: string
  product: string
  status: "pending" | "processing" | "completed" | "cancelled"
  price: number
  createdAt: string
}

const orders: Order[] = [
  { id: "ORD001", customer: "ООО \"Рога и копыта\"", product: "Шкаф-купе \"Эксклюзив\"", status: "completed", price: 75000, createdAt: "2025-08-15" },
  { id: "ORD002", customer: "ИП Иванов И.И.", product: "Кухонный гарнитур \"Модерн\"", status: "processing", price: 120000, createdAt: "2025-09-01" },
  { id: "ORD003", customer: "Частное лицо", product: "Стол письменный", status: "pending", price: 25000, createdAt: "2025-09-08" },
];

const statusVariant = {
  pending: "secondary",
  processing: "default",
  completed: "outline",
  cancelled: "destructive",
} as const;

// Типизируем колонки с помощью ColumnDef
const columns: ColumnDef<Order>[] = [
  {
    accessorKey: "id",
    header: "ID Заказа",
  },
  {
    accessorKey: "customer",
    header: "Заказчик",
  },
  {
    accessorKey: "product",
    header: "Изделие",
  },
  {
    accessorKey: "status",
    header: "Статус",
    enableGrouping: true,
    cell: ({ row, getValue }) => {
      if (row.getIsGrouped()) {
        // Групповая строка: показываем значение статуса и количество заказов
        return `${getValue()} (${row.subRows.length})`
      }
      const status = row.getValue("status") as keyof typeof statusVariant
      return (
        <Badge variant={statusVariant[status]}>
          {status}
        </Badge>
      )
    },
  },
  {
    accessorKey: "price",
    header: "Цена",
    // aggregationFn используется react-table для высчета суммы в группе
    aggregationFn: "sum",
    cell: ({ row, getValue }) => {
      // Обычная строка
      if (!row.getIsGrouped()) {
        const price = Number(getValue())
        const formatted = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB" }).format(price)
        return <div className="text-right font-medium">{formatted}</div>
      }
      // Групповая строка: суммарная цена группы
      const total = row
        .subRows
        .reduce((acc, r) => acc + Number(r.getValue("price")), 0)
      const formattedTotal = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB" }).format(total)
      return <div className="text-right font-semibold">Σ {formattedTotal}</div>
    },
    footer: ({ table }) => {
      const total = table.getFilteredRowModel().rows.reduce((acc, r) => acc + Number(r.getValue("price")), 0)
      const formattedTotal = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB" }).format(total)
      return <div className="text-right font-semibold">Итого: {formattedTotal}</div>
    }
  },
  {
    accessorKey: "createdAt",
    header: "Создан",
  },
]

const OrdersPageInner = () => {
  const [dateRange, setDateRange] = React.useState<DateRange | undefined>()

  const filtered = React.useMemo(() => {
    if (!dateRange?.from && !dateRange?.to) return orders
    return orders.filter(o => {
      const d = o.createdAt
      if (dateRange.from && d < dateRange.from) return false
      if (dateRange.to && d > dateRange.to) return false
      return true
    })
  }, [dateRange])

  return (
    <div className="p-6 w-full">
      <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
        <h1 className="text-2xl font-bold">Заказы</h1>
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      </div>
      <DataTable columns={columns} data={filtered} tableId="orders" initialGrouping={["status"]} />
    </div>
  )
}

export default function OrdersPage() { return <OrdersPageInner /> }
