"use client"

import { useState, useMemo, useEffect } from "react"
import {
  useReactTable,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type SortingState,
  type ColumnFiltersState,
  type VisibilityState,
  type ColumnDef,
} from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ArrowUpDown,
  Eye,
  Download,
  Copy,
  Filter,
  Calendar,
  Package,
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  TrendingUp,
  Repeat,
  Loader2,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { DateRangeFilter, type DateRange } from "@/components/date-range-filter"

type OrderStatus = 'completed' | 'cancelled' | 'processing' | 'failed'

type HistoryOrder = {
  id: string
  orderNumber: string
  customerName: string
  productName: string
  status: OrderStatus
  createdAt: string
  completedAt?: string
  totalAmount: number
  itemsCount: number
  duration?: string
  notes?: string
  tags?: string[]
}

// Пустые начальные данные (mock убран)

export default function HistoryPage() {
  const { toast } = useToast()
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [globalFilter, setGlobalFilter] = useState("")
  const [selectedOrder, setSelectedOrder] = useState<HistoryOrder | null>(null)
  const [historyOrders, setHistoryOrders] = useState<HistoryOrder[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [dateRange, setDateRange] = useState<DateRange | undefined>()

  // Загрузка завершённых заказов из API
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await fetch('/api/v1/orders')
        if (response.ok) {
          const data = await response.json()
          if (data && data.length > 0) {
            // Преобразуем формат API в формат UI
            const formattedOrders: HistoryOrder[] = data.map((order: {
              id: string
              customer_ref?: string
              notes?: string
              created_at: string
            }, index: number) => ({
              id: order.id,
              orderNumber: `ORD-${order.id.slice(0, 8).toUpperCase()}`,
              customerName: order.customer_ref || "Не указан",
              productName: order.notes || "Не указано",
              status: "completed" as OrderStatus, // TODO: добавить статус в API
              createdAt: order.created_at,
              completedAt: order.created_at, // TODO: добавить completedAt в API
              totalAmount: 0, // TODO: добавить цену в API
              itemsCount: 1,
            }))
            setHistoryOrders(formattedOrders)
          }
        }
      } catch (error) {
        console.error('Failed to load history:', error)
        // При ошибке оставляем пустой массив
      } finally {
        setIsLoading(false)
      }
    }

    loadHistory()
  }, [])

  // Фильтрация по дате
  const filteredOrders = useMemo(() => {
    if (!dateRange?.from) return historyOrders

    return historyOrders.filter(order => {
      const orderDate = new Date(order.createdAt)
      const from = dateRange.from
      const to = dateRange.to || dateRange.from

      // Устанавливаем время на начало и конец дня для корректного сравнения
      const fromStart = new Date(from)
      fromStart.setHours(0, 0, 0, 0)

      const toEnd = new Date(to)
      toEnd.setHours(23, 59, 59, 999)

      return orderDate >= fromStart && orderDate <= toEnd
    })
  }, [historyOrders, dateRange])

  const columns: ColumnDef<HistoryOrder>[] = useMemo(
    () => [
      {
        accessorKey: "orderNumber",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              № Заказа
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => (
          <div className="font-medium">{row.getValue("orderNumber")}</div>
        ),
      },
      {
        accessorKey: "customerName",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Клиент
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => (
          <div className="font-medium">{row.getValue("customerName")}</div>
        ),
      },
      {
        accessorKey: "productName",
        header: "Продукт",
        cell: ({ row }) => {
          const name = row.getValue("productName") as string
          const tags = row.original.tags
          return (
            <div>
              <div className="font-medium">{name}</div>
              {tags && (
                <div className="flex gap-1 mt-1">
                  {tags.map((tag, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )
        },
      },
      {
        accessorKey: "status",
        header: "Статус",
        cell: ({ row }) => {
          const status = row.getValue("status") as OrderStatus
          const statusConfig = {
            completed: { label: "Завершен", color: "default", icon: CheckCircle },
            cancelled: { label: "Отменен", color: "secondary", icon: XCircle },
            processing: { label: "В процессе", color: "default", icon: Clock },
            failed: { label: "Ошибка", color: "destructive", icon: AlertCircle }
          } as const
          
          const config = statusConfig[status]
          const Icon = config.icon
          
          return (
            <Badge variant={config.color} className="flex items-center space-x-1">
              <Icon className="h-3 w-3" />
              <span>{config.label}</span>
            </Badge>
          )
        },
      },
      {
        accessorKey: "createdAt",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Дата создания
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const date = new Date(row.getValue("createdAt"))
          return (
            <div className="text-sm">
              {date.toLocaleDateString('ru-RU')}
              <div className="text-muted-foreground text-xs">
                {date.toLocaleTimeString('ru-RU')}
              </div>
            </div>
          )
        },
      },
      {
        accessorKey: "duration",
        header: "Длительность",
        cell: ({ row }) => {
          const duration = row.original.duration
          if (!duration) return <span className="text-muted-foreground">—</span>
          return <div className="text-sm">{duration}</div>
        },
      },
      {
        accessorKey: "totalAmount",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Сумма
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const amount = row.getValue("totalAmount") as number
          const formatted = new Intl.NumberFormat("ru-RU", {
            style: "currency",
            currency: "RUB",
          }).format(amount)
          return <div className="text-right font-medium">{formatted}</div>
        },
      },
      {
        id: "actions",
        cell: ({ row }) => {
          const order = row.original
          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-8 w-8 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Действия</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setSelectedOrder(order)}>
                  <Eye className="h-4 w-4 mr-2" />
                  Просмотр
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => {
                  navigator.clipboard.writeText(order.orderNumber)
                  toast({ title: "Скопировано", description: "Номер заказа скопирован в буфер обмена" })
                }}>
                  <Copy className="h-4 w-4 mr-2" />
                  Копировать номер
                </DropdownMenuItem>
                {order.status === 'completed' && (
                  <>
                    <DropdownMenuItem>
                      <Download className="h-4 w-4 mr-2" />
                      Скачать файлы
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Repeat className="h-4 w-4 mr-2" />
                      Повторить заказ
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )
        },
      },
    ],
    []
  )

  const table = useReactTable({
    data: filteredOrders,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: "includesString",
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      globalFilter,
    },
  })

  const stats = useMemo(() => {
    const total = filteredOrders.length
    const completed = filteredOrders.filter(order => order.status === 'completed').length
    const cancelled = filteredOrders.filter(order => order.status === 'cancelled').length
    const totalRevenue = filteredOrders
      .filter(order => order.status === 'completed')
      .reduce((sum, order) => sum + order.totalAmount, 0)

    return { total, completed, cancelled, totalRevenue }
  }, [filteredOrders])

  return (
    <div className="p-6 w-full space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">История заказов</h1>
          <p className="text-muted-foreground">
            Архив всех заказов с возможностью фильтрации и детального просмотра
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DateRangeFilter
            value={dateRange}
            onChange={setDateRange}
            placeholder="Период"
          />
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Экспорт
          </Button>
        </div>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <Package className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">Всего заказов</div>
          </div>
          <div className="text-2xl font-bold">{stats.total}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <div className="text-sm font-medium">Завершено</div>
          </div>
          <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <XCircle className="h-4 w-4 text-gray-500" />
            <div className="text-sm font-medium">Отменено</div>
          </div>
          <div className="text-2xl font-bold text-gray-500">{stats.cancelled}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-4 w-4 text-blue-600" />
            <div className="text-sm font-medium">Выручка</div>
          </div>
          <div className="text-2xl font-bold">
            {new Intl.NumberFormat("ru-RU", {
              style: "currency",
              currency: "RUB",
              notation: "compact",
              maximumFractionDigits: 1
            }).format(stats.totalRevenue)}
          </div>
        </Card>
      </div>

      {/* Фильтры */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Фильтры и поиск</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col space-y-4 md:flex-row md:space-y-0 md:space-x-4">
            <div className="flex-1">
              <Input
                placeholder="Поиск по номеру заказа, клиенту или продукту..."
                value={globalFilter ?? ""}
                onChange={(event) => setGlobalFilter(String(event.target.value))}
                className="w-full"
              />
            </div>
            <Select
              value={(table.getColumn("status")?.getFilterValue() as string) ?? "all"}
              onValueChange={(value) => 
                table.getColumn("status")?.setFilterValue(value === "all" ? "" : value)
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Статус" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все статусы</SelectItem>
                <SelectItem value="completed">Завершен</SelectItem>
                <SelectItem value="cancelled">Отменен</SelectItem>
                <SelectItem value="failed">Ошибка</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Таблица */}
      <Card>
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
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
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
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
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  Нет результатов
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Пагинация */}
      <div className="flex items-center justify-between space-x-2 py-4">
        <div className="text-sm text-muted-foreground">
          Показано {table.getFilteredRowModel().rows.length} из{" "}
          {filteredOrders.length} заказов
          {dateRange?.from && ` (всего: ${historyOrders.length})`}
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            <p className="text-sm font-medium">Строк на странице</p>
            <select
              value={table.getState().pagination.pageSize}
              onChange={(e) => {
                table.setPageSize(Number(e.target.value))
              }}
              className="h-8 w-[70px] rounded border border-input bg-background px-2 text-sm"
            >
              {[10, 20, 30, 40, 50].map((pageSize) => (
                <option key={pageSize} value={pageSize}>
                  {pageSize}
                </option>
              ))}
            </select>
          </div>
          <div className="flex w-[100px] items-center justify-center text-sm font-medium">
            Страница {table.getState().pagination.pageIndex + 1} из{" "}
            {table.getPageCount()}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => table.setPageIndex(0)}
              disabled={!table.getCanPreviousPage()}
            >
              <ChevronsLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => table.setPageIndex(table.getPageCount() - 1)}
              disabled={!table.getCanNextPage()}
            >
              <ChevronsRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Модальное окно детального просмотра */}
      <Dialog open={!!selectedOrder} onOpenChange={() => setSelectedOrder(null)}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Детали заказа {selectedOrder?.orderNumber}</DialogTitle>
            <DialogDescription>
              Подробная информация о заказе
            </DialogDescription>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Клиент:</label>
                  <p className="text-sm text-muted-foreground">{selectedOrder.customerName}</p>
                </div>
                <div>
                  <label className="text-sm font-medium">Продукт:</label>
                  <p className="text-sm text-muted-foreground">{selectedOrder.productName}</p>
                </div>
                <div>
                  <label className="text-sm font-medium">Дата создания:</label>
                  <p className="text-sm text-muted-foreground">
                    {new Date(selectedOrder.createdAt).toLocaleString('ru-RU')}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium">Дата завершения:</label>
                  <p className="text-sm text-muted-foreground">
                    {selectedOrder.completedAt 
                      ? new Date(selectedOrder.completedAt).toLocaleString('ru-RU')
                      : '—'
                    }
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium">Количество позиций:</label>
                  <p className="text-sm text-muted-foreground">{selectedOrder.itemsCount}</p>
                </div>
                <div>
                  <label className="text-sm font-medium">Общая сумма:</label>
                  <p className="text-sm text-muted-foreground">
                    {new Intl.NumberFormat("ru-RU", {
                      style: "currency",
                      currency: "RUB",
                    }).format(selectedOrder.totalAmount)}
                  </p>
                </div>
              </div>
              {selectedOrder.notes && (
                <div>
                  <label className="text-sm font-medium">Примечания:</label>
                  <p className="text-sm text-muted-foreground">{selectedOrder.notes}</p>
                </div>
              )}
              {selectedOrder.tags && selectedOrder.tags.length > 0 && (
                <div>
                  <label className="text-sm font-medium">Теги:</label>
                  <div className="flex gap-1 mt-1">
                    {selectedOrder.tags.map((tag, index) => (
                      <Badge key={index} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
