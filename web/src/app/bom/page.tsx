"use client"

import { useSearchParams } from 'next/navigation'
import { useState, useEffect, useCallback, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Download, Package, Loader2, Check } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { getAuthHeader } from "@/lib/auth"
import { StatCardSkeleton } from "@/components/ui/table-skeleton"
import { ProductionStepper } from "@/components/production-stepper"
import { MachineProfileModal, hasSelectedMachineProfile } from "@/components/machine-profile-modal"
import { BOMHeader, PanelsTable, HardwareTable, EdgeBandTable, SheetLayoutPreview } from "@/components/bom"
import type { FullBOM, BOMPanel, BOMHardware, BOMFastener, BOMEdgeBand } from "@/types/api"

// Тип статуса сохранения
type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

// Empty state component
function EmptyBomState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="rounded-full bg-muted p-4 mb-4">
        <Package className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">Нет данных спецификации</h3>
      <p className="text-muted-foreground text-center max-w-md mb-6">
        Выберите заказ из списка или создайте новый через диалог с ИИ-технологом
      </p>
      <div className="flex gap-3">
        <Button variant="outline" asChild>
          <a href="/orders">Список заказов</a>
        </Button>
        <Button asChild>
          <a href="/orders/new">Создать заказ</a>
        </Button>
      </div>
    </div>
  )
}

