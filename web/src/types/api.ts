/**
 * TypeScript типы для API проекта Мебель-ИИ
 * Автоматически сгенерированы на основе Pydantic схем (api/schemas.py) и SQLAlchemy моделей (api/models.py)
 */

// ============================================================================
// Enum типы
// ============================================================================

/** Статус CAM задачи */
export type JobStatus = 'Created' | 'Processing' | 'Completed' | 'Failed'

/** Статус валидации */
export type ValidationStatus = 'Pending' | 'Approved' | 'Rejected'

/** Тип входных данных для извлечения спецификации */
export type InputType = 'text' | 'image' | 'sketch'

/** Этап валидации спецификации */
export type ValidationStage = 'extraction_review' | 'rag_review'

/** Тип CAM задачи */
export type CAMJobKind = 'DXF' | 'GCODE'

/** Роль участника диалога */
export type DialogueRole = 'user' | 'assistant'

/** Статус валидации (для ответа после апрува) */
export type ValidationApprovalStatus = 'completed' | 'failed'

/** Тип артефакта (файла) */
export type ArtifactType = 'DXF' | 'GCODE' | 'ZIP' | 'IMAGE' | 'PDF'

// ============================================================================
// Базовые модели сущностей
// ============================================================================

/** Заказ (Order) */
export interface Order {
  /** UUID заказа */
  id: string
  /** Дата создания */
  created_at: string
  /** Дата последнего обновления */
  updated_at: string
  /** Ссылка на клиента или внешний идентификатор */
  customer_ref?: string | null
  /** Заметки к заказу */
  notes?: string | null
}

/** Базовые поля для создания заказа */
export interface OrderBase {
  /** Ссылка на клиента или внешний идентификатор */
  customer_ref?: string | null
  /** Заметки к заказу */
  notes?: string | null
}

/** Запрос на создание заказа */
export interface OrderCreateRequest extends OrderBase {}

/** Конфигурация изделия */
export interface ProductConfig {
  /** UUID конфигурации */
  id: string
  /** UUID заказа, к которому относится изделие */
  order_id?: string | null
  /** Название изделия */
  name?: string | null
  /** Ширина в миллиметрах */
  width_mm: number
  /** Высота в миллиметрах */
  height_mm: number
  /** Глубина в миллиметрах */
  depth_mm: number
  /** Материал */
  material?: string | null
  /** Толщина материала в миллиметрах */
  thickness_mm?: number | null
  /** Дополнительные параметры (JSON) */
  params: Record<string, any>
  /** Заметки */
  notes?: string | null
}

/** Панель (деталь) изделия */
export interface Panel {
  /** UUID панели */
  id: string
  /** UUID изделия, к которому относится панель */
  product_id: string
  /** Название панели */
  name: string
  /** Ширина в миллиметрах */
  width_mm: number
  /** Высота в миллиметрах */
  height_mm: number
  /** Толщина в миллиметрах */
  thickness_mm: number
  /** Материал */
  material?: string | null
  /** Толщина кромки в миллиметрах */
  edge_band_mm?: number | null
  /** Заметки */
  notes?: string | null
}

/** Поставщик */
export interface Supplier {
  /** UUID поставщика */
  id: string
  /** Название поставщика */
  name: string
  /** URL сайта поставщика */
  url?: string | null
  /** Контактный email */
  contact_email?: string | null
  /** Дополнительные метаданные */
  meta: Record<string, any>
}

/** Позиция фурнитуры */
export interface HardwareItem {
  /** UUID позиции */
  id: string
  /** Артикул (SKU) */
  sku: string
  /** Бренд */
  brand?: string | null
  /** Тип фурнитуры */
  type: string
  /** Название */
  name?: string | null
  /** Описание */
  description?: string | null
  /** Параметры (JSON) */
  params: Record<string, any>
  /** Список совместимых материалов/типов */
  compat: string[]
  /** URL на страницу товара */
  url?: string | null
  /** Версия/модель */
  version?: string | null
  /** UUID поставщика */
  supplier_id?: string | null
  /** Векторное представление для поиска (256-мерный вектор) */
  embedding?: number[] | null
  /** Версия модели эмбеддингов */
  embedding_version?: string | null
  /** Хеш контента для проверки актуальности */
  content_hash?: string | null
  /** Время индексации */
  indexed_at?: string | null
  /** Категория фурнитуры */
  category?: string | null
  /** Тип материала для совместимости */
  material_type?: string | null
  /** Минимальная толщина материала в мм */
  thickness_min_mm?: number | null
  /** Максимальная толщина материала в мм */
  thickness_max_mm?: number | null
  /** Цена в рублях */
  price_rub?: number | null
  /** Активность позиции в каталоге */
  is_active: boolean
}

