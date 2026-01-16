"use client"

import { useSearchParams } from 'next/navigation'
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
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  ArrowUpDown,
  Download,
  Filter,
  Plus,
  Search,
  Settings2,
  FileText,
  Package,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/table-skeleton"

type BOMItem = {
  id: string
  sku: string
  name: string
  category: string
  material: string
  thickness?: number
  quantity: number
  unit: string
  supplier: string
  cost: number
  totalCost: number
  status: 'available' | 'ordered' | 'out_of_stock'
  version?: string
  notes?: string
}

interface ProductConfig {
  id: string
  name: string | null
  width_mm: number
  height_mm: number
  depth_mm: number
  material: string | null
  thickness_mm: number | null
  params: {
    furniture_type?: string
    body_material?: { type: string; thickness_mm?: number; color?: string }
    facade_material?: { type: string; thickness_mm?: number; color?: string }
    hardware?: { type: string; sku?: string; name?: string; qty: number }[]
    edge_band?: { type: string; thickness_mm?: number }
    door_count?: number
    drawer_count?: number
    shelf_count?: number
  }
  notes: string | null
}

interface OrderWithProducts {
  id: string
  customer_ref: string | null
  notes: string | null
  created_at: string
  products: ProductConfig[]
}

function convertOrderToBOM(order: OrderWithProducts): BOMItem[] {
  const items: BOMItem[] = []
  let id = 1

  for (const product of order.products) {
    const params = product.params

    // Добавляем материал корпуса
    if (params.body_material) {
      items.push({
        id: String(id++),
        sku: `MAT-${(params.body_material.type || 'UNKNOWN').toUpperCase().replace(/\s+/g, '-')}`,
        name: `${params.body_material.type || ''} ${params.body_material.color || ''}`.trim() || 'Материал корпуса',
        category: 'Плитные материалы',
        material: params.body_material.type || '',
        thickness: params.body_material.thickness_mm,
        quantity: 1,
        unit: 'лист',
        supplier: '-',
        cost: 0,
        totalCost: 0,
        status: 'available' as const,
      })
    }

    // Добавляем материал фасада
    if (params.facade_material && params.facade_material.type !== params.body_material?.type) {
      items.push({
        id: String(id++),
        sku: `MAT-${(params.facade_material.type || 'UNKNOWN').toUpperCase().replace(/\s+/g, '-')}`,
        name: `${params.facade_material.type || ''} ${params.facade_material.color || ''}`.trim() || 'Материал фасада',
        category: 'Плитные материалы',
        material: params.facade_material.type || '',
        thickness: params.facade_material.thickness_mm,
        quantity: 1,
        unit: 'лист',
        supplier: '-',
        cost: 0,
        totalCost: 0,
        status: 'available' as const,
      })
    }

    // Добавляем фурнитуру
    for (const hw of params.hardware || []) {
      items.push({
        id: String(id++),
        sku: hw.sku || `HW-${(hw.type || 'UNKNOWN').toUpperCase().replace(/\s+/g, '-')}`,
        name: hw.name || hw.type || 'Фурнитура',
        category: 'Фурнитура',
        material: '-',
        quantity: hw.qty || 1,
        unit: 'шт',
        supplier: '-',
        cost: 0,
        totalCost: 0,
        status: 'available' as const,
      })
    }

    // Добавляем кромку
    if (params.edge_band) {
      items.push({
        id: String(id++),
        sku: `EDGE-${params.edge_band.thickness_mm || 2}`,
        name: `Кромка ${params.edge_band.type || 'ПВХ'} ${params.edge_band.thickness_mm || 2}мм`,
        category: 'Кромочные материалы',
        material: params.edge_band.type || 'ПВХ',
        thickness: params.edge_band.thickness_mm,
        quantity: 10,
        unit: 'п.м',
        supplier: '-',
        cost: 0,
        totalCost: 0,
        status: 'available' as const,
      })
    }
  }

  return items
}

