"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import {
  Plug,
  ExternalLink,
  Settings,
  Database,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Eye,
  Play,
  Download,
  Upload,
  Server,
  Shield,
  Zap,
  Activity,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"

type IntegrationStatus = 'connected' | 'disconnected' | 'error' | 'connecting'
type SyncStatus = 'idle' | 'syncing' | 'success' | 'error'

type SyncLog = {
  id: string
  timestamp: string
  type: 'export' | 'import'
  entity: string
  status: 'success' | 'error' | 'pending'
  recordsCount?: number
  duration?: string
  error?: string
}

const mockSyncLogs: SyncLog[] = [
  {
    id: "1",
    timestamp: "2024-12-14T15:30:00Z",
    type: "export",
    entity: "Заказы",
    status: "success",
    recordsCount: 15,
    duration: "2.3с"
  },
  {
    id: "2",
    timestamp: "2024-12-14T14:15:00Z",
    type: "import",
    entity: "Номенклатура",
    status: "success",
    recordsCount: 248,
    duration: "5.1с"
  },
  {
    id: "3",
    timestamp: "2024-12-14T13:45:00Z",
    type: "export",
    entity: "BOM",
    status: "error",
    recordsCount: 0,
    error: "Ошибка подключения к базе данных 1С"
  },
  {
    id: "4",
    timestamp: "2024-12-14T12:30:00Z",
    type: "import",
    entity: "Контрагенты",
    status: "success",
    recordsCount: 67,
    duration: "1.8с"
  }
]

