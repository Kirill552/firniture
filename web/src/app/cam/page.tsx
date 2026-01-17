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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  ArrowUpDown,
  Download,
  Play,
  Pause,
  RotateCcw,
  Settings,
  FileCode,
  Eye,
  RefreshCw,
  MoreHorizontal,
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle,
  Upload,
  Zap,
} from "lucide-react"
import { StatCardSkeleton, TableSkeleton, ChartSkeleton } from "@/components/ui/table-skeleton"
import { useToast } from "@/hooks/use-toast"
import { SettingsIndicator } from "@/components/settings-indicator"

type CAMJobStatus = 'Created' | 'Processing' | 'Completed' | 'Failed'
type CAMJobType = 'DXF' | 'GCODE'

type CAMJob = {
  id: string
  orderId: string
  type: CAMJobType
  name: string
  description?: string
  status: CAMJobStatus
  createdAt: string
  completedAt?: string
  progress?: number
  estimatedTime?: string
  actualTime?: string
  fileSize?: number
  downloadUrl?: string
  error?: string
  parameters?: {
    material?: string
    thickness?: number
    toolDiameter?: number
    feedRate?: number
    spindleSpeed?: number
  }
}

// Empty state component for CAM
function EmptyCamState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="rounded-full bg-muted p-4 mb-4">
        <FileCode className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">Нет CAM задач</h3>
      <p className="text-muted-foreground text-center max-w-md mb-6">
        CAM задачи создаются автоматически при генерации DXF или G-code из спецификации
      </p>
      <Button variant="outline" asChild>
        <a href="/bom">Перейти к спецификации</a>
      </Button>
    </div>
  )
}

function DXFViewer({ url, jobType }: { url?: string; jobType?: CAMJobType }) {
  return (
    <div className="h-[300px] w-full bg-muted/20 border rounded-lg flex items-center justify-center">
      {url ? (
        <div className="text-center p-6">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="font-medium mb-2">
            {jobType === 'GCODE' ? 'G-code готов' : 'DXF готов'}
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            {jobType === 'GCODE'
              ? 'Программа ЧПУ сгенерирована и готова к загрузке на станок'
              : 'Чертёж раскроя сгенерирован. Откройте в AutoCAD или LibreCAD для просмотра'
            }
          </p>
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <FileCode className="h-4 w-4" />
            <span>{jobType === 'GCODE' ? '.nc / .gcode' : '.dxf'}</span>
          </div>
        </div>
      ) : (
        <div className="text-center text-muted-foreground p-6">
          <FileCode className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Выберите задачу для предпросмотра</p>
          <p className="text-xs mt-2">Кликните по строке в таблице слева</p>
        </div>
      )}
    </div>
  )
}

