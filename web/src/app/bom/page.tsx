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
import { Card } from "@/components/ui/card"
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
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [globalFilter, setGlobalFilter] = useState("")
  const [isLoading, setIsLoading] = useState(true)

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

  const table = useReactTable({
    data: mockBOMData,
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
    return mockBOMData.reduce((sum, item) => sum + item.totalCost, 0)
  }, [])

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
          <div className="text-2xl font-bold">{mockBOMData.length}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">В наличии</div>
          </div>
          <div className="text-2xl font-bold text-green-600">
            {mockBOMData.filter(item => item.status === 'available').length}
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">Заказано</div>
          </div>
          <div className="text-2xl font-bold text-blue-600">
            {mockBOMData.filter(item => item.status === 'ordered').length}
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
