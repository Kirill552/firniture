"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Circle, Loader2, AlertCircle, Download, FileText, Settings, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

// Типы для статусов шагов
export type StepStatus = "pending" | "loading" | "completed" | "error"

export interface ProductionStepperProps {
  orderId: string
  hasOrder: boolean
  // DXF state
  dxfStatus: StepStatus
  dxfDownloadUrl: string | null
  dxfError: string | null
  onGenerateDxf: () => void
  // G-code state
  gcodeStatus: StepStatus
  gcodeDownloadUrl: string | null
  gcodeError: string | null
  onGenerateGcode: () => void
  // Machine profile
  machineProfile: string | null
  onOpenProfileModal: () => void
}

// Вспомогательный компонент для индикатора шага
interface StepIndicatorProps {
  stepNumber: number
  status: StepStatus
}

function StepIndicator({ stepNumber, status }: StepIndicatorProps) {
  const baseClasses = "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors"

  switch (status) {
    case "completed":
      return (
        <div className={cn(baseClasses, "border-green-500 bg-green-500 text-white")}>
          <Check className="h-5 w-5" />
        </div>
      )
    case "loading":
      return (
        <div className={cn(baseClasses, "border-blue-500 bg-blue-50")}>
          <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
        </div>
      )
    case "error":
      return (
        <div className={cn(baseClasses, "border-red-500 bg-red-50")}>
          <AlertCircle className="h-5 w-5 text-red-500" />
        </div>
      )
    case "pending":
    default:
      return (
        <div className={cn(baseClasses, "border-muted-foreground/30 bg-muted text-muted-foreground")}>
          <span className="text-sm font-medium">{stepNumber}</span>
        </div>
      )
  }
}

// Компонент коннектора между шагами
function StepConnector({ completed }: { completed: boolean }) {
  return (
    <div
      className={cn(
        "mx-2 h-0.5 flex-1 transition-colors",
        completed ? "bg-green-500" : "bg-muted-foreground/30"
      )}
    />
  )
}

// Основной компонент ProductionStepper
export function ProductionStepper({
  orderId,
  hasOrder,
  dxfStatus,
  dxfDownloadUrl,
  dxfError,
  onGenerateDxf,
  gcodeStatus,
  gcodeDownloadUrl,
  gcodeError,
  onGenerateGcode,
  machineProfile,
  onOpenProfileModal,
}: ProductionStepperProps) {
  // Статус первого шага (спецификация) — всегда completed если есть заказ
  const specStatus: StepStatus = hasOrder ? "completed" : "pending"

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-lg">Производство</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Stepper с 3 шагами */}
        <div className="flex items-start">
          {/* Шаг 1: Спецификация */}
          <div className="flex flex-col items-center">
            <StepIndicator stepNumber={1} status={specStatus} />
            <span className="mt-2 text-center text-sm font-medium">Спецификация</span>
            {specStatus === "completed" && (
              <Badge variant="outline" className="mt-1 text-xs text-green-600">
                Готово
              </Badge>
            )}
          </div>

          <StepConnector completed={specStatus === "completed"} />

          {/* Шаг 2: Раскрой (DXF) */}
          <div className="flex flex-col items-center">
            <StepIndicator stepNumber={2} status={dxfStatus} />
            <span className="mt-2 text-center text-sm font-medium">Раскрой (DXF)</span>

            {/* Действия для DXF */}
            <div className="mt-2 flex flex-col items-center gap-1">
              {dxfStatus === "pending" && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onGenerateDxf}
                  disabled={!hasOrder}
                >
                  <FileText className="mr-1.5 h-4 w-4" />
                  Создать
                </Button>
              )}

              {dxfStatus === "loading" && (
                <Badge variant="secondary" className="text-xs">
                  Генерация...
                </Badge>
              )}

              {dxfStatus === "completed" && dxfDownloadUrl && (
                <Button
                  size="sm"
                  variant="outline"
                  className="text-green-600 hover:text-green-700"
                  asChild
                >
                  <a href={dxfDownloadUrl} download>
                    <Download className="mr-1.5 h-4 w-4" />
                    Скачать
                  </a>
                </Button>
              )}

              {dxfStatus === "error" && dxfError && (
                <span className="text-center text-xs text-red-500">{dxfError}</span>
              )}
            </div>
          </div>

          <StepConnector completed={dxfStatus === "completed"} />

          {/* Шаг 3: Программа ЧПУ (G-code) */}
          <div className="flex flex-col items-center">
            <StepIndicator stepNumber={3} status={gcodeStatus} />
            <span className="mt-2 text-center text-sm font-medium">Программа ЧПУ</span>

            {/* Профиль станка */}
            {machineProfile && (
              <button
                onClick={onOpenProfileModal}
                className="mt-1 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <Settings className="h-3 w-3" />
                {machineProfile}
              </button>
            )}

            {/* Действия для G-code */}
            <div className="mt-2 flex flex-col items-center gap-1">
              {gcodeStatus === "pending" && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onGenerateGcode}
                  disabled={dxfStatus !== "completed"}
                >
                  <FileText className="mr-1.5 h-4 w-4" />
                  Сгенерировать
                </Button>
              )}

              {gcodeStatus === "loading" && (
                <Badge variant="secondary" className="text-xs">
                  Генерация...
                </Badge>
              )}

              {gcodeStatus === "completed" && gcodeDownloadUrl && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-green-600 hover:text-green-700"
                    asChild
                  >
                    <a href={gcodeDownloadUrl} download>
                      <Download className="mr-1.5 h-4 w-4" />
                      Скачать
                    </a>
                  </Button>

                  <Link
                    href={`/cam?orderId=${orderId}`}
                    className="mt-1 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Открыть в CAM
                  </Link>
                </>
              )}

              {gcodeStatus === "error" && gcodeError && (
                <span className="text-center text-xs text-red-500">{gcodeError}</span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
