import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query'
import type {
  Order,
  OrderCreateRequest,
  SpecExtractRequest,
  SpecExtractResponse,
  HardwareSelectRequest,
  HardwareSelectResponse,
  SpecValidateRequest,
  SpecValidateResponse,
  ValidationApproveRequest,
  ValidationApproveResponse,
  CAMJobRequest,
  CAMJobResponse,
  CAMJobStatusResponse,
  DialogueTurnRequest,
  Export1CRequest,
  Export1CResponse,
  ZIPJobRequest,
} from '@/types/api'

// ============================================================================
// Конфигурация API
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

// ============================================================================
// Дополнительные типы для API ответов
// ============================================================================

// Тип для ZIPJobResponse (отсутствует в api.ts, добавляем локально)
interface ZIPJobResponse {
  zip_job_id: string
  status: 'processing' | 'created'
}

// ============================================================================
// Утилиты для работы с API
// ============================================================================

/**
 * Базовая функция для выполнения fetch запросов с обработкой ошибок
 */
async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(
      `API Error (${response.status}): ${errorText || response.statusText}`
    )
  }

  return response.json()
}

// ============================================================================
// Query Keys (для инвалидации и кэширования)
// ============================================================================

export const apiKeys = {
  orders: ['orders'] as const,
  order: (id: string) => ['orders', id] as const,
  camJob: (jobId: string) => ['cam-jobs', jobId] as const,
  hardware: ['hardware'] as const,
  validations: ['validations'] as const,
}

// ============================================================================
// ORDERS - Заказы
// ============================================================================

/**
 * Создать новый заказ
 * @example
 * const mutation = useCreateOrder()
 * mutation.mutate({ customer_ref: 'ИП Иванов', notes: 'Срочный заказ' })
 */
export function useCreateOrder(
  options?: UseMutationOptions<Order, Error, OrderCreateRequest>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: OrderCreateRequest) => {
      return apiFetch<Order>('/api/v1/orders', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeys.orders })
    },
    ...options,
  })
}

// ============================================================================
// SPEC - Извлечение параметров из ТЗ
// ============================================================================

/**
 * Извлечь параметры изделия из текста, изображения или эскиза
 * @example
 * const mutation = useExtractSpec()
 * mutation.mutate({
 *   input_type: 'text',
 *   content: 'Шкаф 800x600x400 из ЛДСП 18мм'
 * })
 */
export function useExtractSpec(
  options?: UseMutationOptions<SpecExtractResponse, Error, SpecExtractRequest>
) {
  return useMutation({
    mutationFn: async (data: SpecExtractRequest) => {
      return apiFetch<SpecExtractResponse>('/api/v1/spec/extract', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    ...options,
  })
}

/**
 * Валидировать извлеченные параметры спецификации
 * @example
 * const mutation = useValidateSpec()
 * mutation.mutate({
 *   product_config_id: 'uuid',
 *   stage: 'extraction_review',
 *   required_approvals: [...]
 * })
 */
export function useValidateSpec(
  options?: UseMutationOptions<SpecValidateResponse, Error, SpecValidateRequest>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: SpecValidateRequest) => {
      return apiFetch<SpecValidateResponse>('/api/v1/spec/validate', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeys.validations })
    },
    ...options,
  })
}

// ============================================================================
// VALIDATION - Подтверждение валидации
// ============================================================================

/**
 * Подтвердить или отклонить параметры валидации
 * @example
 * const mutation = useApproveValidation()
 * mutation.mutate({
 *   validation_id: 'uuid',
 *   approvals: [{ validation_item_id: 'id', approved: true }]
 * })
 */
export function useApproveValidation(
  options?: UseMutationOptions<ValidationApproveResponse, Error, ValidationApproveRequest>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: ValidationApproveRequest) => {
      return apiFetch<ValidationApproveResponse>('/api/v1/validation/approve', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeys.validations })
    },
    ...options,
  })
}

// ============================================================================
// HARDWARE - RAG подбор фурнитуры
// ============================================================================

/**
 * Подобрать фурнитуру с помощью векторного поиска (RAG)
 * @example
 * const mutation = useSelectHardware()
 * mutation.mutate({
 *   product_config_id: 'uuid',
 *   criteria: { material: 'ЛДСП', thickness: 18 }
 * })
 */
export function useSelectHardware(
  options?: UseMutationOptions<HardwareSelectResponse, Error, HardwareSelectRequest>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: HardwareSelectRequest) => {
      return apiFetch<HardwareSelectResponse>('/api/v1/hardware/select', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeys.hardware })
    },
    ...options,
  })
}

// ============================================================================
// CAM - Генерация DXF чертежей и G-code
// ============================================================================

/**
 * Создать задачу на генерацию DXF чертежа
 * @example
 * const mutation = useGenerateDXF()
 * mutation.mutate({ product_config_id: 'uuid' })
 */
export function useGenerateDXF(
  options?: UseMutationOptions<CAMJobResponse, Error, CAMJobRequest>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CAMJobRequest) => {
      return apiFetch<CAMJobResponse>('/api/v1/cam/dxf', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    onSuccess: (response) => {
      if (response.dxf_job_id) {
        queryClient.invalidateQueries({
          queryKey: apiKeys.camJob(response.dxf_job_id)
        })
      }
    },
    ...options,
  })
}

