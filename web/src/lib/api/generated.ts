/**
 * Auto-generated API contract from OpenAPI snapshot.
 * Source: tests/fixtures/openapi_snapshot.json
 * DO NOT EDIT MANUALLY — regenerate with:
 *   python scripts/generate_api_types.py
 *
 * Drift detected? Update snapshot:
 *   MOCK_MODE=true pytest tests/test_openapi_contract.py --update-snapshot
 */

// Enums

export type ApprovalDecision = 'approved' | 'rejected'

export type CabinetType = 'wall' | 'base' | 'base_sink' | 'drawer' | 'tall' | 'corner'

export type FieldSource = 'ocr' | 'inferred' | 'default' | 'user' | 'ai'

export type GuestScope = 'read:order' | 'read:bom' | '*'

// Schema interfaces

/** ApprovalRequest — Запрос на approve/reject.

expected_revision — optimistic concurrency.
confirmed — явное подтверждение технолога (checkbox/фразa в UI). */
export interface ApprovalRequest {
  comment?: string | null
  /** Технолог подтверждает ручную проверку и допуск к производству */
  confirmed: boolean
  /** Ожидаемая ревизия для OCC */
  expected_revision: number
}

/** ApprovalResponse — Успешный ответ approve. */
export interface ApprovalResponse {
  audit: Record<string, unknown>
  decision: ApprovalDecision
  new_status: string
  order_manufacturing_status: string
  revision_id: string
  revision_number: number
}

/** ArtifactDownload — Информация для скачивания артефакта. */
export interface ArtifactDownload {
  artifact_id: string
  download_url: string
  /** Время жизни ссылки (сек) */
  expires_in_seconds?: number
  filename: string
  size_bytes: number
  type: 'DXF' | 'GCODE' | 'ZIP'
}

/** CAMJobListItem — Краткая информация о CAM задаче для списка. */
export interface CAMJobListItem {
  created_at: string
  job_id: string
  job_kind: 'DXF' | 'GCODE' | 'ZIP' | 'DRILLING'
  order_id?: string | null
  status: 'Created' | 'Processing' | 'Completed' | 'Failed'
  updated_at: string
}

/** CAMJobStatus — Статус CAM задачи. */
export interface CAMJobStatus {
  artifact_id?: string | null
  created_at: string
  error?: string | null
  job_id: string
  job_kind: 'DXF' | 'GCODE' | 'ZIP' | 'DRILLING'
  /** Размещено панелей */
  panels_placed?: number | null
  /** Не размещено панелей */
  panels_unplaced?: number | null
  status: 'Created' | 'Processing' | 'Completed' | 'Failed'
  updated_at: string
  /** Утилизация листа (%) */
  utilization_percent?: number | null
}

/** CAMJobsListResponse — Список CAM задач. */
export interface CAMJobsListResponse {
  jobs: CAMJobListItem[]
  total: number
}

/** CalculatePanelsRequest — Запрос на расчёт панелей. */
export interface CalculatePanelsRequest {
  cabinet_type: CabinetType
  /** Глубина корпуса */
  depth_mm: number
  /** Количество дверей */
  door_count?: number
  /** Количество ящиков */
  drawer_count?: number
  /** Толщина кромки */
  edge_thickness_mm?: number | null
  /** Высота корпуса */
  height_mm: number
  /** Материал */
  material?: string
  /** Количество полок */
  shelf_count?: number
  /** Толщина материала */
  thickness_mm?: number | null
  /** Ширина корпуса */
  width_mm: number
}

/** CalculatePanelsResponse — Ответ с рассчитанными панелями. */
export interface CalculatePanelsResponse {
  cabinet_type: string
  /** Габариты {width, height, depth} */
  dimensions: Record<string, number>
  /** Длина кромки (м) */
  edge_length_m: number
  panels: CalculatedPanel[]
  success?: boolean
  /** Общая площадь панелей (м²) */
  total_area_m2: number
  total_panels: number
  warnings?: string[]
}

