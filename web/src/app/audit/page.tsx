"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { 
  ColumnDef, 
  flexRender, 
  getCoreRowModel, 
  getFilteredRowModel, 
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
  ColumnFiltersState,
  VisibilityState
} from "@tanstack/react-table"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { 
  Activity, 
  Shield, 
  AlertTriangle, 
  Users, 
  FileText, 
  Database,
  Eye,
  Download,
  Filter,
  Search,
  Calendar,
  Clock,
  User,
  Settings,
  ChevronLeft,
  ChevronRight
} from "lucide-react"
import { motion } from "framer-motion"

type AuditLogEntry = {
  id: string
  timestamp: string
  userId: string
  userEmail: string
  action: string
  resource: string
  resourceId: string
  ipAddress: string
  userAgent: string
  severity: "info" | "warning" | "error" | "critical"
  details: string
  status: "success" | "failed"
  duration: number
}

type SecurityEvent = {
  id: string
  timestamp: string
  eventType: string
  severity: "low" | "medium" | "high" | "critical"
  userId?: string
  ipAddress: string
  description: string
  resolved: boolean
}

type SystemMetric = {
  name: string
  value: number
  unit: string
  change: number
  status: "normal" | "warning" | "critical"
}

const mockAuditLogs: AuditLogEntry[] = [
  {
    id: "1",
    timestamp: "2025-01-15 14:30:22",
    userId: "user-1",
    userEmail: "technologist@furniture.ru",
    action: "Создание заказа",
    resource: "orders",
    resourceId: "order-2025-001",
    ipAddress: "192.168.1.100",
    userAgent: "Mozilla/5.0 Chrome/120.0.0.0",
    severity: "info",
    details: "Создан новый заказ на кухонный гарнитур",
    status: "success",
    duration: 1250
  },
  {
    id: "2",
    timestamp: "2025-01-15 14:25:15",
    userId: "admin-1",
    userEmail: "admin@furniture.ru",
    action: "Изменение настроек",
    resource: "settings",
    resourceId: "cam-config",
    ipAddress: "192.168.1.10",
    userAgent: "Mozilla/5.0 Chrome/120.0.0.0",
    severity: "warning",
    details: "Изменены параметры CAM обработки",
    status: "success",
    duration: 850
  },
  {
    id: "3",
    timestamp: "2025-01-15 14:20:08",
    userId: "user-2",
    userEmail: "operator@furniture.ru",
    action: "Неудачная авторизация",
    resource: "auth",
    resourceId: "",
    ipAddress: "185.123.45.67",
    userAgent: "Mozilla/5.0 Firefox/122.0",
    severity: "error",
    details: "Множественные попытки входа с неверным паролем",
    status: "failed",
    duration: 0
  }
]

const mockSecurityEvents: SecurityEvent[] = [
  {
    id: "1",
    timestamp: "2025-01-15 14:20:08",
    eventType: "Подозрительная активность",
    severity: "high",
    userId: "user-2",
    ipAddress: "185.123.45.67",
    description: "Множественные неудачные попытки входа",
    resolved: false
  },
  {
    id: "2", 
    timestamp: "2025-01-15 12:15:30",
    eventType: "Необычная геолокация",
    severity: "medium",
    userId: "user-1",
    ipAddress: "203.45.67.89",
    description: "Вход из нового местоположения (Казахстан)",
    resolved: true
  }
]

const mockSystemMetrics: SystemMetric[] = [
  { name: "Активные пользователи", value: 24, unit: "пользователей", change: 12, status: "normal" },
  { name: "Действий за час", value: 156, unit: "действий", change: -8, status: "normal" },
  { name: "Неудачных входов", value: 7, unit: "попыток", change: 150, status: "warning" },
  { name: "Системных ошибок", value: 2, unit: "ошибок", change: -50, status: "normal" }
]

