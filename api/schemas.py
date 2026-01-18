from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class OrderBase(BaseModel):
    customer_ref: str | None = None
    notes: str | None = None


class OrderCreate(OrderBase):
    pass


class Order(OrderBase):
    id: UUID
    status: str = "draft"  # draft | ready | completed
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpecExtractRequest(BaseModel):
    input_type: Literal["text", "image", "sketch"]
    content: str


class SpecExtractResponse(BaseModel):
    product_config_id: str
    parameters: dict[str, Any]


class HardwareSelectCriteria(BaseModel):
    material: str | None = None
    thickness: float | None = Field(None, description="Толщина в мм")


class HardwareSelectRequest(BaseModel):
    product_config_id: str
    criteria: HardwareSelectCriteria


class BOMItem(BaseModel):
    hardware_item_id: str
    sku: str
    name: str | None = None
    quantity: int
    supplier: str | None = None
    version: str | None = None


class HardwareSelectResponse(BaseModel):
    bom_id: str
    items: list[BOMItem]


class SpecValidateItem(BaseModel):
    parameter: str
    value: Any
    confidence: float | None = None
    question: str | None = None


class SpecValidateRequest(BaseModel):
    product_config_id: str
    stage: Literal["extraction_review", "rag_review"]
    required_approvals: list[SpecValidateItem]


class SpecValidateResponse(BaseModel):
    validation_id: str
    validation_required: bool
    approvals_needed: int
    next_step_allowed: bool


class ValidationApproveItem(BaseModel):
    validation_item_id: str
    approved: bool
    comment: str | None = None


class ValidationApproveRequest(BaseModel):
    validation_id: str
    approvals: list[ValidationApproveItem]


class ValidationApproveResponse(BaseModel):
    validation_id: str
    status: Literal["completed", "failed"]
    next_step_allowed: bool


class CAMJobRequest(BaseModel):
    product_config_id: str
    order_id: str | None = None
    dxf_job_id: str | None = None # For G-code jobs
    context: dict[str, Any] = Field(default_factory=dict)


class CAMJobResponse(BaseModel):
    dxf_job_id: str | None = None
    gcode_job_id: str | None = None
    status: Literal["processing", "created"]


class CAMJobStatusResponse(BaseModel):
    job_id: str
    job_kind: Literal["DXF", "GCODE"]
    status: Literal["Created", "Processing", "Completed", "Failed"]
    artifact_id: str | None = None
    error: str | None = None


class ArtifactDownloadResponse(BaseModel):
    artifact_id: str
    url: str


