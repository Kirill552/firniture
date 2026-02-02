/**
 * Утилиты для работы с API типами проекта АвтоРаскрой
 * Включает type guards, валидаторы и хелперы
 */

import {
  JobStatus,
  ValidationStatus,
  CAMJobKind,
  DialogueRole,
  InputType,
  CAMJobStatusResponse,
  Order,
  ProductConfig,
} from '@/types/api'

// ============================================================================
// Type Guards (проверки типов)
// ============================================================================

/**
 * Проверяет, является ли статус задачи завершенным
 */
export function isJobCompleted(status: JobStatus): boolean {
  return status === 'Completed'
}

/**
 * Проверяет, является ли статус задачи проваленным
 */
export function isJobFailed(status: JobStatus): boolean {
  return status === 'Failed'
}

/**
 * Проверяет, выполняется ли задача в данный момент
 */
export function isJobInProgress(status: JobStatus): boolean {
  return status === 'Processing' || status === 'Created'
}

/**
 * Проверяет, можно ли скачать артефакт задачи
 */
export function canDownloadArtifact(job: CAMJobStatusResponse): boolean {
  return isJobCompleted(job.status) && job.artifact_id !== null
}

/**
 * Проверяет, утверждена ли валидация
 */
export function isValidationApproved(status: ValidationStatus): boolean {
  return status === 'Approved'
}

/**
 * Проверяет, отклонена ли валидация
 */
export function isValidationRejected(status: ValidationStatus): boolean {
  return status === 'Rejected'
}

/**
 * Проверяет, является ли роль пользователем
 */
export function isUserMessage(role: DialogueRole): boolean {
  return role === 'user'
}

/**
 * Проверяет, является ли роль ассистентом
 */
export function isAssistantMessage(role: DialogueRole): boolean {
  return role === 'assistant'
}

/**
 * Проверяет, является ли тип задачи DXF
 */
export function isDXFJob(jobKind: CAMJobKind): boolean {
  return jobKind === 'DXF'
}

/**
 * Проверяет, является ли тип задачи GCODE
 */
export function isGCodeJob(jobKind: CAMJobKind): boolean {
  return jobKind === 'GCODE'
}

// ============================================================================
// Форматирование и отображение
// ============================================================================

/**
 * Возвращает человекочитаемое название статуса задачи
 */
export function getJobStatusLabel(status: JobStatus): string {
  const labels: Record<JobStatus, string> = {
    Created: 'Создана',
    Processing: 'Выполняется',
    Completed: 'Завершена',
    Failed: 'Ошибка',
  }
  return labels[status]
}

/**
 * Возвращает человекочитаемое название статуса валидации
 */
export function getValidationStatusLabel(status: ValidationStatus): string {
  const labels: Record<ValidationStatus, string> = {
    Pending: 'Ожидает',
    Approved: 'Утверждена',
    Rejected: 'Отклонена',
  }
  return labels[status]
}

/**
 * Возвращает человекочитаемое название типа задачи
 */
export function getJobKindLabel(jobKind: CAMJobKind): string {
  const labels: Record<CAMJobKind, string> = {
    DXF: 'DXF чертеж',
    GCODE: 'G-code программа',
  }
  return labels[jobKind]
}

/**
 * Возвращает человекочитаемое название типа входных данных
 */
export function getInputTypeLabel(inputType: InputType): string {
  const labels: Record<InputType, string> = {
    text: 'Текст',
    image: 'Изображение',
    sketch: 'Эскиз',
  }
  return labels[inputType]
}

/**
 * Возвращает CSS класс для статуса задачи (для Badge компонента)
 */
export function getJobStatusVariant(
  status: JobStatus
): 'default' | 'secondary' | 'outline' | 'destructive' {
  const variants: Record<JobStatus, 'default' | 'secondary' | 'outline' | 'destructive'> = {
    Created: 'secondary',
    Processing: 'default',
    Completed: 'outline',
    Failed: 'destructive',
  }
  return variants[status]
}

/**
 * Возвращает CSS класс для статуса валидации (для Badge компонента)
 */
export function getValidationStatusVariant(
  status: ValidationStatus
): 'default' | 'secondary' | 'outline' | 'destructive' {
  const variants: Record<ValidationStatus, 'default' | 'secondary' | 'outline' | 'destructive'> = {
    Pending: 'secondary',
    Approved: 'outline',
    Rejected: 'destructive',
  }
  return variants[status]
}

// ============================================================================
// Валидация данных
// ============================================================================

/**
 * Проверяет, является ли строка валидным UUID
 */
export function isValidUUID(value: string): boolean {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  return uuidRegex.test(value)
}

/**
 * Проверяет, является ли значение валидным размером в мм
 */
export function isValidDimension(value: number): boolean {
  return value > 0 && value < 10000 // Макс 10 метров
}

/**
 * Проверяет, является ли значение валидной толщиной материала в мм
 */