/** CalculatedPanel — Рассчитанная панель. */
export interface CalculatedPanel {
  /** Кромка сзади */
  edge_back?: boolean
  /** Кромка снизу */
  edge_bottom?: boolean
  /** Кромка спереди */
  edge_front?: boolean
  /** Толщина кромки */
  edge_thickness_mm?: number
  /** Кромка сверху */
  edge_top?: boolean
  /** Паз под заднюю стенку */
  has_slot_for_back?: boolean
  /** Высота в мм */
  height_mm: number
  /** Название панели (Боковина левая, Дно и т.д.) */
  name: string
  /** Примечания */
  notes?: string
  /** Количество */
  quantity?: number
  /** Толщина в мм */
  thickness_mm?: number
  /** Ширина в мм */
  width_mm: number
}

/** ClaimRequest — Запрос claim гостевого заказа после логина. */
export interface ClaimRequest {
  guest_capability_token: string
}

/** ClaimResponse — Ответ claim гостевого заказа. */
export interface ClaimResponse {
  guest_identity: GuestIdentity
  message: string
}

/** CostBreakdownItem — Детализация стоимости. */
export interface CostBreakdownItem {
  /** Название позиции */
  name: string
  /** Количество */
  quantity: number
  /** Итоговая цена */
  total_price: number
  /** Ед. изм. */
  unit: string
  /** Цена за единицу */
  unit_price: number
}

/** CostEstimateResponse — Ответ с расчётом себестоимости. */
export interface CostEstimateResponse {
  /** Детализация */
  breakdown: CostBreakdownItem[]
  /** Валюта */
  currency?: string
  /** Стоимость фурнитуры */
  hardware_cost: number
  /** Стоимость материалов */
  materials_cost: number
  /** Стоимость операций (распил, кромление) */
  operations_cost: number
  /** Общая себестоимость */
  total_cost: number
}

/** DXFJobRequest — Запрос на генерацию DXF. */
export interface DXFJobRequest {
  /** Зазор между панелями (на пропил) */
  gap_mm?: number
  /** Ключ идемпотентности */
  idempotency_key?: string | null
  /** Оптимизировать раскрой */
  optimize_layout?: boolean
  /** ID заказа */
  order_id?: string | null
  /** Список панелей */
  panels: PanelInput[]
  /** Высота листа (авто если не указано) */
  sheet_height_mm?: number | null
  /** Ширина листа (авто если не указано) */
  sheet_width_mm?: number | null
}

/** DXFJobResponse — Ответ на создание DXF задачи. */
export interface DXFJobResponse {
  job_id: string
  panels_count: number
  sheet_size: [number, number]
  status?: 'created' | 'processing'
}

/** DialogueMessageCreate */
export interface DialogueMessageCreate {
  content: string
  role: 'user' | 'assistant'
}

/** DialogueTurnRequest */
export interface DialogueTurnRequest {
  current_params?: Record<string, unknown> | null
  extracted_context?: string | null
  messages: DialogueMessageCreate[]
  order_id: string
}

/** DrillingGcodeRequest — Запрос на генерацию G-code присадки. */
export interface DrillingGcodeRequest {
  /** Профиль станка: weihong, syntec, fanuc, dsp, homag */
  machine_profile?: string
  order_id: string
  /** zip — архив с файлами по панелям, single — один файл */
  output_format?: 'zip' | 'single'
}

/** DrillingGcodeResponse — Ответ на запрос G-code присадки. */
export interface DrillingGcodeResponse {
  /** Список ожидаемых файлов в архиве */
  estimated_files?: string[]
  job_id: string
  panels_count: number
  status: string
}

/** Export1CRequest */
export interface Export1CRequest {
  format?: 'excel' | 'csv'
  order_id: string
}

/** Export1CResponse */
export interface Export1CResponse {
  download_url: string
  expires_in_seconds?: number
  filename: string
  format: string
  success: boolean
}