class DialogueMessageBase(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class DialogueMessageCreate(DialogueMessageBase):
    pass

class DialogueMessage(DialogueMessageBase):
    id: UUID
    order_id: UUID
    turn_number: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class DialogueTurnRequest(BaseModel):
    order_id: UUID
    messages: list[DialogueMessageCreate]
    extracted_context: str | None = None  # Контекст из Vision OCR (размеры, материал и т.д.)


class Export1CRequest(BaseModel):
    order_id: UUID
    format: Literal["excel", "csv"] = "excel"


class Export1CResponse(BaseModel):
    success: bool
    format: str
    filename: str
    download_url: str
    expires_in_seconds: int = 900  # 15 минут


class ZIPJobRequest(BaseModel):
    order_id: str
    job_ids: list[str]


# ============================================================================
# Vision OCR - извлечение параметров из изображений
# ============================================================================

class FurnitureType(BaseModel):
    """Тип мебельного изделия."""
    category: Literal[
        "навесной_шкаф", "напольный_шкаф", "тумба", "пенал",
        "столешница", "фасад", "полка", "ящик", "другое"
    ]
    subcategory: str | None = None
    description: str | None = None


class ExtractedDimensions(BaseModel):
    """Извлечённые размеры изделия."""
    width_mm: int | None = Field(None, description="Ширина в мм")
    height_mm: int | None = Field(None, description="Высота в мм")
    depth_mm: int | None = Field(None, description="Глубина в мм")
    thickness_mm: float | None = Field(None, description="Толщина материала в мм")


class ExtractedMaterial(BaseModel):
    """Извлечённый материал."""
    type: Literal["ЛДСП", "МДФ", "массив", "фанера", "ДВП", "стекло", "металл", "другое"] | None = None
    color: str | None = None
    texture: str | None = None
    brand: str | None = None


class ExtractedFurnitureParams(BaseModel):
    """Структурированные параметры мебели, извлечённые из изображения."""
    furniture_type: FurnitureType | None = None
    dimensions: ExtractedDimensions | None = None
    body_material: ExtractedMaterial | None = Field(None, description="Материал корпуса")
    facade_material: ExtractedMaterial | None = Field(None, description="Материал фасада")

    # Дополнительные параметры
    door_count: int | None = Field(None, description="Количество дверей")
    drawer_count: int | None = Field(None, description="Количество ящиков")
    shelf_count: int | None = Field(None, description="Количество полок")
    has_legs: bool | None = Field(None, description="Есть ли ножки")

    # Текст из OCR
    raw_text: str | None = Field(None, description="Исходный распознанный текст")

    # Уверенность распознавания
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Уверенность распознавания (0-1)")
    needs_clarification: bool = Field(False, description="Требуется уточнение от пользователя")
    clarification_questions: list[str] | None = Field(default=None, description="Вопросы для уточнения")

    @field_validator("clarification_questions", mode="before")
    @classmethod
    def convert_none_to_empty_list(cls, v):
        """Конвертирует None в пустой список."""
        return v if v is not None else []


class ImageExtractRequest(BaseModel):
    """Запрос на извлечение параметров из изображения или PDF."""
    image_base64: str = Field(..., description="Изображение или PDF в формате base64")
    image_mime_type: Literal["image/jpeg", "image/png", "image/webp", "application/pdf"] = "image/jpeg"
    order_id: UUID | None = Field(None, description="ID заказа для привязки")
    language_hint: Literal["ru", "en", "auto"] = "ru"


class ImageExtractResponse(BaseModel):
    """Ответ с извлечёнными параметрами."""
    success: bool
    parameters: ExtractedFurnitureParams | None = None

    # Если требуется уточнение - предлагаем перейти в диалог
    fallback_to_dialogue: bool = Field(False, description="Рекомендуется перейти в диалог для уточнения")
    dialogue_prompt: str | None = Field(None, description="Начальный промпт для диалога")

    # Метаданные
    ocr_confidence: float = Field(0.0, description="Уверенность OCR")
    processing_time_ms: int = Field(0, description="Время обработки в мс")
    error: str | None = None

    # Новые поля для валидации модулей
    error_type: Literal["multiple_modules", "file_too_large", "unsupported_format", "ocr_failed"] | None = Field(
        None, description="Тип ошибки для программной обработки"
    )
    module_count: int | None = Field(None, description="Количество модулей на изображении (если определено)")


# ============================================================================
# CAM - генерация DXF и G-code (P1)
# ============================================================================

class PanelInput(BaseModel):
    """Панель для генерации DXF."""
    name: str = Field(..., description="Название панели (напр. 'Боковина левая')")
    width_mm: float = Field(..., gt=0, description="Ширина в мм")
    height_mm: float = Field(..., gt=0, description="Высота в мм")
    thickness_mm: float = Field(16.0, gt=0, description="Толщина в мм")
    material: str = Field("ЛДСП", description="Материал")

    # Кромка
    edge_top: bool = Field(False, description="Кромка сверху")
    edge_bottom: bool = Field(False, description="Кромка снизу")
    edge_left: bool = Field(False, description="Кромка слева")
    edge_right: bool = Field(False, description="Кромка справа")
    edge_thickness_mm: float = Field(0.4, ge=0, description="Толщина кромки")

    # Присадка (отверстия)
    drilling_holes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Отверстия: [{'x': 50, 'y': 37, 'diameter': 5, 'depth': 12}, ...]"
    )

    notes: str = Field("", description="Комментарий")


