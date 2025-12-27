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
import { useState, useEffect } from "react"

// Определяем тип для данных заказа
type Order = {
  id: string
  name: string
  status: "active" | "processing" | "done"
  date: string
}

const orders: Order[] = [
  { id: "1", name: "Заказ 1", status: "active", date: "2025-09-09" },
  { id: "2", name: "Заказ 2", status: "processing", date: "2025-09-08" },
]

const statusData = [
  { name: 'Активные', count: orders.filter(o => o.status === 'active').length },
  { name: 'В обработке', count: orders.filter(o => o.status === 'processing').length },
  { name: 'Готово', count: orders.filter(o => o.status === 'done').length },
]

const camQueue = [
  { id: "1", task: "DXF generation", status: "processing" },
  { id: "2", task: "G-code", status: "pending" },
]

// Типизируем колонки с помощью ColumnDef
const columns: ColumnDef<Order>[] = [
  {
    accessorKey: "name",
    header: "Название",
    // Для агрегированных групп можно показать количество элементов в группе.
    // В @tanstack/react-table v8 aggregation задаётся через aggregationFn, но нам
    // достаточно отобразить счетчик в cell когда строка сгруппирована.
    // aggregatedCell уберём, оставим обычный cell и будем проверять row.subRows.
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
      return (
        <Badge variant={variant}>
          {status}
        </Badge>
      )
    },
  },
  {
    accessorKey: "date",
    header: "Дата",
  },
]

// Используем общие motion пресеты из lib/motion

export default function Dashboard() {
  const [isLoading, setIsLoading] = useState(false)
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)
  }, [])

  if (!isMounted) {
    return null
  }

  const handleCreateOrder = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/orders', { method: 'POST' })
      const data = await response.json()
      window.location.href = `/orders/new/tz-upload?orderId=${data.orderId}`
    } catch (error) {
      console.error("Failed to create order:", error)
      // TODO: Show an error message to the user
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
                {isLoading ? "Создание..." : "Начать"}
              </Button>
            </CardContent>
          </Card>
        </motion.div>

  <motion.div variants={fadeInUp}>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Очередь CAM</CardTitle>
              <CardDescription>Задачи в обработке</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {camQueue.map((item) => (
                  <li key={item.id} className="flex justify-between items-center">
                    <span>{item.task}</span>
                    <Badge variant={item.status === "processing" ? "default" : "secondary"}>{item.status}</Badge>
                  </li>
                ))}
              </ul>
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
              <Button variant="outline" className="w-full">Открыть чат</Button>
            </CardContent>
          </Card>
        </motion.div>

  <motion.div variants={fadeInUp} className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Статистика заказов</CardTitle>
              <CardDescription>Распределение по статусам</CardDescription>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

  <motion.div variants={fadeInUp} className="lg:col-span-4">
          <Card>
            <CardHeader>
              <CardTitle>Активные заказы</CardTitle>
              <CardDescription>Текущие заказы в работе</CardDescription>
            </CardHeader>
            <CardContent>
              {isMounted ? (
                <DataTable
                  columns={columns}
                  data={orders}
                  tableId="dashboard-orders"
                  // GroupingState = string[]; группируем по статусу
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