/** ExtractedDimensions — Извлечённые размеры изделия. */
export interface ExtractedDimensions {
  /** Глубина в мм */
  depth_mm?: number | null
  /** Высота в мм */
  height_mm?: number | null
  /** Толщина материала в мм */
  thickness_mm?: number | null
  /** Ширина в мм */
  width_mm?: number | null
}

/** ExtractedFurnitureParams — Структурированные параметры мебели, извлечённые из изображения. */
export interface ExtractedFurnitureParams {
  /** Материал корпуса */
  body_material?: ExtractedMaterial | null
  /** Вопросы для уточнения */
  clarification_questions?: string[] | null
  /** Уверенность распознавания (0-1) */
  confidence?: number
  dimensions?: ExtractedDimensions | null
  /** Количество дверей */
  door_count?: number | null
  /** Количество ящиков */
  drawer_count?: number | null
  /** Материал фасада */
  facade_material?: ExtractedMaterial | null
  furniture_type?: FurnitureType | null
  /** Есть ли ножки */
  has_legs?: boolean | null
  /** Требуется уточнение от пользователя */
  needs_clarification?: boolean
  /** Исходный распознанный текст */
  raw_text?: string | null
  /** Количество полок */
  shelf_count?: number | null
}

/** ExtractedMaterial — Извлечённый материал. */
export interface ExtractedMaterial {
  brand?: string | null
  color?: string | null
  texture?: string | null
  type?: 'ЛДСП' | 'МДФ' | 'массив' | 'фанера' | 'ДВП' | 'стекло' | 'металл' | 'другое' | null
}

/** FactoryInfo — Информация о фабрике. */
export interface FactoryInfo {
  id: string
  name: string
}

/** FactorySettingsResponse — Ответ GET /settings — настройки с дефолтами для UI. */
export interface FactorySettingsResponse {
  /** Поля, где использованы дефолты */
  defaults_used: string[]
  factory_name: string
  owner_email: string
  /** Merged настройки (значения + дефолты) */
  settings: Record<string, unknown>
}

/** FactorySettingsUpdate — Запрос на обновление настроек (PATCH). */
export interface FactorySettingsUpdate {
  cut_depth?: number | null
  decor?: string | null
  edge_thickness_mm?: number | null
  /** Название фабрики */
  factory_name?: string | null
  feed_rate_cutting?: number | null
  feed_rate_plunge?: number | null
  gap_mm?: number | null
  machine_profile?: 'weihong' | 'syntec' | 'fanuc' | 'dsp' | 'homag' | null
  safe_height?: number | null
  sheet_height_mm?: number | null
  sheet_width_mm?: number | null
  spindle_speed?: number | null
  thickness_mm?: number | null
  tool_diameter?: number | null
}

/** FactorySettingsUpdateResponse — Ответ PATCH /settings. */
export interface FactorySettingsUpdateResponse {
  success?: boolean
  /** Обновлённые поля */
  updated_fields: string[]
}

/** FinalizeOrderResponse — Ответ после финализации. */
export interface FinalizeOrderResponse {
  message: string
  order_id: string
  product_config_id: string
  success: boolean
}

/** FurnitureType — Тип мебельного изделия. */
export interface FurnitureType {
  category: 'навесной_шкаф' | 'напольный_шкаф' | 'тумба' | 'пенал' | 'столешница' | 'фасад' | 'полка' | 'ящик' | 'другое'
  description?: string | null
  subcategory?: string | null
}

/** GCodeJobRequest — Запрос на генерацию G-code из DXF артефакта. */
export interface GCodeJobRequest {
  /** Глубина резки (мм) */
  cut_depth?: number | null
  /** ID DXF артефакта для конвертации */
  dxf_artifact_id: string
  /** Подача резки (мм/мин) */
  feed_rate_cutting?: number | null
  /** Подача врезания (мм/мин) */
  feed_rate_plunge?: number | null
  /** Ключ идемпотентности */
  idempotency_key?: string | null
  /** Профиль станка ЧПУ. Если не задан — используется из настроек фабрики */
  machine_profile?: 'weihong' | 'syntec' | 'fanuc' | 'dsp' | 'homag' | null
  /** ID заказа */
  order_id?: string | null
  /** Безопасная высота (мм) */
  safe_height?: number | null
  /** Скорость шпинделя (об/мин) */
  spindle_speed?: number | null
  /** Диаметр фрезы (мм) */
  tool_diameter?: number | null
}