/** Позиция в спецификации (BOM) */
export interface BOMItem {
  /** UUID позиции в BOM */
  id: string
  /** UUID заказа */
  order_id?: string | null
  /** Артикул */
  sku: string
  /** Название позиции */
  name: string
  /** Количество */
  qty: number
  /** Единица измерения */
  unit: string
  /** Дополнительные параметры */
  params: Record<string, any>
  /** Артикул у поставщика */
  supplier_sku?: string | null
  /** UUID поставщика */
  supplier_id?: string | null
}

/** Артефакт (файл) */
export interface Artifact {
  /** UUID артефакта */
  id: string
  /** Тип файла */
  type: string
  /** Ключ в хранилище (S3) */
  storage_key: string
  /** Предподписанный URL для скачивания */
  presigned_url?: string | null
  /** Размер файла в байтах */
  size_bytes?: number | null
  /** Контрольная сумма (checksum) */
  checksum?: string | null
  /** Дата создания */
  created_at: string
  /** Дата истечения срока действия */
  expires_at?: string | null
}

/** CAM задача (для генерации DXF или G-code) */
export interface CAMJob {
  /** UUID задачи */
  id: string
  /** UUID заказа */
  order_id?: string | null
  /** Тип задачи (DXF или GCODE) */
  job_kind: string
  /** UUID артефакта (результата) */
  artifact_id?: string | null
  /** Статус задачи */
  status: JobStatus
  /** Дата создания */
  created_at: string
  /** Дата последнего обновления */
  updated_at: string
  /** Количество попыток выполнения */
  attempt: number
  /** Текст ошибки (если есть) */
  error?: string | null
  /** Контекст задачи (дополнительные данные) */
  context: Record<string, any>
  /** Ключ идемпотентности */
  idempotency_key?: string | null
}

/** Запись в журнале аудита */
export interface AuditLog {
  /** UUID записи */
  id: string
  /** Временная метка */
  ts: string
  /** Роль актора (пользователя/системы) */
  actor_role: string
  /** Действие */
  action: string
  /** Сущность, над которой выполнено действие */
  entity: string
  /** UUID сущности */
  entity_id: string
  /** Детали действия */
  details: Record<string, any>
}

/** Сообщение в диалоге с ИИ */
export interface DialogueMessage {
  /** UUID сообщения */
  id: string
  /** UUID заказа */
  order_id: string
  /** Номер витка диалога */
  turn_number: number
  /** Роль (user или assistant) */
  role: DialogueRole
  /** Содержимое сообщения */
  content: string
  /** Временная метка */
  timestamp: string
}

/** Валидация (процесс проверки данных) */
export interface Validation {
  /** UUID валидации */
  id: string
  /** Связанная сущность (тип) */
  related_entity: string
  /** UUID связанной сущности */
  related_id: string
  /** Статус валидации */
  status: ValidationStatus
  /** Дата создания */
  created_at: string
  /** Дата последнего обновления */
  updated_at: string
}

/** Элемент валидации (конкретный параметр для проверки) */
export interface ValidationItem {
  /** UUID элемента */
  id: string
  /** UUID валидации */
  validation_id: string
  /** Ключ параметра */
  key: string
  /** Описание параметра */
  description?: string | null
  /** Текущее значение */
  current_value?: any | null
  /** Предложенное значение */
  proposed_value?: any | null
  /** Статус элемента */
  status: string
  /** Комментарий */
  comment?: string | null
}

// ============================================================================
// API запросы и ответы
// ============================================================================

/** Запрос на извлечение спецификации из ТЗ */
export interface SpecExtractRequest {
  /** Тип входных данных */
  input_type: InputType
  /** Содержимое (текст, base64 изображения или эскиза) */
  content: string
}

/** Ответ на запрос извлечения спецификации */
export interface SpecExtractResponse {
  /** UUID созданной конфигурации изделия */
  product_config_id: string
  /** Извлеченные параметры */
  parameters: Record<string, any>
}

/** Критерии подбора фурнитуры */
export interface HardwareSelectCriteria {
  /** Материал */
  material?: string | null
  /** Толщина материала в миллиметрах */
  thickness?: number | null
}

/** Запрос на подбор фурнитуры */
export interface HardwareSelectRequest {
  /** UUID конфигурации изделия */
  product_config_id: string
  /** Критерии подбора */
  criteria: HardwareSelectCriteria
}

/** Позиция в BOM (для ответа) */
export interface BOMItemResponse {
  /** UUID позиции фурнитуры */
  hardware_item_id: string
  /** Артикул */
  sku: string
  /** Название */
  name?: string | null
  /** Количество */
  quantity: number
  /** Поставщик */
  supplier?: string | null
  /** Версия/модель */
  version?: string | null
}

