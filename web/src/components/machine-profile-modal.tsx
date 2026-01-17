"use client"

import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { getAuthHeader } from "@/lib/auth"

interface MachineProfile {
  id: string
  name: string
  description: string
}

interface MachineProfileModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentProfile: string | null
  onSelectProfile: (profileId: string) => void
  isFirstTime: boolean
}

const MACHINE_PROFILE_KEY = "hasSelectedMachineProfile"

export function MachineProfileModal({
  open,
  onOpenChange,
  currentProfile,
  onSelectProfile,
  isFirstTime,
}: MachineProfileModalProps) {
  const [profiles, setProfiles] = useState<MachineProfile[]>([])
  const [selectedProfile, setSelectedProfile] = useState<string>(currentProfile || "weihong")
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Загрузка списка профилей
  useEffect(() => {
    if (!open) return

    const loadProfiles = async () => {
      setIsLoading(true)
      try {
        const response = await fetch("/api/v1/cam/machine-profiles", {
          headers: getAuthHeader(),
        })
        if (response.ok) {
          const data = await response.json()
          setProfiles(data.profiles || [])
        }
      } catch (error) {
        console.error("Failed to load profiles:", error)
        // Fallback профили
        setProfiles([
          { id: "weihong", name: "Weihong (NCStudio)", description: "~30% рынка, бюджетный сегмент" },
          { id: "syntec", name: "Syntec (KDT/WoodTec)", description: "~25% рынка, FANUC-совместимый" },
          { id: "fanuc", name: "FANUC", description: "Премиум сегмент, ISO стандарт" },
          { id: "dsp", name: "DSP-контроллер", description: "Бюджетный сегмент" },
          { id: "homag", name: "HOMAG", description: "Премиум мебельное оборудование" },
        ])
      } finally {
        setIsLoading(false)
      }
    }

    loadProfiles()
  }, [open])

  // Обновляем selectedProfile при изменении currentProfile
  useEffect(() => {
    if (currentProfile) {
      setSelectedProfile(currentProfile)
    }
  }, [currentProfile])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // Сохраняем в настройки фабрики
      await fetch("/api/v1/settings", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          machine_profile: selectedProfile,
        }),
      })

      // Отмечаем что профиль выбран
      localStorage.setItem(MACHINE_PROFILE_KEY, "true")

      onSelectProfile(selectedProfile)
      onOpenChange(false)
    } catch (error) {
      console.error("Failed to save profile:", error)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isFirstTime ? "Выберите ваш станок" : "Изменить профиль станка"}
          </DialogTitle>
          <DialogDescription>
            {isFirstTime
              ? "Выберите систему ЧПУ вашего станка для совместимости программы"
              : "Профиль станка влияет на формат G-code"}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="text-center text-muted-foreground py-4">
              Загрузка профилей...
            </div>
          ) : (
            <div className="space-y-2">
              {profiles.map((profile) => (
                <label
                  key={profile.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedProfile === profile.id
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  <input
                    type="radio"
                    name="machineProfile"
                    value={profile.id}
                    checked={selectedProfile === profile.id}
                    onChange={(e) => setSelectedProfile(e.target.value)}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="font-medium">{profile.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {profile.description}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        <DialogFooter>
          {!isFirstTime && (
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
          )}
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Сохранение..." : "Сохранить и продолжить"}
          </Button>
        </DialogFooter>

        {isFirstTime && (
          <p className="text-xs text-muted-foreground text-center">
            Изменить можно в Настройки → Станок
          </p>
        )}
      </DialogContent>
    </Dialog>
  )
}

// Хелпер для проверки первого запуска
export function hasSelectedMachineProfile(): boolean {
  if (typeof window === "undefined") return true
  return localStorage.getItem(MACHINE_PROFILE_KEY) === "true"
}
