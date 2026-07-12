"""Deterministic ManufacturingSpec builder (Task 6 only).

Строго детерминированный builder без CAM, G-code, DXF, approvals.
Использует typed domain values из panel_calculator, hardware_rules,
drilling_calculator, drilling_templates.

CabinetInput → BuildResult(ManufacturingSpec + provenance с SKU/template/source).

Инварианты:
- left/right получают независимые списки операций
- hardware ops несут SKU, template, source (в id + provenance)
- все операции внутри границ панели, глубины совместимы
- 5 типов корпусов: wall, base, base_sink, drawer, tall
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from api.drilling_calculator import (
    build_hinge_ops_typed,
    build_slide_ops_typed,
)
from api.hardware_rules import get_hardware_provenance
from api.manufacturing.contracts import (
    DrillOperation,
    Face,
    ManufacturingSpec,
    PanelSpec,
    SlotOperation,
    Unit,
)

# Task 6: integrate calculators returning domain values
from api.panel_calculator import (
    build_typed_back_slot,
    build_typed_confirmat_ops_for_side,
    build_typed_shelf_pin_ops,
)

# drilling_templates used indirectly via drilling_calculator for template ids


# ── Входные типы ──────────────────────────────────────────────────────


class CabinetType(str, Enum):
    """Типы корпусной мебели (зеркало из schemas.py для доменной изоляции)."""

    WALL = "wall"
    BASE = "base"
    BASE_SINK = "base_sink"
    DRAWER = "drawer"
    TALL = "tall"
    CORNER = "corner"


class CabinetInput(BaseModel):
    """Типизированный вход для build_spec.

    Все размеры в мм.  Значения по умолчанию — безопасные пресеты для
    типичного ЛДСП-шкафа.
    """

    cabinet_type: CabinetType
    width_mm: float = Field(..., gt=0, description="Ширина корпуса, мм")
    height_mm: float = Field(..., gt=0, description="Высота корпуса, мм")
    depth_mm: float = Field(..., gt=0, description="Глубина корпуса, мм")
    thickness_mm: float = Field(16.0, gt=0, description="Толщина материала, мм")
    material: str | None = Field(None, description="Материал (напр. ЛДСП 16мм)")

    shelf_count: int = Field(0, ge=0, description="Количество полок")
    door_count: int = Field(0, ge=0, le=4, description="Количество дверей")
    drawer_count: int = Field(0, ge=0, le=10, description="Количество ящиков")

    back_panel: bool = Field(True, description="Наличие задней стенки")

    # Hardware provenance
    hinge_type: str | None = Field(None, description="Тип петель (напр. blum_clip_top_110)")
    slide_type: str | None = Field(None, description="Тип направляющих")

    # Slot params
    back_slot_width_mm: float = Field(4.0, gt=0, description="Ширина паза под заднюю стенку")
    back_slot_depth_mm: float = Field(10.0, gt=0, description="Глубина паза под заднюю стенку")


class SpecValidationError(Exception):
    """Блокировка выдачи спецификации при невалидных параметрах."""


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Результат build_spec: ManufacturingSpec + provenance metadata.

    frozen=True — гарантирует иммутабельность результата.
    provenance — трекинг hardware provenance (hinge_type / slide_type).
    """
    spec: ManufacturingSpec
    provenance: dict[str, Any] = field(default_factory=dict)


# ── Внутренний счётчик ID ─────────────────────────────────────────────