/** GCodeJobResponse — Ответ на создание G-code задачи. */
export interface GCodeJobResponse {
  /** ID исходного DXF артефакта */
  dxf_artifact_id: string
  job_id: string
  /** Используемый профиль станка */
  machine_profile: string
  status?: 'created' | 'processing'
}

/** GenerateBOMRequest — Запрос на генерацию полного BOM. */
export interface GenerateBOMRequest {
  cabinet_type: CabinetType
  depth_mm: number
  door_count?: number
  drawer_count?: number
  height_mm: number
  material?: string
  order_id?: string | null
  shelf_count?: number
  /** Толщина материала в мм (если не указано — берём из настроек) */
  thickness_mm?: number | null
  width_mm: number
}

/** GenerateBOMResponse — Полный BOM с панелями и фурнитурой. */
export interface GenerateBOMResponse {
  cabinet_type: string
  dimensions: Record<string, number>
  edge_length_m: number
  hardware: HardwareRecommendation[]
  order_id?: string | null
  panels: CalculatedPanel[]
  success?: boolean
  total_area_m2: number
  total_hardware_items: number
  total_panels: number
  warnings?: string[]
}

/** GuestIdentity */
export interface GuestIdentity {
  factory_id: string
  scopes: GuestScope[]
  token_id: string
}

/** HTTPValidationError */
export interface HTTPValidationError {
  detail?: ValidationError[]
}

/** HardwareRecommendation — Рекомендация по фурнитуре. */
export interface HardwareRecommendation {
  /** Название */
  name: string
  /** Количество */
  quantity: number
  /** Артикул из каталога */
  sku?: string | null
  /** Источник: calculated | rag */
  source?: string
  /** Тип фурнитуры */
  type: string
  /** Единица измерения */
  unit?: string
}

/** HardwareSearchItem — Элемент результата поиска фурнитуры. */
export interface HardwareSearchItem {
  brand: string | null
  category: string | null
  description: string | null
  name: string | null
  params?: Record<string, unknown>
  price_rub: number | null
  /** Релевантность (0-1) */
  score: number
  sku: string
  type: string
}

/** HardwareSearchResponse — Ответ на поиск фурнитуры. */
export interface HardwareSearchResponse {
  items: HardwareSearchItem[]
  /** Исходный запрос */
  query: string
  /** Общее количество найденных позиций */
  total: number
}

/** HingeTemplateInfo — Информация о шаблоне петли для UI. */
export interface HingeTemplateInfo {
  cup_diameter_mm: number
  id: string
  name: string
  type: string
}

/** ImageExtractRequest — Запрос на извлечение параметров из изображения или PDF. */
export interface ImageExtractRequest {
  /** Изображение или PDF в формате base64 */
  image_base64: string
  image_mime_type?: 'image/jpeg' | 'image/png' | 'image/webp' | 'application/pdf'
  language_hint?: 'ru' | 'en' | 'auto'
  /** ID заказа для привязки */
  order_id?: string | null
}

/** ImageExtractResponse — Ответ с извлечёнными параметрами. */
export interface ImageExtractResponse {
  /** Начальный промпт для диалога */
  dialogue_prompt?: string | null
  error?: string | null
  /** Тип ошибки для программной обработки */
  error_type?: 'multiple_modules' | 'file_too_large' | 'unsupported_format' | 'ocr_failed' | null
  /** Рекомендуется перейти в диалог для уточнения */
  fallback_to_dialogue?: boolean
  /** Источник каждого поля: ocr/inferred/default */
  field_sources?: Record<string, FieldSource> | null
  /** Поля, требующие проверки пользователем */
  fields_need_review?: string[]
  /** Количество модулей на изображении (если определено) */
  module_count?: number | null
  /** Уверенность OCR */
  ocr_confidence?: number
  parameters?: ExtractedFurnitureParams | null
  /** Время обработки в мс */
  processing_time_ms?: number
  /** Количество распознанных полей (не default) */
  recognized_count?: number
  success: boolean
  /** Предлагаемый промпт для AI-уточнения */
  suggested_prompt?: string | null
}

