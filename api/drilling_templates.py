"""
Шаблоны присадки для мебельной фурнитуры.

Координаты опираются на общеотраслевую европейскую систему 32.
Точные размеры конкретной модели подтверждаются техкартой производителя.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

# Версия шаблонов нужна для отслеживания происхождения координат.
TEMPLATE_VERSION = "2026-07-v1"


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
    hinge_type: Literal["overlay", "half_overlay", "inset", "corner_45", "mini"]
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
    slide_type: Literal["ball_h35", "ball_h45", "roller", "concealed_full"]
    profile_height_mm: float
    load_capacity_kg: float
    # Отступ линии крепления от низа боковины
    line_offset_from_bottom_mm: float
    # Передний отступ сетки: типовое значение системы 32, сверять с техкартой.
    front_edge_offset_mm: float = 37.0
    hole_diameter_mm: float = 4.0
    hole_spacing_mm: float = 32.0  # Шаг между отверстиями (система 32)
    hole_depth_mm: float = 12.0
    dxf_layer: str = "DRILL_H_4"


# ═══════════════════════════════════════════════════════════════════════════
# ПЕТЛИ — Шаблоны присадки
# ═══════════════════════════════════════════════════════════════════════════

HINGE_TEMPLATES: dict[str, HingeTemplate] = {
    # Накладная: отступ 21,5 мм, глубина 12 мм — типовые 35 мм системы 32;
    # конкретную чашку сверять с техкартой производителя.
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
    # Полунакладная: около 22 мм и глубина 12 мм — типовая система 32;
    # смещение ответной планки уточнять по техкарте производителя.
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
    # Вкладная: около 22 мм, глубина 12 мм, другая ответная планка — типовая
    # практика системы 32; точный монтаж уточнять по техкарте производителя.
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
    # 45°: отступ 21,5 мм и глубина 12 мм — типовые значения системы 32.
    # Точный угол и ответную планку уточнять по техкарте производителя.
    "hinge_35mm_corner_45": HingeTemplate(
        name="Петля угловая 45° 35мм",
        hinge_type="corner_45",
        cup_diameter_mm=35.0,
        cup_depth_mm=12.0,
        edge_offset_mm=21.5,
        body_offset_mm=37.0,
    ),
    # Mini: чашка 26 мм, глубина 10,5 мм — типовая практика европейской
    # системы 32; точный размер зависит от артикула и техкарты производителя.
    "hinge_26mm_mini": HingeTemplate(
        name="Петля mini 26мм",
        hinge_type="mini",
        cup_diameter_mm=26.0,
        cup_depth_mm=10.5,
        edge_offset_mm=17.5,
        body_offset_mm=32.0,
        dxf_layer_cup="DRILL_V_26",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# НАПРАВЛЯЮЩИЕ — Шаблоны присадки
# ═══════════════════════════════════════════════════════════════════════════

SLIDE_TEMPLATES: dict[str, SlideTemplate] = {
    # H45: типовая сетка системы 32, сверять отступ с техкартой бренда.
    "slide_ball_h45": SlideTemplate(
        name="Направляющие шариковые H45 (45кг)",
        slide_type="ball_h45",
        profile_height_mm=45.0,
        load_capacity_kg=45.0,
        line_offset_from_bottom_mm=22.5,
        front_edge_offset_mm=37.0,
    ),
    # H35: другая высота оси и передний отступ, типовой профиль системы 32.
    "slide_ball_h35": SlideTemplate(
        name="Направляющие шариковые H35 (35кг)",
        slide_type="ball_h35",
        profile_height_mm=35.0,
        load_capacity_kg=35.0,
        line_offset_from_bottom_mm=17.5,
        front_edge_offset_mm=35.0,
    ),
    # Роликовые: типовые 32 мм от края и ось 10 мм; уточнить по техкарте.
    "slide_roller": SlideTemplate(
        name="Направляющие роликовые (20кг)",
        slide_type="roller",
        profile_height_mm=17.0,
        load_capacity_kg=20.0,
        line_offset_from_bottom_mm=10.0,
        front_edge_offset_mm=32.0,
    ),
    # Скрытый полный выдвижение: 39 мм от края и ось 30 мм — типовая
    # система 32; точная присадка зависит от конкретного механизма.
    "slide_concealed_full": SlideTemplate(
        name="Направляющие скрытого монтажа полного выдвижения",
        slide_type="concealed_full",
        profile_height_mm=40.0,
        load_capacity_kg=40.0,
        line_offset_from_bottom_mm=30.0,
        front_edge_offset_mm=39.0,
    ),
}

def get_hinge_template(template_id: str) -> HingeTemplate | None:
    """Получить шаблон петли по ID."""
    return HINGE_TEMPLATES.get(template_id)


def get_slide_template(template_id: str) -> SlideTemplate | None:
    """Получить шаблон направляющих по ID."""
    return SLIDE_TEMPLATES.get(template_id)


def _cup_diameter(params: Mapping[str, object]) -> float | None:
    """Диаметр чашки из карточки: прошлые парсеры писали ключ без единиц."""
    for key in ("cup_diameter_mm", "cup_diameter"):
        try:
            return float(params[key])  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _search_text(position_type: str, params: Mapping[str, object], *keys: str) -> str:
    """Наложение петли и вид направляющей лежат либо в типе, либо в полях карточки."""
    parts = [position_type]
    for key in keys:
        value = params.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).lower().strip()


def get_template_for_position(
    position_type: str, params: Mapping[str, object]
) -> HingeTemplate | SlideTemplate | None:
    """Выбрать шаблон без догадок по типу и диаметру чашки."""
    normalized = position_type.lower().strip()
    if "петл" in normalized:
        diameter = _cup_diameter(params)
        if diameter is None:
            return None
        haystack = _search_text(position_type, params, "mount_type", "name")
        markers = (
            ("полунаклад", "hinge_35mm_half_overlay"),
            ("вклад", "hinge_35mm_inset"),
            ("мини", "hinge_26mm_mini"),
            ("mini", "hinge_26mm_mini"),
            ("наклад", "hinge_35mm_overlay"),
        )
        for marker, template_id in markers:
            if marker in haystack:
                template = get_hinge_template(template_id)
                return template if template and template.cup_diameter_mm == diameter else None
        return None
    slide_haystack = _search_text(position_type, params, "slide_type", "name")
    if any(marker in slide_haystack for marker in ("направля", "шарик", "ролик", "скрыт", "slide")):
        markers = (
            ("скрыт", "slide_concealed_full"),
            ("concealed", "slide_concealed_full"),
            ("ролик", "slide_roller"),
            ("roller", "slide_roller"),
            ("h35", "slide_ball_h35"),
            ("h45", "slide_ball_h45"),
        )
        for marker, template_id in markers:
            if marker in slide_haystack:
                return get_slide_template(template_id)
    return None


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
