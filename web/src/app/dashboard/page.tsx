"use client"

import { motion } from "framer-motion"
import { StaggerContainer } from '@/components/animation/stagger-container'
import { fadeInUp } from '@/lib/motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useState, useEffect, useMemo } from "react"
import { Loader2, FileText, Wrench, CheckCircle2, Clock, AlertCircle, ArrowRight } from "lucide-react"

type Order = {
  id: string
  name: string
  status: "draft" | "ready" | "completed"
  date: string
}

type CAMJob = {
  id: string
  task: string
  status: string
}

type DashboardStats = {
  draft: number
  ready: number
  completed: number
  total: number
}

const statusLabels: Record<string, string> = {
  draft: "Черновик",
  ready: "Готов к производству",
  completed: "Выполнен",
}

const statusVariant = {
  draft: "secondary",
  ready: "default",
  completed: "outline",
} as const

export default function Dashboard() {
  const [orders, setOrders] = useState<Order[]>([])
  const [stats, setStats] = useState<DashboardStats>({ draft: 0, ready: 0, completed: 0, total: 0 })
  const [camQueue, setCamQueue] = useState<CAMJob[]>([])
  const [isDataLoading, setIsDataLoading] = useState(true)
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)

    const loadData = async () => {
      try {
        // Загружаем заказы — это основной источник правды
        const ordersRes = await fetch('/api/v1/orders')
        if (ordersRes.ok) {
          const data = await ordersRes.json()
          if (data && data.length > 0) {
            const formattedOrders: Order[] = data.map((order: { id: string; customer_ref?: string; notes?: string; status?: string; created_at: string }) => ({
              id: order.id,
              name: order.customer_ref || order.notes || `Заказ ${order.id.slice(0, 8)}`,
              status: (order.status || "draft") as Order["status"],
              date: new Date(order.created_at).toISOString().split('T')[0],
            }))
            setOrders(formattedOrders)

            // Считаем статистику из реальных данных
            const calculatedStats = formattedOrders.reduce((acc, order) => {
              acc[order.status] = (acc[order.status] || 0) + 1
              acc.total++
              return acc
            }, { draft: 0, ready: 0, completed: 0, total: 0 } as DashboardStats)
            setStats(calculatedStats)
          }
        }

        // Загружаем CAM задачи
        const camRes = await fetch('/api/v1/cam/jobs?limit=5')
        if (camRes.ok) {
          const camData = await camRes.json()
          if (camData?.jobs) {
            const formattedJobs: CAMJob[] = camData.jobs.map((job: { job_id: string; job_kind: string; status: string }) => ({
              id: job.job_id,
              task: job.job_kind,
              status: job.status,
            }))
            setCamQueue(formattedJobs)
          }
        }

      } catch (error) {
        console.error('Failed to load dashboard data:', error)
      } finally {
        setIsDataLoading(false)
      }
    }

    loadData()
  }, [])

  // Статистика по статусам для графика
  const chartData = useMemo(() => [
    { name: 'Черновик', count: stats.draft, fill: 'var(--color-muted-foreground)' },
    { name: 'В производство', count: stats.ready, fill: 'var(--color-warning)' },
    { name: 'Выполнен', count: stats.completed, fill: 'var(--color-success)' },
  ], [stats])

  // Последние заказы (до 5)
  const recentOrders = useMemo(() => orders.slice(0, 5), [orders])

  if (!isMounted) {
    return null
  }

  return (
    <div className="p-6 w-full min-w-0">
      {/* Заголовок */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-foreground">Обзор</h1>
        <p className="text-muted-foreground mt-1">Статус вашего производства</p>
      </div>

      <StaggerContainer className="grid w-full grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* Карточки со статистикой */}
        <motion.div variants={fadeInUp}>
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Всего заказов
              </CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              ) : (
                <div className="text-3xl font-bold">{stats.total}</div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                В производство
              </CardTitle>
              <Clock className="h-4 w-4 text-warning" />
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              ) : (
                <div className="text-3xl font-bold text-warning">{stats.ready}</div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Выполнено
              </CardTitle>
              <CheckCircle2 className="h-4 w-4 text-success" />
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              ) : (
                <div className="text-3xl font-bold text-success">{stats.completed}</div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                CAM задачи
              </CardTitle>
              <Wrench className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              ) : (
                <div className="text-3xl font-bold">{camQueue.length}</div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* График */}
        <motion.div variants={fadeInUp} className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Статистика по статусам</CardTitle>
            </CardHeader>
            <CardContent className="h-64">
              {isDataLoading ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : stats.total === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                  <FileText className="h-12 w-12 mb-3 opacity-30" />
                  <p>Нет заказов</p>
                  <Link href="/orders/new" className="mt-3">
                    <Button variant="outline" size="sm">Создать первый заказ</Button>
                  </Link>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* CAM очередь */}
        <motion.div variants={fadeInUp} className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Очередь CAM</CardTitle>
                <CardDescription>Последние задачи обработки</CardDescription>
              </div>
              <Link href="/cam">
                <Button variant="ghost" size="sm">
                  Все задачи
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : camQueue.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <Wrench className="h-10 w-10 mb-2 opacity-30" />
                  <p className="text-sm">Нет активных задач</p>
                </div>
              ) : (
                <ul className="space-y-3">
                  {camQueue.map((item) => {
                    const camStatusLabels: Record<string, string> = {
                      Created: "Создана",
                      Processing: "В работе",
                      Completed: "Готово",
                      Failed: "Ошибка",
                    }
                    const statusLabel = camStatusLabels[item.status] || item.status
                    const isActive = item.status === "Processing"
                    const isFailed = item.status === "Failed"
                    const isCompleted = item.status === "Completed"

                    return (
                      <li key={item.id} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                        <div className="flex items-center gap-3">
                          {isCompleted && <CheckCircle2 className="h-4 w-4 text-success" />}
                          {isActive && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                          {isFailed && <AlertCircle className="h-4 w-4 text-destructive" />}
                          {!isCompleted && !isActive && !isFailed && <Clock className="h-4 w-4 text-muted-foreground" />}
                          <span className="text-sm font-medium">
                            {item.task === "DXF" ? "Раскрой DXF" : item.task === "GCODE" ? "G-code" : item.task}
                          </span>
                        </div>
                        <Badge
                          variant={isActive ? "default" : isFailed ? "destructive" : isCompleted ? "outline" : "secondary"}
                          className="text-xs"
                        >
                          {statusLabel}
                        </Badge>
                      </li>
                    )
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Последние заказы */}
        <div className="lg:col-span-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Последние заказы</CardTitle>
                <CardDescription>
                  {isDataLoading ? "Загрузка..." : `${orders.length} всего`}
                </CardDescription>
              </div>
              <Link href="/orders">
                <Button variant="ghost" size="sm">
                  Все заказы
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {isDataLoading ? (
                <div className="h-32 flex items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : recentOrders.length === 0 ? (
                <div className="h-32 flex flex-col items-center justify-center text-muted-foreground">
                  <FileText className="h-10 w-10 mb-2 opacity-30" />
                  <p className="text-sm">Нет заказов</p>
                  <Link href="/orders/new" className="mt-3">
                    <Button variant="outline" size="sm">Создать первый заказ</Button>
                  </Link>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">ID</th>
                        <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Название</th>
                        <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Статус</th>
                        <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Дата</th>
                        <th className="text-right py-3 px-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentOrders.map((order) => (
                        <tr key={order.id} className="border-b border-border/50 last:border-0 hover:bg-muted/30 transition-colors">
                          <td className="py-3 px-2">
                            <span className="font-mono text-sm text-muted-foreground">{order.id.slice(0, 8)}</span>
                          </td>
                          <td className="py-3 px-2">
                            <span className="font-medium">{order.name}</span>
                          </td>
                          <td className="py-3 px-2">
                            <Badge variant={statusVariant[order.status]}>
                              {statusLabels[order.status]}
                            </Badge>
                          </td>
                          <td className="py-3 px-2 text-muted-foreground text-sm">{order.date}</td>
                          <td className="py-3 px-2 text-right">
                            <Link href={`/bom?orderId=${order.id}`}>
                              <Button variant="ghost" size="sm">
                                Открыть
                              </Button>
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </StaggerContainer>
    </div>
  )
}