/** LayoutPanelInput — Упрощённая панель для preview (только размеры). */
export interface LayoutPanelInput {
  /** Высота в мм */
  height_mm: number
  /** Название панели */
  name: string
  /** Ширина в мм */
  width_mm: number
}

/** LayoutPreviewRequest — Запрос на предпросмотр раскладки. */
export interface LayoutPreviewRequest {
  /** Зазор между панелями (на пропил) */
  gap_mm?: number
  /** Список панелей */
  panels: LayoutPanelInput[]
  /** Высота листа */
  sheet_height_mm?: number
  /** Ширина листа */
  sheet_width_mm?: number
}

/** LayoutPreviewResponse — Ответ с раскладкой панелей (без генерации файла). */
export interface LayoutPreviewResponse {
  /** Метод раскладки (guillotine/maxrects) */
  layout_method?: string
  panels_placed: number
  panels_total: number
  placed_panels: PlacedPanelInfo[]
  sheet_height_mm: number
  sheet_width_mm: number
  success?: boolean
  /** Названия панелей, которые не поместились */
  unplaced_panels?: string[]
  /** Утилизация листа (%) */
  utilization_percent: number
}

/** LoginRequest — Запрос на вход (отправка magic link). */
export interface LoginRequest {
  email: string
}

/** MachineProfileInfo — Информация о профиле станка для российского рынка. */
export interface MachineProfileInfo {
  /** Подача резки (мм/мин) */
  feed_rate_cutting: number
  /** Идентификатор профиля (weihong, syntec, fanuc, dsp, homag) */
  id: string
  /** Тип системы ЧПУ */
  machine_type: string
  /** Доля рынка в России */
  market_share?: string | null
  /** Название профиля */
  name: string
  /** Скорость шпинделя (об/мин) */
  spindle_speed: number
  /** Диаметр инструмента (мм) */
  tool_diameter: number
}

/** MachineProfilesList — Список доступных профилей станков. */
export interface MachineProfilesList {
  profiles: MachineProfileInfo[]
}

/** MessageResponse — Простой ответ с сообщением. */
export interface MessageResponse {
  dev_magic_link?: string | null
  message: string
}

/** Order */
export interface Order {
  created_at: string
  customer_ref?: string | null
  id: string
  notes?: string | null
  status?: string
  updated_at: string
}

/** OrderCreate */
export interface OrderCreate {
  customer_ref?: string | null
  notes?: string | null
}

/** OrderWithProductsResponse — Ответ с заказом и продуктами. */
export interface OrderWithProductsResponse {
  created_at: string
  customer_ref: string | null
  id: string
  notes: string | null
  products: ProductConfigResponse[]
}

/** PDFCuttingMapRequest — Запрос на генерацию PDF карты раскроя. */
export interface PDFCuttingMapRequest {
  /** Зазор на пропил (мм) */
  gap_mm?: number
  /** Информация о заказе для заголовка */
  order_info?: string | null
  /** Список панелей */
  panels: LayoutPanelInput[]
  /** Высота листа (мм) */
  sheet_height_mm?: number | null
  /** Ширина листа (мм) */
  sheet_width_mm?: number | null
}