class DXFJobRequest(BaseModel):
    """Запрос на генерацию DXF."""
    order_id: UUID | None = Field(None, description="ID заказа")
    panels: list[PanelInput] = Field(..., min_length=1, description="Список панелей")

    # Параметры листа
    sheet_width_mm: float | None = Field(None, description="Ширина листа (авто если не указано)")
    sheet_height_mm: float | None = Field(None, description="Высота листа (авто если не указано)")

    # Опции
    optimize_layout: bool = Field(True, description="Оптимизировать раскрой")
    gap_mm: float = Field(4.0, ge=0, description="Зазор между панелями (на пропил)")

    # Идемпотентность
    idempotency_key: str | None = Field(None, description="Ключ идемпотентности")


class DXFJobResponse(BaseModel):
    """Ответ на создание DXF задачи."""
    job_id: UUID
    status: Literal["created", "processing"] = "created"
    panels_count: int
    sheet_size: tuple[float, float]


class CAMJobStatus(BaseModel):
    """Статус CAM задачи."""
    job_id: UUID
    job_kind: Literal["DXF", "GCODE", "ZIP"]
    status: Literal["Created", "Processing", "Completed", "Failed"]
    artifact_id: UUID | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    # Дополнительная информация
    utilization_percent: float | None = Field(None, description="Утилизация листа (%)")
    panels_placed: int | None = Field(None, description="Размещено панелей")
    panels_unplaced: int | None = Field(None, description="Не размещено панелей")


class CAMJobListItem(BaseModel):
    """Краткая информация о CAM задаче для списка."""
    job_id: UUID
    job_kind: Literal["DXF", "GCODE", "ZIP"]
    status: Literal["Created", "Processing", "Completed", "Failed"]
    order_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CAMJobsListResponse(BaseModel):
    """Список CAM задач."""
    jobs: list[CAMJobListItem]
    total: int


class ArtifactDownload(BaseModel):
    """Информация для скачивания артефакта."""
    artifact_id: UUID
    type: Literal["DXF", "GCODE", "ZIP"]
    filename: str
    download_url: str
    size_bytes: int
    expires_in_seconds: int = Field(900, description="Время жизни ссылки (сек)")


# ============================================================================
# G-code генерация (P2)
# ============================================================================

class MachineProfileInfo(BaseModel):
    """Информация о профиле станка для российского рынка."""
    id: str = Field(..., description="Идентификатор профиля (weihong, syntec, fanuc, dsp, homag)")
    name: str = Field(..., description="Название профиля")
    machine_type: str = Field(..., description="Тип системы ЧПУ")
    spindle_speed: int = Field(..., description="Скорость шпинделя (об/мин)")
    feed_rate_cutting: int = Field(..., description="Подача резки (мм/мин)")
    tool_diameter: float = Field(..., description="Диаметр инструмента (мм)")
    market_share: str | None = Field(None, description="Доля рынка в России")


class MachineProfilesList(BaseModel):
    """Список доступных профилей станков."""
    profiles: list[MachineProfileInfo]


class GCodeJobRequest(BaseModel):
    """Запрос на генерацию G-code из DXF артефакта."""
    dxf_artifact_id: UUID = Field(..., description="ID DXF артефакта для конвертации")
    order_id: UUID | None = Field(None, description="ID заказа")

    # Профиль станка (если не задан — берётся из настроек фабрики или дефолт weihong)
    machine_profile: Literal["weihong", "syntec", "fanuc", "dsp", "homag"] | None = Field(
        None,
        description="Профиль станка ЧПУ. Если не задан — используется из настроек фабрики"
    )

    # Переопределение параметров профиля
    spindle_speed: int | None = Field(None, ge=1000, le=30000, description="Скорость шпинделя (об/мин)")
    feed_rate_cutting: int | None = Field(None, ge=100, le=15000, description="Подача резки (мм/мин)")
    feed_rate_plunge: int | None = Field(None, ge=100, le=5000, description="Подача врезания (мм/мин)")
    cut_depth: float | None = Field(None, ge=1, le=50, description="Глубина резки (мм)")
    safe_height: float | None = Field(None, ge=1, le=50, description="Безопасная высота (мм)")
    tool_diameter: float | None = Field(None, ge=1, le=20, description="Диаметр фрезы (мм)")

    # Идемпотентность
    idempotency_key: str | None = Field(None, description="Ключ идемпотентности")


