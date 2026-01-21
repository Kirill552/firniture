"use client"

import { LucideIcon, Loader2, Download, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export type FileStatus =
  | "idle"
  | "generating"
  | "ready"
  | "error"
  | "outdated"
  | "blocked"

interface FileGenerationCardProps {
  icon: LucideIcon
  label: string
  status: FileStatus
  downloadUrl?: string | null
  error?: string | null
  blockedReason?: string
  onGenerate: () => void
  onRegenerate?: () => void
}

export function FileGenerationCard({
  icon: Icon,
  label,
  status,
  downloadUrl,
  error,
  blockedReason,
  onGenerate,
  onRegenerate,
}: FileGenerationCardProps) {
  return (
    <div className="flex items-center justify-between py-2 px-3 border rounded-lg bg-card">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium">{label}</span>
      </div>

      <div className="flex items-center gap-2">
        {status === "idle" && (
          <Button size="sm" onClick={onGenerate}>
            Создать
          </Button>
        )}

        {status === "generating" && (
          <Button size="sm" disabled>
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
            Создаётся...
          </Button>
        )}

        {status === "ready" && downloadUrl && (
          <>
            <Button size="sm" variant="outline" className="text-green-600" asChild>
              <a href={downloadUrl} download>
                <Download className="h-4 w-4 mr-1" />
                Скачать
              </a>
            </Button>
            {onRegenerate && (
              <Button size="sm" variant="ghost" onClick={onRegenerate}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            )}
          </>
        )}

        {status === "error" && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-destructive">{error || "Ошибка"}</span>
            <Button size="sm" variant="destructive" onClick={onGenerate}>
              Повторить
            </Button>
          </div>
        )}

        {status === "outdated" && downloadUrl && (
          <>
            <Button size="sm" variant="outline" className="text-amber-600" asChild>
              <a href={downloadUrl} download>
                <Download className="h-4 w-4 mr-1" />
                Устарел
              </a>
            </Button>
            {onRegenerate && (
              <Button size="sm" onClick={onRegenerate}>
                Пересоздать
              </Button>
            )}
          </>
        )}

        {status === "blocked" && (
          <Button size="sm" disabled title={blockedReason}>
            {blockedReason || "Недоступно"}
          </Button>
        )}
      </div>
    </div>
  )
}
