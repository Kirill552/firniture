/**
 * Клиент для работы с API проекта Мебель-ИИ
 * Предоставляет типизированные функции для всех эндпоинтов
 */

import {
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
  ArtifactDownloadResponse,
  DialogueTurnRequest,
  Export1CRequest,
  Export1CResponse,
  ZIPJobRequest,
  APIError,
  ImageExtractRequest,
  ImageExtractResponse,
} from '@/types/api'
import { getAuthHeader, TokenResponse, AuthUser } from './auth'

/**
 * Базовый URL API бэкенда
 * В production должен браться из переменной окружения
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

/**
 * Класс для обработки ошибок API
 */
export class APIClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message)
    this.name = 'APIClientError'
  }
}

/**
 * Базовая функция для выполнения запросов к API
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit,
  skipAuth: boolean = false
): Promise<T> {
  const url = `${API_BASE_URL}${API_PREFIX}${endpoint}`

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(skipAuth ? {} : getAuthHeader()),
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const errorData: APIError = await response.json().catch(() => ({
        detail: response.statusText,
      }))
      throw new APIClientError(
        `API Error: ${errorData.detail}`,
        response.status,
        errorData.detail
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIClientError) {
      throw error
    }
    throw new APIClientError(
      `Network Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      0
    )
  }
}

// ============================================================================
// Auth типы
// ============================================================================

export interface RegisterRequest {
  email: string
  factory_name: string
}

export interface LoginRequest {
  email: string
}

export interface VerifyRequest {
  token: string
}

export interface MessageResponse {
  message: string
  dev_magic_link?: string  // Только в dev режиме (mock email)
}

/**
 * API клиент с типизированными методами
 */
export const apiClient = {
  // ============================================================================
  // Аутентификация (Auth)
  // ============================================================================

  /**
   * Регистрация новой фабрики
   */
  async register(data: RegisterRequest): Promise<MessageResponse> {
    return fetchAPI<MessageResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }, true)
  },

  /**
   * Запрос magic link для входа
   */
  async login(data: LoginRequest): Promise<MessageResponse> {
    return fetchAPI<MessageResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }, true)
  },

  /**
   * Проверка magic token и получение JWT
   */
  async verify(data: VerifyRequest): Promise<TokenResponse> {
    return fetchAPI<TokenResponse>('/auth/verify', {
      method: 'POST',
      body: JSON.stringify(data),
    }, true)
  },

  /**
   * Получить текущего пользователя
   */
  async getMe(): Promise<AuthUser> {
    return fetchAPI<AuthUser>('/auth/me')
  },

  // ============================================================================
  // Заказы (Orders)
  // ============================================================================

  /**
   * Создать новый заказ
   */
  async createOrder(data: OrderCreateRequest): Promise<Order> {
    return fetchAPI<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  /**
   * Получить заказ по ID
   */
  async getOrder(orderId: string): Promise<Order> {
    return fetchAPI<Order>(`/orders/${orderId}`)
  },

  // ============================================================================
  // Извлечение спецификации (Spec Extraction)
  // ============================================================================

  /**
   * Извлечь спецификацию из ТЗ (текст, изображение или эскиз)
   */
  async extractSpec(data: SpecExtractRequest): Promise<SpecExtractResponse> {
    return fetchAPI<SpecExtractResponse>('/spec/extract', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  /**
   * Извлечь параметры мебели из изображения (Vision OCR)
   * P0: Ключевой дифференциатор — фото → параметры
   */
  async extractFromImage(data: ImageExtractRequest): Promise<ImageExtractResponse> {
    return fetchAPI<ImageExtractResponse>('/spec/extract-from-image', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // ============================================================================
  // Подбор фурнитуры (Hardware Selection)
  // ============================================================================

  /**
   * Подобрать фурнитуру для изделия
   */
  async selectHardware(
    data: HardwareSelectRequest
  ): Promise<HardwareSelectResponse> {
    return fetchAPI<HardwareSelectResponse>('/hardware/select', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // ============================================================================
  // Валидация спецификации (Spec Validation)
  // ============================================================================

  /**
   * Создать запрос на валидацию спецификации
   */
  async validateSpec(
    data: SpecValidateRequest
  ): Promise<SpecValidateResponse> {
    return fetchAPI<SpecValidateResponse>('/spec/validate', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  /**
   * Утвердить или отклонить элементы валидации
   */
  async approveValidation(
    data: ValidationApproveRequest
  ): Promise<ValidationApproveResponse> {
    return fetchAPI<ValidationApproveResponse>('/spec/validate/approve', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // ============================================================================
  // CAM задачи (CAM Jobs)
  // ============================================================================

  /**
   * Создать CAM задачу (DXF или G-code)
   */
  async createCAMJob(data: CAMJobRequest): Promise<CAMJobResponse> {
    return fetchAPI<CAMJobResponse>('/cam/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  /**
   * Получить статус CAM задачи
   */
  async getCAMJobStatus(jobId: string): Promise<CAMJobStatusResponse> {
    return fetchAPI<CAMJobStatusResponse>(`/cam/jobs/${jobId}/status`)
  },

  /**
   * Скачать артефакт (результат CAM задачи)
   */
  async downloadArtifact(artifactId: string): Promise<ArtifactDownloadResponse> {
    return fetchAPI<ArtifactDownloadResponse>(`/cam/artifacts/${artifactId}/download`)
  },

  /**
   * Создать ZIP архив с файлами
   */
  async createZIPJob(data: ZIPJobRequest): Promise<CAMJobResponse> {
    return fetchAPI<CAMJobResponse>('/cam/zip', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // ============================================================================
  // Диалог с ИИ (Dialogue)
  // ============================================================================

  /**
   * Отправить сообщение в диалог и получить потоковый ответ
   * Возвращает ReadableStream для чтения ответа по частям
   */
  async sendDialogueMessage(
    data: DialogueTurnRequest
  ): Promise<ReadableStream<Uint8Array>> {
    const url = `${API_BASE_URL}${API_PREFIX}/dialogue/clarify`

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const errorData: APIError = await response.json().catch(() => ({
        detail: response.statusText,
      }))
      throw new APIClientError(
        `API Error: ${errorData.detail}`,
        response.status,
        errorData.detail
      )
    }

    if (!response.body) {
      throw new APIClientError('Response body is null', response.status)
    }

    return response.body
  },

  // ============================================================================
  // Интеграция с 1С (1C Integration)
  // ============================================================================

  /**
   * Экспортировать заказ в 1С
   */
  async export1C(data: Export1CRequest): Promise<Export1CResponse> {
    return fetchAPI<Export1CResponse>('/integrations/1c/export', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

/**
 * Хуки для React компонентов (опционально, для использования с React Query или SWR)
 */

// Пример типа для ключей React Query
export const apiKeys = {
  orders: {
    all: ['orders'] as const,
    detail: (id: string) => ['orders', id] as const,
  },
  camJobs: {
    all: ['cam-jobs'] as const,
    status: (id: string) => ['cam-jobs', id, 'status'] as const,
  },
  hardware: {
    all: ['hardware'] as const,
  },
} as const

// Экспорт для удобного использования
export default apiClient