export default function CamPage() {
  const { toast } = useToast()
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [selectedJob, setSelectedJob] = useState<CAMJob | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [jobs, setJobs] = useState<CAMJob[]>([])
  const [isLoadingDownloadUrl, setIsLoadingDownloadUrl] = useState(false)

  // Load CAM jobs from API
  useEffect(() => {
    const loadJobs = async () => {
      try {
        const response = await fetch('/api/v1/cam/jobs')
        if (response.ok) {
          const data = await response.json()
          if (data.jobs && data.jobs.length > 0) {
            // Преобразуем формат API в формат UI
            const formattedJobs: CAMJob[] = data.jobs.map((job: {
              job_id: string
              job_kind: string
              status: string
              order_id?: string
              created_at: string
              updated_at: string
            }) => ({
              id: job.job_id,
              orderId: job.order_id || '',
              type: job.job_kind as CAMJobType,
              name: `${job.job_kind} задача`,
              status: job.status as CAMJobStatus,
              createdAt: job.created_at,
              completedAt: job.status === 'Completed' ? job.updated_at : undefined,
            }))
            setJobs(formattedJobs)
          }
        }
      } catch (error) {
        console.error('Failed to load CAM jobs:', error)
        // При ошибке оставляем пустой массив
      } finally {
        setIsLoading(false)
      }
    }

    loadJobs()

    // Обновляем каждые 5 секунд
    const interval = setInterval(loadJobs, 5000)
    return () => clearInterval(interval)
  }, [])

  // Load download URL when job is selected
  useEffect(() => {
    if (!selectedJob || selectedJob.status !== 'Completed' || selectedJob.downloadUrl) return

    const loadDownloadUrl = async () => {
      setIsLoadingDownloadUrl(true)
      try {
        const response = await fetch(`/api/v1/cam/jobs/${selectedJob.id}/download`)
        if (response.ok) {
          const data = await response.json()
          if (data.download_url) {
            setSelectedJob(prev => prev ? { ...prev, downloadUrl: data.download_url } : null)
            // Также обновляем в списке jobs
            setJobs(prevJobs => prevJobs.map(job =>
              job.id === selectedJob.id ? { ...job, downloadUrl: data.download_url } : job
            ))
          }
        }
      } catch (error) {
        console.error('Failed to load download URL:', error)
      } finally {
        setIsLoadingDownloadUrl(false)
      }
    }

    loadDownloadUrl()
  }, [selectedJob?.id, selectedJob?.status])

  const columns: ColumnDef<CAMJob>[] = useMemo(
    () => [
      {
        accessorKey: "type",
        header: "Тип",
        cell: ({ row }) => {
          const type = row.getValue("type") as CAMJobType
          return (
            <Badge variant={type === "DXF" ? "default" : "secondary"}>
              {type}
            </Badge>
          )
        },
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
              Название
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const name = row.getValue("name") as string
          const description = row.original.description
          return (
            <div>
              <div className="font-medium">{name}</div>
              {description && <div className="text-sm text-muted-foreground">{description}</div>}
            </div>
          )
        },
      },
      {
        accessorKey: "status",
        header: "Статус",
        cell: ({ row }) => {
          const status = row.getValue("status") as CAMJobStatus
          const progress = row.original.progress ?? 0
          const StatusIcon = {
            Created: Clock,
            Processing: RefreshCw,
            Completed: CheckCircle,
            Failed: XCircle
          }[status]
          
          const statusColors = {
            Created: "secondary",
            Processing: "default", 
            Completed: "default",
            Failed: "destructive"
          } as const

          return (
            <div className="flex items-center space-x-2">
              <Badge variant={statusColors[status]} className="flex items-center space-x-1">
                <StatusIcon className="h-3 w-3" />
                <span>{status === 'Created' ? 'Создана' : status === 'Processing' ? 'Выполняется' : status === 'Completed' ? 'Готова' : 'Ошибка'}</span>
              </Badge>
              {status === 'Processing' && (
                <div className="flex items-center space-x-2">
                  <div className="w-12 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground">{progress}%</span>
                </div>
              )}
            </div>
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
              Создано
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const date = new Date(row.getValue("createdAt"))
          return (
            <div className="text-sm">
              {date.toLocaleDateString('ru-RU')} {date.toLocaleTimeString('ru-RU')}
            </div>
          )
        },
      },
      {
        accessorKey: "parameters",
        header: "Параметры",
        cell: ({ row }) => {
          const params = row.original.parameters
          if (!params) return <span className="text-muted-foreground">-</span>
          return (
            <div className="text-sm">
              {params.material && <div>Материал: {params.material}</div>}
              {params.thickness && <div>Толщина: {params.thickness}мм</div>}
              {params.toolDiameter && <div>Инструмент: ⌀{params.toolDiameter}мм</div>}
            </div>
          )
        },
      },
      {
        accessorKey: "fileSize",
        header: "Размер файла",
        cell: ({ row }) => {
          const size = row.original.fileSize
          if (!size) return <span className="text-muted-foreground">-</span>
          return <div className="text-sm">{size.toFixed(1)} KB</div>
        },
      },
      {
        id: "actions",
        cell: ({ row }) => {
          const job = row.original
          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-8 w-8 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setSelectedJob(job)}>
                  <Eye className="h-4 w-4 mr-2" />
                  Предпросмотр
                </DropdownMenuItem>
                {job.status === 'Completed' && (
                  <DropdownMenuItem>
                    <Download className="h-4 w-4 mr-2" />
                    Скачать
                  </DropdownMenuItem>
                )}
                {job.status === 'Created' && (
                  <DropdownMenuItem>
                    <Play className="h-4 w-4 mr-2" />
                    Запустить
                  </DropdownMenuItem>
                )}
                {job.status === 'Processing' && (
                  <DropdownMenuItem>
                    <Pause className="h-4 w-4 mr-2" />
                    Остановить
                  </DropdownMenuItem>
                )}
                {job.status === 'Failed' && (
                  <DropdownMenuItem>
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Повторить
                  </DropdownMenuItem>
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
    data: jobs,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
    },
  })

  const stats = useMemo(() => {
    const total = jobs.length
    const completed = jobs.filter(job => job.status === 'Completed').length
    const processing = jobs.filter(job => job.status === 'Processing').length
    const failed = jobs.filter(job => job.status === 'Failed').length

    return { total, completed, processing, failed }
  }, [jobs])

  const handleCreateDXF = () => {
    toast({
      title: "Создание DXF",
      description: "Функционал создания DXF будет доступен в ближайшем обновлении"
    })
  }

  const handleCreateGCode = () => {
    toast({
      title: "Создание G-code",
      description: "Функционал создания G-code будет доступен в ближайшем обновлении"
    })
  }

  if (isLoading) {
    return (
      <div className="p-6 w-full space-y-6">
        {/* Заголовок */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Файлы для станка</h1>
            <p className="text-muted-foreground">
              Чертежи раскроя (DXF) и программы ЧПУ (G-code)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button disabled variant="outline">
              <Upload className="h-4 w-4 mr-2" />
              Создать DXF
            </Button>
            <Button disabled>
              <Zap className="h-4 w-4 mr-2" />
              Создать G-code
            </Button>
          </div>
        </div>

        {/* Статистика (скелетон) */}
        <StatCardSkeleton count={4} />

        {/* Tabs с содержимым */}
        <Tabs defaultValue="jobs" className="w-full">
          <TabsList>
            <TabsTrigger value="jobs">Очередь задач</TabsTrigger>
            <TabsTrigger value="preview" disabled>3D Предпросмотр</TabsTrigger>
          </TabsList>
          <TabsContent value="jobs" className="space-y-4">
            <TableSkeleton rows={6} columns={7} />
          </TabsContent>
        </Tabs>
      </div>
    )
  }

  // Показываем empty state если нет задач
  if (jobs.length === 0) {
    return (
      <div className="p-6 w-full space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Файлы для станка</h1>
            <p className="text-muted-foreground">
              Чертежи раскроя (DXF) и программы ЧПУ (G-code)
            </p>
          </div>
        </div>
        <Card>
          <EmptyCamState />
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 w-full space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Файлы для станка</h1>
          <p className="text-muted-foreground">
            Чертежи раскроя (DXF) и программы ЧПУ (G-code)
          </p>
        </div>
      </div>

      {/* Индикатор настроек */}
      <SettingsIndicator
        fields={['machine_profile', 'sheet_width_mm', 'sheet_height_mm', 'gap_mm', 'spindle_speed', 'feed_rate_cutting', 'tool_diameter']}
        targetTab="generation"
      />

      {/* Статистика */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <FileCode className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm font-medium">Всего задач</div>
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
            <RefreshCw className="h-4 w-4 text-blue-600" />
            <div className="text-sm font-medium">В обработке</div>
          </div>
          <div className="text-2xl font-bold text-blue-600">{stats.processing}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center space-x-2">
            <XCircle className="h-4 w-4 text-red-600" />
            <div className="text-sm font-medium">Ошибки</div>
          </div>
          <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
        </Card>
      </div>

      {/* Основной контент */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Список задач */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Задачи CAM</span>
                <Input
                  placeholder="Поиск задач..."
                  value={(table.getColumn("name")?.getFilterValue() as string) ?? ""}
                  onChange={(event) =>
                    table.getColumn("name")?.setFilterValue(event.target.value)
                  }
                  className="max-w-sm"
                />
              </CardTitle>
            </CardHeader>
            <CardContent>
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
                        className={`cursor-pointer transition-colors hover:bg-muted/30 ${selectedJob?.id === row.original.id ? "bg-muted/50" : ""}`}
                        onClick={() => setSelectedJob(row.original)}
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
                        Нет задач CAM
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>

        {/* Панель предпросмотра */}
        <div className="lg:col-span-1">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Eye className="h-4 w-4" />
                <span>Предпросмотр</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedJob ? (
                <Tabs defaultValue="preview">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="preview">Предпросмотр</TabsTrigger>
                    <TabsTrigger value="details">Детали</TabsTrigger>
                  </TabsList>
                  <TabsContent value="preview" className="mt-4 space-y-4">
                    {/* Информация о выбранной задаче */}
                    <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Badge variant={selectedJob.type === "DXF" ? "default" : "secondary"}>
                          {selectedJob.type}
                        </Badge>
                        <span className="text-sm font-medium">{selectedJob.name}</span>
                      </div>
                      {selectedJob.status === 'Completed' && (
                        isLoadingDownloadUrl ? (
                          <Button size="sm" disabled>
                            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            Загрузка...
                          </Button>
                        ) : selectedJob.downloadUrl ? (
                          <Button size="sm" asChild>
                            <a href={selectedJob.downloadUrl} target="_blank" rel="noopener noreferrer">
                              <Download className="h-4 w-4 mr-2" />
                              Скачать
                            </a>
                          </Button>
                        ) : null
                      )}
                    </div>
                    <DXFViewer url={selectedJob.downloadUrl} jobType={selectedJob.type} />
                  </TabsContent>
                  <TabsContent value="details" className="mt-4">
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm font-medium">Название:</label>
                        <p className="text-sm text-muted-foreground">{selectedJob.name}</p>
                      </div>
                      {selectedJob.description && (
                        <div>
                          <label className="text-sm font-medium">Описание:</label>
                          <p className="text-sm text-muted-foreground">{selectedJob.description}</p>
                        </div>
                      )}
                      <div>
                        <label className="text-sm font-medium">Статус:</label>
                        <p className="text-sm text-muted-foreground">
                          {selectedJob.status === 'Created' ? 'Создана' : selectedJob.status === 'Processing' ? 'Выполняется' : selectedJob.status === 'Completed' ? 'Готова' : 'Ошибка'}
                        </p>
                      </div>
                      {selectedJob.error && (
                        <div>
                          <label className="text-sm font-medium text-red-600">Ошибка:</label>
                          <p className="text-sm text-red-600">{selectedJob.error}</p>
                        </div>
                      )}
                      {selectedJob.parameters && (
                        <div>
                          <label className="text-sm font-medium">Параметры:</label>
                          <div className="text-sm text-muted-foreground space-y-1">
                            {selectedJob.parameters.material && <div>Материал: {selectedJob.parameters.material}</div>}
                            {selectedJob.parameters.thickness && <div>Толщина: {selectedJob.parameters.thickness}мм</div>}
                            {selectedJob.parameters.toolDiameter && <div>Диаметр инструмента: {selectedJob.parameters.toolDiameter}мм</div>}
                            {selectedJob.parameters.feedRate && <div>Подача: {selectedJob.parameters.feedRate} мм/мин</div>}
                            {selectedJob.parameters.spindleSpeed && <div>Обороты шпинделя: {selectedJob.parameters.spindleSpeed} об/мин</div>}
                          </div>
                        </div>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              ) : (
                <div className="h-[400px] flex items-center justify-center border rounded-lg bg-muted/20">
                  <div className="text-center text-muted-foreground">
                    <Settings className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Выберите задачу для предпросмотра</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