class GCodeJobResponse(BaseModel):
    """Ответ на создание G-code задачи."""
    job_id: UUID
    status: Literal["created", "processing"] = "created"
    machine_profile: str = Field(..., description="Используемый профиль станка")
    dxf_artifact_id: UUID = Field(..., description="ID исходного DXF артефакта")


class DirectGCodeRequest(BaseModel):
    """Запрос на прямую генерацию G-code из панелей (без DXF артефакта)."""
    order_id: UUID | None = Field(None, description="ID заказа")
    panels: list[PanelInput] = Field(..., min_length=1, description="Список панелей")

    # Профиль станка (российский рынок)
    machine_profile: Literal["weihong", "syntec", "fanuc", "dsp", "homag"] = Field(
        "weihong",
        description="Профиль станка ЧПУ (weihong=NCStudio 30-35%, syntec=KDT/WoodTec 20-25%, fanuc=премиум 15-20%, dsp=бюджетный 8-12%, homag=премиум мебельный)"
    )

    # Параметры листа
    sheet_width_mm: float | None = Field(None, description="Ширина листа")
    sheet_height_mm: float | None = Field(None, description="Высота листа")
    optimize_layout: bool = Field(True, description="Оптимизировать раскрой")
    gap_mm: float = Field(4.0, ge=0, description="Зазор между панелями")

    # Переопределение параметров профиля
    cut_depth: float | None = Field(None, ge=1, le=50, description="Глубина резки (мм)")

    # Идемпотентность
    idempotency_key: str | None = Field(None, description="Ключ идемпотентности")


# ============================================================================
# Финализация заказа (Phase 2)
# ============================================================================

class HardwareSpec(BaseModel):
    """Спецификация фурнитуры."""
    type: str = Field(..., description="Тип фурнитуры (петля, ручка, направляющая)")
    sku: str | None = Field(None, description="Артикул")
    name: str | None = Field(None, description="Название")
    qty: int = Field(1, description="Количество")


class MaterialSpec(BaseModel):
    """Спецификация материала."""
    type: str = Field(..., description="Тип материала (ЛДСП, МДФ)")
    thickness_mm: float | None = Field(None, description="Толщина в мм")
    color: str | None = Field(None, description="Цвет")
    texture: str | None = Field(None, description="Текстура")


class DimensionsSpec(BaseModel):
    """Габариты изделия."""
    width_mm: float = Field(..., gt=0, description="Ширина в мм")
    height_mm: float = Field(..., gt=0, description="Высота в мм")
    depth_mm: float = Field(..., gt=0, description="Глубина в мм")


class FinalizeOrderRequest(BaseModel):
    """Запрос на финализацию заказа после диалога."""
    furniture_type: str = Field(..., description="Тип мебели")
    dimensions: DimensionsSpec
    body_material: MaterialSpec | None = None
    facade_material: MaterialSpec | None = None
    hardware: list[HardwareSpec] = Field(default_factory=list)
    edge_band: dict | None = Field(None, description="Кромка")
    door_count: int | None = None
    drawer_count: int | None = None
    shelf_count: int | None = None
    notes: str | None = None


class FinalizeOrderResponse(BaseModel):
    """Ответ после финализации."""
    success: bool
    order_id: str
    product_config_id: str
    message: str


class ProductConfigResponse(BaseModel):
    """Ответ с конфигурацией продукта."""
    id: str
    name: str | None
    width_mm: float
    height_mm: float
    depth_mm: float
    material: str | None
    thickness_mm: float | None
    params: dict
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderWithProductsResponse(BaseModel):
    """Ответ с заказом и продуктами."""
    id: str
    customer_ref: str | None
    notes: str | None
    created_at: datetime
    products: list[ProductConfigResponse]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Поиск фурнитуры (Hardware Search)
# ============================================================================

class HardwareSearchItem(BaseModel):
    """Элемент результата поиска фурнитуры."""
    sku: str
    name: str | None
    description: str | None
    brand: str | None
    type: str
    category: str | None
    price_rub: float | None
    params: dict[str, Any] = Field(default_factory=dict)
    score: float = Field(..., description="Релевантность (0-1)")


class HardwareSearchResponse(BaseModel):
    """Ответ на поиск фурнитуры."""
    items: list[HardwareSearchItem]
    total: int = Field(..., description="Общее количество найденных позиций")
    query: str = Field(..., description="Исходный запрос")