const mockBOMData: BOMItem[] = [
  {
    id: "1",
    sku: "PLT-18-2440-1220",
    name: "ЛДСП белая 18мм",
    category: "Плитные материалы",
    material: "ЛДСП",
    thickness: 18,
    quantity: 2,
    unit: "лист",
    supplier: "Кроношпан",
    cost: 2850.00,
    totalCost: 5700.00,
    status: "available",
    version: "v1.2",
    notes: "Основной материал корпуса"
  },
  {
    id: "2", 
    sku: "EDG-18-WHT",
    name: "Кромка ПВХ белая 18мм",
    category: "Кромочные материалы",
    material: "ПВХ",
    thickness: 0.4,
    quantity: 15,
    unit: "п.м",
    supplier: "Рехау",
    cost: 45.50,
    totalCost: 682.50,
    status: "available"
  },
  {
    id: "3",
    sku: "HNG-35-CLIP",
    name: "Петля накладная с доводчиком",
    category: "Фурнитура",
    material: "Сталь",
    quantity: 6,
    unit: "шт",
    supplier: "Blum",
    cost: 320.00,
    totalCost: 1920.00,
    status: "ordered",
    notes: "Для навесных модулей"
  },
  {
    id: "4",
    sku: "GUI-45-SOFT",
    name: "Направляющие полного выдвижения",
    category: "Фурнитура", 
    material: "Сталь",
    quantity: 4,
    unit: "пара",
    supplier: "Hettich",
    cost: 680.00,
    totalCost: 2720.00,
    status: "available"
  },
  {
    id: "5",
    sku: "HND-128-CHR",
    name: "Ручка-скоба хром 128мм",
    category: "Фурнитура",
    material: "Алюминий",
    quantity: 8,
    unit: "шт",
    supplier: "GTV",
    cost: 125.00,
    totalCost: 1000.00,
    status: "out_of_stock"
  },
]