/** Ответ на запрос подбора фурнитуры */
export interface HardwareSelectResponse {
  /** UUID созданной спецификации (BOM) */
  bom_id: string
  /** Список подобранных позиций */
  items: BOMItemResponse[]
}

/** Элемент для валидации */
export interface SpecValidateItem {
  /** Параметр для проверки */
  parameter: string
  /** Значение параметра */
  value: any
  /** Уверенность (0-1) */
  confidence?: number | null
  /** Вопрос для уточнения */
  question?: string | null
}

/** Запрос на валидацию спецификации */
export interface SpecValidateRequest {
  /** UUID конфигурации изделия */
  product_config_id: string
  /** Этап валидации */
  stage: ValidationStage
  /** Список элементов для утверждения */
  required_approvals: SpecValidateItem[]
}

/** Ответ на запрос валидации спецификации */
export interface SpecValidateResponse {
  /** UUID созданной валидации */
  validation_id: string
  /** Требуется ли валидация */
  validation_required: boolean
  /** Количество элементов, требующих утверждения */
  approvals_needed: number
  /** Можно ли переходить к следующему шагу */
  next_step_allowed: boolean
}

/** Элемент утверждения в валидации */
export interface ValidationApproveItem {
  /** UUID элемента валидации */
  validation_item_id: string
  /** Утверждено ли значение */
  approved: boolean
  /** Комментарий */
  comment?: string | null
}

/** Запрос на утверждение валидации */
export interface ValidationApproveRequest {
  /** UUID валидации */
  validation_id: string
  /** Список утверждений */
  approvals: ValidationApproveItem[]
}

/** Ответ на запрос утверждения валидации */
export interface ValidationApproveResponse {
  /** UUID валидации */
  validation_id: string
  /** Статус после утверждения */
  status: ValidationApprovalStatus
  /** Можно ли переходить к следующему шагу */
  next_step_allowed: boolean
}

/** Запрос на создание CAM задачи */
export interface CAMJobRequest {
  /** UUID конфигурации изделия */
  product_config_id: string
  /** UUID заказа (опционально) */
  order_id?: string | null
  /** UUID DXF задачи (для G-code генерации) */
  dxf_job_id?: string | null
  /** Контекст задачи */
  context?: Record<string, any>
}

/** Ответ на запрос создания CAM задачи */
export interface CAMJobResponse {
  /** UUID DXF задачи */
  dxf_job_id?: string | null
  /** UUID G-code задачи */
  gcode_job_id?: string | null
  /** Статус задачи */
  status: 'processing' | 'created'
}

/** Ответ на запрос статуса CAM задачи */
export interface CAMJobStatusResponse {
  /** UUID задачи */
  job_id: string
  /** Тип задачи */
  job_kind: CAMJobKind
  /** Статус задачи */
  status: JobStatus
  /** UUID артефакта (результата) */
  artifact_id?: string | null
  /** Текст ошибки */
  error?: string | null
}

/** Ответ на запрос скачивания артефакта */
export interface ArtifactDownloadResponse {
  /** UUID артефакта */
  artifact_id: string
  /** URL для скачивания */
  url: string
}

/** Базовое сообщение диалога */
export interface DialogueMessageBase {
  /** Роль отправителя */
  role: DialogueRole
  /** Содержимое сообщения */
  content: string
}

/** Запрос на создание сообщения диалога */
export interface DialogueMessageCreate extends DialogueMessageBase {}

/** Запрос на следующий виток диалога */
export interface DialogueTurnRequest {
  /** UUID заказа */
  order_id: string
  /** Список новых сообщений от пользователя */
  messages: DialogueMessageCreate[]
}

/** Запрос на экспорт в 1С */
export interface Export1CRequest {
  /** UUID заказа */
  order_id: string
}

/** Ответ на запрос экспорта в 1С */
export interface Export1CResponse {
  /** Успешность экспорта */
  success: boolean
  /** ID заказа в 1С */
  one_c_order_id?: string | null
}

/** Запрос на создание ZIP архива */
export interface ZIPJobRequest {
  /** UUID заказа */
  order_id: string
  /** Список UUID задач для архивирования */
  job_ids: string[]
}

// ============================================================================
// Вспомогательные типы
// ============================================================================

/** Общий ответ об ошибке API */
export interface APIError {
  /** Сообщение об ошибке */
  detail: string
}

/** Пагинация (если будет добавлена в будущем) */
export interface Pagination {
  /** Номер страницы */
  page: number
  /** Размер страницы */
  page_size: number
  /** Общее количество элементов */
  total: number
  /** Общее количество страниц */
  total_pages: number
}

/** Список с пагинацией */
export interface PaginatedResponse<T> {
  /** Массив элементов */
  items: T[]
  /** Информация о пагинации */
  pagination: Pagination
}

