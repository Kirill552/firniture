'use client'

import { useFeatureFlags } from "@/features/mvp"
import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { getAuthHeader } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Loader2, AlertCircle, Check, Settings, Cpu, Package, Wrench } from "lucide-react"
import Link from "next/link"
import { useToast } from "@/hooks/use-toast"

type FactorySettings = {
  factory_name: string
  owner_email: string
  settings: {
    machine_profile: string
    sheet_width_mm: number
    sheet_height_mm: number
    thickness_mm: number
    edge_thickness_mm: number
    decor: string | null
    gap_mm: number
    spindle_speed: number
    feed_rate_cutting: number
    feed_rate_plunge: number
    cut_depth: number
    safe_height: number
    tool_diameter: number
    bottom_mount: "on_bottom" | "inset"
    tie_beam_height_mm: number
    facade_gap_mm: number
    shelf_gap_mm: number
    legs_height_mm: number
    fastener_type: "confirmat" | "dowel"
    hardware_mount: "screws" | "euro_screw"
    price_board_m2: number
    price_facade_board_m2: number
    price_hdf_m2: number
    price_edge_visible_m: number
    price_edge_hidden_m: number
    price_cut_m: number
    price_edging_m: number
    price_drilling_hole: number
    currency: "RUB" | "EUR" | "USD" | "KZT" | "BYN" | "RSD"
  }
  defaults_used: string[]
}

const MACHINE_PROFILES = [
  { value: "weihong", label: "Weihong (NCStudio)", description: "Рекомендуется, ~30-35% рынка" },
  { value: "syntec", label: "Syntec (KDT/WoodTec)", description: "FANUC-совместимый, ~20-25%" },
  { value: "fanuc", label: "FANUC", description: "ISO стандарт, премиум" },
  { value: "dsp", label: "DSP", description: "Бюджетный сегмент" },
  { value: "homag", label: "HOMAG", description: "Премиум мебельное" },
]

const STANDARD_NUMBER_FIELDS = [
  { key: "tie_beam_height_mm", label: "Ширина верхних планок (царг), мм", description: "Перемычка вместо сплошного верха у напольной тумбы." },
  { key: "facade_gap_mm", label: "Зазор фасада, мм", description: "Общий зазор по ширине корпуса и по высоте фасада." },
  { key: "shelf_gap_mm", label: "Зазор полки с каждой стороны, мм", description: "Свободное место, чтобы полка встала без подгонки." },
  { key: "legs_height_mm", label: "Высота ножек, мм", description: "На сколько поднять напольный модуль от пола." },
] as const

const PRICE_FIELDS = [
  { key: "price_board_m2", label: "Корпусная плита", unit: "за м²", description: "Белая плита дешевле цветной; цена квадратного метра корпуса." },
  { key: "price_facade_board_m2", label: "Фасадная плита", unit: "за м²", description: "Цветная плита для фасадов, обычно дороже белой." },
  { key: "price_hdf_m2", label: "ХДФ / ДВП", unit: "за м²", description: "Цена квадратного метра задней стенки." },
  { key: "price_edge_visible_m", label: "Кромка видимая 2 мм", unit: "за метр", description: "Кромка на лицевые торцы." },
  { key: "price_edge_hidden_m", label: "Кромка скрытая 0,4 мм", unit: "за метр", description: "Кромка на внутренние торцы." },
  { key: "price_cut_m", label: "Распил", unit: "за метр", description: "Стоимость погонного метра реза." },
  { key: "price_edging_m", label: "Кромление", unit: "за метр", description: "Стоимость нанесения кромки." },
  { key: "price_drilling_hole", label: "Присадка", unit: "за отверстие", description: "Сверление отверстий под фурнитуру." },
] as const
const CURRENCY_SYMBOLS: Record<FactorySettings["settings"]["currency"], string> = {
  RUB: "₽", EUR: "€", USD: "$", KZT: "₸", BYN: "Br", RSD: "дин",
}

