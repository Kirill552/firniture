"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  CheckCircle,
  Package,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"

type Order = {
  id: string
  customer_ref: string | null
  notes: string | null
  created_at: string
  status?: string
}

type ExportFormat = "excel" | "csv"

export default function IntegrationsPage() {
  const { toast } = useToast()
  const [orders, setOrders] = useState<Order[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [exportingOrderId, setExportingOrderId] = useState<string | null>(null)
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("excel")

  // Загрузка заказов
  useEffect(() => {
    async function fetchOrders() {
      try {
        const response = await fetch("/api/v1/orders")
        if (response.ok) {
          const data = await response.json()
          setOrders(data)
        }
      } catch (error) {
        console.error("Failed to fetch orders:", error)
        toast({
          title: "Ошибка",
          description: "Не удалось загрузить список заказов",
          variant: "destructive",
        })
      } finally {
        setIsLoading(false)
      }
    }
    fetchOrders()
  }, [toast])

  // Экспорт заказа
  const handleExport = async (orderId: string) => {
    setExportingOrderId(orderId)

    try {
      const response = await fetch("/api/v1/integrations/1c/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: orderId,
          format: selectedFormat,
        }),
      })

      if (!response.ok) {
        throw new Error("Export failed")
      }

      const data = await response.json()

      // Открываем ссылку для скачивания
      if (data.download_url) {
        window.open(data.download_url, "_blank")
        toast({
          title: "Экспорт готов",
          description: `Файл ${data.filename} готов к скачиванию`,
        })
      }
    } catch (error) {
      console.error("Export error:", error)
      toast({
        title: "Ошибка экспорта",
        description: "Не удалось экспортировать заказ",
        variant: "destructive",
      })
    } finally {
      setExportingOrderId(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  return (
    <div className="p-6 w-full space-y-6">
      {/* Заголовок */}
      <div>
        <h1 className="text-2xl font-bold">Экспорт в 1С</h1>
        <p className="text-muted-foreground">
          Выгрузка заказов в формате Excel для импорта в 1С:Предприятие
        </p>
      </div>

      {/* Инструкция */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            Как импортировать в 1С
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>1. Выберите заказ и нажмите <strong>Скачать</strong></p>
          <p>2. Откройте 1С:УНФ или 1С:ERP → Администрирование → Загрузка данных из файла</p>
          <p>3. Выберите скачанный Excel файл и следуйте инструкциям мастера</p>
          <p className="text-xs pt-2">
            Файл содержит 4 листа: Заказ, Изделия, Панели, Фурнитура
          </p>
        </CardContent>
      </Card>

      {/* Настройки экспорта */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Настройки экспорта</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium">Формат файла:</label>
            <Select value={selectedFormat} onValueChange={(v) => setSelectedFormat(v as ExportFormat)}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="excel">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="h-4 w-4" />
                    Excel (.xlsx)
                  </div>
                </SelectItem>
                <SelectItem value="csv">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    CSV (.zip)
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Список заказов */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Package className="h-5 w-5" />
            Заказы для экспорта
          </CardTitle>
          <CardDescription>
            Выберите заказ для выгрузки в 1С
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : orders.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>Нет заказов для экспорта</p>
              <p className="text-sm">Создайте заказ через диалог с ИИ-технологом</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID заказа</TableHead>
                  <TableHead>Клиент</TableHead>
                  <TableHead>Дата создания</TableHead>
                  <TableHead>Статус</TableHead>
                  <TableHead className="text-right">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-mono text-xs">
                      {order.id.slice(0, 8)}...
                    </TableCell>
                    <TableCell>
                      {order.customer_ref || "—"}
                    </TableCell>
                    <TableCell>
                      {formatDate(order.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={order.status === "completed" ? "default" : "secondary"}>
                        {order.status === "completed" ? "Готов" : "В работе"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        onClick={() => handleExport(order.id)}
                        disabled={exportingOrderId === order.id}
                      >
                        {exportingOrderId === order.id ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Экспорт...
                          </>
                        ) : (
                          <>
                            <Download className="h-4 w-4 mr-2" />
                            Скачать
                          </>
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
