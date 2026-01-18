"use client"

import { useSearchParams } from 'next/navigation'
import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Download, Plus, Package, Loader2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { getAuthHeader } from "@/lib/auth"
import { StatCardSkeleton } from "@/components/ui/table-skeleton"
import { ProductionStepper } from "@/components/production-stepper"
import { MachineProfileModal, hasSelectedMachineProfile } from "@/components/machine-profile-modal"
import { BOMHeader, PanelsTable, HardwareTable, EdgeBandTable, SheetLayoutPreview } from "@/components/bom"
import type { FullBOM, BOMPanel, BOMHardware, BOMFastener, BOMEdgeBand } from "@/types/api"

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
  const [isSaving, setIsSaving] = useState(false)

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
        setHasChanges(false)
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

  // Update BOM data (local state)
  const handleBomUpdate = useCallback((updates: Partial<FullBOM>) => {
    if (!bom) return
    setBom({ ...bom, ...updates })
    setHasChanges(true)
  }, [bom])

  // Save BOM to server
  const handleSave = async () => {
    if (!effectiveOrderId || !bom) return

    setIsSaving(true)
    try {
      const response = await fetch(`/api/v1/orders/${effectiveOrderId}/bom`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          dimensions: bom.dimensions,
          furniture_type: bom.furniture_type,
          body_material: bom.body_material,
          panels: bom.panels,
          hardware: bom.hardware,
          fasteners: bom.fasteners,
          edge_bands: bom.edge_bands,
        }),
      })

      if (!response.ok) {
        throw new Error('Ошибка сохранения')
      }

      const updatedBom = await response.json()
      setBom(updatedBom)
      setHasChanges(false)
      toast({
        title: "Сохранено",
        description: "Спецификация успешно обновлена",
      })
    } catch (error) {
      toast({
        title: "Ошибка",
        description: error instanceof Error ? error.message : "Не удалось сохранить",
        variant: "destructive",
      })
    } finally {
      setIsSaving(false)
    }
  }

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
          const downloadResponse = await fetch(`/api/v1/cam/jobs/${jobId}/download`, {
            headers: getAuthHeader()
          })
          if (downloadResponse.ok) {
            const downloadData = await downloadResponse.json()
            setDxfDownloadUrl(downloadData.download_url)
          }
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
          const downloadResponse = await fetch(`/api/v1/cam/jobs/${jobId}/download`, {
            headers: getAuthHeader(),
          })
          if (downloadResponse.ok) {
            const downloadData = await downloadResponse.json()
            setGcodeDownloadUrl(downloadData.download_url)
          }
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
        onSave={handleSave}
        hasChanges={hasChanges}
        isLoading={isSaving}
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

      {/* Индикатор несохранённых изменений */}
      {hasChanges && (
        <div className="fixed bottom-6 right-6 bg-amber-100 dark:bg-amber-900/50 border border-amber-300 dark:border-amber-700 rounded-lg px-4 py-3 shadow-lg flex items-center gap-3">
          <span className="text-amber-800 dark:text-amber-200 text-sm">
            Есть несохранённые изменения
          </span>
          <Button size="sm" onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : null}
            Сохранить
          </Button>
        </div>
      )}
    </div>
  )
}