const auditColumns: ColumnDef<AuditLogEntry>[] = [
  {
    accessorKey: "timestamp",
    header: "Время",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-gray-400" />
        <span className="text-sm">{row.getValue("timestamp")}</span>
      </div>
    ),
  },
  {
    accessorKey: "userEmail",
    header: "Пользователь",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <User className="h-4 w-4 text-gray-400" />
        <span className="text-sm">{row.getValue("userEmail")}</span>
      </div>
    ),
  },
  {
    accessorKey: "action",
    header: "Действие",
  },
  {
    accessorKey: "resource",
    header: "Ресурс",
    cell: ({ row }) => (
      <Badge variant="outline">
        {row.getValue("resource")}
      </Badge>
    ),
  },
  {
    accessorKey: "severity",
    header: "Критичность",
    cell: ({ row }) => {
      const severity = row.getValue("severity") as string
      const variants = {
        info: "default",
        warning: "secondary",
        error: "destructive",
        critical: "destructive"
      }
      return (
        <Badge variant={variants[severity as keyof typeof variants] as any}>
          {severity === "info" && "Инфо"}
          {severity === "warning" && "Внимание"}
          {severity === "error" && "Ошибка"}
          {severity === "critical" && "Критично"}
        </Badge>
      )
    },
  },
  {
    accessorKey: "status",
    header: "Статус",
    cell: ({ row }) => {
      const status = row.getValue("status") as string
      return (
        <Badge variant={status === "success" ? "default" : "destructive"}>
          {status === "success" ? "Успешно" : "Неудача"}
        </Badge>
      )
    },
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm">
            <Eye className="h-4 w-4" />
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Детали события аудита</DialogTitle>
            <DialogDescription>
              Подробная информация о событии {row.original.id}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium mb-1">Время</h4>
                <p className="text-sm text-gray-600">{row.original.timestamp}</p>
              </div>
              <div>
                <h4 className="font-medium mb-1">Пользователь</h4>
                <p className="text-sm text-gray-600">{row.original.userEmail}</p>
              </div>
              <div>
                <h4 className="font-medium mb-1">IP адрес</h4>
                <p className="text-sm text-gray-600">{row.original.ipAddress}</p>
              </div>
              <div>
                <h4 className="font-medium mb-1">Продолжительность</h4>
                <p className="text-sm text-gray-600">{row.original.duration}мс</p>
              </div>
            </div>
            <div>
              <h4 className="font-medium mb-1">Детали</h4>
              <p className="text-sm text-gray-600">{row.original.details}</p>
            </div>
            <div>
              <h4 className="font-medium mb-1">User Agent</h4>
              <p className="text-sm text-gray-600 break-all">{row.original.userAgent}</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    ),
  },
]

const securityColumns: ColumnDef<SecurityEvent>[] = [
  {
    accessorKey: "timestamp",
    header: "Время",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-gray-400" />
        <span className="text-sm">{row.getValue("timestamp")}</span>
      </div>
    ),
  },
  {
    accessorKey: "eventType",
    header: "Тип события",
  },
  {
    accessorKey: "severity",
    header: "Критичность",
    cell: ({ row }) => {
      const severity = row.getValue("severity") as string
      const variants = {
        low: "default",
        medium: "secondary", 
        high: "destructive",
        critical: "destructive"
      }
      return (
        <Badge variant={variants[severity as keyof typeof variants] as any}>
          {severity === "low" && "Низкая"}
          {severity === "medium" && "Средняя"}
          {severity === "high" && "Высокая"}
          {severity === "critical" && "Критическая"}
        </Badge>
      )
    },
  },
  {
    accessorKey: "ipAddress",
    header: "IP адрес",
  },
  {
    accessorKey: "resolved",
    header: "Статус",
    cell: ({ row }) => {
      const resolved = row.getValue("resolved") as boolean
      return (
        <Badge variant={resolved ? "default" : "secondary"}>
          {resolved ? "Решено" : "Активно"}
        </Badge>
      )
    },
  },
]

