'use client'

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

export default function SettingsPage() {
  const searchParams = useSearchParams()
  const initialTab = searchParams.get('tab') || 'factory'
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
        const response = await fetch('http://localhost:8000/api/v1/settings', {
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

      const response = await fetch('http://localhost:8000/api/v1/settings', {
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

      <Tabs defaultValue={initialTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="factory" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">Фабрика</span>
          </TabsTrigger>
          <TabsTrigger value="machine" className="flex items-center gap-2">
            <Cpu className="h-4 w-4" />
            <span className="hidden sm:inline">Станок</span>
          </TabsTrigger>
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
        </TabsContent>

        {/* Вкладка: Станок */}
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
