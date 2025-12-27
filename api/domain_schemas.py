"""Доменные Pydantic-схемы (мм, без ПДн).

Сущности: Order, ProductConfig, Panel, BOM(+BOMItem), HardwareItem, Supplier,
DXFJob, GCodeJob, Artifact, AuditLog, Validation(+ValidationItem).

Примечания:
- Все линейные размеры в миллиметрах (мм).
- Поля id — UUID4, времена — timezone-aware (UTC).
- Presigned URL не храним долговечно; используем storage_key для обращения к объекту.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


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
    material: Optional[str] = None
    edge_band_mm: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class ProductConfig(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: Optional[str] = None
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    depth_mm: float = Field(gt=0)
    material: Optional[str] = None
    thickness_mm: Optional[float] = Field(default=None, gt=0)
    panels: List[Panel] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class BOMItem(BaseModel):
    sku: str
    name: str
    qty: float = Field(gt=0)
    unit: str = Field(description="Единица учёта, например pcs, set")
    params: Dict[str, Any] = Field(default_factory=dict)
    supplier_sku: Optional[str] = None
    supplier_id: Optional[UUID] = None


class BOM(BaseModel):
    items: List[BOMItem] = Field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.items)


class HardwareItem(BaseModel):
    sku: str
    brand: Optional[str] = None
    type: HardwareType = HardwareType.OTHER
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    compat: List[str] = Field(default_factory=list, description="Список совместимостей/тегов")
    url: Optional[HttpUrl] = None
    version: Optional[str] = None
    supplier_id: Optional[UUID] = None
    # Поля для совместимости с материалами
    material_type: Optional[str] = None
    thickness_min_mm: Optional[float] = None
    thickness_max_mm: Optional[float] = None
    price_rub: Optional[float] = None


class Supplier(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    url: Optional[HttpUrl] = None
    contact_email: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: ArtifactType
    storage_key: str = Field(description="Ключ в объектном хранилище")
    presigned_url: Optional[HttpUrl] = Field(default=None, description="Временная ссылка (TTL ≤ 15 мин)")
    size_bytes: Optional[int] = Field(default=None, ge=0)
    checksum: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    expires_at: Optional[datetime] = None


class BaseJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    order_id: Optional[UUID] = None
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    attempt: int = 0
    error: Optional[str] = None
    artifacts: List[Artifact] = Field(default_factory=list)


class DXFJob(BaseJob):
    job_kind: str = Field(default="DXF")
    # Контекст построения (например, параметры панелей)
    context: Dict[str, Any] = Field(default_factory=dict)


class GCodeJob(BaseJob):
    job_kind: str = Field(default="GCODE")
    # Постпроцессор, по умолчанию GRBL
    postprocessor: str = Field(default="GRBL")
    context: Dict[str, Any] = Field(default_factory=dict)


class AuditLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ts: datetime = Field(default_factory=lambda: datetime.utcnow())
    actor_role: str = Field(description="роль: admin | technologist | designer")
    action: str
    entity: str
    entity_id: UUID
    details: Dict[str, Any] = Field(default_factory=dict)


class ValidationItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    key: str = Field(description="Параметр/поле, которое проверяется")
    description: Optional[str] = None
    current_value: Any = None
    proposed_value: Any = None
    status: ValidationStatus = ValidationStatus.PENDING
    comment: Optional[str] = None


class Validation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    related_entity: str = Field(description="Например: Order, ProductConfig, etc")
    related_id: UUID
    status: ValidationStatus = ValidationStatus.PENDING
    items: List[ValidationItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class Order(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    customer_ref: Optional[str] = Field(default=None, description="Внешний идентификатор без ПДн")
    products: List[ProductConfig] = Field(default_factory=list)
    bom: Optional[BOM] = None
    notes: Optional[str] = None