export function isValidThickness(value: number): boolean {
  return value > 0 && value < 100 // Макс 10 см
}

// ============================================================================
// Преобразование данных
// ============================================================================

/**
 * Форматирует дату ISO 8601 в человекочитаемый формат
 */
export function formatDate(isoDate: string): string {
  const date = new Date(isoDate)
  return new Intl.DateTimeFormat('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/**
 * Форматирует дату ISO 8601 в краткий формат
 */
export function formatDateShort(isoDate: string): string {
  const date = new Date(isoDate)
  return new Intl.DateTimeFormat('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

/**
 * Форматирует размер файла в человекочитаемый формат
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Б'

  const k = 1024
  const sizes = ['Б', 'КБ', 'МБ', 'ГБ']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${Math.round((bytes / Math.pow(k, i)) * 100) / 100} ${sizes[i]}`
}

/**
 * Форматирует размеры изделия в человекочитаемый формат
 */
export function formatDimensions(
  width: number,
  height: number,
  depth: number
): string {
  return `${width}×${height}×${depth} мм`
}

/**
 * Извлекает краткое описание ошибки из детального сообщения
 */
export function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  if (typeof error === 'string') {
    return error
  }
  return 'Неизвестная ошибка'
}

// ============================================================================
// Вычисления и бизнес-логика
// ============================================================================

/**
 * Вычисляет площадь изделия в м²
 */
export function calculateArea(productConfig: ProductConfig): number {
  return (
    (productConfig.width_mm * productConfig.height_mm) /
    1000000
  )
}

/**
 * Вычисляет объем изделия в м³
 */
export function calculateVolume(productConfig: ProductConfig): number {
  return (
    (productConfig.width_mm *
      productConfig.height_mm *
      productConfig.depth_mm) /
    1000000000
  )
}

/**
 * Проверяет, нужно ли показывать предупреждение о размерах
 */
export function shouldWarnAboutDimensions(productConfig: ProductConfig): boolean {
  // Предупреждаем, если хотя бы один размер больше 3 метров
  const maxDimension = Math.max(
    productConfig.width_mm,
    productConfig.height_mm,
    productConfig.depth_mm
  )
  return maxDimension > 3000
}

/**
 * Генерирует краткое описание изделия для отображения
 */
export function getProductSummary(productConfig: ProductConfig): string {
  const dims = formatDimensions(
    productConfig.width_mm,
    productConfig.height_mm,
    productConfig.depth_mm
  )
  const material = productConfig.material || 'материал не указан'
  const thickness = productConfig.thickness_mm
    ? `${productConfig.thickness_mm} мм`
    : 'толщина не указана'

  return `${dims}, ${material}, ${thickness}`
}

/**
 * Вычисляет процент завершенности заказа на основе статусов задач
 */
export function calculateOrderProgress(jobs: CAMJobStatusResponse[]): number {
  if (jobs.length === 0) return 0

  const completedJobs = jobs.filter((job) => isJobCompleted(job.status)).length
  return Math.round((completedJobs / jobs.length) * 100)
}

// ============================================================================
// Работа с потоковыми ответами (Streaming)
// ============================================================================

/**
 * Читает потоковый ответ и вызывает callback для каждого чанка
 */
export async function readStreamAsText(
  stream: ReadableStream<Uint8Array>,
  onChunk: (chunk: string) => void,
  onComplete?: () => void,
  onError?: (error: Error) => void
): Promise<void> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        onComplete?.()
        break
      }

      const chunk = decoder.decode(value, { stream: true })
      onChunk(chunk)
    }
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error('Stream reading error'))
  } finally {
    reader.releaseLock()
  }
}

/**
 * Преобразует потоковый ответ в полную строку
 */
export async function streamToString(
  stream: ReadableStream<Uint8Array>
): Promise<string> {
  let result = ''
  await readStreamAsText(
    stream,
    (chunk) => {
      result += chunk
    }
  )
  return result
}

// ============================================================================
// Константы
// ============================================================================

/**
 * Максимальные размеры для предупреждений
 */
export const DIMENSION_LIMITS = {
  /** Максимальная ширина без предупреждения (мм) */
  MAX_WIDTH_SAFE: 3000,
  /** Максимальная высота без предупреждения (мм) */
  MAX_HEIGHT_SAFE: 3000,
  /** Максимальная глубина без предупреждения (мм) */
  MAX_DEPTH_SAFE: 3000,
  /** Минимальная толщина материала (мм) */
  MIN_THICKNESS: 4,
  /** Максимальная толщина материала (мм) */
  MAX_THICKNESS: 50,
} as const

/**
 * Таймауты для различных операций (мс)
 */
export const TIMEOUTS = {
  /** Таймаут для API запросов */
  API_REQUEST: 30000,
  /** Таймаут для загрузки файлов */
  FILE_UPLOAD: 120000,
  /** Таймаут для потокового ответа */
  STREAMING: 300000,
} as const