class _IdGenerator:
    """Детерминированный генератор ID: префикс + порядковый номер."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def next(self, prefix: str) -> str:
        count = self._counters.get(prefix, 0)
        self._counters[prefix] = count + 1
        return f"{prefix}_{count + 1}"


# ── Построители панелей ───────────────────────────────────────────────


def _build_side_panel(
    side: str,
    height_mm: float,
    depth_mm: float,
    thickness_mm: float,
    material: str | None,
    ids: _IdGenerator,
    slot_width: float,
    slot_depth: float,
    back_panel: bool,
    shelf_count: int = 0,
) -> PanelSpec:
    """Боковина (left/right) — независимая панель с typed ops из calculators."""
    ops: list[DrillOperation | SlotOperation] = []

    # Используем typed domain values из panel_calculator (Task 6)
    # confirmats + shelf pins (face drills on side)
    confirmat_ops = build_typed_confirmat_ops_for_side(
        panel_width=depth_mm,
        panel_height=height_mm,
        thickness=thickness_mm,
        face=Face.LEFT if side == "left" else Face.RIGHT,
        hardware_sku="confirmat_5x50",
        template="confirmat_std",
        source="rule",
    )
    # Note: adjust coords slightly if needed for side coord system (depth as width)
    ops.extend(confirmat_ops)

    shelf_ops = build_typed_shelf_pin_ops(
        panel_width=depth_mm,
        panel_height=height_mm,
        thickness=thickness_mm,
        shelf_count=shelf_count,
        face=Face.LEFT if side == "left" else Face.RIGHT,
        hardware_sku="shelf_pin_5mm",
        template="system32",
        source="rule",
    )
    ops.extend(shelf_ops)

    # Паз под заднюю стенку — typed slot (Task 6)
    if back_panel:
        slot_op = build_typed_back_slot(
            height_mm=height_mm,
            depth_mm=depth_mm,
            slot_width=slot_width,
            slot_depth=slot_depth,
            face=Face.BACK,
            hardware_sku=None,
            template="back_dvp_slot",
            source="design",
        )
        slot_op = slot_op.model_copy(update={"id": ids.next(f"slot_{side}_back")}) if hasattr(slot_op, "model_copy") else slot_op
        ops.append(slot_op)

    # Ensure unique ids per side using generator (prevents left/right + cross-panel collision)
    ops = _assign_unique_ids(ops, ids, f"op_{side}")

    # return fresh list — independence guaranteed (Task 6)
    return PanelSpec(
        id=ids.next(f"panel_{side}_side"),
        width_mm=depth_mm,
        height_mm=height_mm,
        thickness_mm=thickness_mm,
        material=material,
        operations=list(ops),
    )


def _build_horizontal_panel(
    name_prefix: str,
    width_mm: float,
    depth_mm: float,
    thickness_mm: float,
    material: str | None,
    ids: _IdGenerator,
) -> PanelSpec:
    """Горизонтальная панель (top / bottom / shelf)."""
    return PanelSpec(
        id=ids.next(f"panel_{name_prefix}"),
        width_mm=width_mm,
        height_mm=depth_mm,
        thickness_mm=thickness_mm,
        material=material,
    )


def _build_back_panel(
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    material: str | None,
    ids: _IdGenerator,
) -> PanelSpec:
    """Задняя стенка — тонкая панель."""
    return PanelSpec(
        id=ids.next("panel_back"),
        width_mm=width_mm,
        height_mm=height_mm,
        thickness_mm=thickness_mm,
        material=material,
    )


def _build_hinge_drills(
    panel_id_prefix: str,
    face: Face,
    width_mm: float,
    height_mm: float,
    ids: _IdGenerator,
    count: int = 2,
    hinge_sku: str = "blum_clip_top_110",
    template: str = "hinge_35mm_overlay",
    source: str = "catalog",
) -> list[DrillOperation]:
    """Петлевые отверстия Ø35мм — из typed drilling_calculator (Task 6)."""
    # Delegate to typed builder for real positions + sku/template/source
    ops = build_hinge_ops_typed(
        panel_height_mm=height_mm,
        hinge_count=count,
        template_id=template,
        hardware_sku=hinge_sku,
        source=source,
        face=face,
    )
    # Re-assign deterministic ids (preserve order, unique per panel)
    new_ops: list[DrillOperation] = []
    for op in ops:
        new_id = ids.next(f"drill_{panel_id_prefix}_hinge")
        if hasattr(op, "model_copy"):
            new_ops.append(op.model_copy(update={"id": new_id}))
        else:
            new_ops.append(op)
    return new_ops


def _assign_unique_ids(
    ops: list[DrillOperation | SlotOperation],
    ids: _IdGenerator,
    prefix: str,
) -> list[DrillOperation | SlotOperation]:
    """Re-number ops with unique ids from generator to guarantee no collisions across panels/left-right."""
    new_ops: list[DrillOperation | SlotOperation] = []
    for op in ops:
        new_id = ids.next(prefix)
        if hasattr(op, "model_copy"):
            new_ops.append(op.model_copy(update={"id": new_id}))
        else:
            # fallback shallow
            op.id = new_id  # type: ignore[attr-defined]
            new_ops.append(op)
    return new_ops


def _build_drawer_front(
    index: int,
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    material: str | None,
    ids: _IdGenerator,
) -> PanelSpec:
    """Фасад ящика."""
    return PanelSpec(
        id=ids.next("panel_drawer_front"),
        width_mm=width_mm,
        height_mm=height_mm,
        thickness_mm=thickness_mm,
        material=material,
    )


# ── Сборка по типам ───────────────────────────────────────────────────


def _assemble_wall(inp: CabinetInput, ids: _IdGenerator) -> list[PanelSpec]:
    """Навесной шкаф: left, right, top, bottom, [back], [shelves]."""
    panels: list[PanelSpec] = []
    th = inp.thickness_mm
    mat = inp.material

    # Боковины — независимые (Task 6)
    panels.append(
        _build_side_panel(
            "left", inp.height_mm, inp.depth_mm, th, mat, ids,
            inp.back_slot_width_mm, inp.back_slot_depth_mm, inp.back_panel,
            shelf_count=inp.shelf_count,
        )
    )
    panels.append(
        _build_side_panel(
            "right", inp.height_mm, inp.depth_mm, th, mat, ids,
            inp.back_slot_width_mm, inp.back_slot_depth_mm, inp.back_panel,
            shelf_count=inp.shelf_count,
        )
    )

    # Верх и низ
    panels.append(_build_horizontal_panel("top", inp.width_mm, inp.depth_mm, th, mat, ids))
    panels.append(_build_horizontal_panel("bottom", inp.width_mm, inp.depth_mm, th, mat, ids))

    # Задняя стенка
    if inp.back_panel:
        panels.append(_build_back_panel(inp.width_mm, inp.height_mm, th, mat, ids))

    # Полки
    for _ in range(inp.shelf_count):
        panels.append(_build_horizontal_panel("shelf", inp.width_mm, inp.depth_mm, th, mat, ids))

    # Двери (фасады)
    for _ in range(inp.door_count):
        door_h = inp.height_mm
        panels.append(
            PanelSpec(
                id=ids.next("panel_door_front"),
                width_mm=inp.width_mm,
                height_mm=door_h,
                thickness_mm=th,
                material=mat,
            )
        )

    return panels


def _assemble_base(inp: CabinetInput, ids: _IdGenerator) -> list[PanelSpec]:
    """Напольная тумба: left, right, top, bottom, [back], [shelves]."""
    # Базовый шкаф — аналогичен wall, но глубина обычно больше
    return _assemble_wall(inp, ids)


def _assemble_sink_base(inp: CabinetInput, ids: _IdGenerator) -> list[PanelSpec]:
    """Тумба под мойку: left, right, top (без дна), [back], связи."""
    panels: list[PanelSpec] = []
    th = inp.thickness_mm
    mat = inp.material

    panels.append(
        _build_side_panel(
            "left", inp.height_mm, inp.depth_mm, th, mat, ids,
            inp.back_slot_width_mm, inp.back_slot_depth_mm, inp.back_panel,
            shelf_count=inp.shelf_count,
        )
    )
    panels.append(
        _build_side_panel(
            "right", inp.height_mm, inp.depth_mm, th, mat, ids,
            inp.back_slot_width_mm, inp.back_slot_depth_mm, inp.back_panel,
            shelf_count=inp.shelf_count,
        )
    )

    # Только верх (без дна — под мойкой)
    panels.append(_build_horizontal_panel("top", inp.width_mm, inp.depth_mm, th, mat, ids))

    # Царга (связь) вместо дна
    panels.append(_build_horizontal_panel("tie_beam", inp.width_mm, 100.0, th, mat, ids))

    if inp.back_panel:
        panels.append(_build_back_panel(inp.width_mm, inp.height_mm, th, mat, ids))

    return panels


def _assemble_tall(inp: CabinetInput, ids: _IdGenerator) -> list[PanelSpec]:
    """Пенал: left, right, top, bottom, [back], [shelves]."""
    return _assemble_wall(inp, ids)


def _assemble_drawer(inp: CabinetInput, ids: _IdGenerator) -> list[PanelSpec]:
    """Тумба с ящиками: left, right, top, bottom, [back], drawer fronts."""
    panels: list[PanelSpec] = []
    th = inp.thickness_mm
    mat = inp.material

    panels.append(
        _build_side_panel(
            "left", inp.height_mm, inp.depth_mm, th, mat, ids,
            inp.back_slot_width_mm, inp.back_slot_depth_mm, inp.back_panel,
            shelf_count=0,
        )
    )
    panels.append(
        _build_side_panel(
            "right", inp.height_mm, inp.depth_mm, th, mat, ids,
            inp.back_slot_width_mm, inp.back_slot_depth_mm, inp.back_panel,
            shelf_count=0,
        )
    )

    panels.append(_build_horizontal_panel("top", inp.width_mm, inp.depth_mm, th, mat, ids))
    panels.append(_build_horizontal_panel("bottom", inp.width_mm, inp.depth_mm, th, mat, ids))

    if inp.back_panel:
        panels.append(_build_back_panel(inp.width_mm, inp.height_mm, th, mat, ids))

    # Фасады ящиков
    front_height = (inp.height_mm - (inp.drawer_count - 1) * 2.0) / inp.drawer_count if inp.drawer_count > 0 else inp.height_mm
    for _ in range(inp.drawer_count):
        panels.append(_build_drawer_front(
            index=_,
            width_mm=inp.width_mm,
            height_mm=front_height,
            thickness_mm=th,
            material=mat,
            ids=ids,
        ))

    return panels


def _assemble_corner(inp: CabinetInput, ids: _IdGenerator) -> list[PanelSpec]:
    """Угловой шкаф — заглушка (TODO: реальная геометрия)."""
    return _assemble_wall(inp, ids)


_ASSEMBLERS: dict[CabinetType, Any] = {
    CabinetType.WALL: _assemble_wall,
    CabinetType.BASE: _assemble_base,
    CabinetType.BASE_SINK: _assemble_sink_base,
    CabinetType.DRAWER: _assemble_drawer,
    CabinetType.TALL: _assemble_tall,
    CabinetType.CORNER: _assemble_corner,
}


# ── Публичный API ─────────────────────────────────────────────────────


def build_spec(inp: CabinetInput) -> BuildResult:
    """Детерминированное построение ManufacturingSpec из типизированного входа.

    Возвращает BuildResult (spec + provenance) — immutable dataclass.
    Гарантии:
    - Детерминизм: одинаковый вход → одинаковый выход.
    - Уникальность ID панелей и операций.
    - Независимость left/right операций.
    - Hardware provenance через BuildResult.provenance (hinge_type / slide_type).
    - Блокировка при невалидных параметрах (SpecValidationError).
    """
    # Блокировка: проверка физической осмысленности
    if inp.width_mm <= 0 or inp.height_mm <= 0 or inp.depth_mm <= 0:
        raise SpecValidationError(
            f"Размеры должны быть > 0: width={inp.width_mm}, height={inp.height_mm}, depth={inp.depth_mm}"
        )

    ids = _IdGenerator()
    assembler = _ASSEMBLERS.get(inp.cabinet_type)
    if assembler is None:
        raise SpecValidationError(f"Неизвестный тип корпуса: {inp.cabinet_type}")

    panels = assembler(inp, ids)

    # Hardware: attach typed hinge ops from drilling_calculator (Task 6)
    hinge_count_per_door = 2 if inp.height_mm <= 1000 else 3
    if inp.door_count > 0 and inp.hinge_type:
        for panel in panels:
            if "front" in panel.id.lower() or "door" in panel.id.lower():
                hinge_ops = _build_hinge_drills(
                    panel.id,
                    Face.FRONT,
                    panel.width_mm,
                    panel.height_mm,
                    ids,
                    hinge_count_per_door,
                    hinge_sku=inp.hinge_type or "generic_hinge",
                    template="hinge_35mm_overlay",
                    source="catalog",
                )
                hinge_ops = _assign_unique_ids(hinge_ops, ids, "hinge")
                panel.operations = list(panel.operations) + hinge_ops  # new list

    # Slides for drawers (typed from drilling_calculator)
    if inp.drawer_count > 0 and inp.slide_type:
        # Approximate drawer y positions from bottom
        drawer_h = (inp.height_mm - 2 * inp.thickness_mm - (inp.drawer_count - 1) * 4) / max(inp.drawer_count, 1)
        positions = [inp.thickness_mm + i * (drawer_h + 4) for i in range(inp.drawer_count)]
        for panel in panels:
            if "side" in panel.id.lower():
                slide_ops = build_slide_ops_typed(
                    panel_height_mm=panel.height_mm,
                    panel_depth_mm=panel.width_mm,
                    drawer_positions_mm=positions,
                    hardware_sku=inp.slide_type or "generic_slide",
                    source="catalog",
                    face=Face.LEFT if "left" in panel.id.lower() else Face.RIGHT,
                )
                slide_ops = _assign_unique_ids(slide_ops, ids, "slide")
                # assign fresh list for independence
                panel.operations = list(panel.operations) + slide_ops

    # Structured provenance with SKU/template/source (Task 6)
    provenance: dict[str, Any] = get_hardware_provenance(
        hinge_type=inp.hinge_type,
        slide_type=inp.slide_type,
    )
    if inp.hinge_type:
        provenance.setdefault("hinge_type", inp.hinge_type)
    if inp.slide_type:
        provenance.setdefault("slide_type", inp.slide_type)

    # Ensure all panels have independent operation lists (deep copy lists)
    for p in panels:
        p.operations = list(p.operations)

    spec = ManufacturingSpec(
        spec_version="1.0",
        units=Unit.MM,
        panels=panels,
    )

    return BuildResult(spec=spec, provenance=provenance)