export default function BomPage() {
  const { info } = useToast()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('orderId')

  const [order, setOrder] = useState<OrderWithProducts | null>(null)
  const [isLoadingOrder, setIsLoadingOrder] = useState(false)
  const [orderError, setOrderError] = useState<string | null>(null)

  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [globalFilter, setGlobalFilter] = useState("")
  const [isLoading, setIsLoading] = useState(true)

  // Load order data if orderId is present
  useEffect(() => {
    if (!orderId) return

    const loadOrder = async () => {
      setIsLoadingOrder(true)
      setOrderError(null)
      try {
        const response = await fetch(`/api/v1/orders/${orderId}`)
        if (!response.ok) {
          throw new Error('Заказ не найден')
        }
        const data: OrderWithProducts = await response.json()
        setOrder(data)
      } catch (err) {
        setOrderError(err instanceof Error ? err.message : 'Ошибка загрузки заказа')
      } finally {
        setIsLoadingOrder(false)
      }
    }

    loadOrder()
  }, [orderId])

  // Simulate data loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 1500)
    return () => clearTimeout(timer)
  }, [])

  const columns: ColumnDef<BOMItem>[] = useMemo(
    () => [
      {
        accessorKey: "sku",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Артикул
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => (
          <div className="font-medium">{row.getValue("sku")}</div>
        ),
      },
      {
        accessorKey: "name",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Наименование
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const name = row.getValue("name") as string
          const notes = row.original.notes
          return (
            <div>
              <div className="font-medium">{name}</div>
              {notes && <div className="text-sm text-muted-foreground">{notes}</div>}
            </div>
          )
        },
      },
      {
        accessorKey: "category",
        header: "Категория",
        cell: ({ row }) => (
          <Badge variant="secondary" className="text-xs">
            {row.getValue("category")}
          </Badge>
        ),
      },
      {
        accessorKey: "material",
        header: "Материал",
        cell: ({ row }) => {
          const material = row.getValue("material") as string
          const thickness = row.original.thickness
          return (
            <div>
              <div>{material}</div>
              {thickness && <div className="text-sm text-muted-foreground">{thickness}мм</div>}
            </div>
          )
        },
      },
      {
        accessorKey: "quantity",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Количество
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const quantity = row.getValue("quantity") as number
          const unit = row.original.unit
          return (
            <div className="text-right font-medium">
              {quantity} {unit}
            </div>
          )
        },
      },
      {
        accessorKey: "supplier",
        header: "Поставщик",
        cell: ({ row }) => (
          <div className="text-sm">{row.getValue("supplier")}</div>
        ),
      },
      {
        accessorKey: "cost",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Цена за ед.
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const cost = row.getValue("cost") as number
          const formatted = new Intl.NumberFormat("ru-RU", {
            style: "currency",
            currency: "RUB",
          }).format(cost)
          return <div className="text-right font-medium">{formatted}</div>
        },
      },
      {
        accessorKey: "totalCost",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="h-8 px-2"
            >
              Общая стоимость
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const totalCost = row.getValue("totalCost") as number
          const formatted = new Intl.NumberFormat("ru-RU", {
            style: "currency",
            currency: "RUB",
          }).format(totalCost)
          return <div className="text-right font-semibold">{formatted}</div>
        },
      },
      {
        accessorKey: "status",
        header: "Статус",
        cell: ({ row }) => {
          const status = row.getValue("status") as string
          const statusLabels = {
            available: "В наличии",
            ordered: "Заказано", 
            out_of_stock: "Нет в наличии"
          }
          const statusColors = {
            available: "default",
            ordered: "secondary",
            out_of_stock: "destructive"
          } as const
          
          return (
            <Badge variant={statusColors[status as keyof typeof statusColors]}>
              {statusLabels[status as keyof typeof statusLabels]}
            </Badge>
          )
        },
      },
    ],
    []
  )

  // Используем данные из API или mock
  const bomData = order ? convertOrderToBOM(order) : mockBOMData

  const table = useReactTable({
    data: bomData,
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

  const totalCost = useMemo(() => {
    return bomData.reduce((sum, item) => sum + item.totalCost, 0)
  }, [bomData])

  const handleCreateBom = () => {
    info("Создание BOM", "Функционал создания спецификации будет доступен в ближайшем обновлении")
  }

  const handleExport = () => {
    info("Экспорт BOM", "Функционал экспорта будет доступен в ближайшем обновлении")
  }

  if (isLoading) {
    return (
      <div className="p-6 w-full space-y-6">
        {/* Заголовок и действия */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Спецификация (BOM)</h1>
            <p className="text-muted-foreground">
              Детальная спецификация материалов и компонентов для производства
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button disabled variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Экспорт
            </Button>
            <Button disabled>
              <Plus className="h-4 w-4 mr-2" />
              Создать BOM
            </Button>
          </div>
        </div>

        {/* Статистика (скелетон) */}
        <StatCardSkeleton count={4} />

        {/* Таблица (скелетон) */}
        <Card>
          <div className="p-4">
            <TableSkeleton rows={8} columns={8} />
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 w-full space-y-6">
      {/* Заголовок и действия */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Спецификация (BOM)</h1>
          <p className="text-muted-foreground">
            Детальная спецификация материалов и компонентов для производства
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleExport} variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Экспорт
          </Button>
          <Button onClick={handleCreateBom}>
            <Plus className="h-4 w-4 mr-2" />
            Создать BOM
          </Button>
        </div>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <Package className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">Всего позиций</div>
          </div>
          <div className="text-2xl font-bold">{bomData.length}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">В наличии</div>
          </div>
          <div className="text-2xl font-bold text-green-600">
            {bomData.filter(item => item.status === 'available').length}
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">Заказано</div>
          </div>
          <div className="text-2xl font-bold text-blue-600">
            {bomData.filter(item => item.status === 'ordered').length}
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">Общая стоимость</div>
          </div>
          <div className="text-2xl font-bold">
            {new Intl.NumberFormat("ru-RU", {
              style: "currency",
              currency: "RUB",
            }).format(totalCost)}
          </div>
        </Card>
      </div>

      {/* Order info card */}
      {order && order.products[0] && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">
              Заказ: {order.products[0].name || 'Новое изделие'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Габариты:</span>
                <p className="font-medium">
                  {order.products[0].width_mm} × {order.products[0].height_mm} × {order.products[0].depth_mm} мм
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Материал:</span>
                <p className="font-medium">{order.products[0].material || '-'}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Толщина:</span>
                <p className="font-medium">{order.products[0].thickness_mm || '-'} мм</p>
              </div>
              <div>
                <span className="text-muted-foreground">ID:</span>
                <p className="font-medium font-mono text-xs">{order.id.slice(0, 8)}...</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading/error states */}
      {isLoadingOrder && (
        <Card className="mb-6">
          <CardContent className="py-8 text-center text-muted-foreground">
            Загрузка заказа...
          </CardContent>
        </Card>
      )}

      {orderError && (
        <Card className="mb-6 border-destructive">
          <CardContent className="py-4 text-center text-destructive">
            {orderError}
          </CardContent>
        </Card>
      )}

      {/* Фильтры и поиск */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Поиск по всем полям..."
              value={globalFilter ?? ""}
              onChange={(event) => setGlobalFilter(String(event.target.value))}
              className="pl-8 w-[300px]"
            />
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Filter className="h-4 w-4 mr-2" />
                Фильтры
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => {
                  return (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      className="capitalize"
                      checked={column.getIsVisible()}
                      onCheckedChange={(value) => column.toggleVisibility(!!value)}
                    >
                      {column.id}
                    </DropdownMenuCheckboxItem>
                  )
                })}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex items-center space-x-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Settings2 className="h-4 w-4 mr-2" />
                Настройки
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => {
                  return (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      className="capitalize"
                      checked={column.getIsVisible()}
                      onCheckedChange={(value) => column.toggleVisibility(!!value)}
                    >
                      {column.id}
                    </DropdownMenuCheckboxItem>
                  )
                })}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Таблица */}
      <Card>
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  )
                })}
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
          {table.getFilteredSelectedRowModel().rows.length} из{" "}
          {table.getFilteredRowModel().rows.length} строк выбрано
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
    </div>
  )
}
