"""Edge banding export core — Task 12.

Deterministic edge banding data extraction from ManufacturingSpec
with Russian CSV export for production tracking.

Domain:
- EdgeSpec: one edge of a panel (position, material, thickness)
- EdgeExportRecord: stable-ID export record for one edge
- ExportStatus: draft/approved decision domain
- build_edge_records: extract edge data from spec
- export_edge_csv: produce Russian CSV (UTF-8 BOM, semicolon delimiter)
"""
from __future__ import annotations

import csv
import hashlib
import io
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from api.manufacturing.contracts import ManufacturingSpec, PanelSpec

# ── Enums ─────────────────────────────────────────────────────────────


class EdgePosition(str, Enum):
    """Позиция кромки на панели."""

    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"


class EdgeMaterial(str, Enum):
    """Материал кромки."""

    PVC_04 = "PVC 0.4"
    PVC_10 = "PVC 1.0"
    PVC_20 = "PVC 2.0"
    MELAMINE = "Меламин"
    ABS_10 = "ABS 1.0"
    ABS_20 = "ABS 2.0"
    VENEER = "Шпон"
    NONE = "Без кромки"


class ExportStatus(str, Enum):
    """Статус экспорта: черновик или утверждён."""

    DRAFT = "draft"
    APPROVED = "approved"


# ── Models ────────────────────────────────────────────────────────────


class EdgeSpec(BaseModel):
    """Одна кромка панели."""

    position: EdgePosition
    material: EdgeMaterial = EdgeMaterial.PVC_04
    width_mm: float = Field(22.0, gt=0, description="Ширина кромки, мм")

    @field_validator("width_mm", mode="before")
    @classmethod
    def _validate_width(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"width_mm должно быть > 0, получено {v}")
        return v


class EdgeExportRecord(BaseModel):
    """Запись экспорта кромки со стабильным ID."""

    record_id: str
    panel_id: str
    position: EdgePosition
    material: EdgeMaterial
    width_mm: float
    length_mm: float
    status: ExportStatus = ExportStatus.DRAFT

    @field_validator("record_id", mode="before")
    @classmethod
    def _validate_record_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("record_id не может быть пустым")
        return v


class PanelEdgeSummary(BaseModel):
    """Сводка кромок одной панели."""

    panel_id: str
    width_mm: float
    height_mm: float
    material: str | None = None
    edges: list[EdgeSpec] = Field(default_factory=list)


# ── Стабильные ID ─────────────────────────────────────────────────────


def make_edge_record_id(panel_id: str, position: EdgePosition, revision: int = 1) -> str:
    """Детерминированный ID записи кромки (stable export identifier).

    Включает revision, чтобы ID был идентичен в BOM / Excel/CSV / CAM manifest.
    CAM manifest contract: только идентификаторы (Task 12, не CAM/G-code impl).
    """
    raw = f"{panel_id}:{position.value}:r{revision}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"edge_{panel_id}_{position.value}_r{revision}_{h}"


# ── Построение сводки кромок ──────────────────────────────────────────


def build_panel_edge_summary(
    panel: PanelSpec,
    default_material: EdgeMaterial = EdgeMaterial.PVC_04,
    default_width_mm: float = 22.0,
) -> PanelEdgeSummary:
    """Построить сводку кромок для одной панели.

    По умолчанию все 4 торца кромкуются PVC 0.4.
    """
    edges = [
        EdgeSpec(position=pos, material=default_material, width_mm=default_width_mm)
        for pos in EdgePosition
    ]
    return PanelEdgeSummary(
        panel_id=panel.id,
        width_mm=panel.width_mm,
        height_mm=panel.height_mm,
        material=panel.material,
        edges=edges,
    )


def _edge_length(panel: PanelSpec, position: EdgePosition) -> float:
    """Длина кромки зависит от позиции панели."""
    if position in (EdgePosition.FRONT, EdgePosition.BACK):
        return panel.width_mm
    return panel.height_mm


