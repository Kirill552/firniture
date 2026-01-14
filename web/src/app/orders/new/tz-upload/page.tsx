'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useState, useCallback } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Loader2, Upload, ImageIcon, Check, AlertTriangle, Pencil, X } from "lucide-react"
import { FileDropzone } from '@/components/upload/file-dropzone'
import { apiClient } from '@/lib/api-client'
import type { ExtractedFurnitureParams, ImageExtractResponse } from '@/types/api'

/** Конвертация File в base64 */
async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Убираем префикс data:image/...;base64,
      const base64 = result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/** Получение MIME типа из File */
function getMimeType(file: File): 'image/jpeg' | 'image/png' | 'image/webp' {
  if (file.type === 'image/png') return 'image/png'
  if (file.type === 'image/webp') return 'image/webp'
  return 'image/jpeg'
}

/** Проверка, является ли файл изображением */
function isImageFile(file: File): boolean {
  return file.type.startsWith('image/')
}

/** Компонент отображения извлечённых параметров */
function ExtractedParamsDisplay({
  params,
  onEdit,
  onConfirm,
}: {
  params: ExtractedFurnitureParams
  onEdit: () => void
  onConfirm: () => void
}) {
  const { furniture_type, dimensions, body_material, facade_material, door_count, drawer_count, shelf_count, confidence, needs_clarification, clarification_questions } = params

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Извлечённые параметры</h3>
        <Badge variant={confidence >= 0.7 ? "default" : confidence >= 0.5 ? "secondary" : "destructive"}>
          Уверенность: {Math.round(confidence * 100)}%
        </Badge>
      </div>

      {needs_clarification && clarification_questions.length > 0 && (
        <div className="p-3 rounded-md bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">Требуется уточнение:</p>
              <ul className="text-sm text-yellow-700 dark:text-yellow-300 mt-1 space-y-1">
                {clarification_questions.map((q, i) => <li key={i}>• {q}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 text-sm">
        {furniture_type && (
          <div>
            <span className="text-muted-foreground">Тип:</span>
            <p className="font-medium">{furniture_type.category.replace('_', ' ')}</p>
          </div>
        )}

        {dimensions && (
          <div>
            <span className="text-muted-foreground">Размеры:</span>
            <p className="font-medium">
              {dimensions.width_mm || '?'} × {dimensions.height_mm || '?'} × {dimensions.depth_mm || '?'} мм
            </p>
          </div>
        )}

        {body_material && (
          <div>
            <span className="text-muted-foreground">Корпус:</span>
            <p className="font-medium">
              {body_material.type || 'не указан'} {body_material.color || ''}
            </p>
          </div>
        )}

        {facade_material && (
          <div>
            <span className="text-muted-foreground">Фасад:</span>
            <p className="font-medium">
              {facade_material.type || 'не указан'} {facade_material.color || ''}
            </p>
          </div>
        )}

        {door_count !== null && door_count !== undefined && (
          <div>
            <span className="text-muted-foreground">Дверей:</span>
            <p className="font-medium">{door_count}</p>
          </div>
        )}

        {drawer_count !== null && drawer_count !== undefined && (
          <div>
            <span className="text-muted-foreground">Ящиков:</span>
            <p className="font-medium">{drawer_count}</p>
          </div>
        )}

        {shelf_count !== null && shelf_count !== undefined && (
          <div>
            <span className="text-muted-foreground">Полок:</span>
            <p className="font-medium">{shelf_count}</p>
          </div>
        )}
      </div>

      <div className="flex gap-2 pt-2">
        <Button variant="outline" size="sm" onClick={onEdit}>
          <Pencil className="h-4 w-4 mr-1" />
          Редактировать
        </Button>
        <Button size="sm" onClick={onConfirm}>
          <Check className="h-4 w-4 mr-1" />
          Подтвердить и продолжить
        </Button>
      </div>
    </div>
  )
}

export default function TzUploadPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('orderId')

  // Состояние формы
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [imagePreview, setImagePreview] = useState<string | null>(null)

  // Состояние Vision OCR
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState('')
  const [extractedParams, setExtractedParams] = useState<ExtractedFurnitureParams | null>(null)
  const [extractionError, setExtractionError] = useState<string | null>(null)
  const [fallbackToDialogue, setFallbackToDialogue] = useState(false)
  const [dialoguePrompt, setDialoguePrompt] = useState<string | null>(null)

  // Режим редактирования параметров
  const [isEditing, setIsEditing] = useState(false)

  // Финальная отправка
  const [isSubmitting, setIsSubmitting] = useState(false)

  /** Обработка загруженных файлов */
  const handleFiles = useCallback(async (newFiles: File[]) => {
    setFiles(prev => [...prev, ...newFiles])

    // Если есть изображение — автоматически запускаем анализ
    const imageFile = newFiles.find(isImageFile)
    if (imageFile) {
      // Создаём превью
      const previewUrl = URL.createObjectURL(imageFile)
      setImagePreview(previewUrl)

      // Запускаем Vision OCR
      await analyzeImage(imageFile)
    }
  }, [])

  /** Анализ изображения через Vision OCR */
  const analyzeImage = async (file: File) => {
    setIsAnalyzing(true)
    setAnalysisProgress('Загружаю изображение...')
    setExtractionError(null)
    setExtractedParams(null)
    setFallbackToDialogue(false)

    try {
      setAnalysisProgress('Конвертирую в base64...')
      const base64 = await fileToBase64(file)
      const mimeType = getMimeType(file)

      setAnalysisProgress('Анализирую изображение...')

      const response: ImageExtractResponse = await apiClient.extractFromImage({
        image_base64: base64,
        image_mime_type: mimeType,
        order_id: orderId || undefined,
        language_hint: 'ru',
      })

      if (response.success && response.parameters) {
        setExtractedParams(response.parameters)
        setAnalysisProgress(`Готово за ${response.processing_time_ms} мс`)

        if (response.fallback_to_dialogue) {
          setFallbackToDialogue(true)
          setDialoguePrompt(response.dialogue_prompt || null)
        }
      } else {
        setExtractionError(response.error || 'Не удалось извлечь параметры')
        if (response.fallback_to_dialogue) {
          setFallbackToDialogue(true)
          setDialoguePrompt(response.dialogue_prompt || 'Пожалуйста, уточните детали изделия')
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка анализа'
      setExtractionError(message)
    } finally {
      setIsAnalyzing(false)
    }
  }

  /** Удаление файла */
  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
    if (files[index] && isImageFile(files[index])) {
      setImagePreview(null)
      setExtractedParams(null)
    }
  }

  /** Формирование строки контекста из извлечённых параметров */
  const formatExtractedContext = (params: ExtractedFurnitureParams): string => {
    const lines: string[] = []

    if (params.furniture_type) {
      lines.push(`Тип изделия: ${params.furniture_type.category.replace('_', ' ')}`)
    }

    if (params.dimensions) {
      const { width_mm, height_mm, depth_mm, thickness_mm } = params.dimensions
      const dims = [width_mm, height_mm, depth_mm].filter(Boolean).join(' × ')
      if (dims) lines.push(`Размеры: ${dims} мм`)
      if (thickness_mm) lines.push(`Толщина материала: ${thickness_mm} мм`)
    }

    if (params.body_material) {
      const mat = [params.body_material.type, params.body_material.color].filter(Boolean).join(' ')
      if (mat) lines.push(`Корпус: ${mat}`)
    }

    if (params.facade_material) {
      const mat = [params.facade_material.type, params.facade_material.color].filter(Boolean).join(' ')
      if (mat) lines.push(`Фасад: ${mat}`)
    }

    if (params.door_count !== null && params.door_count !== undefined) {
      lines.push(`Дверей: ${params.door_count}`)
    }

    if (params.drawer_count !== null && params.drawer_count !== undefined) {
      lines.push(`Ящиков: ${params.drawer_count}`)
    }

    if (params.shelf_count !== null && params.shelf_count !== undefined) {
      lines.push(`Полок: ${params.shelf_count}`)
    }

    return lines.join('\n')
  }

  /** Переход к диалогу */
  const goToDialogue = () => {
    if (!orderId) return

    // Формируем контекст из извлечённых параметров
    const contextParts: string[] = []

    if (extractedParams) {
      contextParts.push(formatExtractedContext(extractedParams))
    }

    if (dialoguePrompt) {
      contextParts.push(`\n${dialoguePrompt}`)
    }

    const context = contextParts.join('\n').trim()
    const contextParam = context ? `&context=${encodeURIComponent(context)}` : ''

    router.push(`/orders/new/dialogue?orderId=${orderId}${contextParam}`)
  }

  /** Подтверждение параметров и переход */
  const confirmAndContinue = async () => {
    if (!orderId) return
    setIsSubmitting(true)

    try {
      // TODO: Сохранить extractedParams в заказ через API
      // await apiClient.updateOrderParams(orderId, extractedParams)

      // Формируем контекст из извлечённых параметров
      const context = extractedParams ? formatExtractedContext(extractedParams) : ''
      const contextParam = context ? `&context=${encodeURIComponent(context)}` : ''

      router.push(`/orders/new/dialogue?orderId=${orderId}${contextParam}`)
    } catch (err) {
      console.error('Ошибка сохранения:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  /** Отправка формы (для текстового ТЗ) */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orderId) return

    setIsSubmitting(true)
    try {
      // TODO: Отправить text + files на API

      // Формируем контекст: либо из извлечённых параметров, либо из текста
      let context = ''
      if (extractedParams) {
        context = formatExtractedContext(extractedParams)
      } else if (text.trim()) {
        context = `Текстовое описание от пользователя:\n${text.trim()}`
      }

      const contextParam = context ? `&context=${encodeURIComponent(context)}` : ''
      router.push(`/orders/new/dialogue?orderId=${orderId}${contextParam}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>Загрузка технического задания</CardTitle>
          <CardDescription>
            Загрузите фото или эскиз изделия — система автоматически извлечёт параметры.
            <br />
            Также можно ввести описание текстом.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Зона загрузки файлов */}
            <div className="space-y-3">
              <Label>Загрузить фото или эскиз</Label>
              <FileDropzone
                onFiles={handleFiles}
                onReject={(reasons) => console.warn('Отклонено:', reasons)}
                accept={['.png', '.jpg', '.jpeg', '.webp']}
                maxFiles={1}
                description="Поддерживаются изображения PNG, JPG, WebP"
                disabled={isAnalyzing}
              />
            </div>

            {/* Превью изображения */}
            {imagePreview && (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Превью загруженного изображения"
                  className="w-full max-h-64 object-contain rounded-lg border"
                />
                <Button
                  type="button"
                  variant="destructive"
                  size="icon"
                  className="absolute top-2 right-2 h-8 w-8"
                  onClick={() => {
                    setImagePreview(null)
                    setFiles([])
                    setExtractedParams(null)
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}

            {/* Индикатор анализа */}
            {isAnalyzing && (
              <div className="flex items-center gap-3 p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                <div>
                  <p className="font-medium text-blue-800 dark:text-blue-200">
                    {analysisProgress}
                  </p>
                  <p className="text-sm text-blue-600 dark:text-blue-300">
                    Извлекаем размеры, материалы и тип мебели...
                  </p>
                </div>
              </div>
            )}

            {/* Ошибка извлечения */}
            {extractionError && !extractedParams && (
              <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800 dark:text-red-200">
                      Ошибка анализа
                    </p>
                    <p className="text-sm text-red-600 dark:text-red-300">{extractionError}</p>
                    {fallbackToDialogue && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="mt-2"
                        onClick={goToDialogue}
                      >
                        Уточнить в диалоге с ИИ
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Извлечённые параметры */}
            {extractedParams && !isEditing && (
              <ExtractedParamsDisplay
                params={extractedParams}
                onEdit={() => setIsEditing(true)}
                onConfirm={confirmAndContinue}
              />
            )}

            {/* Fallback к диалогу */}
            {fallbackToDialogue && extractedParams && (
              <div className="p-3 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  Распознавание неполное. Рекомендуем уточнить детали в диалоге с ИИ.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={goToDialogue}
                >
                  Перейти к диалогу
                </Button>
              </div>
            )}

            {/* Разделитель */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  или введите текстом
                </span>
              </div>
            </div>

            {/* Текстовое описание */}
            <div className="space-y-2">
              <Label htmlFor="text">Описание ТЗ</Label>
              <Textarea
                id="text"
                placeholder="Опишите изделие, размеры, материалы..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="min-h-[100px]"
              />
            </div>

            {/* Список загруженных файлов (не изображения) */}
            {files.filter(f => !isImageFile(f)).length > 0 && (
              <ul className="text-xs text-muted-foreground space-y-1 max-h-32 overflow-auto border rounded p-2">
                {files.filter(f => !isImageFile(f)).map((f, i) => (
                  <li key={f.name} className="flex justify-between items-center">
                    <span>{f.name} • {Math.round(f.size / 1024)} KB</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => removeFile(i)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}

            {/* Кнопка отправки */}
            <Button
              type="submit"
              className="w-full"
              disabled={isSubmitting || isAnalyzing || !orderId}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Обработка...
                </>
              ) : extractedParams ? (
                'Продолжить к диалогу с ИИ'
              ) : (
                'Продолжить к диалогу с ИИ'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
