"use client"

import { motion } from "framer-motion"
import { StaggerContainer } from '@/components/animation/stagger-container'
import { fadeInUp } from '@/lib/motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"
import Link from "next/link"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useState, useEffect, useMemo } from "react"
import { Loader2 } from "lucide-react"

// Определяем тип для данных заказа
type Order = {
  id: string
  name: string
  status: "active" | "processing" | "done"
  date: string
}

type CAMJob = {
  id: string
  task: string
  status: string
}

// Mock данные как fallback
const mockOrders: Order[] = [
  { id: "1", name: "Заказ 1", status: "active", date: "2025-09-09" },
  { id: "2", name: "Заказ 2", status: "processing", date: "2025-09-08" },
]

const mockCamQueue: CAMJob[] = [
  { id: "1", task: "DXF generation", status: "processing" },
  { id: "2", task: "G-code", status: "pending" },
]

// Типизируем колонки с помощью ColumnDef
const columns: ColumnDef<Order>[] = [
  {
    accessorKey: "name",
    header: "Название",
    cell: ({ row, getValue }) => {
      if (row.getIsGrouped()) {
        return `${getValue()} (${row.subRows.length})`
      }
      return getValue() as string
    },
  },
  {
    accessorKey: "status",
    header: "Статус",
    enableGrouping: true,
    cell: ({ row }) => {
      const status = row.getValue("status") as string
      const variant = status === "active" ? "default" : "secondary"
      const labels: Record<string, string> = {
        active: "Активный",
        processing: "В работе",
        done: "Готов",
      }
      return (
        <Badge variant={variant}>
          {labels[status] || status}
        </Badge>
      )
    },
  },
  {
    accessorKey: "date",
    header: "Дата",
  },
]

export default function Dashboard() {
  const [orders, setOrders] = useState<Order[]>(mockOrders)
  const [camQueue, setCamQueue] = useState<CAMJob[]>(mockCamQueue)
  const [isLoading, setIsLoading] = useState(false)
  const [isDataLoading, setIsDataLoading] = useState(true)
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)

    const loadData = async () => {
      try {
        // Загружаем заказы
        const ordersRes = await fetch('/api/v1/orders')
        if (ordersRes.ok) {
          const data = await ordersRes.json()
          if (data && data.length > 0) {
            // Преобразуем формат API в формат UI
            const formattedOrders: Order[] = data.map((order: { id: string; customer_ref?: string; notes?: string; created_at: string }) => ({
              id: order.id,
              name: order.customer_ref || order.notes || `Заказ ${order.id.slice(0, 8)}`,
              status: "active" as const, // TODO: добавить статус в API
              date: new Date(order.created_at).toISOString().split('T')[0],
            }))
            setOrders(formattedOrders)
          }
        }

        // TODO: Загружаем CAM задачи когда будет endpoint GET /cam/jobs
        // const camRes = await fetch('/api/v1/cam/jobs')
        // if (camRes.ok) { ... }

      } catch (error) {
        console.error('Failed to load dashboard data:', error)
        // Оставляем mock данные при ошибке
      } finally {
        setIsDataLoading(false)
      }
    }

    loadData()
  }, [])

  // Статистика по статусам
  const statusData = useMemo(() => [
    { name: 'Активные', count: orders.filter(o => o.status === 'active').length },
    { name: 'В обработке', count: orders.filter(o => o.status === 'processing').length },
    { name: 'Готово', count: orders.filter(o => o.status === 'done').length },
  ], [orders])

  if (!isMounted) {
    return null
  }

  const handleCreateOrder = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/orders', { method: 'POST' })
      const data = await response.json()
      window.location.href = `/orders/new/tz-upload?orderId=${data.id}`
    } catch (error) {
      console.error("Failed to create order:", error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="p-6 w-full min-w-0">
      <StaggerContainer className="grid w-full grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
        <motion.div variants={fadeInUp} className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Создать заказ из ТЗ</CardTitle>
              <CardDescription>Начните новый проект с загрузки технического задания</CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" onClick={handleCreateOrder} disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Создание...
                  </>
                ) : (
                  "Начать"
                )}
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Очередь CAM</CardTitle>
              <CardDescription>
                {isDataLoading ? "Загрузка..." : `${camQueue.length} задач`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <ul className="space-y-3">
                  {camQueue.map((item) => (
                    <li key={item.id} className="flex justify-between items-center">
                      <span className="text-sm">{item.task}</span>
                      <Badge variant={item.status === "processing" ? "default" : "secondary"}>
                        {item.status === "processing" ? "В работе" : item.status === "pending" ? "Ожидает" : item.status}
                      </Badge>
                    </li>
                  ))}
                  {camQueue.length === 0 && (
                    <li className="text-sm text-muted-foreground text-center py-2">
                      Нет активных задач
                    </li>
                  )}
                </ul>
              )}
              <Link href="/cam">
                <Button variant="outline" className="w-full mt-4" size="sm">
                  Все задачи
                </Button>
              </Link>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>AI-ассистент</CardTitle>
              <CardDescription>Проактивные предложения</CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/hardware">
                <Button variant="outline" className="w-full">Подобрать фурнитуру</Button>
              </Link>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp} className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Статистика заказов</CardTitle>
              <CardDescription>
                {isDataLoading ? "Загрузка..." : `Всего: ${orders.length}`}
              </CardDescription>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#8884d8" name="Количество" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp} className="lg:col-span-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Активные заказы</CardTitle>
                <CardDescription>
                  {isDataLoading ? "Загрузка..." : `${orders.length} заказов`}
                </CardDescription>
              </div>
              <Link href="/orders">
                <Button variant="outline" size="sm">Все заказы</Button>
              </Link>
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : isMounted ? (
                <DataTable
                  columns={columns}
                  data={orders}
                  tableId="dashboard-orders"
                  initialGrouping={['status']}
                />
              ) : (
                <div className="h-64 flex items-center justify-center">
                  <p className="text-muted-foreground">Загрузка таблицы...</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

      </StaggerContainer>
    </div>
  )
}