# ============================================================================
# Factory Settings (настройки фабрики)
# ============================================================================

# Дефолтные значения для настроек
SETTINGS_DEFAULTS: dict[str, Any] = {
    "machine_profile": "weihong",
    "sheet_width_mm": 2800,
    "sheet_height_mm": 2070,
    "thickness_mm": 16,
    "edge_thickness_mm": 0.4,
    "gap_mm": 4,
    "spindle_speed": 18000,
    "feed_rate_cutting": 3000,
    "feed_rate_plunge": 1500,
    "cut_depth": 8,
    "safe_height": 5,
    "tool_diameter": 6,
}


class FactorySettings(BaseModel):
    """Настройки фабрики — станок, материалы, параметры генерации."""

    # Станок
    machine_profile: Literal["weihong", "syntec", "fanuc", "dsp", "homag"] | None = None

    # Лист
    sheet_width_mm: float | None = Field(None, ge=100, le=5000, description="Ширина листа (мм)")
    sheet_height_mm: float | None = Field(None, ge=100, le=5000, description="Высота листа (мм)")

    # Материалы
    thickness_mm: float | None = Field(None, gt=0, le=100, description="Толщина ЛДСП (мм)")
    edge_thickness_mm: float | None = Field(None, ge=0, le=10, description="Толщина кромки (мм)")
    decor: str | None = Field(None, max_length=100, description="Декор/цвет")

    # DXF
    gap_mm: float | None = Field(None, ge=0, le=50, description="Зазор на пропил (мм)")

    # G-code
    spindle_speed: int | None = Field(None, ge=1000, le=30000, description="Скорость шпинделя (об/мин)")
    feed_rate_cutting: int | None = Field(None, ge=100, le=15000, description="Подача резки (мм/мин)")
    feed_rate_plunge: int | None = Field(None, ge=100, le=5000, description="Подача врезания (мм/мин)")
    cut_depth: float | None = Field(None, ge=1, le=50, description="Глубина за проход (мм)")
    safe_height: float | None = Field(None, ge=1, le=100, description="Безопасная высота (мм)")
    tool_diameter: float | None = Field(None, ge=1, le=30, description="Диаметр фрезы (мм)")


class FactorySettingsUpdate(BaseModel):
    """Запрос на обновление настроек (PATCH)."""

    factory_name: str | None = Field(None, max_length=255, description="Название фабрики")

    # Станок
    machine_profile: Literal["weihong", "syntec", "fanuc", "dsp", "homag"] | None = None

    # Лист
    sheet_width_mm: float | None = Field(None, ge=100, le=5000)
    sheet_height_mm: float | None = Field(None, ge=100, le=5000)

    # Материалы
    thickness_mm: float | None = Field(None, gt=0, le=100)
    edge_thickness_mm: float | None = Field(None, ge=0, le=10)
    decor: str | None = Field(None, max_length=100)

    # DXF
    gap_mm: float | None = Field(None, ge=0, le=50)

    # G-code
    spindle_speed: int | None = Field(None, ge=1000, le=30000)
    feed_rate_cutting: int | None = Field(None, ge=100, le=15000)
    feed_rate_plunge: int | None = Field(None, ge=100, le=5000)
    cut_depth: float | None = Field(None, ge=1, le=50)
    safe_height: float | None = Field(None, ge=1, le=100)
    tool_diameter: float | None = Field(None, ge=1, le=30)


class FactorySettingsResponse(BaseModel):
    """Ответ GET /settings — настройки с дефолтами для UI."""

    factory_name: str
    owner_email: str
    settings: dict[str, Any] = Field(..., description="Merged настройки (значения + дефолты)")
    defaults_used: list[str] = Field(..., description="Поля, где использованы дефолты")


class FactorySettingsUpdateResponse(BaseModel):
    """Ответ PATCH /settings."""

    success: bool = True
    updated_fields: list[str] = Field(..., description="Обновлённые поля")


# ============================================================================
# Калькулятор панелей (Panel Calculator)
# ============================================================================