def build_edge_records(
    spec: ManufacturingSpec,
    default_material: EdgeMaterial = EdgeMaterial.PVC_04,
    default_width_mm: float = 22.0,
    *,
    revision: int = 1,
    status: ExportStatus = ExportStatus.DRAFT,
) -> list[EdgeExportRecord]:
    """Извлечь записи кромок из ManufacturingSpec.

    Детерминированный порядок: панели и кромки сортируются по ID.
    revision и status позволяют stable IDs и production gating.
    """
    records: list[EdgeExportRecord] = []
    for panel in sorted(spec.panels, key=lambda p: p.id):
        summary = build_panel_edge_summary(panel, default_material, default_width_mm)
        for edge in summary.edges:
            records.append(
                EdgeExportRecord(
                    record_id=make_edge_record_id(panel.id, edge.position, revision),
                    panel_id=panel.id,
                    position=edge.position,
                    material=edge.material,
                    width_mm=edge.width_mm,
                    length_mm=_edge_length(panel, edge.position),
                    status=status,
                )
            )
    return records


# ── CSV экспорт ───────────────────────────────────────────────────────

_CSV_HEADER = [
    "ID записи",
    "ID панели",
    "Позиция",
    "Материал кромки",
    "Ширина кромки, мм",
    "Длина кромки, мм",
    "Статус",
]

_POSITION_RU: dict[EdgePosition, str] = {
    EdgePosition.FRONT: "Передняя",
    EdgePosition.BACK: "Задняя",
    EdgePosition.LEFT: "Левая",
    EdgePosition.RIGHT: "Правая",
}

_STATUS_RU: dict[ExportStatus, str] = {
    ExportStatus.DRAFT: "Черновик",
    ExportStatus.APPROVED: "Утверждено",
}


def export_edge_csv(records: list[EdgeExportRecord], *, decimal_sep: str = ".", watermark: bool = False) -> str:
    """Сформировать CSV строку с кромками (русская локаль / 1C).

    Формат: UTF-8 BOM, разделитель — точка с запятой.
    decimal_sep: '.' или ',' для русских Excel/CSV fixtures.
    watermark: для preview drafts добавляет водяной знак.
    """
    def _fmt(v: float) -> str:
        return f"{v:.1f}".replace(".", decimal_sep)

    buf = io.StringIO()
    buf.write("\ufeff")
    if watermark:
        # Watermark line for preview drafts (Task 12). Extra row before header.
        buf.write("ВОДЯНОЙ_ЗНАК;ПРЕДВАРИТЕЛЬНЫЙ ЧЕРНОВИК — НЕ ДЛЯ ПРОИЗВОДСТВА;;;\n")
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(_CSV_HEADER)
    for rec in records:
        writer.writerow(
            [
                rec.record_id,
                rec.panel_id,
                _POSITION_RU[rec.position],
                rec.material.value,
                _fmt(rec.width_mm),
                _fmt(rec.length_mm),
                _STATUS_RU[rec.status],
            ]
        )
    return buf.getvalue()


def export_edge_csv_bytes(records: list[EdgeExportRecord], **kwargs: Any) -> bytes:
    """CSV как bytes (для записи в файл)."""
    return export_edge_csv(records, **kwargs).encode("utf-8")


# ── Production gate and CAM identifier contract (Task 12 only) ─────────


PRODUCTION_BLOCK_MSG = (
    "Production export заблокирован для stale draft. "
    "Требуется утверждённая текущая ревизия ManufacturingRevision. "
    "Preview drafts получают watermark."
)


def assert_production_export_allowed(is_approved: bool, context: str = "edge") -> None:
    """Блокировка production export для stale drafts (TDD + spec).

    Только approved revision разрешает production. Черновики — только preview с watermark.
    """
    if not is_approved:
        raise PermissionError(f"[{context}] {PRODUCTION_BLOCK_MSG}")


# CAM manifest identifier contract (identifiers only, no CAM/G-code implementation)
CAM_MANIFEST_CONTRACT = {
    "description": "Panel IDs, record_ids (revision-aware), quantities, units(mm) and revision "
                   "MUST be identical across BOM, edge/1C Excel/CSV and CAM manifests.",
    "panel_id_source": "ManufacturingSpec.panels[].id (stable)",
    "units": "mm",
    "quantity": 1,
    "revision_in_record_id": True,
    "status": ["draft", "approved"],
}


def get_cam_identifier_contract() -> dict:
    """Return the stable identifier contract for cross-verification with CAM manifests."""
    return CAM_MANIFEST_CONTRACT
