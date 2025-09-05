from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .database import Base


class JobStatusEnum(str):
    Created = "Created"
    Processing = "Processing"
    Completed = "Completed"
    Failed = "Failed"


class ValidationStatusEnum(str):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    customer_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    products: Mapped[list["ProductConfig"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class ProductConfig(Base):
    __tablename__ = "product_configs"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    width_mm: Mapped[float] = mapped_column(Float)
    height_mm: Mapped[float] = mapped_column(Float)
    depth_mm: Mapped[float] = mapped_column(Float)
    material: Mapped[str | None] = mapped_column(String(80), nullable=True)
    thickness_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="products")
    panels: Mapped[list["Panel"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Panel(Base):
    __tablename__ = "panels"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product_configs.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    width_mm: Mapped[float] = mapped_column(Float)
    height_mm: Mapped[float] = mapped_column(Float)
    thickness_mm: Mapped[float] = mapped_column(Float)
    material: Mapped[str | None] = mapped_column(String(80), nullable=True)
    edge_band_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["ProductConfig"] = relationship(back_populates="panels")


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class HardwareItem(Base):
    __tablename__ = "hardware_items"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(120), unique=True)
    brand: Mapped[str | None] = mapped_column(String(80), nullable=True)
    type: Mapped[str] = mapped_column(String(40))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    compat: Mapped[list[str]] = mapped_column(JSON, default=list)
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    supplier_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"))
    
    # Поля для векторного поиска (добавлены для 2025)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(256), nullable=True)
    embedding_version: Mapped[str | None] = mapped_column(String(40), nullable=True)  # Версия модели эмбеддингов
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Хеш контента для проверки актуальности
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Время индексации
    
    # Дополнительные поля для каталога фурнитуры
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)  # Категория фурнитуры
    material_type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # Тип материала для совместимости
    thickness_min_mm: Mapped[float | None] = mapped_column(Float, nullable=True)  # Минимальная толщина материала
    thickness_max_mm: Mapped[float | None] = mapped_column(Float, nullable=True)  # Максимальная толщина материала
    price_rub: Mapped[float | None] = mapped_column(Float, nullable=True)  # Цена в рублях
    is_active: Mapped[bool] = mapped_column(default=True)  # Активность позиции


class BOMItem(Base):
    __tablename__ = "bom_items"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(255))
    qty: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supplier_sku: Mapped[str | None] = mapped_column(String(120), nullable=True)
    supplier_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"))


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type: Mapped[str] = mapped_column(String(20))
    storage_key: Mapped[str] = mapped_column(String(255))
    presigned_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CAMJob(Base):
    __tablename__ = "cam_jobs"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"))
    job_kind: Mapped[str] = mapped_column(String(20))  # DXF | GCODE
    artifact_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(Enum(
        JobStatusEnum.Created,
        JobStatusEnum.Processing,
        JobStatusEnum.Completed,
        JobStatusEnum.Failed,
        name="job_status",
        native_enum=False,
    ), default=JobStatusEnum.Created)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    actor_role: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(120))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Validation(Base):
    __tablename__ = "validations"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    related_entity: Mapped[str] = mapped_column(String(40))
    related_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(Enum(
        ValidationStatusEnum.Pending,
        ValidationStatusEnum.Approved,
        ValidationStatusEnum.Rejected,
        name="validation_status",
        native_enum=False,
    ), default=ValidationStatusEnum.Pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ValidationItem(Base):
    __tablename__ = "validation_items"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    validation_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("validations.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    proposed_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ValidationStatusEnum.Pending)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