// ============================================================================
// Типы для фронтенд-специфичных расширений
// ============================================================================

/** Расширенная информация о заказе с продуктами */
export interface OrderWithProducts extends Order {
  /** Список конфигураций изделий */
  products?: ProductConfig[]
  /** Список сообщений диалога */
  dialogue_messages?: DialogueMessage[]
}

/** Расширенная информация о конфигурации изделия с панелями */
export interface ProductConfigWithPanels extends ProductConfig {
  /** Список панелей */
  panels?: Panel[]
}

/** Расширенная информация о CAM задаче с артефактом */
export interface CAMJobWithArtifact extends CAMJob {
  /** Артефакт (файл результата) */
  artifact?: Artifact | null
}

/** Фильтры для списка заказов */
export interface OrderFilters {
  /** Поиск по ссылке на клиента */
  customer_ref?: string
  /** Фильтр по дате создания (с) */
  created_from?: string
  /** Фильтр по дате создания (до) */
  created_to?: string
  /** Сортировка */
  sort_by?: 'created_at' | 'updated_at'
  /** Направление сортировки */
  sort_order?: 'asc' | 'desc'
}

/** Фильтры для списка фурнитуры */
export interface HardwareFilters {
  /** Поиск по названию или артикулу */
  search?: string
  /** Фильтр по типу */
  type?: string
  /** Фильтр по категории */
  category?: string
  /** Фильтр по бренду */
  brand?: string
  /** Фильтр по поставщику */
  supplier_id?: string
  /** Только активные позиции */
  is_active?: boolean
  /** Фильтр по материалу */
  material_type?: string
  /** Минимальная толщина */
  thickness_min?: number
  /** Максимальная толщина */
  thickness_max?: number
}

/** Статистика по заказам */
export interface OrderStatistics {
  /** Общее количество заказов */
  total_orders: number
  /** Заказы в работе */
  in_progress: number
  /** Завершенные заказы */
  completed: number
  /** Заказы с ошибками */
  failed: number
}

// ============================================================================
// Vision OCR — извлечение параметров из изображений (P0)
// ============================================================================

/** Категория мебели */
export type FurnitureCategory =
  | 'навесной_шкаф'
  | 'напольный_шкаф'
  | 'тумба'
  | 'пенал'
  | 'столешница'
  | 'фасад'
  | 'полка'
  | 'ящик'
  | 'другое'

/** Тип материала */
export type MaterialType =
  | 'ЛДСП'
  | 'МДФ'
  | 'массив'
  | 'фанера'
  | 'ДВП'
  | 'стекло'
  | 'металл'
  | 'другое'

/** Тип мебели */
export interface FurnitureType {
  category: FurnitureCategory
  subcategory?: string | null
  description?: string | null
}

/** Извлечённые размеры */
export interface ExtractedDimensions {
  width_mm?: number | null
  height_mm?: number | null
  depth_mm?: number | null
  thickness_mm?: number | null
}

/** Извлечённый материал */
export interface ExtractedMaterial {
  type?: MaterialType | null
  color?: string | null
  texture?: string | null
  brand?: string | null
}

/** Извлечённые параметры мебели */
export interface ExtractedFurnitureParams {
  furniture_type?: FurnitureType | null
  dimensions?: ExtractedDimensions | null
  body_material?: ExtractedMaterial | null
  facade_material?: ExtractedMaterial | null
  door_count?: number | null
  drawer_count?: number | null
  shelf_count?: number | null
  has_legs?: boolean | null
  raw_text?: string | null
  confidence: number
  needs_clarification: boolean
  clarification_questions: string[]
}

/** MIME типы изображений */
export type ImageMimeType = 'image/jpeg' | 'image/png' | 'image/webp'

/** Запрос на извлечение параметров из изображения */
export interface ImageExtractRequest {
  /** Base64 закодированное изображение */
  image_base64: string
  /** MIME тип изображения */
  image_mime_type?: ImageMimeType
  /** UUID заказа (опционально) */
  order_id?: string | null
  /** Подсказка языка для OCR */
  language_hint?: 'ru' | 'en' | 'auto'
}

/** Ответ на запрос извлечения параметров */
export interface ImageExtractResponse {
  /** Успешность операции */
  success: boolean
  /** Извлечённые параметры */
  parameters?: ExtractedFurnitureParams | null
  /** Нужен ли переход к диалогу */
  fallback_to_dialogue: boolean
  /** Промпт для диалога (если fallback) */
  dialogue_prompt?: string | null
  /** Уверенность OCR (0-1) */
  ocr_confidence: number
  /** Время обработки в мс */
  processing_time_ms: number
  /** Ошибка (если есть) */
  error?: string | null
}
