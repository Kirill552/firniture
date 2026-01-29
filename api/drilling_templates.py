"""
Шаблоны присадки для мебельной фурнитуры.

Содержит координаты и параметры сверления для:
- Петли 35мм (накладная, полунакладная, вкладная)
- Направляющие шариковые (H35, H45)
- Направляющие роликовые

Источники данных:
- Boyard каталог 2024
- Blum CLIP TOP спецификация
- krona27.ru чертежи
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MountingHole:
    """Крепёжное отверстие относительно центра чашки петли."""
    dx_mm: float  # Смещение по X от центра чашки
    dy_mm: float  # Смещение по Y от центра чашки
    diameter_mm: float = 5.0  # Диаметр под евровинт
    depth_mm: float = 12.0


@dataclass(frozen=True)
class HingeTemplate:
    """Шаблон присадки для петли 35мм."""
    name: str
    hinge_type: Literal["overlay", "half_overlay", "inset"]
    cup_diameter_mm: float = 35.0
    cup_depth_mm: float = 12.0
    edge_offset_mm: float = 21.5  # От края фасада до центра чашки
    mounting_holes: tuple[MountingHole, ...] = (
        MountingHole(dx_mm=0, dy_mm=22.5),   # Верхнее
        MountingHole(dx_mm=0, dy_mm=-22.5),  # Нижнее
    )
    # Смещение на корпусе (от края боковины)
    body_offset_mm: float = 37.0  # Стандарт для накладной
    dxf_layer_cup: str = "DRILL_V_35"
    dxf_layer_mount: str = "DRILL_V_5"


@dataclass(frozen=True)
class SlideTemplate:
    """Шаблон присадки для направляющих."""
    name: str
    slide_type: Literal["ball_h35", "ball_h45", "roller"]
    profile_height_mm: float
    load_capacity_kg: float
    # Отступ линии крепления от низа боковины
    line_offset_from_bottom_mm: float
    hole_diameter_mm: float = 4.0
    hole_spacing_mm: float = 32.0  # Шаг между отверстиями (система 32)
    hole_depth_mm: float = 12.0
    dxf_layer: str = "DRILL_H_4"


# ═══════════════════════════════════════════════════════════════════════════
# ПЕТЛИ — Шаблоны присадки
# ═══════════════════════════════════════════════════════════════════════════

HINGE_TEMPLATES: dict[str, HingeTemplate] = {
    "hinge_35mm_overlay": HingeTemplate(
        name="Петля накладная 35мм",
        hinge_type="overlay",
        cup_diameter_mm=35.0,
        cup_depth_mm=12.0,
        edge_offset_mm=21.5,
        body_offset_mm=37.0,
        mounting_holes=(
            MountingHole(dx_mm=0, dy_mm=22.5, diameter_mm=5.0, depth_mm=12.0),
            MountingHole(dx_mm=0, dy_mm=-22.5, diameter_mm=5.0, depth_mm=12.0),
        ),
    ),
    "hinge_35mm_half_overlay": HingeTemplate(
        name="Петля полунакладная 35мм",
        hinge_type="half_overlay",
        cup_diameter_mm=35.0,
        cup_depth_mm=12.0,
        edge_offset_mm=21.5,
        body_offset_mm=37.0 + 9.5,  # Смещение для полунакладной
        mounting_holes=(
            MountingHole(dx_mm=0, dy_mm=22.5, diameter_mm=5.0, depth_mm=12.0),
            MountingHole(dx_mm=0, dy_mm=-22.5, diameter_mm=5.0, depth_mm=12.0),
        ),
    ),
    "hinge_35mm_inset": HingeTemplate(
        name="Петля вкладная 35мм",
        hinge_type="inset",
        cup_diameter_mm=35.0,
        cup_depth_mm=12.0,
        edge_offset_mm=21.5,
        body_offset_mm=37.0 + 16.0,  # Смещение для вкладной
        mounting_holes=(
            MountingHole(dx_mm=0, dy_mm=22.5, diameter_mm=5.0, depth_mm=12.0),
            MountingHole(dx_mm=0, dy_mm=-22.5, diameter_mm=5.0, depth_mm=12.0),
        ),
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# НАПРАВЛЯЮЩИЕ — Шаблоны присадки
# ═══════════════════════════════════════════════════════════════════════════

SLIDE_TEMPLATES: dict[str, SlideTemplate] = {
    "slide_ball_h45": SlideTemplate(
        name="Направляющие шариковые H45 (45кг)",
        slide_type="ball_h45",
        profile_height_mm=45.0,
        load_capacity_kg=45.0,
        line_offset_from_bottom_mm=22.5,  # Центр профиля H45
        hole_diameter_mm=4.0,
        hole_spacing_mm=32.0,
        hole_depth_mm=12.0,
    ),
    "slide_ball_h35": SlideTemplate(
        name="Направляющие шариковые H35 (35кг)",
        slide_type="ball_h35",
        profile_height_mm=35.0,
        load_capacity_kg=35.0,
        line_offset_from_bottom_mm=17.5,  # Центр профиля H35
        hole_diameter_mm=4.0,
        hole_spacing_mm=32.0,
        hole_depth_mm=12.0,
    ),
    "slide_roller": SlideTemplate(
        name="Направляющие роликовые (20кг)",
        slide_type="roller",
        profile_height_mm=17.0,
        load_capacity_kg=20.0,
        line_offset_from_bottom_mm=10.0,
        hole_diameter_mm=4.0,
        hole_spacing_mm=32.0,
        hole_depth_mm=12.0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═══════════════════════════════════════════════════════════════════════════

def get_hinge_template(template_id: str) -> HingeTemplate | None:
    """Получить шаблон петли по ID."""
    return HINGE_TEMPLATES.get(template_id)


def get_slide_template(template_id: str) -> SlideTemplate | None:
    """Получить шаблон направляющих по ID."""
    return SLIDE_TEMPLATES.get(template_id)


def list_hinge_templates() -> list[dict]:
    """Список всех шаблонов петель для UI."""
    return [
        {
            "id": tid,
            "name": t.name,
            "type": t.hinge_type,
            "cup_diameter_mm": t.cup_diameter_mm,
        }
        for tid, t in HINGE_TEMPLATES.items()
    ]


def list_slide_templates() -> list[dict]:
    """Список всех шаблонов направляющих для UI."""
    return [
        {
            "id": tid,
            "name": t.name,
            "type": t.slide_type,
            "load_capacity_kg": t.load_capacity_kg,
            "profile_height_mm": t.profile_height_mm,
        }
        for tid, t in SLIDE_TEMPLATES.items()
    ]