export default function AuditPage() {
  const [auditSorting, setAuditSorting] = useState<SortingState>([])
  const [auditColumnFilters, setAuditColumnFilters] = useState<ColumnFiltersState>([])
  const [auditColumnVisibility, setAuditColumnVisibility] = useState<VisibilityState>({})
  
  const [securitySorting, setSecuritySorting] = useState<SortingState>([])
  const [securityColumnFilters, setSecurityColumnFilters] = useState<ColumnFiltersState>([])
  const [securityColumnVisibility, setSecurityColumnVisibility] = useState<VisibilityState>({})

  const auditTable = useReactTable({
    data: mockAuditLogs,
    columns: auditColumns,
    onSortingChange: setAuditSorting,
    onColumnFiltersChange: setAuditColumnFilters,
    onColumnVisibilityChange: setAuditColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      sorting: auditSorting,
      columnFilters: auditColumnFilters,
      columnVisibility: auditColumnVisibility,
    },
  })

  const securityTable = useReactTable({
    data: mockSecurityEvents,
    columns: securityColumns,
    onSortingChange: setSecuritySorting,
    onColumnFiltersChange: setSecurityColumnFilters,
    onColumnVisibilityChange: setSecurityColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      sorting: securitySorting,
      columnFilters: securityColumnFilters,
      columnVisibility: securityColumnVisibility,
    },
  })

  return (
    <div className="p-6 w-full space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Аудит</h1>
          <p className="text-gray-600">Мониторинг безопасности и активности пользователей</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Экспорт
          </Button>
        </div>
      </div>

      {/* Метрики системы */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {mockSystemMetrics.map((metric, index) => (
          <motion.div
            key={metric.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{metric.name}</CardTitle>
                {metric.status === "warning" ? (
                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                ) : metric.status === "critical" ? (
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                ) : (
                  <Activity className="h-4 w-4 text-green-500" />
                )}
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metric.value} <span className="text-sm font-normal text-gray-600">{metric.unit}</span>
                </div>
                <p className={`text-xs ${metric.change >= 0 ? "text-green-600" : "text-red-600"}`}>
                  {metric.change >= 0 ? "+" : ""}{metric.change}% за последний час
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Основное содержимое */}
      <Tabs defaultValue="audit" className="space-y-4">
        <TabsList>
          <TabsTrigger value="audit" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Журнал аудита
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            События безопасности
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Аналитика
          </TabsTrigger>
        </TabsList>

        <TabsContent value="audit" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Журнал аудита</CardTitle>
              <CardDescription>
                Все действия пользователей в системе
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Фильтры */}
              <div className="flex items-center gap-4 py-4">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Поиск по действиям..."
                    value={(auditTable.getColumn("action")?.getFilterValue() as string) ?? ""}
                    onChange={(event) =>
                      auditTable.getColumn("action")?.setFilterValue(event.target.value)
                    }
                    className="w-60"
                  />
                </div>
                <Select
                  value={(auditTable.getColumn("severity")?.getFilterValue() as string) ?? ""}
                  onValueChange={(value) =>
                    auditTable.getColumn("severity")?.setFilterValue(value === "all" ? "" : value)
                  }
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Критичность" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все</SelectItem>
                    <SelectItem value="info">Инфо</SelectItem>
                    <SelectItem value="warning">Внимание</SelectItem>
                    <SelectItem value="error">Ошибка</SelectItem>
                    <SelectItem value="critical">Критично</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={(auditTable.getColumn("status")?.getFilterValue() as string) ?? ""}
                  onValueChange={(value) =>
                    auditTable.getColumn("status")?.setFilterValue(value === "all" ? "" : value)
                  }
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Статус" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все</SelectItem>
                    <SelectItem value="success">Успешно</SelectItem>
                    <SelectItem value="failed">Неудача</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Таблица */}
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    {auditTable.getHeaderGroups().map((headerGroup) => (
                      <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <TableHead key={header.id}>
                            {header.isPlaceholder
                              ? null
                              : flexRender(
                                  header.column.columnDef.header,
                                  header.getContext()
                                )}
                          </TableHead>
                        ))}
                      </TableRow>
                    ))}
                  </TableHeader>
                  <TableBody>
                    {auditTable.getRowModel().rows?.length ? (
                      auditTable.getRowModel().rows.map((row) => (
                        <TableRow key={row.id}>
                          {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id}>
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={auditColumns.length} className="h-24 text-center">
                          Нет данных для отображения
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Пагинация */}
              <div className="flex items-center justify-between space-x-2 py-4">
                <div className="flex-1 text-sm text-muted-foreground">
                  Отображено {auditTable.getFilteredRowModel().rows.length} записей
                </div>
                <div className="space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => auditTable.previousPage()}
                    disabled={!auditTable.getCanPreviousPage()}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Назад
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => auditTable.nextPage()}
                    disabled={!auditTable.getCanNextPage()}
                  >
                    Вперед
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>События безопасности</CardTitle>
              <CardDescription>
                Подозрительная активность и нарушения безопасности
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Фильтры */}
              <div className="flex items-center gap-4 py-4">
                <Select
                  value={(securityTable.getColumn("severity")?.getFilterValue() as string) ?? ""}
                  onValueChange={(value) =>
                    securityTable.getColumn("severity")?.setFilterValue(value === "all" ? "" : value)
                  }
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Критичность" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все</SelectItem>
                    <SelectItem value="low">Низкая</SelectItem>
                    <SelectItem value="medium">Средняя</SelectItem>
                    <SelectItem value="high">Высокая</SelectItem>
                    <SelectItem value="critical">Критическая</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={(securityTable.getColumn("resolved")?.getFilterValue() as string) ?? ""}
                  onValueChange={(value) =>
                    securityTable.getColumn("resolved")?.setFilterValue(
                      value === "all" ? "" : value === "resolved"
                    )
                  }
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Статус" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все</SelectItem>
                    <SelectItem value="resolved">Решено</SelectItem>
                    <SelectItem value="active">Активно</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Таблица */}
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    {securityTable.getHeaderGroups().map((headerGroup) => (
                      <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <TableHead key={header.id}>
                            {header.isPlaceholder
                              ? null
                              : flexRender(
                                  header.column.columnDef.header,
                                  header.getContext()
                                )}
                          </TableHead>
                        ))}
                      </TableRow>
                    ))}
                  </TableHeader>
                  <TableBody>
                    {securityTable.getRowModel().rows?.length ? (
                      securityTable.getRowModel().rows.map((row) => (
                        <TableRow key={row.id}>
                          {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id}>
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={securityColumns.length} className="h-24 text-center">
                          Нет данных для отображения
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Пагинация */}
              <div className="flex items-center justify-between space-x-2 py-4">
                <div className="flex-1 text-sm text-muted-foreground">
                  Отображено {securityTable.getFilteredRowModel().rows.length} записей
                </div>
                <div className="space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => securityTable.previousPage()}
                    disabled={!securityTable.getCanPreviousPage()}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Назад
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => securityTable.nextPage()}
                    disabled={!securityTable.getCanNextPage()}
                  >
                    Вперед
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Активность пользователей</CardTitle>
                <CardDescription>
                  Статистика активности за последние 24 часа
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Всего действий</span>
                    <span className="font-medium">1,247</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Уникальных пользователей</span>
                    <span className="font-medium">24</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Успешных операций</span>
                    <span className="font-medium text-green-600">96.8%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Средняя длительность сессии</span>
                    <span className="font-medium">2ч 15м</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Безопасность</CardTitle>
                <CardDescription>
                  Показатели безопасности системы
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Активных угроз</span>
                    <span className="font-medium text-orange-600">1</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Заблокированных IP</span>
                    <span className="font-medium">3</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Неудачных входов</span>
                    <span className="font-medium text-red-600">7</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Уровень безопасности</span>
                    <Badge variant="secondary">Средний</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Популярные действия</CardTitle>
                <CardDescription>
                  Наиболее частые действия пользователей
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Создание заказов</span>
                    <span className="font-medium">342</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Просмотр спецификаций</span>
                    <span className="font-medium">289</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">CAM обработка</span>
                    <span className="font-medium">156</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Подбор фурнитуры</span>
                    <span className="font-medium">134</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Системные ресурсы</CardTitle>
                <CardDescription>
                  Использование ресурсов сервера
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Использование CPU</span>
                    <span className="font-medium">23%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Использование RAM</span>
                    <span className="font-medium">67%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Место на диске</span>
                    <span className="font-medium">45%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Активных подключений</span>
                    <span className="font-medium">24</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