export default function IntegrationsPage() {
  const { toast } = useToast()
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus>('connected')
  const [syncStatus, setSyncStatus] = useState<SyncStatus>('idle')
  const [showConnectionDialog, setShowConnectionDialog] = useState(false)
  
  const [connectionSettings, setConnectionSettings] = useState({
    serverUrl: "http://192.168.1.100:8080",
    database: "manufacturing_base",
    username: "administrator", 
    password: "",
    apiVersion: "v1"
  })

  const handleTestConnection = () => {
    setIntegrationStatus('connecting')
    // Симуляция проверки подключения
    setTimeout(() => {
      setIntegrationStatus('connected')
      toast({
        title: "Подключение успешно",
        description: "Соединение с 1С:Предприятие установлено"
      })
    }, 2000)
  }

  const handleSync = (entity: string) => {
    setSyncStatus('syncing')
    toast({
      title: `Синхронизация ${entity}`,
      description: "Начата синхронизация данных с 1С"
    })
    
    setTimeout(() => {
      setSyncStatus('success')
      toast({
        title: "Синхронизация завершена",
        description: `${entity} успешно синхронизированы с 1С`
      })
      setTimeout(() => setSyncStatus('idle'), 3000)
    }, 3000)
  }

  const statusIcons = {
    connected: CheckCircle,
    disconnected: XCircle,
    error: AlertCircle,
    connecting: Clock
  }

  const statusColors = {
    connected: "text-green-600",
    disconnected: "text-gray-500", 
    error: "text-red-600",
    connecting: "text-blue-600"
  }

  const statusLabels = {
    connected: "Подключено",
    disconnected: "Отключено",
    error: "Ошибка",
    connecting: "Подключение..."
  }

  const StatusIcon = statusIcons[integrationStatus]

  return (
    <div className="p-6 w-full space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Интеграции (1С)</h1>
          <p className="text-muted-foreground">
            Управление интеграцией с системой 1С:Предприятие
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Dialog open={showConnectionDialog} onOpenChange={setShowConnectionDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Settings className="h-4 w-4 mr-2" />
                Настройки
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Настройки подключения 1С</DialogTitle>
                <DialogDescription>
                  Настройте параметры подключения к вашей базе данных 1С:Предприятие
                </DialogDescription>
              </DialogHeader>
              <form
                className="grid gap-4 py-4"
                onSubmit={(e) => { e.preventDefault(); handleTestConnection(); }}
              >
                <div className="grid gap-2">
                  <label className="text-sm font-medium" htmlFor="serverUrl">URL сервера</label>
                  <Input
                    id="serverUrl"
                    value={connectionSettings.serverUrl}
                    onChange={(e) => setConnectionSettings({...connectionSettings, serverUrl: e.target.value})}
                    placeholder="http://server:port"
                    autoComplete="url"
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium" htmlFor="database">База данных</label>
                  <Input
                    id="database"
                    value={connectionSettings.database}
                    onChange={(e) => setConnectionSettings({...connectionSettings, database: e.target.value})}
                    placeholder="Название базы данных"
                    autoComplete="off"
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium" htmlFor="username">Пользователь</label>
                  <Input
                    id="username"
                    value={connectionSettings.username}
                    onChange={(e) => setConnectionSettings({...connectionSettings, username: e.target.value})}
                    placeholder="Имя пользователя"
                    autoComplete="username"
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium" htmlFor="password">Пароль</label>
                  <Input
                    id="password"
                    type="password"
                    value={connectionSettings.password}
                    onChange={(e) => setConnectionSettings({...connectionSettings, password: e.target.value})}
                    placeholder="Пароль"
                    autoComplete="current-password"
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium" htmlFor="apiVersion">Версия API</label>
                  <Input
                    id="apiVersion"
                    value={connectionSettings.apiVersion}
                    onChange={(e) => setConnectionSettings({...connectionSettings, apiVersion: e.target.value})}
                    placeholder="v1"
                    autoComplete="off"
                  />
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setShowConnectionDialog(false)}>
                    Отмена
                  </Button>
                  <Button type="submit">
                    Проверить подключение
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
          <Button>
            <RefreshCw className="h-4 w-4 mr-2" />
            Синхронизировать всё
          </Button>
        </div>
      </div>

      {/* Статус подключения */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`p-3 rounded-full bg-gray-100 ${statusColors[integrationStatus]}`}>
                <StatusIcon className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold">1С:Предприятие</h3>
                <p className="text-sm text-muted-foreground">
                  Статус: <span className={statusColors[integrationStatus]}>{statusLabels[integrationStatus]}</span>
                </p>
                {integrationStatus === 'connected' && (
                  <p className="text-xs text-muted-foreground">
                    Сервер: {connectionSettings.serverUrl} • База: {connectionSettings.database}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {integrationStatus === 'connected' && (
                <Badge variant="default" className="bg-green-100 text-green-800">
                  Активно
                </Badge>
              )}
              <Button variant="outline" size="sm" onClick={handleTestConnection}>
                {integrationStatus === 'connecting' ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Activity className="h-4 w-4 mr-2" />
                )}
                Проверить
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Основной контент */}
      <Tabs defaultValue="sync" className="space-y-4">
        <TabsList>
          <TabsTrigger value="sync">Синхронизация</TabsTrigger>
          <TabsTrigger value="mapping">Сопоставления</TabsTrigger>
          <TabsTrigger value="logs">Логи</TabsTrigger>
        </TabsList>

        <TabsContent value="sync" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Заказы */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center">
                  <Database className="h-4 w-4 mr-2" />
                  Заказы
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-sm text-muted-foreground">
                    Экспорт готовых заказов и BOM в 1С для производства и учета
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Последняя синхронизация:</span>
                    <span>15:30 сегодня</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button 
                      size="sm" 
                      onClick={() => handleSync('заказов')}
                      disabled={syncStatus === 'syncing'}
                      className="flex-1"
                    >
                      <Upload className="h-3 w-3 mr-1" />
                      Экспорт
                    </Button>
                    <Button variant="outline" size="sm">
                      <Eye className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Номенклатура */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center">
                  <Database className="h-4 w-4 mr-2" />
                  Номенклатура
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-sm text-muted-foreground">
                    Импорт актуальной номенклатуры, цен и остатков из 1С
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Последняя синхронизация:</span>
                    <span>14:15 сегодня</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleSync('номенклатуры')}
                      disabled={syncStatus === 'syncing'}
                      className="flex-1"
                    >
                      <Download className="h-3 w-3 mr-1" />
                      Импорт
                    </Button>
                    <Button variant="outline" size="sm">
                      <Eye className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Контрагенты */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center">
                  <Database className="h-4 w-4 mr-2" />
                  Контрагенты
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-sm text-muted-foreground">
                    Импорт клиентов и поставщиков для синхронизации данных
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Последняя синхронизация:</span>
                    <span>12:30 сегодня</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleSync('контрагентов')}
                      disabled={syncStatus === 'syncing'}
                      className="flex-1"
                    >
                      <Download className="h-3 w-3 mr-1" />
                      Импорт
                    </Button>
                    <Button variant="outline" size="sm">
                      <Eye className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="mapping" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Сопоставление полей</CardTitle>
              <p className="text-sm text-muted-foreground">
                Настройка соответствия полей между Мебель-ИИ и 1С
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h4 className="font-medium">Заказы</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between py-1 border-b">
                      <span>ID заказа</span>
                      <span className="text-muted-foreground">→ НомерДокумента</span>
                    </div>
                    <div className="flex justify-between py-1 border-b">
                      <span>Клиент</span>
                      <span className="text-muted-foreground">→ Контрагент</span>
                    </div>
                    <div className="flex justify-between py-1 border-b">
                      <span>Дата создания</span>
                      <span className="text-muted-foreground">→ Дата</span>
                    </div>
                    <div className="flex justify-between py-1 border-b">
                      <span>Сумма</span>
                      <span className="text-muted-foreground">→ СуммаДокумента</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium">Номенклатура</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between py-1 border-b">
                      <span>Артикул</span>
                      <span className="text-muted-foreground">→ Код</span>
                    </div>
                    <div className="flex justify-between py-1 border-b">
                      <span>Наименование</span>
                      <span className="text-muted-foreground">→ Наименование</span>
                    </div>
                    <div className="flex justify-between py-1 border-b">
                      <span>Цена</span>
                      <span className="text-muted-foreground">→ Цена</span>
                    </div>
                    <div className="flex justify-between py-1 border-b">
                      <span>Единица измерения</span>
                      <span className="text-muted-foreground">→ ЕдиницаИзмерения</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Последнее обновление сопоставлений: 13.12.2024
                </p>
                <Button variant="outline">
                  Редактировать сопоставления
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Журнал синхронизации</CardTitle>
              <p className="text-sm text-muted-foreground">
                История операций синхронизации с 1С
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockSyncLogs.map((log) => {
                  const StatusIcon = log.status === 'success' ? CheckCircle : 
                                   log.status === 'error' ? XCircle : Clock
                  const statusColor = log.status === 'success' ? 'text-green-600' : 
                                    log.status === 'error' ? 'text-red-600' : 'text-yellow-600'
                  
                  return (
                    <div key={log.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <StatusIcon className={`h-4 w-4 ${statusColor}`} />
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">{log.entity}</span>
                            <Badge variant={log.type === 'export' ? 'default' : 'secondary'} className="text-xs">
                              {log.type === 'export' ? 'Экспорт' : 'Импорт'}
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {new Date(log.timestamp).toLocaleString('ru-RU')}
                            {log.recordsCount !== undefined && ` • ${log.recordsCount} записей`}
                            {log.duration && ` • ${log.duration}`}
                          </div>
                          {log.error && (
                            <div className="text-sm text-red-600 mt-1">{log.error}</div>
                          )}
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
