"""Доменные Pydantic-схемы (мм, без ПДн).

Сущности: Order, ProductConfig, Panel, BOM(+BOMItem), HardwareItem, Supplier,
DXFJob, GCodeJob, Artifact, AuditLog, Validation(+ValidationItem).

Примечания:
- Все линейные размеры в миллиметрах (мм).
- Поля id — UUID4, времена — timezone-aware (UTC).
- Presigned URL не храним долговечно; используем storage_key для обращения к объекту.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    CREATED = "Created"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class ValidationStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class ArtifactType(str, Enum):
    DXF = "DXF"
    GCODE = "GCODE"
    ZIP = "ZIP"
    BOM = "BOM"
    REPORT = "REPORT"


class HardwareType(str, Enum):
    HINGE = "hinge"
    SLIDE = "slide"
    HANDLE = "handle"
    LIFT = "lift"
    LEG = "leg"
    CONNECTOR = "connector"
    OTHER = "other"


class Panel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(description="Человеко‑читаемое имя панели")
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    thickness_mm: float = Field(gt=0)
    material: str | None = None
    edge_band_mm: float | None = Field(default=None, ge=0)
    notes: str | None = None


class ProductConfig(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str | None = None
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    depth_mm: float = Field(gt=0)
    material: str | None = None
    thickness_mm: float | None = Field(default=None, gt=0)
    panels: list[Panel] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class BOMItem(BaseModel):
    sku: str
    name: str
    qty: float = Field(gt=0)
    unit: str = Field(description="Единица учёта, например pcs, set")
    params: dict[str, Any] = Field(default_factory=dict)
    supplier_sku: str | None = None
    supplier_id: UUID | None = None


class BOM(BaseModel):
    items: list[BOMItem] = Field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.items)


class HardwareItem(BaseModel):
    sku: str
    brand: str | None = None
    type: HardwareType = HardwareType.OTHER
    name: str | None = None
    description: str | None = None
    category: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    compat: list[str] = Field(default_factory=list, description="Список совместимостей/тегов")
    url: HttpUrl | None = None
    version: str | None = None
    supplier_id: UUID | None = None
    # Поля для совместимости с материалами
    material_type: str | None = None
    thickness_min_mm: float | None = None
    thickness_max_mm: float | None = None
    price_rub: float | None = None


class Supplier(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    url: HttpUrl | None = None
    contact_email: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: ArtifactType
    storage_key: str = Field(description="Ключ в объектном хранилище")
    presigned_url: HttpUrl | None = Field(default=None, description="Временная ссылка (TTL ≤ 15 мин)")
    size_bytes: int | None = Field(default=None, ge=0)
    checksum: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    expires_at: datetime | None = None


class BaseJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID | None = None
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    attempt: int = 0
    error: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)


class DXFJob(BaseJob):
    job_kind: str = Field(default="DXF")
    # Контекст построения (например, параметры панелей)
    context: dict[str, Any] = Field(default_factory=dict)


class GCodeJob(BaseJob):
    job_kind: str = Field(default="GCODE")
    # Постпроцессор, по умолчанию GRBL
    postprocessor: str = Field(default="GRBL")
    context: dict[str, Any] = Field(default_factory=dict)


class AuditLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ts: datetime = Field(default_factory=lambda: datetime.utcnow())
    actor_role: str = Field(description="роль: admin | technologist | designer")
    action: str
    entity: str
    entity_id: UUID
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    key: str = Field(description="Параметр/поле, которое проверяется")
    description: str | None = None
    current_value: Any = None
    proposed_value: Any = None
    status: ValidationStatus = ValidationStatus.PENDING
    comment: str | None = None


class Validation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    related_entity: str = Field(description="Например: Order, ProductConfig, etc")
    related_id: UUID
    status: ValidationStatus = ValidationStatus.PENDING
    items: list[ValidationItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class Order(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    customer_ref: str | None = Field(default=None, description="Внешний идентификатор без ПДн")
    products: list[ProductConfig] = Field(default_factory=list)
    bom: BOM | None = None
    notes: str | None = None