/**
 * Создать задачу на генерацию G-code
 * @example
 * const mutation = useGenerateGCode()
 * mutation.mutate({
 *   product_config_id: 'uuid',
 *   dxf_job_id: 'dxf-uuid'
 * })
 */
export function useGenerateGCode(
  options?: UseMutationOptions<CAMJobResponse, Error, CAMJobRequest>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CAMJobRequest) => {
      return apiFetch<CAMJobResponse>('/api/v1/cam/gcode', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    onSuccess: (response) => {
      if (response.gcode_job_id) {
        queryClient.invalidateQueries({
          queryKey: apiKeys.camJob(response.gcode_job_id)
        })
      }
    },
    ...options,
  })
}

/**
 * Создать задачу на упаковку артефактов в ZIP архив
 * @example
 * const mutation = useCreateZIP()
 * mutation.mutate({
 *   order_id: 'uuid',
 *   job_ids: ['dxf-id', 'gcode-id']
 * })
 */
export function useCreateZIP(
  options?: UseMutationOptions<ZIPJobResponse, Error, ZIPJobRequest>
) {
  return useMutation({
    mutationFn: async (data: ZIPJobRequest) => {
      return apiFetch<ZIPJobResponse>('/api/v1/cam/zip', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    ...options,
  })
}

/**
 * Получить статус CAM задачи (DXF/GCODE/ZIP)
 * @param jobId - ID задачи
 * @param options - Опции useQuery
 * @example
 * const { data, isLoading } = useCAMJobStatus('job-uuid')
 */
export function useCAMJobStatus(
  jobId: string,
  options?: Omit<UseQueryOptions<CAMJobStatusResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: apiKeys.camJob(jobId),
    queryFn: async () => {
      return apiFetch<CAMJobStatusResponse>(`/api/v1/cam/jobs/${jobId}`)
    },
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Автоматически обновлять статус каждые 2 секунды, пока задача в процессе
      if (data?.state === 'data') {
        const status = data.data.status
        return status === 'Processing' || status === 'Created' ? 2000 : false
      }
      return false
    },
    ...options,
  })
}

// ============================================================================
// DIALOGUE - Диалог с ИИ-технологом
// ============================================================================

/**
 * Отправить сообщение ИИ-технологу и получить потоковый ответ
 *
 * ВАЖНО: Этот эндпоинт возвращает StreamingResponse (text/plain),
 * поэтому useMutation здесь может быть не самым удобным вариантом.
 * Для работы со стримингом лучше использовать fetch напрямую.
 *
 * @example
 * const mutation = useDialogueClarify()
 * mutation.mutate({
 *   order_id: 'uuid',
 *   messages: [{ role: 'user', content: 'Вопрос к технологу' }]
 * })
 */
export function useDialogueClarify(
  options?: UseMutationOptions<ReadableStream<Uint8Array>, Error, DialogueTurnRequest>
) {
  return useMutation({
    mutationFn: async (data: DialogueTurnRequest) => {
      const response = await fetch(`${API_BASE}/api/v1/dialogue/clarify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(
          `API Error (${response.status}): ${errorText || response.statusText}`
        )
      }

      if (!response.body) {
        throw new Error('Response body is null')
      }

      return response.body
    },
    ...options,
  })
}

/**
 * Вспомогательная функция для чтения потокового ответа от ИИ-технолога
 * @param stream - ReadableStream от useDialogueClarify
 * @param onChunk - Callback для обработки каждого чанка текста
 *
 * @example
 * const mutation = useDialogueClarify()
 *
 * const handleSend = async () => {
 *   const stream = await mutation.mutateAsync({ ... })
 *   await readDialogueStream(stream, (chunk) => {
 *     console.log('Received chunk:', chunk)
 *   })
 * }
 */
export async function readDialogueStream(
  stream: ReadableStream<Uint8Array>,
  onChunk: (chunk: string) => void
): Promise<void> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      onChunk(chunk)
    }
  } finally {
    reader.releaseLock()
  }
}

// ============================================================================
// INTEGRATIONS - Интеграция с 1С
// ============================================================================

/**
 * Экспортировать заказ в 1С
 * @example
 * const mutation = useExport1C()
 * mutation.mutate({ order_id: 'uuid' })
 */
export function useExport1C(
  options?: UseMutationOptions<Export1CResponse, Error, Export1CRequest>
) {
  return useMutation({
    mutationFn: async (data: Export1CRequest) => {
      return apiFetch<Export1CResponse>('/api/v1/integrations/1c/export', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    ...options,
  })
}

// ============================================================================
// HEALTH - Проверка доступности API
// ============================================================================

/**
 * Проверить доступность API
 * @example
 * const { data, isLoading } = useAPIHealth()
 */
export function useAPIHealth(
  options?: Omit<UseQueryOptions<{ status: string }, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      return apiFetch<{ status: string }>('/health')
    },
    retry: false,
    ...options,
  })
}
