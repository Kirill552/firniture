"""Manufacturing contracts: Face, operations, PanelSpec, ManufacturingSpec.

Pydantic v2 typed models для описания операций ЧПУ-обработки панелей.
Все размеры в мм (или конвертируются из inches через Unit).
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Face(str, Enum):
    """Лицевая сторона панели — локальная система координат."""
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


class OperationType(str, Enum):
    """Тип операции обработки."""
    DRILL = "drill"
    SLOT = "slot"
    POCKET = "pocket"


class Unit(str, Enum):
    """Единицы измерения спецификации."""
    MM = "mm"
    INCH = "inch"


# ---------------------------------------------------------------------------
# Validators (shared)
# ---------------------------------------------------------------------------

def _positive_nonzero(v: float, field_name: str = "value") -> float:
    """Значение должно быть положительным и конечным (не nan/inf)."""
    if not math.isfinite(v):
        raise ValueError(f"{field_name} не может быть nan или inf")
    if v <= 0:
        raise ValueError(f"{field_name} должно быть > 0, получено {v}")
    return v


def _nonempty_id(v: str) -> str:
    """ID операции не может быть пустой строкой."""
    if not v or not v.strip():
        raise ValueError("id операции не может быть пустым")
    return v


# ---------------------------------------------------------------------------
# Base operation
# ---------------------------------------------------------------------------

class BaseOperation(BaseModel):
    """Базовый класс операции обработки."""
    id: Annotated[str, Field(min_length=1)]
    op_type: OperationType
    face: Face
    x_mm: float
    y_mm: float

    _validate_id = field_validator("id", mode="before")(
        classmethod(lambda cls, v: _nonempty_id(v))
    )

    @field_validator("x_mm", "y_mm", mode="before")
    @classmethod
    def _check_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("координата не может быть nan или inf")
        return v


# ---------------------------------------------------------------------------
# Concrete operations
# ---------------------------------------------------------------------------

class DrillOperation(BaseOperation):
    """Операция сверления отверстия."""
    op_type: Literal[OperationType.DRILL] = OperationType.DRILL
    diameter_mm: float
    depth_mm: float

    @field_validator("diameter_mm", mode="before")
    @classmethod
    def _validate_diameter(cls, v: float) -> float:
        return _positive_nonzero(v, "diameter_mm")

    @field_validator("depth_mm", mode="before")
    @classmethod
    def _validate_depth(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("depth_mm не может быть nan или inf")
        if v < 0:
            raise ValueError(f"depth_mm должно быть >= 0, получено {v}")
        return v


class SlotOperation(BaseOperation):
    """Операция нарезки паза (выемки)."""
    op_type: Literal[OperationType.SLOT] = OperationType.SLOT
    length_mm: float
    width_mm: float
    depth_mm: float

    @field_validator("length_mm", mode="before")
    @classmethod
    def _validate_length(cls, v: float) -> float:
        return _positive_nonzero(v, "length_mm")

    @field_validator("width_mm", mode="before")
    @classmethod
    def _validate_width(cls, v: float) -> float:
        return _positive_nonzero(v, "width_mm")

    @field_validator("depth_mm", mode="before")
    @classmethod
    def _validate_depth(cls, v: float) -> float:
        return _positive_nonzero(v, "depth_mm")


class PocketOperation(BaseOperation):
    """Операция фрезеровки кармана (выемки)."""
    op_type: Literal[OperationType.POCKET] = OperationType.POCKET
    width_mm: float
    height_mm: float
    depth_mm: float

    @field_validator("width_mm", mode="before")
    @classmethod
    def _validate_width(cls, v: float) -> float:
        return _positive_nonzero(v, "width_mm")

    @field_validator("height_mm", mode="before")
    @classmethod
    def _validate_height(cls, v: float) -> float:
        return _positive_nonzero(v, "height_mm")

    @field_validator("depth_mm", mode="before")
    @classmethod
    def _validate_depth(cls, v: float) -> float:
        return _positive_nonzero(v, "depth_mm")


# Union type for dispatching
AnyOperation = DrillOperation | SlotOperation | PocketOperation


# ---------------------------------------------------------------------------
# PanelSpec
# ---------------------------------------------------------------------------

class PanelSpec(BaseModel):
    """Описание одной панели со списком операций обработки."""
    id: str
    width_mm: float
    height_mm: float
    thickness_mm: float
    material: str | None = None
    operations: list[AnyOperation] = Field(default_factory=list)

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        return _nonempty_id(v)

    @field_validator("width_mm", "height_mm", mode="before")
    @classmethod
    def _validate_dimensions(cls, v: float) -> float:
        return _positive_nonzero(v, "размер панели")

    @field_validator("thickness_mm", mode="before")
    @classmethod
    def _validate_thickness(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("thickness_mm не может быть nan или inf")
        if v <= 0:
            raise ValueError(f"thickness_mm должно быть > 0, получено {v}")
        return v

    @model_validator(mode="after")
    def _check_unique_op_ids(self) -> PanelSpec:
        ids = [op.id for op in self.operations]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            raise ValueError(f"дублирующиеся id операций: {dupes}")
        return self


# ---------------------------------------------------------------------------
# ManufacturingSpec
# ---------------------------------------------------------------------------

class ManufacturingSpec(BaseModel):
    """Верхний уровень: набор панелей с единицами и версией формата."""
    spec_version: str = "1.0"
    units: Unit = Unit.MM
    panels: list[PanelSpec] = Field(default_factory=list)

    @field_validator("spec_version", mode="before")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("spec_version не может быть пустым")
        return v

    @model_validator(mode="after")
    def _check_unique_panel_ids(self) -> ManufacturingSpec:
        ids = [p.id for p in self.panels]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            raise ValueError(f"дублирующиеся id панелей: {dupes}")
        return self
    def to_canonical_dict(self) -> dict:
        """Детерминированное dict-представление: панели и операции отсортированы по id.

        Не мутирует исходную модель — создаёт новые dict.
        """
        raw = self.model_dump(mode="json", exclude_none=True)
        panels = sorted(raw.get("panels", []), key=lambda p: p.get("id", ""))
        return {
            **raw,
            "panels": [
                {
                    **panel,
                    "operations": sorted(
                        panel.get("operations", []),
                        key=lambda op: op.get("id", ""),
                    ),
                }
                for panel in panels
            ],
        }
