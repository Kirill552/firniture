"use client"

import { useState, useMemo, useEffect, Suspense } from "react"
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
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Environment, Grid, Center } from "@react-three/drei"
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

const mockCAMJobs: CAMJob[] = [
  {
    id: "dxf-001",
    orderId: "ORD-2024-001",
    type: "DXF",
    name: "Кухонный гарнитур - боковины",
    description: "DXF чертежи для боковых панелей",
    status: "Completed",
    createdAt: "2024-12-14T10:30:00Z",
    completedAt: "2024-12-14T10:32:15Z",
    progress: 100,
    actualTime: "2м 15с",
    fileSize: 245.5,
    downloadUrl: "/downloads/dxf-001.zip",
    parameters: {
      material: "ЛДСП",
      thickness: 18
    }
  },
  {
    id: "gcode-001",
    orderId: "ORD-2024-001", 
    type: "GCODE",
    name: "Кухонный гарнитур - фрезеровка",
    description: "G-code для фрезерных операций",
    status: "Processing",
    createdAt: "2024-12-14T11:00:00Z",
    progress: 65,
    estimatedTime: "1м 30с",
    parameters: {
      material: "ЛДСП",
      thickness: 18,
      toolDiameter: 6,
      feedRate: 1200,
      spindleSpeed: 18000
    }
  },
  {
    id: "dxf-002",
    orderId: "ORD-2024-002",
    type: "DXF", 
    name: "Шкаф-купе - раскрой",
    description: "DXF раскроя для шкафа-купе",
    status: "Created",
    createdAt: "2024-12-14T11:15:00Z",
    progress: 0,
    estimatedTime: "3м 45с",
    parameters: {
      material: "ЛДСП",
      thickness: 16
    }
  },
  {
    id: "gcode-002",
    orderId: "ORD-2024-003",
    type: "GCODE",
    name: "Стол письменный - обработка торцов",
    status: "Failed",
    createdAt: "2024-12-14T09:45:00Z",
    progress: 0,
    error: "Ошибка при генерации траектории: слишком малый радиус инструмента для данной толщины материала",
    parameters: {
      material: "МДФ",
      thickness: 22,
      toolDiameter: 3,
      feedRate: 800,
      spindleSpeed: 16000
    }
  }
]

function DXFViewer({ url }: { url?: string }) {
  return (
    <div className="h-[400px] w-full bg-gray-50 border rounded-lg flex items-center justify-center">
      {url ? (
        <Canvas camera={{ position: [10, 10, 10], fov: 50 }}>
          <Suspense fallback={null}>
            <ambientLight intensity={0.6} />
            <directionalLight position={[10, 10, 5]} intensity={0.5} />
            <Environment preset="studio" />
            <Grid infiniteGrid cellSize={1} cellThickness={0.5} />
            <Center>
              {/* Здесь будет загрузка DXF файла */}
              <mesh>
                <boxGeometry args={[2, 0.1, 1]} />
                <meshStandardMaterial color="#8B4513" />
              </mesh>
              <mesh position={[0, 0.15, 0]}>
                <boxGeometry args={[1.8, 0.1, 0.8]} />
                <meshStandardMaterial color="#CD853F" />
              </mesh>
            </Center>
            <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} />
          </Suspense>
        </Canvas>
      ) : (
        <div className="text-center text-muted-foreground">
          <FileCode className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Выберите задачу для предпросмотра DXF</p>
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

  // Simulate data loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 2000)
    return () => clearTimeout(timer)
  }, [])

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
    data: mockCAMJobs,
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
    const total = mockCAMJobs.length
    const completed = mockCAMJobs.filter(job => job.status === 'Completed').length
    const processing = mockCAMJobs.filter(job => job.status === 'Processing').length
    const failed = mockCAMJobs.filter(job => job.status === 'Failed').length
    
    return { total, completed, processing, failed }
  }, [])

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
            <h1 className="text-2xl font-bold">CAM (DXF/G-code)</h1>
            <p className="text-muted-foreground">
              Управление задачами генерации DXF-чертежей и G-code для станков с ЧПУ
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

  return (
    <div className="p-6 w-full space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">CAM (DXF/G-code)</h1>
          <p className="text-muted-foreground">
            Управление задачами генерации DXF-чертежей и G-code для станков с ЧПУ
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreateDXF} variant="outline">
            <Upload className="h-4 w-4 mr-2" />
            Создать DXF
          </Button>
          <Button onClick={handleCreateGCode}>
            <Zap className="h-4 w-4 mr-2" />
            Создать G-code
          </Button>
        </div>
      </div>

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
                        className={selectedJob?.id === row.original.id ? "bg-muted/50" : ""}
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
                  <TabsContent value="preview" className="mt-4">
                    <DXFViewer url={selectedJob.downloadUrl} />
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
                        <p className="text-sm text-muted-foreground">{selectedJob.status}</p>
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