export default function BomPage() {
  const { toast } = useToast()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('orderId')

  // BOM data state
  const [bom, setBom] = useState<FullBOM | null>(null)
  const [isLoadingBom, setIsLoadingBom] = useState(false)
  const [bomError, setBomError] = useState<string | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [needsRecalculation, setNeedsRecalculation] = useState(false)
  const [isRecalculating, setIsRecalculating] = useState(false)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')

  // Refs для debounce и исходного BOM
  const originalBomRef = useRef<FullBOM | null>(null)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const savedIndicatorTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // DXF generation state
  const [isGeneratingDxf, setIsGeneratingDxf] = useState(false)
  const [dxfJobId, setDxfJobId] = useState<string | null>(null)
  const [dxfDownloadUrl, setDxfDownloadUrl] = useState<string | null>(null)
  const [dxfError, setDxfError] = useState<string | null>(null)

  // G-code generation state
  const [isGeneratingGcode, setIsGeneratingGcode] = useState(false)
  const [gcodeJobId, setGcodeJobId] = useState<string | null>(null)
  const [gcodeDownloadUrl, setGcodeDownloadUrl] = useState<string | null>(null)
  const [gcodeError, setGcodeError] = useState<string | null>(null)

  // Machine profile state
  const [machineProfile, setMachineProfile] = useState<string | null>(null)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [isFirstTimeProfile, setIsFirstTimeProfile] = useState(false)

  // Ключ для localStorage
  const LAST_ORDER_KEY = 'lastBomOrderId'

  // Эффективный orderId (из URL или localStorage)
  const [effectiveOrderId, setEffectiveOrderId] = useState<string | null>(orderId)

  useEffect(() => {
    if (orderId) {
      localStorage.setItem(LAST_ORDER_KEY, orderId)
      setEffectiveOrderId(orderId)
    } else {
      const savedOrderId = localStorage.getItem(LAST_ORDER_KEY)
      if (savedOrderId) {
        setEffectiveOrderId(savedOrderId)
      }
    }
  }, [orderId])

  // Load BOM data
  useEffect(() => {
    if (!effectiveOrderId) return

    const loadBom = async () => {
      setIsLoadingBom(true)
      setBomError(null)
      try {
        const response = await fetch(`/api/v1/orders/${effectiveOrderId}/bom`, {
          headers: getAuthHeader(),
        })
        if (!response.ok) {
          if (response.status === 404) {
            localStorage.removeItem(LAST_ORDER_KEY)
            throw new Error('Заказ не найден или спецификация ещё не создана')
          }
          throw new Error('Ошибка загрузки спецификации')
        }
        const data: FullBOM = await response.json()
        setBom(data)
        originalBomRef.current = JSON.parse(JSON.stringify(data)) // Deep copy
        setHasChanges(false)
        setNeedsRecalculation(false)
        setSaveStatus('idle')
      } catch (err) {
        setBomError(err instanceof Error ? err.message : 'Ошибка загрузки')
      } finally {
        setIsLoadingBom(false)
      }
    }

    loadBom()
  }, [effectiveOrderId])

  // Load machine profile from settings
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch("/api/v1/settings", {
          headers: getAuthHeader(),
        })
        if (response.ok) {
          const data = await response.json()
          if (data.settings?.machine_profile) {
            setMachineProfile(data.settings.machine_profile)
          }
        }
      } catch (error) {
        console.error("Failed to load settings:", error)
      }
    }
    loadSettings()
  }, [])

  // Проверка нужен ли полный пересчёт (изменились габариты/материал/тип)
  const checkNeedsRecalculation = useCallback((newBom: FullBOM) => {
    const original = originalBomRef.current
    if (!original) return false

    // Проверяем габариты
    if (
      newBom.dimensions.width_mm !== original.dimensions.width_mm ||
      newBom.dimensions.height_mm !== original.dimensions.height_mm ||
      newBom.dimensions.depth_mm !== original.dimensions.depth_mm
    ) {
      return true
    }

    // Проверяем материал и толщину
    if (
      newBom.body_material.type !== original.body_material.type ||
      newBom.body_material.thickness_mm !== original.body_material.thickness_mm
    ) {
      return true
    }

    // Проверяем тип мебели
    if (newBom.furniture_type !== original.furniture_type) {
      return true
    }

    return false
  }, [])

  // Автосохранение (debounced)
  const debouncedSave = useCallback(async (bomToSave: FullBOM) => {
    if (!effectiveOrderId) return

    setSaveStatus('saving')
    try {
      const response = await fetch(`/api/v1/orders/${effectiveOrderId}/bom`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          dimensions: bomToSave.dimensions,
          furniture_type: bomToSave.furniture_type,
          body_material: bomToSave.body_material,
          panels: bomToSave.panels,
          hardware: bomToSave.hardware,
          fasteners: bomToSave.fasteners,
          edge_bands: bomToSave.edge_bands,
        }),
      })

      if (!response.ok) {
        throw new Error('Ошибка сохранения')
      }

      setSaveStatus('saved')
      setHasChanges(false)

      // Убираем индикатор "Сохранено" через 2 сек
      if (savedIndicatorTimeoutRef.current) {
        clearTimeout(savedIndicatorTimeoutRef.current)
      }
      savedIndicatorTimeoutRef.current = setTimeout(() => {
        setSaveStatus('idle')
      }, 2000)
    } catch {
      setSaveStatus('error')
      toast({
        title: "Ошибка автосохранения",
        description: "Не удалось сохранить изменения",
        variant: "destructive",
      })
    }
  }, [effectiveOrderId, toast])

  // Update BOM data (local state) с определением типа изменения
  const handleBomUpdate = useCallback((updates: Partial<FullBOM>, skipAutosave = false) => {
    if (!bom) return

    const newBom = { ...bom, ...updates }
    setBom(newBom)
    setHasChanges(true)

    const needsRecalc = checkNeedsRecalculation(newBom)
    setNeedsRecalculation(needsRecalc)

    // Если нужен пересчёт — не автосохраняем, ждём кнопку "Пересчитать"
    // Если мелкие изменения — автосохраняем с debounce
    if (!needsRecalc && !skipAutosave) {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      saveTimeoutRef.current = setTimeout(() => {
        debouncedSave(newBom)
      }, 1500)
    }
  }, [bom, checkNeedsRecalculation, debouncedSave])

  // Пересчёт BOM через калькуляторы
  const handleRecalculate = async () => {
    if (!effectiveOrderId || !bom) return

    setIsRecalculating(true)
    try {
      // Сначала сохраняем текущие габариты
      await fetch(`/api/v1/orders/${effectiveOrderId}/bom`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          dimensions: bom.dimensions,
          furniture_type: bom.furniture_type,
          body_material: bom.body_material,
        }),
      })

      // Затем вызываем пересчёт
      const response = await fetch(`/api/v1/orders/${effectiveOrderId}/bom/recalculate`, {
        method: 'POST',
        headers: getAuthHeader(),
      })

      if (!response.ok) {
        throw new Error('Ошибка пересчёта')
      }

      const updatedBom = await response.json()
      setBom(updatedBom)
      originalBomRef.current = JSON.parse(JSON.stringify(updatedBom))
      setHasChanges(false)
      setNeedsRecalculation(false)
      setSaveStatus('saved')

      toast({
        title: "Пересчитано",
        description: `Панели: ${updatedBom.summary?.total_panels || 0}, площадь: ${updatedBom.summary?.total_area_m2 || 0} м²`,
      })

      // Убираем индикатор через 2 сек
      if (savedIndicatorTimeoutRef.current) {
        clearTimeout(savedIndicatorTimeoutRef.current)
      }
      savedIndicatorTimeoutRef.current = setTimeout(() => {
        setSaveStatus('idle')
      }, 2000)
    } catch (error) {
      toast({
        title: "Ошибка",
        description: error instanceof Error ? error.message : "Не удалось пересчитать",
        variant: "destructive",
      })
    } finally {
      setIsRecalculating(false)
    }
  }

  // Очистка таймаутов при размонтировании
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
      if (savedIndicatorTimeoutRef.current) clearTimeout(savedIndicatorTimeoutRef.current)
    }
  }, [])

  // Panel handlers
  const handlePanelUpdate = (panelId: string, updates: Partial<BOMPanel>) => {
    if (!bom) return
    const updatedPanels = bom.panels.map(p =>
      p.id === panelId ? { ...p, ...updates } : p
    )
    handleBomUpdate({ panels: updatedPanels })
  }

  const handlePanelDelete = async (panelId: string) => {
    if (!effectiveOrderId || !bom) return

    try {
      const response = await fetch(
        `/api/v1/orders/${effectiveOrderId}/bom/panel/${panelId}`,
        {
          method: 'DELETE',
          headers: getAuthHeader(),
        }
      )

      if (!response.ok) {
        throw new Error('Ошибка удаления панели')
      }

      const updatedPanels = bom.panels.filter(p => p.id !== panelId)
      handleBomUpdate({ panels: updatedPanels })
      toast({
        title: "Удалено",
        description: "Панель удалена из спецификации",
      })
    } catch (error) {
      toast({
        title: "Ошибка",
        description: error instanceof Error ? error.message : "Не удалось удалить",
        variant: "destructive",
      })
    }
  }

  const handlePanelAdd = async (panel: Omit<BOMPanel, "id">) => {
    if (!effectiveOrderId || !bom) return

    try {
      const response = await fetch(
        `/api/v1/orders/${effectiveOrderId}/bom/add-panel`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader(),
          },
          body: JSON.stringify(panel),
        }
      )

      if (!response.ok) {
        throw new Error('Ошибка добавления панели')
      }

      const result = await response.json()
      if (result.panel) {
        handleBomUpdate({ panels: [...bom.panels, result.panel] })
        toast({
          title: "Добавлено",
          description: "Панель добавлена в спецификацию",
        })
      }
    } catch (error) {
      toast({
        title: "Ошибка",
        description: error instanceof Error ? error.message : "Не удалось добавить",
        variant: "destructive",
      })
    }
  }

  // Hardware/Fastener handlers
  const handleHardwareUpdate = (sku: string, updates: Partial<BOMHardware>) => {
    if (!bom) return
    const updatedHardware = bom.hardware.map(h =>
      h.sku === sku ? { ...h, ...updates } : h
    )
    handleBomUpdate({ hardware: updatedHardware })
  }

  const handleFastenerUpdate = (id: string, updates: Partial<BOMFastener>) => {
    if (!bom) return
    const updatedFasteners = bom.fasteners.map(f =>
      f.id === id ? { ...f, ...updates } : f
    )
    handleBomUpdate({ fasteners: updatedFasteners })
  }

  const handleEdgeBandUpdate = (id: string, updates: Partial<BOMEdgeBand>) => {
    if (!bom) return
    const updatedEdgeBands = bom.edge_bands.map(eb =>
      eb.id === id ? { ...eb, ...updates } : eb
    )
    handleBomUpdate({ edge_bands: updatedEdgeBands })
  }

  // DXF generation
  const handleGenerateDxf = async () => {
    if (!bom || !effectiveOrderId) return

    setIsGeneratingDxf(true)
    setDxfError(null)

    try {
      const panels = bom.panels.length > 0 ? bom.panels : [
        {
          name: 'Боковина левая',
          width_mm: bom.dimensions.depth_mm - bom.body_material.thickness_mm,
          height_mm: bom.dimensions.height_mm,
          thickness_mm: bom.body_material.thickness_mm,
          material: bom.body_material.type,
        },
        {
          name: 'Боковина правая',
          width_mm: bom.dimensions.depth_mm - bom.body_material.thickness_mm,
          height_mm: bom.dimensions.height_mm,
          thickness_mm: bom.body_material.thickness_mm,
          material: bom.body_material.type,
        },
        {
          name: 'Верх',
          width_mm: bom.dimensions.width_mm - bom.body_material.thickness_mm * 2,
          height_mm: bom.dimensions.depth_mm - bom.body_material.thickness_mm,
          thickness_mm: bom.body_material.thickness_mm,
          material: bom.body_material.type,
        },
        {
          name: 'Низ',
          width_mm: bom.dimensions.width_mm - bom.body_material.thickness_mm * 2,
          height_mm: bom.dimensions.depth_mm - bom.body_material.thickness_mm,
          thickness_mm: bom.body_material.thickness_mm,
          material: bom.body_material.type,
        },
      ]

      const response = await fetch('/api/v1/cam/dxf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader()
        },
        body: JSON.stringify({
          order_id: effectiveOrderId,
          panels,
          sheet_width_mm: 2440,
          sheet_height_mm: 1220,
        }),
      })

      const data = await response.json()

      if (data.job_id) {
        setDxfJobId(data.job_id)
        pollJobStatus(data.job_id)
      } else {
        setDxfError(data.detail || 'Ошибка создания задачи')
        setIsGeneratingDxf(false)
      }
    } catch (error) {
      setDxfError(error instanceof Error ? error.message : 'Ошибка генерации')
      setIsGeneratingDxf(false)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 30
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000))

      try {
        const response = await fetch(`/api/v1/cam/jobs/${jobId}`, {
          headers: getAuthHeader()
        })
        const data = await response.json()

        if (data.status === 'Completed' && data.artifact_id) {
          // Используем прямой endpoint /file вместо presigned URL
          setDxfDownloadUrl(`/api/v1/cam/jobs/${jobId}/file`)
          setIsGeneratingDxf(false)
          return
        }
        if (data.status === 'Failed') {
          setDxfError(data.error || 'Генерация не удалась')
          setIsGeneratingDxf(false)
          return
        }
      } catch {
        // Continue polling
      }
    }

    setDxfError('Превышено время ожидания')
    setIsGeneratingDxf(false)
  }

  const handleGenerateGcode = async () => {
    if (!hasSelectedMachineProfile() || !machineProfile) {
      setIsFirstTimeProfile(true)
      setShowProfileModal(true)
      return
    }

    if (!dxfDownloadUrl && !isGeneratingDxf) {
      await handleGenerateDxf()
    }

    if (isGeneratingDxf) {
      setTimeout(() => handleGenerateGcode(), 2000)
      return
    }

    if (!dxfJobId) {
      setGcodeError("Сначала сгенерируйте DXF")
      return
    }

    setIsGeneratingGcode(true)
    setGcodeError(null)

    try {
      const jobResponse = await fetch(`/api/v1/cam/jobs/${dxfJobId}`, {
        headers: getAuthHeader(),
      })
      const jobData = await jobResponse.json()

      if (!jobData.artifact_id) {
        throw new Error("DXF артефакт не найден")
      }

      const response = await fetch("/api/v1/cam/gcode", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          dxf_artifact_id: jobData.artifact_id,
          machine_profile: machineProfile,
          cut_depth: bom?.body_material.thickness_mm || 18.0,
        }),
      })

      const data = await response.json()

      if (data.job_id) {
        setGcodeJobId(data.job_id)
        pollGcodeJobStatus(data.job_id)
      } else {
        setGcodeError(data.detail || "Ошибка создания задачи G-code")
        setIsGeneratingGcode(false)
      }
    } catch (error) {
      setGcodeError(error instanceof Error ? error.message : "Ошибка генерации G-code")
      setIsGeneratingGcode(false)
    }
  }

  const pollGcodeJobStatus = async (jobId: string) => {
    const maxAttempts = 30
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((resolve) => setTimeout(resolve, 1000))

      try {
        const response = await fetch(`/api/v1/cam/jobs/${jobId}`, {
          headers: getAuthHeader(),
        })
        const data = await response.json()

        if (data.status === "Completed" && data.artifact_id) {
          // Используем прямой endpoint /file вместо presigned URL
          setGcodeDownloadUrl(`/api/v1/cam/jobs/${jobId}/file`)
          setIsGeneratingGcode(false)
          return
        }
        if (data.status === "Failed") {
          setGcodeError(data.error || "Генерация G-code не удалась")
          setIsGeneratingGcode(false)
          return
        }
      } catch {
        // Continue polling
      }
    }

    setGcodeError("Превышено время ожидания")
    setIsGeneratingGcode(false)
  }

  const handleProfileSelected = (profileId: string) => {
    setMachineProfile(profileId)
    setTimeout(() => {
      handleGenerateGcode()
    }, 100)
  }

  const handleExport = () => {
    toast({
      title: "Экспорт BOM",
      description: "Функционал экспорта будет доступен в ближайшем обновлении",
    })
  }

  // Empty state
  if (!effectiveOrderId) {
    return (
      <div className="p-6 w-full space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Спецификация (BOM)</h1>
            <p className="text-muted-foreground">
              Детальная спецификация материалов и компонентов для производства
            </p>
          </div>
        </div>
        <Card>
          <EmptyBomState />
        </Card>
      </div>
    )
  }

  // Loading state
  if (isLoadingBom) {
    return (
      <div className="p-6 w-full space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Спецификация (BOM)</h1>
            <p className="text-muted-foreground">Загрузка...</p>
          </div>
        </div>
        <StatCardSkeleton count={4} />
      </div>
    )
  }

  // Error state
  if (bomError) {
    return (
      <div className="p-6 w-full space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Спецификация (BOM)</h1>
            <p className="text-muted-foreground">Ошибка загрузки</p>
          </div>
        </div>
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive mb-4">{bomError}</p>
            <Button variant="outline" asChild>
              <a href="/orders">К списку заказов</a>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // No BOM data
  if (!bom) {
    return (
      <div className="p-6 w-full space-y-6">
        <Card>
          <EmptyBomState />
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 w-full space-y-6">
      {/* Заголовок */}
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
        </div>
      </div>

      {/* Шапка заказа (редактируемая) */}
      <BOMHeader
        furnitureType={bom.furniture_type}
        dimensions={bom.dimensions}
        bodyMaterial={bom.body_material}
        onUpdate={(updates) => {
          if (updates.dimensions) {
            handleBomUpdate({ dimensions: { ...bom.dimensions, ...updates.dimensions } })
          }
          if (updates.body_material) {
            handleBomUpdate({ body_material: { ...bom.body_material, ...updates.body_material } })
          }
          if (updates.furniture_type) {
            handleBomUpdate({ furniture_type: updates.furniture_type })
          }
        }}
        onRecalculate={needsRecalculation ? handleRecalculate : undefined}
        hasChanges={needsRecalculation}
        isLoading={isRecalculating}
      />

      {/* Production Stepper */}
      <ProductionStepper
        orderId={effectiveOrderId}
        hasOrder={true}
        dxfStatus={
          isGeneratingDxf
            ? "loading"
            : dxfError
              ? "error"
              : dxfDownloadUrl
                ? "completed"
                : "pending"
        }
        dxfDownloadUrl={dxfDownloadUrl}
        dxfError={dxfError}
        onGenerateDxf={handleGenerateDxf}
        gcodeStatus={
          isGeneratingGcode
            ? "loading"
            : gcodeError
              ? "error"
              : gcodeDownloadUrl
                ? "completed"
                : "pending"
        }
        gcodeDownloadUrl={gcodeDownloadUrl}
        gcodeError={gcodeError}
        onGenerateGcode={handleGenerateGcode}
        machineProfile={machineProfile}
        onOpenProfileModal={() => {
          setIsFirstTimeProfile(false)
          setShowProfileModal(true)
        }}
      />

      {/* Machine Profile Modal */}
      <MachineProfileModal
        open={showProfileModal}
        onOpenChange={setShowProfileModal}
        currentProfile={machineProfile}
        onSelectProfile={handleProfileSelected}
        isFirstTime={isFirstTimeProfile}
      />

      {/* Визуализация раскладки на листе */}
      <SheetLayoutPreview
        panels={bom.panels}
        sheetWidth={2800}
        sheetHeight={2070}
        showCombineSuggestion={true}
      />

      {/* Таблица панелей */}
      <PanelsTable
        panels={bom.panels}
        onPanelUpdate={handlePanelUpdate}
        onPanelDelete={handlePanelDelete}
        onPanelAdd={handlePanelAdd}
        sheetArea={5.8}
      />

      {/* Таблица фурнитуры и крепежа */}
      <HardwareTable
        hardware={bom.hardware}
        fasteners={bom.fasteners}
        onHardwareUpdate={handleHardwareUpdate}
        onFastenerUpdate={handleFastenerUpdate}
      />

      {/* Таблица кромки */}
      <EdgeBandTable
        edgeBands={bom.edge_bands}
        onEdgeBandUpdate={handleEdgeBandUpdate}
      />

      {/* Индикатор статуса сохранения */}
      {(saveStatus !== 'idle' || needsRecalculation) && (
        <div className={`fixed bottom-6 right-6 rounded-lg px-4 py-3 shadow-lg flex items-center gap-3 transition-all ${
          needsRecalculation
            ? 'bg-amber-100 dark:bg-amber-900/50 border border-amber-300 dark:border-amber-700'
            : saveStatus === 'saving'
              ? 'bg-blue-100 dark:bg-blue-900/50 border border-blue-300 dark:border-blue-700'
              : saveStatus === 'saved'
                ? 'bg-green-100 dark:bg-green-900/50 border border-green-300 dark:border-green-700'
                : 'bg-red-100 dark:bg-red-900/50 border border-red-300 dark:border-red-700'
        }`}>
          {needsRecalculation ? (
            <>
              <span className="text-amber-800 dark:text-amber-200 text-sm">
                Габариты изменены — нужен пересчёт
              </span>
              <Button size="sm" onClick={handleRecalculate} disabled={isRecalculating}>
                {isRecalculating ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : null}
                Пересчитать
              </Button>
            </>
          ) : saveStatus === 'saving' ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />
              <span className="text-blue-800 dark:text-blue-200 text-sm">Сохранение...</span>
            </>
          ) : saveStatus === 'saved' ? (
            <>
              <Check className="h-4 w-4 text-green-600 dark:text-green-400" />
              <span className="text-green-800 dark:text-green-200 text-sm">Сохранено</span>
            </>
          ) : (
            <span className="text-red-800 dark:text-red-200 text-sm">Ошибка сохранения</span>
          )}
        </div>
      )}
    </div>
  )
}
