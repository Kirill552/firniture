"use client"

import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"

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
    cell: ({ row }) => {
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
    cell: ({ row }) => {
      const price = parseFloat(row.getValue("price") as string)
      const formatted = new Intl.NumberFormat("ru-RU", {
        style: "currency",
        currency: "RUB",
      }).format(price)

      return <div className="text-right font-medium">{formatted}</div>
    },
  },
  {
    accessorKey: "createdAt",
    header: "Создан",
  },
]

export default function OrdersPage() {
  return (
    <div className="p-6 w-full">
      <h1 className="text-2xl font-bold mb-4">Заказы</h1>
      <DataTable columns={columns} data={orders} tableId="orders" />
    </div>
  )
}