/** PanelInput — Панель для генерации DXF. */
export interface PanelInput {
  /** Точки присадки: [{'x': 50, 'y': 37, 'diameter': 5, 'depth': 12, 'side': 'face', 'hardware_type': 'confirmat'}, ...] */
  drilling_points?: Record<string, unknown>[]
  /** Кромка снизу */
  edge_bottom?: boolean
  /** Кромка слева */
  edge_left?: boolean
  /** Кромка справа */
  edge_right?: boolean
  /** Толщина кромки */
  edge_thickness_mm?: number
  /** Кромка сверху */
  edge_top?: boolean
  /** Высота в мм */
  height_mm: number
  /** Материал */
  material?: string
  /** Название панели (напр. 'Боковина левая') */
  name: string
  /** Комментарий */
  notes?: string
  /** Толщина в мм */
  thickness_mm?: number
  /** Ширина в мм */
  width_mm: number
}

/** PlacedPanelInfo — Информация о размещённой панели. */
export interface PlacedPanelInfo {
  /** Высота (после возможного поворота) */
  height_mm: number
  name: string
  /** Повёрнута ли панель на 90° */
  rotated?: boolean
  /** Ширина (после возможного поворота) */
  width_mm: number
  /** X координата левого нижнего угла */
  x: number
  /** Y координата левого нижнего угла */
  y: number
}

/** ProductConfigResponse — Ответ с конфигурацией продукта. */
export interface ProductConfigResponse {
  depth_mm: number
  height_mm: number
  id: string
  material: string | null
  name: string | null
  notes?: string | null
  params: Record<string, unknown>
  thickness_mm: number | null
  width_mm: number
}

/** RegisterRequest — Запрос на регистрацию фабрики. */
export interface RegisterRequest {
  email: string
  factory_name: string
}

/** SlideTemplateInfo — Информация о шаблоне направляющих для UI. */
export interface SlideTemplateInfo {
  id: string
  load_capacity_kg: number
  name: string
  profile_height_mm: number
  type: string
}

/** TemplatesListResponse — Список доступных шаблонов. */
export interface TemplatesListResponse {
  hinges: HingeTemplateInfo[]
  slides: SlideTemplateInfo[]
}

/** TokenResponse — Ответ с JWT токеном. */
export interface TokenResponse {
  access_token: string
  expires_in: number
  token_type?: string
  user: UserInfo
}

/** UserInfo — Информация о пользователе. */
export interface UserInfo {
  email: string
  factory: FactoryInfo
  id: string
  is_owner: boolean
}

/** ValidateResponse — Результат валидации для UI технолога. */
export interface ValidateResponse {
  blocking_errors: ValidationIssue[]
  order_id: string
  revision_number: number
  spec_valid: boolean
  summary: string
  warnings: ValidationIssue[]
}

/** ValidationError */
export interface ValidationError {
  loc: string | number[]
  msg: string
  type: string
}

/** ValidationIssue — Отдельная ошибка/предупреждение с точной ссылкой на операцию. */
export interface ValidationIssue {
  code: string
  message: string
  operation_id?: string | null
  panel_id?: string | null
  severity?: string
}

/** VerifyRequest — Проверка magic token. */
export interface VerifyRequest {
  token: string
}

/** _LegacyApprovalRequest — Тело совместимого revision-level approve/reject запроса. */
export interface _LegacyApprovalRequest {
  comment?: string | null
  decision: ApprovalDecision
  expected_revision: number
}

// API endpoint contracts

/** POST /api/v1/auth/claim-guest-order - Claim Guest Order */
export interface claim_guest_order_api_v1_auth_claim_guest_order_post {
  body: ClaimRequest
  response: ClaimResponse
}

/** POST /api/v1/auth/login - Login */
export interface login_api_v1_auth_login_post {
  body: LoginRequest
  response: MessageResponse
}

/** GET /api/v1/auth/me - Get Me */
export interface get_me_api_v1_auth_me_get {
  response: UserInfo
}

/** POST /api/v1/auth/register - Register */
export interface register_api_v1_auth_register_post {
  body: RegisterRequest
  response: MessageResponse
}

/** POST /api/v1/auth/verify - Verify */
export interface verify_api_v1_auth_verify_post {
  body: VerifyRequest
  response: TokenResponse
}