export default function SettingsPage() {
  const searchParams = useSearchParams()
  const { machineFeaturesEnabled } = useFeatureFlags()
  const initialTab = searchParams.get('tab') || 'factory'
  const activeTab = (initialTab === 'machine' && !machineFeaturesEnabled) ? 'factory' : initialTab
  const { toast } = useToast()

  const [settings, setSettings] = useState<FactorySettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Локальное состояние для формы
  const [formData, setFormData] = useState<Partial<FactorySettings['settings']> & { factory_name?: string }>({})

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch('/api/v1/settings', {
          headers: { ...getAuthHeader() },
        })
        if (response.ok) {
          const data: FactorySettings = await response.json()
          setSettings(data)
          setFormData({
            factory_name: data.factory_name,
            ...data.settings
          })
        } else if (response.status === 401) {
          setError('not_authenticated')
        } else {
          setError('Ошибка загрузки настроек')
        }
      } catch (err) {
        console.error('Failed to load settings:', err)
        setError('not_authenticated')
      } finally {
        setIsLoading(false)
      }
    }

    loadSettings()
  }, [])

  const handleSave = async () => {
    if (!settings) return

    setIsSaving(true)
    try {
      // Собираем только изменённые поля
      const changedFields: Record<string, unknown> = {}

      if (formData.factory_name !== settings.factory_name) {
        changedFields.factory_name = formData.factory_name
      }

      // Проверяем все поля настроек
      const settingsKeys = Object.keys(settings.settings) as (keyof typeof settings.settings)[]
      for (const key of settingsKeys) {
        if (formData[key] !== settings.settings[key]) {
          changedFields[key] = formData[key]
        }
      }

      if (Object.keys(changedFields).length === 0) {
        toast({
          title: "Нет изменений",
          description: "Вы не изменили ни одного поля",
        })
        setIsSaving(false)
        return
      }

      const response = await fetch('/api/v1/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify(changedFields),
      })

      if (response.ok) {
        const result = await response.json()
        toast({
          title: "Настройки сохранены",
          description: `Обновлено полей: ${result.updated_fields.length}`,
        })
        // Обновляем локальное состояние
        setSettings(prev => prev ? {
          ...prev,
          factory_name: formData.factory_name || prev.factory_name,
          settings: { ...prev.settings, ...formData }
        } : null)
      } else {
        const err = await response.json()
        toast({
          title: "Ошибка",
          description: err.detail || "Не удалось сохранить настройки",
          variant: "destructive",
        })
      }
    } catch (err) {
      console.error('Failed to save settings:', err)
      toast({
        title: "Ошибка",
        description: "Не удалось сохранить настройки",
        variant: "destructive",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const updateField = (field: string, value: string | number | null) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (isLoading) {
    return (
      <div className="p-6 w-full max-w-4xl mx-auto">
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error === 'not_authenticated') {
    return (
      <div className="p-6 w-full max-w-4xl mx-auto">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-8 w-8 text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-4">Войдите в систему для просмотра настроек</p>
            <Button asChild>
              <Link href="/login">Войти</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 w-full max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Настройки</h1>
        <p className="text-muted-foreground">Настройки фабрики, станка и параметров генерации</p>
      </div>

      <Tabs defaultValue={activeTab} className="space-y-6">
        <TabsList className={`grid w-full ${machineFeaturesEnabled ? 'grid-cols-4' : 'grid-cols-3'}`}>
          <TabsTrigger value="factory" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">Фабрика</span>
          </TabsTrigger>
          {machineFeaturesEnabled && (
            <TabsTrigger value="machine" className="flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              <span className="hidden sm:inline">Станок</span>
            </TabsTrigger>
          )}
          <TabsTrigger value="materials" className="flex items-center gap-2">
            <Package className="h-4 w-4" />
            <span className="hidden sm:inline">Материалы</span>
          </TabsTrigger>
          <TabsTrigger value="generation" className="flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            <span className="hidden sm:inline">Генерация</span>
          </TabsTrigger>
        </TabsList>

        {/* Вкладка: Фабрика */}
        <TabsContent value="factory">
          <Card>
            <CardHeader>
              <CardTitle>Профиль фабрики</CardTitle>
              <CardDescription>Основная информация о вашей организации</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="factory_name">Название фабрики</Label>
                <Input
                  id="factory_name"
                  value={formData.factory_name || ''}
                  onChange={(e) => updateField('factory_name', e.target.value)}
                  placeholder="ООО Мебель-Про"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="owner_email">Email владельца</Label>
                <Input
                  id="owner_email"
                  type="email"
                  value={settings?.owner_email || ''}
                  readOnly
                  className="bg-muted"
                />
                <p className="text-xs text-muted-foreground">
                  Для смены email обратитесь в поддержку
                </p>
              </div>
            </CardContent>
          </Card>
          <div className="mt-6 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Стандарты цеха</CardTitle>
                <CardDescription>Настройте конструктив один раз — дальше расчёты будут под ваши привычки.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="bottom_mount">Как стоит дно</Label>
                  <Select
                    value={formData.bottom_mount || "on_bottom"}
                    onValueChange={(value) => updateField("bottom_mount", value)}
                  >
                    <SelectTrigger id="bottom_mount"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="on_bottom">Боковины на дне</SelectItem>
                      <SelectItem value="inset">Дно вкладное</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Куда встаёт масса корпуса. Большинство ставит боковины на дно.</p>
                  {settings?.defaults_used.includes("bottom_mount") && <p className="text-xs text-amber-600">Используется значение по умолчанию</p>}
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {STANDARD_NUMBER_FIELDS.map((field) => (
                    <div key={field.key} className="space-y-2">
                      <Label htmlFor={field.key}>{field.label}</Label>
                      <Input
                        id={field.key}
                        type="number"
                        step="0.1"
                        value={formData[field.key] ?? ""}
                        onChange={(e) => updateField(field.key, parseFloat(e.target.value) || null)}
                      />
                      <p className="text-xs text-muted-foreground">{field.description}</p>
                      {settings?.defaults_used.includes(field.key) && <p className="text-xs text-amber-600">Используется значение по умолчанию</p>}
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fastener_type">Тип крепежа</Label>
                  <Select
                    value={formData.fastener_type || "confirmat"}
                    onValueChange={(value) => updateField("fastener_type", value)}
                  >
                    <SelectTrigger id="fastener_type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="confirmat">Конфирмат</SelectItem>
                      <SelectItem value="dowel">Шкант</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Чем соединять детали корпуса по умолчанию.</p>
                  {settings?.defaults_used.includes("fastener_type") && <p className="text-xs text-amber-600">Используется значение по умолчанию</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="hardware_mount">Чем крепите планки и направляющие</Label>
                  <Select
                    value={formData.hardware_mount || "screws"}
                    onValueChange={(value) => updateField("hardware_mount", value)}
                  >
                    <SelectTrigger id="hardware_mount"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="screws">Саморезы (без присадки)</SelectItem>
                      <SelectItem value="euro_screw">Евровинт в сверловку 5 мм</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Ответные планки и направляющие без лишних отверстий по умолчанию.</p>
                  {settings?.defaults_used.includes("hardware_mount") && <p className="text-xs text-amber-600">Используется значение по умолчанию</p>}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Цены</CardTitle>
                <CardDescription>До ввода своих цен смета считается по прикидке. Укажите цены поставщика, чтобы итог был ближе к реальности.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {PRICE_FIELDS.map((field) => (
                    <div key={field.key} className="space-y-2">
                      <Label htmlFor={field.key}>{field.label}</Label>
                      <div className="flex items-center gap-2">
                        <Input
                          id={field.key}
                          type="number"
                          min="0"
                          step="0.01"
                          value={formData[field.key] ?? ""}
                          onChange={(e) => updateField(field.key, parseFloat(e.target.value) || null)}
                        />
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {CURRENCY_SYMBOLS[(formData.currency as FactorySettings["settings"]["currency"]) || "RUB"]} {field.unit}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">{field.description}</p>
                      {settings?.defaults_used.includes(field.key) && (
                        <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                          Прикидка по российскому рынку. При другой валюте введите свои цены.
                        </p>
                      )}
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="currency">Валюта цен мастера</Label>
                  <Select value={(formData.currency as string) || "RUB"} onValueChange={(value) => updateField("currency", value)}>
                    <SelectTrigger id="currency"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="RUB">₽ (RUB)</SelectItem>
                      <SelectItem value="EUR">€ (EUR)</SelectItem>
                      <SelectItem value="USD">$ (USD)</SelectItem>
                      <SelectItem value="KZT">₸ (KZT)</SelectItem>
                      <SelectItem value="BYN">Br (BYN)</SelectItem>
                      <SelectItem value="RSD">дин (RSD)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Валюта материалов, фурнитуры и работ в смете.</p>
                  {formData.currency && formData.currency !== "RUB" && settings?.defaults_used.some((key) => key.startsWith("price_")) && (
                    <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                      Внимание: цены по умолчанию — прикидка по российскому рынку. Введите свои цены в выбранной валюте.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Вкладка: Станок */}
        {machineFeaturesEnabled && (
          <TabsContent value="machine">
            <Card>
              <CardHeader>
                <CardTitle>Профиль станка</CardTitle>
                <CardDescription>Выберите профиль вашего ЧПУ станка для корректной генерации G-code</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="machine_profile">Профиль ЧПУ</Label>
                  <Select
                    value={formData.machine_profile || 'weihong'}
                    onValueChange={(value) => updateField('machine_profile', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите профиль" />
                    </SelectTrigger>
                    <SelectContent>
                      {MACHINE_PROFILES.map((profile) => (
                        <SelectItem key={profile.value} value={profile.value}>
                          <div className="flex flex-col">
                            <span>{profile.label}</span>
                            <span className="text-xs text-muted-foreground">{profile.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {settings?.defaults_used.includes('machine_profile') && (
                    <p className="text-xs text-amber-600">Используется значение по умолчанию</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Вкладка: Материалы */}
        <TabsContent value="materials">
          <Card>
            <CardHeader>
              <CardTitle>Материалы по умолчанию</CardTitle>
              <CardDescription>Параметры листа ЛДСП и кромки</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="sheet_width_mm">Ширина листа (мм)</Label>
                  <Input
                    id="sheet_width_mm"
                    type="number"
                    value={formData.sheet_width_mm || ''}
                    onChange={(e) => updateField('sheet_width_mm', parseFloat(e.target.value) || null)}
                    placeholder="2800"
                  />
                  {settings?.defaults_used.includes('sheet_width_mm') && (
                    <p className="text-xs text-amber-600">По умолчанию</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sheet_height_mm">Высота листа (мм)</Label>
                  <Input
                    id="sheet_height_mm"
                    type="number"
                    value={formData.sheet_height_mm || ''}
                    onChange={(e) => updateField('sheet_height_mm', parseFloat(e.target.value) || null)}
                    placeholder="2070"
                  />
                  {settings?.defaults_used.includes('sheet_height_mm') && (
                    <p className="text-xs text-amber-600">По умолчанию</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="thickness_mm">Толщина ЛДСП (мм)</Label>
                  <Input
                    id="thickness_mm"
                    type="number"
                    value={formData.thickness_mm || ''}
                    onChange={(e) => updateField('thickness_mm', parseFloat(e.target.value) || null)}
                    placeholder="16"
                  />
                  {settings?.defaults_used.includes('thickness_mm') && (
                    <p className="text-xs text-amber-600">По умолчанию</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edge_thickness_mm">Толщина кромки (мм)</Label>
                  <Input
                    id="edge_thickness_mm"
                    type="number"
                    step="0.1"
                    value={formData.edge_thickness_mm || ''}
                    onChange={(e) => updateField('edge_thickness_mm', parseFloat(e.target.value) || null)}
                    placeholder="0.4"
                  />
                  {settings?.defaults_used.includes('edge_thickness_mm') && (
                    <p className="text-xs text-amber-600">По умолчанию</p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="decor">Декор / цвет</Label>
                <Input
                  id="decor"
                  value={formData.decor || ''}
                  onChange={(e) => updateField('decor', e.target.value || null)}
                  placeholder="Белый W1000, Дуб Сонома и т.д."
                />
                <p className="text-xs text-muted-foreground">Опционально, для справки</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Вкладка: Генерация */}
        <TabsContent value="generation">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>DXF раскрой</CardTitle>
                <CardDescription>Параметры для генерации DXF файлов</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Label htmlFor="gap_mm">Зазор на пропил (мм)</Label>
                  <Input
                    id="gap_mm"
                    type="number"
                    value={formData.gap_mm || ''}
                    onChange={(e) => updateField('gap_mm', parseFloat(e.target.value) || null)}
                    placeholder="4"
                  />
                  {settings?.defaults_used.includes('gap_mm') && (
                    <p className="text-xs text-amber-600">По умолчанию</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Расстояние между панелями при раскрое
                  </p>
                </div>
              </CardContent>
            </Card>

            {machineFeaturesEnabled && (
              <Card>
                <CardHeader>
                  <CardTitle>G-code параметры</CardTitle>
                  <CardDescription>Параметры обработки для ЧПУ станка</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="spindle_speed">Скорость шпинделя (об/мин)</Label>
                      <Input
                        id="spindle_speed"
                        type="number"
                        value={formData.spindle_speed || ''}
                        onChange={(e) => updateField('spindle_speed', parseInt(e.target.value) || null)}
                        placeholder="18000"
                      />
                      {settings?.defaults_used.includes('spindle_speed') && (
                        <p className="text-xs text-amber-600">По умолчанию</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="tool_diameter">Диаметр фрезы (мм)</Label>
                      <Input
                        id="tool_diameter"
                        type="number"
                        value={formData.tool_diameter || ''}
                        onChange={(e) => updateField('tool_diameter', parseFloat(e.target.value) || null)}
                        placeholder="6"
                      />
                      {settings?.defaults_used.includes('tool_diameter') && (
                        <p className="text-xs text-amber-600">По умолчанию</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="feed_rate_cutting">Подача резки (мм/мин)</Label>
                      <Input
                        id="feed_rate_cutting"
                        type="number"
                        value={formData.feed_rate_cutting || ''}
                        onChange={(e) => updateField('feed_rate_cutting', parseInt(e.target.value) || null)}
                        placeholder="3000"
                      />
                      {settings?.defaults_used.includes('feed_rate_cutting') && (
                        <p className="text-xs text-amber-600">По умолчанию</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="feed_rate_plunge">Подача врезания (мм/мин)</Label>
                      <Input
                        id="feed_rate_plunge"
                        type="number"
                        value={formData.feed_rate_plunge || ''}
                        onChange={(e) => updateField('feed_rate_plunge', parseInt(e.target.value) || null)}
                        placeholder="1500"
                      />
                      {settings?.defaults_used.includes('feed_rate_plunge') && (
                        <p className="text-xs text-amber-600">По умолчанию</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="cut_depth">Глубина за проход (мм)</Label>
                      <Input
                        id="cut_depth"
                        type="number"
                        value={formData.cut_depth || ''}
                        onChange={(e) => updateField('cut_depth', parseFloat(e.target.value) || null)}
                        placeholder="8"
                      />
                      {settings?.defaults_used.includes('cut_depth') && (
                        <p className="text-xs text-amber-600">По умолчанию</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="safe_height">Безопасная высота (мм)</Label>
                      <Input
                        id="safe_height"
                        type="number"
                        value={formData.safe_height || ''}
                        onChange={(e) => updateField('safe_height', parseFloat(e.target.value) || null)}
                        placeholder="5"
                      />
                      {settings?.defaults_used.includes('safe_height') && (
                        <p className="text-xs text-amber-600">По умолчанию</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Кнопка сохранения */}
      <div className="mt-6 flex justify-end">
        <Button onClick={handleSave} disabled={isSaving} className="min-w-[140px]">
          {isSaving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Сохранение...
            </>
          ) : (
            <>
              <Check className="h-4 w-4 mr-2" />
              Сохранить
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