class CabinetType(str, Enum):
    """Типы корпусной мебели."""
    WALL = "wall"           # Навесной шкаф
    BASE = "base"           # Напольная тумба
    BASE_SINK = "base_sink" # Тумба под мойку
    DRAWER = "drawer"       # Тумба с ящиками
    TALL = "tall"           # Пенал
    CORNER = "corner"       # Угловой шкаф


class CalculatedPanel(BaseModel):
    """Рассчитанная панель."""
    name: str = Field(..., description="Название панели (Боковина левая, Дно и т.д.)")
    width_mm: float = Field(..., gt=0, description="Ширина в мм")
    height_mm: float = Field(..., gt=0, description="Высота в мм")
    thickness_mm: float = Field(16.0, gt=0, description="Толщина в мм")
    quantity: int = Field(1, ge=1, description="Количество")

    # Кромка
    edge_front: bool = Field(False, description="Кромка спереди")
    edge_back: bool = Field(False, description="Кромка сзади")
    edge_top: bool = Field(False, description="Кромка сверху")
    edge_bottom: bool = Field(False, description="Кромка снизу")
    edge_thickness_mm: float = Field(0.4, ge=0, description="Толщина кромки")

    # Опции
    has_slot_for_back: bool = Field(False, description="Паз под заднюю стенку")
    notes: str = Field("", description="Примечания")


class CalculatePanelsRequest(BaseModel):
    """Запрос на расчёт панелей."""
    cabinet_type: CabinetType
    width_mm: int = Field(..., gt=0, le=3000, description="Ширина корпуса")
    height_mm: int = Field(..., gt=0, le=3000, description="Высота корпуса")
    depth_mm: int = Field(..., gt=0, le=1000, description="Глубина корпуса")

    # Опции
    material: str = Field("ЛДСП 16мм", description="Материал")
    shelf_count: int = Field(1, ge=0, le=10, description="Количество полок")
    door_count: int = Field(1, ge=0, le=4, description="Количество дверей")
    drawer_count: int = Field(0, ge=0, le=10, description="Количество ящиков")

    # Настройки (если не указаны — берутся из фабрики)
    thickness_mm: float | None = Field(None, description="Толщина материала")
    edge_thickness_mm: float | None = Field(None, description="Толщина кромки")


class CalculatePanelsResponse(BaseModel):
    """Ответ с рассчитанными панелями."""
    success: bool = True
    cabinet_type: str
    dimensions: dict[str, int] = Field(..., description="Габариты {width, height, depth}")

    panels: list[CalculatedPanel]

    # Сводка
    total_panels: int
    total_area_m2: float = Field(..., description="Общая площадь панелей (м²)")
    edge_length_m: float = Field(..., description="Длина кромки (м)")

    # Предупреждения
    warnings: list[str] = Field(default_factory=list)


class HardwareRecommendation(BaseModel):
    """Рекомендация по фурнитуре."""
    type: str = Field(..., description="Тип фурнитуры")
    sku: str | None = Field(None, description="Артикул из каталога")
    name: str = Field(..., description="Название")
    quantity: int = Field(..., ge=1, description="Количество")
    unit: str = Field("шт", description="Единица измерения")
    source: str = Field("calculated", description="Источник: calculated | rag")


class GenerateBOMRequest(BaseModel):
    """Запрос на генерацию полного BOM."""
    order_id: UUID | None = None
    cabinet_type: CabinetType
    width_mm: int = Field(..., gt=0, le=3000)
    height_mm: int = Field(..., gt=0, le=3000)
    depth_mm: int = Field(..., gt=0, le=1000)
    material: str = Field("ЛДСП 16мм")
    shelf_count: int = Field(1, ge=0)
    door_count: int = Field(1, ge=0)
    drawer_count: int = Field(0, ge=0)


class GenerateBOMResponse(BaseModel):
    """Полный BOM с панелями и фурнитурой."""
    success: bool = True
    order_id: UUID | None = None

    cabinet_type: str
    dimensions: dict[str, int]

    panels: list[CalculatedPanel]
    hardware: list[HardwareRecommendation]

    # Сводка
    total_panels: int
    total_area_m2: float
    edge_length_m: float
    total_hardware_items: int

    warnings: list[str] = Field(default_factory=list)