/** POST /api/v1/bom/generate - Generate Bom Endpoint */
export interface generate_bom_endpoint_api_v1_bom_generate_post {
  body: GenerateBOMRequest
  response: GenerateBOMResponse
}

/** POST /api/v1/cam/cutting-map-pdf - Generate Cutting Map Pdf */
export interface generate_cutting_map_pdf_api_v1_cam_cutting_map_pdf_post {
  body: PDFCuttingMapRequest
  response: void
}

/** POST /api/v1/cam/drilling - Create Drilling Job */
export interface create_drilling_job_api_v1_cam_drilling_post {
  body: DrillingGcodeRequest
  response: DrillingGcodeResponse
}

/** POST /api/v1/cam/dxf - Create Dxf Job */
export interface create_dxf_job_api_v1_cam_dxf_post {
  body: DXFJobRequest
  response: DXFJobResponse
}

/** POST /api/v1/cam/gcode - Create Gcode Job */
export interface create_gcode_job_api_v1_cam_gcode_post {
  body: GCodeJobRequest
  response: GCodeJobResponse
}

/** GET /api/v1/cam/jobs - List Cam Jobs */
export interface list_cam_jobs_api_v1_cam_jobs_get {
  response: CAMJobsListResponse
}

/** GET /api/v1/cam/jobs/{job_id} - Get Cam Job Status */
export interface get_cam_job_status_api_v1_cam_jobs__job_id__get {
  job_id: string
  response: CAMJobStatus
}

/** GET /api/v1/cam/jobs/{job_id}/download - Download Cam Artifact */
export interface download_cam_artifact_api_v1_cam_jobs__job_id__download_get {
  job_id: string
  response: ArtifactDownload
}

/** GET /api/v1/cam/jobs/{job_id}/file - Stream Cam File */
export interface stream_cam_file_api_v1_cam_jobs__job_id__file_get {
  job_id: string
  response: void
}

/** POST /api/v1/cam/layout-preview - Layout Preview */
export interface layout_preview_api_v1_cam_layout_preview_post {
  body: LayoutPreviewRequest
  response: LayoutPreviewResponse
}

/** GET /api/v1/cam/machine-profiles - List Machine Profiles */
export interface list_machine_profiles_api_v1_cam_machine_profiles_get {
  response: MachineProfilesList
}

/** GET /api/v1/dashboard/stats - Get Dashboard Stats */
export interface get_dashboard_stats_api_v1_dashboard_stats_get {
  response: void
}

/** POST /api/v1/dialogue/clarify - Dialogue Clarify */
export interface dialogue_clarify_api_v1_dialogue_clarify_post {
  body: DialogueTurnRequest
  response: void
}

/** POST /api/v1/dialogue/clarify-with-tools - Dialogue Clarify With Tools */
export interface dialogue_clarify_with_tools_api_v1_dialogue_clarify_with_tools_post {
  body: DialogueTurnRequest
  response: void
}

/** GET /api/v1/hardware/search - Search Hardware */
export interface search_hardware_api_v1_hardware_search_get {
  response: HardwareSearchResponse
}

/** GET /api/v1/hardware/templates - Get Hardware Templates */
export interface get_hardware_templates_api_v1_hardware_templates_get {
  response: TemplatesListResponse
}

/** POST /api/v1/integrations/1c/export - Export 1C */
export interface export_1c_api_v1_integrations_1c_export_post {
  body: Export1CRequest
  response: Export1CResponse
}

/** POST /api/v1/manufacturing/revisions/{revision_id}/approve - Legacy Approve Revision */
export interface legacy_approve_revision_api_v1_manufacturing_revisions__revision_id__approve_post {
  revision_id: string
  body: _LegacyApprovalRequest
  response: Record<string, unknown>
}

/** GET /api/v1/manufacturing/revisions/{revision_id}/cam-gate - Legacy Cam Gate */
export interface legacy_cam_gate_api_v1_manufacturing_revisions__revision_id__cam_gate_get {
  revision_id: string
  response: Record<string, unknown>
}

