"use client"

import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DateRangeFilter, DateRange } from "@/components/date-range-filter"
import Link from "next/link"
import * as React from "react"
import { Loader2, Plus, Eye } from "lucide-react"

// Определяем тип для данных заказа
type Order = {
  id: string
  customer: string
  product: string
  status: "pending" | "processing" | "completed" | "cancelled"
  price: number
  createdAt: string
}

// Mock данные как fallback
const mockOrders: Order[] = [
  { id: "ORD001", customer: "ООО \"Рога и копыта\"", product: "Шкаф-купе \"Эксклюзив\"", status: "completed", price: 75000, createdAt: "2025-08-15" },
  { id: "ORD002", customer: "ИП Иванов И.И.", product: "Кухонный гарнитур \"Модерн\"", status: "processing", price: 120000, createdAt: "2025-09-01" },
  { id: "ORD003", customer: "Частное лицо", product: "Стол письменный", status: "pending", price: 25000, createdAt: "2025-09-08" },
]

const statusVariant = {
  pending: "secondary",
  processing: "default",
  completed: "outline",
  cancelled: "destructive",
} as const

const statusLabels: Record<string, string> = {
  pending: "Ожидает",
  processing: "В работе",
  completed: "Завершён",
  cancelled: "Отменён",
}

// Типизируем колонки с помощью ColumnDef
const columns: ColumnDef<Order>[] = [
  {
    accessorKey: "id",
    header: "ID Заказа",
    cell: ({ row }) => {
      const id = row.getValue("id") as string
      return (
        <Link href={`/bom?orderId=${id}`} className="text-primary hover:underline font-mono text-sm">
          {id.slice(0, 8)}...
        </Link>
      )
    },
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
        const status = getValue() as string
        return `${statusLabels[status] || status} (${row.subRows.length})`
      }
      const status = row.getValue("status") as keyof typeof statusVariant
      return (
        <Badge variant={statusVariant[status]}>
          {statusLabels[status] || status}
        </Badge>
      )
    },
  },
  {
    accessorKey: "price",
    header: "Цена",
    aggregationFn: "sum",
    cell: ({ row, getValue }) => {
      if (!row.getIsGrouped()) {
        const price = Number(getValue())
        const formatted = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB" }).format(price)
        return <div className="text-right font-medium">{formatted}</div>
      }
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
  {
    id: "actions",
    header: "",
    cell: ({ row }) => {
      const id = row.original.id
      return (
        <Link href={`/bom?orderId=${id}`}>
          <Button variant="ghost" size="sm">
            <Eye className="h-4 w-4" />
          </Button>
        </Link>
      )
    },
  },
]

const OrdersPageInner = () => {
  const [orders, setOrders] = React.useState<Order[]>(mockOrders)
  const [isLoading, setIsLoading] = React.useState(true)
  const [dateRange, setDateRange] = React.useState<DateRange | undefined>()

  React.useEffect(() => {
    const loadOrders = async () => {
      try {
        const response = await fetch('/api/v1/orders')
        if (response.ok) {
          const data = await response.json()
          if (data && data.length > 0) {
            // Преобразуем формат API в формат UI
            const formattedOrders: Order[] = data.map((order: {
              id: string
              customer_ref?: string
              notes?: string
              created_at: string
            }) => ({
              id: order.id,
              customer: order.customer_ref || "Не указан",
              product: order.notes || "Не указано",
              status: "pending" as const, // TODO: добавить статус в API
              price: 0, // TODO: добавить цену в API
              createdAt: new Date(order.created_at).toISOString().split('T')[0],
            }))
            setOrders(formattedOrders)
          }
        }
      } catch (error) {
        console.error('Failed to load orders:', error)
        // Оставляем mock данные при ошибке
      } finally {
        setIsLoading(false)
      }
    }

    loadOrders()
  }, [])

  const filtered = React.useMemo(() => {
    if (!dateRange?.from && !dateRange?.to) return orders
    return orders.filter(o => {
      const d = o.createdAt
      if (dateRange.from && d < dateRange.from) return false
      if (dateRange.to && d > dateRange.to) return false
      return true
    })
  }, [dateRange, orders])

  return (
    <div className="p-6 w-full">
      <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Заказы</h1>
          <p className="text-sm text-muted-foreground">
            {isLoading ? "Загрузка..." : `${orders.length} заказов`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
          <Link href="/orders/new/tz-upload">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Новый заказ
            </Button>
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="h-64 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          tableId="orders"
          initialGrouping={["status"]}
        />
      )}
    </div>
  )
}

export default function OrdersPage() {
  return <OrdersPageInner />
}
