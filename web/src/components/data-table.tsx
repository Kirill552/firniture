import * as React from "react"
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  SortingState,
  ColumnFiltersState,
  RowSelectionState,
  VisibilityState,
} from "@tanstack/react-table"

import { ArrowUpDown, ChevronDown, Download, Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useIsMobile } from "@/hooks/use-mobile"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  tableId?: string
}

export function DataTable<TData, TValue>({
  columns,
  data,
  tableId = "datatable",
}: DataTableProps<TData, TValue>) {
  const isMobile = useIsMobile()
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({})
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})

  // Колонка выбора строк добавляется автоматически
  const columnsWithSelection = React.useMemo<ColumnDef<TData, any>[]>(() => {
    const selectionCol: ColumnDef<TData, any> = {
      id: "select",
      header: () => null,
      cell: () => null,
      enableHiding: false,
      enableSorting: false,
    }
    return [selectionCol, ...columns]
  }, [columns])

  const table = useReactTable({
    data,
    columns: columnsWithSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      rowSelection,
      columnVisibility,
    },
  })

  // ======= Persistence (localStorage) =======
  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(`datatable:${tableId}`)
      if (!raw) return
      const saved = JSON.parse(raw) as {
        sorting?: SortingState
        columnFilters?: ColumnFiltersState
        columnVisibility?: VisibilityState
      }
      if (saved.sorting) setSorting(saved.sorting)
      if (saved.columnFilters) setColumnFilters(saved.columnFilters)
      if (saved.columnVisibility) setColumnVisibility(saved.columnVisibility)
    } catch {}
  }, [tableId])

  React.useEffect(() => {
    const payload = JSON.stringify({ sorting, columnFilters, columnVisibility })
    try {
      localStorage.setItem(`datatable:${tableId}`, payload)
    } catch {}
  }, [sorting, columnFilters, columnVisibility, tableId])

  // ========= Экспорт =========
  function toCSV(rows: TData[], visibleCols: string[]) {
    const headers = visibleCols
    const body = rows.map((row: any) =>
      headers.map((key) => JSON.stringify(row[key] ?? "")).join(",")
    )
    return [headers.join(","), ...body].join("\n")
  }

  function downloadBlob(content: string, filename: string, type = "text/csv;charset=utf-8;") {
    const blob = new Blob([content], { type })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExport = (onlySelected = false, format: "csv" | "xlsx" = "csv") => {
    const rows = (onlySelected ? table.getFilteredSelectedRowModel().rows : table.getFilteredRowModel().rows)
      .map(r => r.original as TData)
    const visibleCols = table
      .getAllLeafColumns()
      .filter(c => c.getIsVisible() && c.id !== "select")
      .map(c => c.id)
    if (format === "csv") {
      const csv = toCSV(rows, visibleCols)
      downloadBlob(csv, `${tableId}-${onlySelected ? "selected" : "all"}.csv`)
    } else {
      // Простейший TSV как fallback для Excel
      const headers = visibleCols.join("\t")
      const body = (rows as any[]).map(row => visibleCols.map(k => row[k] ?? "").join("\t")).join("\n")
      downloadBlob([headers, body].join("\n"), `${tableId}-${onlySelected ? "selected" : "all"}.xls`, "application/vnd.ms-excel")
    }
  }

  return (
    <div className="w-full">
      <div className="flex items-center gap-2 py-4">
        <Input
          placeholder="Фильтр заказов..."
          value={(table.getState().columnFilters[0]?.value ?? '') as string}
          onChange={(e) => {
            const firstFilterable = table
              .getAllLeafColumns()
              .find((c) => c.getCanFilter() && c.id !== "select")?.id
            if (firstFilterable) {
              table.getColumn(firstFilterable)?.setFilterValue(e.currentTarget.value)
            }
          }}
          className="max-w-sm"
        />
        {table.getFilteredSelectedRowModel().rows.length > 0 ? (
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => handleExport(true, "csv")}>Экспорт выделенных (CSV)</Button>
            <Button size="sm" variant="outline" onClick={() => handleExport(true, "xlsx")}>Экспорт выделенных (Excel)</Button>
          </div>
        ) : null}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="ml-auto">
              Колонки <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Выберите колонки</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {table.getAllColumns().filter((c) => c.id !== "select").map((column) => {
              return (
                <DropdownMenuCheckboxItem
                  key={column.id}
                  className="capitalize"
                  checked={column.getIsVisible()}
                  onCheckedChange={(value) => column.toggleVisibility(value)}
                >
                  {column.id}
                </DropdownMenuCheckboxItem>
              )
            })}
          </DropdownMenuContent>
        </DropdownMenu>
        <div className="ml-2 flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => handleExport(false, "csv")}>
            <Download className="h-4 w-4 mr-1" /> CSV
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleExport(false, "xlsx")}>
            <Download className="h-4 w-4 mr-1" /> Excel
          </Button>
        </div>
      </div>
      <div className="rounded-md border">
        {!isMobile ? (
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    return (
                      <TableHead key={header.id}>
                        {header.isPlaceholder ? null : (
                          <div className="flex items-center space-x-2">
                            {header.id === "select" ? (
                              <Checkbox
                                data-testid="table-select-all"
                                checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
                                onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
                                aria-label="Выбрать все"
                              />
                            ) : null}
                            {header.id !== "select" && (
                              <Button
                                variant="ghost"
                                onClick={header.column.getToggleSortingHandler()}
                                className="px-2 h-8 w-8"
                              >
                                <ArrowUpDown className="ml-2 h-4 w-4" />
                              </Button>
                            )}
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                          </div>
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
                        {cell.column.id === "select" ? (
                          <Checkbox
                            data-testid={`table-select-row-${row.id}`}
                            checked={row.getIsSelected()}
                            onCheckedChange={(value) => row.toggleSelected(!!value)}
                            aria-label="Выбрать строку"
                          />
                        ) : (
                          flexRender(cell.column.columnDef.cell, cell.getContext())
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={columns.length} className="h-48 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Search className="h-12 w-12 text-muted-foreground" />
                      <h3 className="text-lg font-semibold text-muted-foreground">
                        Нет данных для отображения
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        Попробуйте изменить фильтры или добавить новые записи.
                      </p>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        ) : (
          <div className="divide-y">
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <div key={row.id} className="p-3">
                  <div className="flex items-start justify-between">
                    <div className="text-sm font-medium text-foreground">Запись</div>
                    <Checkbox
                      checked={row.getIsSelected()}
                      onCheckedChange={(value) => row.toggleSelected(!!value)}
                      aria-label="Выбрать запись"
                    />
                  </div>
                  <div className="mt-2 grid grid-cols-1 gap-2">
                    {row.getVisibleCells().filter(c => c.column.id !== "select").map((cell) => (
                      <div key={cell.id} className="flex items-start justify-between gap-4">
                        <div className="text-xs text-muted-foreground capitalize">{cell.column.id}</div>
                        <div className="text-sm text-foreground max-w-[60%]">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-6 text-center">
                <div className="flex flex-col items-center justify-center space-y-2">
                  <Search className="h-12 w-12 text-muted-foreground" />
                  <h3 className="text-lg font-semibold text-muted-foreground">Нет данных для отображения</h3>
                  <p className="text-sm text-muted-foreground">Попробуйте изменить фильтры или добавить новые записи.</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="flex items-center justify-end space-x-2 py-4">
        <div className="flex-1 text-sm text-muted-foreground">
          {table.getFilteredSelectedRowModel().rows.length} из {table.getFilteredRowModel().rows.length} строк
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            Предыдущая
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            Следующая
          </Button>
        </div>
      </div>
    </div>
  )
}