/** POST /api/v1/manufacturing/revisions/{revision_id}/reject - Legacy Reject Revision */
export interface legacy_reject_revision_api_v1_manufacturing_revisions__revision_id__reject_post {
  revision_id: string
  body: _LegacyApprovalRequest
  response: Record<string, unknown>
}

/** GET /api/v1/orders - List Orders */
export interface list_orders_api_v1_orders_get {
  response: Order[]
}

/** POST /api/v1/orders - Create Order */
export interface create_order_api_v1_orders_post {
  body: OrderCreate
  response: Order
}

/** POST /api/v1/orders/anonymous - Create Anonymous Order */
export interface create_anonymous_order_api_v1_orders_anonymous_post {
  body: OrderCreate
  response: Order
}

/** GET /api/v1/orders/{order_id} - Get Order With Products Endpoint */
export interface get_order_with_products_endpoint_api_v1_orders__order_id__get {
  order_id: string
  response: OrderWithProductsResponse
}

/** GET /api/v1/orders/{order_id}/bom - Get Order Bom */
export interface get_order_bom_api_v1_orders__order_id__bom_get {
  order_id: string
  response: void
}

/** PATCH /api/v1/orders/{order_id}/bom - Update Order Bom */
export interface update_order_bom_api_v1_orders__order_id__bom_patch {
  order_id: string
  body: Record<string, unknown>
  response: void
}

/** POST /api/v1/orders/{order_id}/bom/add-panel - Add Panel To Bom */
export interface add_panel_to_bom_api_v1_orders__order_id__bom_add_panel_post {
  order_id: string
  body: Record<string, unknown>
  response: void
}

/** DELETE /api/v1/orders/{order_id}/bom/panel/{panel_id} - Delete Panel From Bom */
export interface delete_panel_from_bom_api_v1_orders__order_id__bom_panel__panel_id__delete {
  order_id: string
  panel_id: string
  response: void
}

/** POST /api/v1/orders/{order_id}/bom/recalculate - Recalculate Bom */
export interface recalculate_bom_api_v1_orders__order_id__bom_recalculate_post {
  order_id: string
  response: void
}

/** GET /api/v1/orders/{order_id}/cost - Calculate Order Cost */
export interface calculate_order_cost_api_v1_orders__order_id__cost_get {
  order_id: string
  response: CostEstimateResponse
}

/** POST /api/v1/orders/{order_id}/finalize - Finalize Order Endpoint */
export interface finalize_order_endpoint_api_v1_orders__order_id__finalize_post {
  order_id: string
  body: Record<string, unknown>
  response: FinalizeOrderResponse
}

/** POST /api/v1/orders/{order_id}/manufacturing/approve - Approve Manufacturing */
export interface approve_manufacturing_api_v1_orders__order_id__manufacturing_approve_post {
  order_id: string
  body: ApprovalRequest
  response: ApprovalResponse
}

/** POST /api/v1/orders/{order_id}/manufacturing/validate - Validate Manufacturing */
export interface validate_manufacturing_api_v1_orders__order_id__manufacturing_validate_post {
  order_id: string
  response: ValidateResponse
}

/** POST /api/v1/panels/calculate - Calculate Panels Endpoint */
export interface calculate_panels_endpoint_api_v1_panels_calculate_post {
  body: CalculatePanelsRequest
  response: CalculatePanelsResponse
}

/** GET /api/v1/settings - Get Settings */
export interface get_settings_api_v1_settings_get {
  response: FactorySettingsResponse
}

/** PATCH /api/v1/settings - Update Settings */
export interface update_settings_api_v1_settings_patch {
  body: FactorySettingsUpdate
  response: FactorySettingsUpdateResponse
}

/** POST /api/v1/spec/extract-from-image - Extract From Image */
export interface extract_from_image_api_v1_spec_extract_from_image_post {
  body: ImageExtractRequest
  response: ImageExtractResponse
}

/** GET /health - Health */
export interface health_health_get {
  response: Record<string, unknown>
}
