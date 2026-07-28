"""
Калькулятор панелей для корпусной мебели.

Использует технические стандарты из etl_pipeline/knowledge_base/tech_standards_ldsp_16mm.md:
- Конфирмат 7x50: отступ от края 8мм, от передней кромки 50мм
- Система 32: шаг 32мм, отступ 37мм
- Кромка: 0.4мм скрытая, 1мм видимая, 2мм фасад
- Зазор съёмной полки: 3мм с каждой стороны
- Зазор ящика: 26мм ВСЕГО (13мм с каждой стороны)
- Провис полки: макс 600мм без усиления
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from api.constants import (
    DEFAULT_BACK_SLOT_DEPTH_MM,
    DEFAULT_DRAWER_GAP_MM,
    DEFAULT_EDGE_THICKNESS_MM,
    DEFAULT_FACADE_EDGE_THICKNESS_MM,
    DEFAULT_FACADE_GAP_MM,
    DEFAULT_HARDWARE_MOUNT,
    DEFAULT_LEGS_HEIGHT_MM,
    DEFAULT_MAX_SHELF_SPAN_MM,
    DEFAULT_SHELF_GAP_MM,
    DEFAULT_THICKNESS_MM,
    DEFAULT_TIE_BEAM_HEIGHT_MM,
    DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
)

# Task 6: typed domain imports for returning contract values (not dicts) from calculators
from api.manufacturing.contracts import (
    DrillOperation,
    Face,
    SlotOperation,
)
from api.hardware_rules import calculate_hinge_count

log = logging.getLogger(__name__)


# =============================================================================
# Константы присадки (мебельные стандарты ЛДСП 16мм)
# =============================================================================

# Конфирмат 5x50 (евровинт)
CONFIRMAT_DIAMETER_MM = 5.0           # Диаметр сверла
CONFIRMAT_DEPTH_FACE_MM = 11.0        # Глубина в пласть
CONFIRMAT_DEPTH_EDGE_MM = 50.0        # Глубина в торец
CONFIRMAT_EDGE_OFFSET_MM = 8.0        # Отступ от края панели
CONFIRMAT_FRONT_OFFSET_MM = 50.0      # Отступ от передней кромки
CONFIRMAT_SPACING_MM = 128.0          # Расстояние между конфирматами (кратно 32)

# Система 32 (полкодержатели, петли)
SYSTEM32_STEP_MM = 32.0               # Шаг отверстий
SYSTEM32_FRONT_OFFSET_MM = 37.0       # Отступ от переднего края
SYSTEM32_DIAMETER_MM = 5.0            # Диаметр под полкодержатель
SYSTEM32_DEPTH_MM = 12.0              # Глубина отверстия

# Петля мебельная (чашка 35мм)
HINGE_CUP_DIAMETER_MM = 35.0          # Диаметр чашки
HINGE_CUP_DEPTH_MM = 12.0             # Глубина фрезеровки
HINGE_EDGE_OFFSET_MM = 22.0           # Отступ от края фасада
HINGE_TOP_BOTTOM_OFFSET_MM = 100.0    # Отступ от верха/низа фасада
# Стандарты цеха по умолчанию. Единственный источник значений — api/constants.py,
# поверх них ложатся настройки конкретного мастера.
FASTENER_DEFAULTS = {
    "bottom_mount": "on_bottom",
    "tie_beam_height_mm": DEFAULT_TIE_BEAM_HEIGHT_MM,
    "facade_gap_mm": DEFAULT_FACADE_GAP_MM,
    "shelf_gap_mm": DEFAULT_SHELF_GAP_MM,
    "legs_height_mm": DEFAULT_LEGS_HEIGHT_MM,
    "fastener_type": "confirmat",
    "hardware_mount": DEFAULT_HARDWARE_MOUNT,
}


def _merge_standards(standards: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(FASTENER_DEFAULTS)
    if standards:
        merged.update({key: value for key, value in standards.items() if value is not None})
    return merged


def _fastener_hole(
    x: float,
    y: float,
    side: str,
    standards: dict[str, Any],
) -> dict:
    if standards["fastener_type"] == "dowel":
        return {
            "x": x, "y": y, "diameter": 8.0, "depth": 24.0,
            "side": side, "hardware_type": "dowel",
        }
    return {
        "x": x, "y": y, "diameter": CONFIRMAT_DIAMETER_MM,
        "depth": CONFIRMAT_DEPTH_FACE_MM if side == "face" else CONFIRMAT_DEPTH_EDGE_MM,
        "side": side, "hardware_type": "confirmat",
    }
def _convert_fasteners(holes: list[dict], standards: dict[str, Any] | None) -> list[dict]:
    settings = _merge_standards(standards)
    if settings["fastener_type"] != "dowel":
        return holes
    return [
        {
            **hole,
            "diameter": 8.0,
            "depth": 24.0,
            "hardware_type": "dowel",
        }
        for hole in holes
        if hole.get("hardware_type") == "confirmat"
    ] + [hole for hole in holes if hole.get("hardware_type") != "confirmat"]

def _generate_bottom_mount_side_holes(
    panel_width: float,
    thickness: float,
    standards: dict[str, Any],
) -> list[dict]:
    """Отверстия в нижнем торце боковины для дна на боковинах."""
    holes = []
    for x in (CONFIRMAT_FRONT_OFFSET_MM, panel_width - CONFIRMAT_FRONT_OFFSET_MM):
        holes.append(_fastener_hole(x, 0, "edge", standards))
    return holes


def _generate_bottom_face_holes(
    panel_width: float,
    panel_depth: float,
    thickness: float,
    standards: dict[str, Any],
) -> list[dict]:
    """Отверстия в пласти дна, когда боковины стоят на нём.

    Конфирмат идёт снизу вверх: сквозь дно в нижний торец боковины. Поэтому
    сверлится именно дно, по два отверстия под каждую боковину, а ответные
    отверстия в торцах боковин делает `_generate_bottom_mount_side_holes`.
    """
    holes = []
    for x in (thickness / 2, panel_width - thickness / 2):
        for y in (CONFIRMAT_FRONT_OFFSET_MM, panel_depth - CONFIRMAT_FRONT_OFFSET_MM):
            holes.append(_fastener_hole(x, y, "face", standards))
    return holes

def _generate_confirmat_holes_for_horizontal(
    panel_width: float,
    panel_height: float,
    thickness: float,
    standards: dict[str, Any] | None = None,
) -> list[dict]:
    """Генерирует крепёжные отверстия в торцах горизонтальной панели."""
    settings = _merge_standards(standards)
    front_offset = CONFIRMAT_FRONT_OFFSET_MM
    usable_depth = panel_height - 2 * front_offset
    y_positions = (
        [front_offset, panel_height - front_offset]
        if usable_depth > CONFIRMAT_SPACING_MM
        else [panel_height / 2]
    )
    holes = []
    for x in (0, panel_width):
        for y in y_positions:
            holes.append(_fastener_hole(x, y, "edge", settings))
    return holes

def _generate_fixed_shelf_holes(
    panel_width: float,
    panel_height: float,
    thickness: float,
    fixed_shelf_count: int,
    standards: dict[str, Any] | None = None,
) -> list[dict]:
    """Ответные отверстия в пласти боковин под конструкционные полки."""
    if fixed_shelf_count <= 0:
        return []
    inner_height = panel_height - 2 * thickness
    y_positions = [
        thickness + inner_height * index / (fixed_shelf_count + 1)
        for index in range(1, fixed_shelf_count + 1)
    ]
    x_positions = [CONFIRMAT_FRONT_OFFSET_MM, panel_width - CONFIRMAT_FRONT_OFFSET_MM]
    holes = [
        {
            "x": x,
            "y": y,
            "diameter": CONFIRMAT_DIAMETER_MM,
            "depth": CONFIRMAT_DEPTH_FACE_MM,
            "side": "face",
            "hardware_type": "confirmat",
        }
        for y in y_positions
        for x in x_positions
    ]
    return _convert_fasteners(holes, standards)


def _generate_confirmat_holes_for_tie_beams_on_side(
    panel_width: float,
    panel_height: float,
    thickness: float,
    beam_height: float,
    standards: dict[str, Any] | None = None,
) -> list[dict]:
    """Отверстия в боковине под передние и задние царги напольной тумбы.

    Царга стоит на ребро у верхнего края: по глубине занимает свою толщину,
    по высоте — `beam_height`. Два конфирмата на стык, разведённые к краям
    планки; на узкой планке, куда два винта не встают, остаётся один по центру.
    Планка 70 мм — рабочий минимум для пары: отступ 20 мм от каждого края.
    """
    holes: list[dict] = []

    edge_offset = 20.0
    if beam_height >= 2 * edge_offset + 20.0:
        y_positions = [
            panel_height - beam_height + edge_offset,
            panel_height - edge_offset,
        ]
    else:
        y_positions = [panel_height - beam_height / 2]

    # Передняя царга прижата к переднему краю, задняя — к заднему.
    x_positions = [thickness / 2, panel_width - thickness / 2]

    for x in x_positions:
        for y in y_positions:
            holes.append({
                "x": x,
                "y": y,
                "diameter": CONFIRMAT_DIAMETER_MM,
                "depth": CONFIRMAT_DEPTH_FACE_MM,
                "side": "face",
                "hardware_type": "confirmat",
            })

    return _convert_fasteners(holes, standards)


def _generate_confirmat_holes_for_side(
    panel_width: float,
    panel_height: float,
    thickness: float,
    top_panel: bool = True,
    bottom_panel: bool = True,
    standards: dict[str, Any] | None = None,
) -> list[dict]:
    """
    Генерирует отверстия под конфирматы для боковины.
    Конфирматы идут в пласть панели сверху и снизу.
    """
    holes = []

    # Отступ от переднего и заднего края
    front_offset = CONFIRMAT_FRONT_OFFSET_MM
    back_offset = CONFIRMAT_FRONT_OFFSET_MM

    # Позиции по глубине (ось X на боковине = глубина корпуса)
    usable_depth = panel_width - front_offset - back_offset
    if usable_depth > CONFIRMAT_SPACING_MM:
        x_positions = [front_offset, panel_width - back_offset]
    else:
        x_positions = [panel_width / 2]

    # Верхние отверстия (под верхнюю панель)
    if top_panel:
        y_top = panel_height - thickness / 2  # Центр верхней панели
        for x in x_positions:
            holes.append({
                "x": x,
                "y": y_top,
                "diameter": CONFIRMAT_DIAMETER_MM,
                "depth": CONFIRMAT_DEPTH_FACE_MM,
                "side": "face",
                "hardware_type": "confirmat",
            })

    # Нижние отверстия (под нижнюю панель)
    if bottom_panel:
        y_bottom = thickness / 2  # Центр нижней панели
        for x in x_positions:
            holes.append({
                "x": x,
                "y": y_bottom,
                "diameter": CONFIRMAT_DIAMETER_MM,
                "depth": CONFIRMAT_DEPTH_FACE_MM,
                "side": "face",
                "hardware_type": "confirmat",
            })

    return _convert_fasteners(holes, standards)


def _generate_shelf_pin_holes(
    panel_width: float,
    panel_height: float,
    thickness: float,
    shelf_count: int,
    bottom_offset: float = 100.0,
    top_offset: float = 100.0,
) -> list[dict]:
    """
    Генерирует ряды отверстий системы 32 для полкодержателей на боковине.
    """
    if shelf_count == 0:
        return []

    holes = []

    # Позиция по X (глубина) — отступ от переднего края
    x_front = SYSTEM32_FRONT_OFFSET_MM
    x_back = panel_width - SYSTEM32_FRONT_OFFSET_MM

    # Диапазон по Y (высота) — где могут быть полки
    y_start = bottom_offset + thickness
    y_end = panel_height - top_offset - thickness

    # Генерируем отверстия с шагом 32мм
    y = y_start
    while y <= y_end:
        # Передний ряд
        holes.append({
            "x": x_front,
            "y": y,
            "diameter": SYSTEM32_DIAMETER_MM,
            "depth": SYSTEM32_DEPTH_MM,
            "side": "face",
            "hardware_type": "shelf_pin",
        })
        # Задний ряд
        holes.append({
            "x": x_back,
            "y": y,
            "diameter": SYSTEM32_DIAMETER_MM,
            "depth": SYSTEM32_DEPTH_MM,
            "side": "face",
            "hardware_type": "shelf_pin",
        })
        y += SYSTEM32_STEP_MM

    return holes


def _generate_hinge_cup_holes(panel_height: float, hinge_count: int) -> list[dict]:
    """Чашки петель на фасаде: ряд по краю навески, отступы от верха и низа.

    Сверлится именно фасад — в боковину идёт ответная планка, а не чашка.
    """
    if hinge_count <= 0:
        return []

    if hinge_count == 1:
        y_positions = [panel_height / 2]
    else:
        top = HINGE_TOP_BOTTOM_OFFSET_MM
        bottom = panel_height - HINGE_TOP_BOTTOM_OFFSET_MM
        step = (bottom - top) / (hinge_count - 1)
        y_positions = [top + step * i for i in range(hinge_count)]

    return [
        {
            "x": HINGE_EDGE_OFFSET_MM,
            "y": y,
            "diameter": HINGE_CUP_DIAMETER_MM,
            "depth": HINGE_CUP_DEPTH_MM,
            "side": "face",
            "hardware_type": "hinge_cup",
        }
        for y in y_positions
    ]


def _generate_hinge_mount_holes(cup_holes: list[dict]) -> list[dict]:
    """Ответные планки: два отверстия ø5 на каждую петлю."""
    holes = []
    for cup in cup_holes:
        for offset in (-16.0, 16.0):
            holes.append({
                "x": HINGE_EDGE_OFFSET_MM + offset,
                "y": cup["y"],
                "diameter": 5.0,
                "depth": 12.0,
                "side": "face",
                "hardware_type": "hinge_mount",
            })
    return holes
def _facade_panels(
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    door_count: int,
    gap_mm: float = DEFAULT_FACADE_GAP_MM,
    facade_color: str | None = None,
) -> list[PanelSpec]:
    """Накладные фасады корпуса с присадкой под петли."""
    if door_count <= 0:
        return []

    facade_width = (width_mm - gap_mm) / door_count
    facade_height = height_mm - gap_mm
    hinge_count = calculate_hinge_count(facade_height)
    cups = _generate_hinge_cup_holes(facade_height, hinge_count)
    color_note = f", декор фасада: {facade_color}" if facade_color else ""

    return [
        PanelSpec(
            name="Фасад" if door_count == 1 else f"Фасад {index + 1}",
            width_mm=round(facade_width, 1),
            height_mm=round(facade_height, 1),
            thickness_mm=thickness_mm,
            edge_front=True,
            edge_back=True,
            edge_top=True,
            edge_bottom=True,
            edge_thickness_mm=DEFAULT_FACADE_EDGE_THICKNESS_MM,
            notes=f"Накладной фасад, зазор {gap_mm:.0f} мм, петель {hinge_count}{color_note}",
            drilling_points=list(cups),
        )
        for index in range(door_count)
    ]


def _append_facades(
    result: CalculationResult,
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    door_count: int,
    gap_mm: float,
    include_facades: bool,
    facade_color: str | None,
) -> None:
    if not include_facades:
        result.warnings.append("Фасады в раскрой не включены; петли остаются в фурнитуре")
        return
    result.panels.extend(_facade_panels(
        width_mm, height_mm, thickness_mm, door_count, gap_mm, facade_color,
    ))


@dataclass
class PanelSpec:
    """Спецификация панели."""
    name: str
    width_mm: float
    height_mm: float
    thickness_mm: float = DEFAULT_THICKNESS_MM
    quantity: int = 1

    edge_front: bool = False
    edge_back: bool = False
    edge_top: bool = False
    edge_bottom: bool = False
    edge_thickness_mm: float = DEFAULT_EDGE_THICKNESS_MM

    has_slot_for_back: bool = False
    notes: str = ""

    # Координаты присадки (для G-code)
    drilling_points: list[dict] = field(default_factory=list)

    @property
    def area_m2(self) -> float:
        """Площадь панели в м2."""
        return (self.width_mm * self.height_mm * self.quantity) / 1_000_000

    @property
    def edge_length_mm(self) -> float:
        """Длина кромки в мм."""
        length = 0.0
        if self.edge_front:
            length += self.height_mm
        if self.edge_back:
            length += self.height_mm
        if self.edge_top:
            length += self.width_mm
        if self.edge_bottom:
            length += self.width_mm
        return length * self.quantity

    def to_dict(self) -> dict[str, Any]:
        """Конвертация в словарь для API."""
        return {
            "name": self.name,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "thickness_mm": self.thickness_mm,
            "quantity": self.quantity,
            "edge_front": self.edge_front,
            "edge_back": self.edge_back,
            "edge_top": self.edge_top,
            "edge_bottom": self.edge_bottom,
            "edge_thickness_mm": self.edge_thickness_mm,
            "has_slot_for_back": self.has_slot_for_back,
            "notes": self.notes,
            "drilling_points": self.drilling_points,
        }


@dataclass
class CalculationResult:
    """Результат расчёта панелей."""
    cabinet_type: str
    width_mm: int
    height_mm: int
    depth_mm: int

    panels: list[PanelSpec] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_panels(self) -> int:
        return sum(p.quantity for p in self.panels)

    @property
    def total_area_m2(self) -> float:
        return sum(p.area_m2 for p in self.panels)

    @property
    def edge_length_m(self) -> float:
        return sum(p.edge_length_mm for p in self.panels) / 1000


# ============================================================================
# Шаблоны корпусов
# ============================================================================

class CabinetTemplate:
    """Базовый шаблон корпуса."""

    def __init__(
        self,
        width_mm: int,
        height_mm: int,
        depth_mm: int,
        thickness_mm: float = DEFAULT_THICKNESS_MM,
        edge_thickness_mm: float = DEFAULT_EDGE_THICKNESS_MM,
        standards: dict[str, Any] | None = None,
        include_facades: bool = True,
        facade_color: str | None = None,
    ):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.depth_mm = depth_mm
        self.thickness_mm = thickness_mm
        self.edge_thickness_mm = edge_thickness_mm
        self.include_facades = include_facades
        self.facade_color = facade_color
        self.standards = _merge_standards(standards)
 
    @property
    def inner_width(self) -> float:
        """Внутренняя ширина (между боковинами)."""
        return self.width_mm - 2 * self.thickness_mm

    @property
    def inner_height(self) -> float:
        """Внутренняя высота."""
        return self.height_mm - 2 * self.thickness_mm

    @property
    def inner_depth(self) -> float:
        """Внутренняя глубина (минус задняя стенка)."""
        return self.depth_mm - DEFAULT_BACK_SLOT_DEPTH_MM

    def calculate(
        self,
        shelf_count: int = 1,
        fixed_shelf_count: int = 0,
        door_count: int = 1,
        drawer_count: int = 0,
    ) -> CalculationResult:
        """Рассчитать панели. Переопределяется в подклассах."""
        raise NotImplementedError


class WallCabinetTemplate(CabinetTemplate):
    """Навесной шкаф."""

    def calculate(
        self,
        shelf_count: int = 1,
        fixed_shelf_count: int = 0,
        door_count: int = 1,
        drawer_count: int = 0,
    ) -> CalculationResult:
        result = CalculationResult(
            cabinet_type="wall",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        # Боковины (2 шт)
        # Высота = полная высота корпуса
        # Глубина = глубина корпуса - паз под заднюю стенку
        side_depth = self.depth_mm - DEFAULT_BACK_SLOT_DEPTH_MM

        # Присадка для боковин: конфирматы под верх/низ + полкодержатели
        side_drilling = _generate_confirmat_holes_for_side(
            panel_width=side_depth,
            panel_height=self.height_mm,
            thickness=self.thickness_mm,
            top_panel=True,
            bottom_panel=True,
        )
        if shelf_count > 0:
            side_drilling.extend(_generate_shelf_pin_holes(
                panel_width=side_depth,
                panel_height=self.height_mm,
                thickness=self.thickness_mm,
                shelf_count=shelf_count,
            ))
        side_drilling.extend(_generate_fixed_shelf_holes(
            panel_width=side_depth,
            panel_height=self.height_mm,
            thickness=self.thickness_mm,
            fixed_shelf_count=fixed_shelf_count,
        ))

        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,  # Видимая кромка спереди
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            notes="Паз под ДВП 4x10мм",
            drilling_points=list(side_drilling),  # independent copy (Task 6)
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            notes="Паз под ДВП 4x10мм",
            drilling_points=list(side_drilling),  # independent copy, not shared mutable (Task 6)
        ))

        # Верх и низ
        # Ширина = ширина корпуса - 2 x толщина боковин
        horizontal_width = self.inner_width
        horizontal_depth = side_depth

        # Присадка для горизонтальных панелей: конфирматы в торцы
        horizontal_drilling = _generate_confirmat_holes_for_horizontal(
            panel_width=horizontal_width,
            panel_height=horizontal_depth,
            thickness=self.thickness_mm,
        )

        result.panels.append(PanelSpec(
            name="Верх",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
            drilling_points=list(horizontal_drilling),
        ))

        result.panels.append(PanelSpec(
            name="Низ",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
            drilling_points=list(horizontal_drilling),
        ))

        if fixed_shelf_count > 0:
            result.panels.append(PanelSpec(
                name="Полка конструкционная",
                width_mm=horizontal_width,
                height_mm=horizontal_depth,
                thickness_mm=self.thickness_mm,
                quantity=fixed_shelf_count,
                edge_front=True,
                edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
                notes="Конструкционная полка в распор",
                drilling_points=list(horizontal_drilling),
            ))

        # Полки (съёмные)
        if shelf_count > 0:
            # Ширина полки = внутренняя ширина - 2 x зазор
            shelf_width = horizontal_width - 2 * DEFAULT_SHELF_GAP_MM
            shelf_depth = horizontal_depth - DEFAULT_SHELF_GAP_MM  # Зазор сзади

            result.panels.append(PanelSpec(
                name="Полка",
                width_mm=shelf_width,
                height_mm=shelf_depth,
                thickness_mm=self.thickness_mm,
                quantity=shelf_count,
                edge_front=True,
                edge_back=True,
                edge_top=True,
                edge_bottom=True,
                edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
                notes="Съёмная полка на полкодержателях",
            ))

            # Проверка провиса
            if shelf_width > DEFAULT_MAX_SHELF_SPAN_MM:
                result.warnings.append(
                    f"Полка {shelf_width:.0f}мм может провиснуть (макс {DEFAULT_MAX_SHELF_SPAN_MM:.0f}мм). "
                    "Рекомендуется вертикальная перегородка."
                )

        # Фасады: у навесного шкафа они накладные, петли сверлятся в них.
        _append_facades(
            result, self.width_mm, self.height_mm, self.thickness_mm, door_count,
            self.standards["facade_gap_mm"], self.include_facades, self.facade_color,
        )

        return result


class BaseCabinetTemplate(CabinetTemplate):
    """Напольная тумба (с дном, без верха - накрывается столешницей)."""

    def calculate(
        self,
        shelf_count: int = 1,
        fixed_shelf_count: int = 0,
        door_count: int = 1,
        drawer_count: int = 0,
    ) -> CalculationResult:
        result = CalculationResult("base", self.width_mm, self.height_mm, self.depth_mm)
        side_depth = self.depth_mm - DEFAULT_BACK_SLOT_DEPTH_MM
        on_bottom = self.standards["bottom_mount"] == "on_bottom"
        side_height = self.height_mm - self.thickness_mm if on_bottom else self.height_mm
        side_drilling = _generate_confirmat_holes_for_side(
            side_depth, side_height, self.thickness_mm,
            top_panel=False, bottom_panel=not on_bottom, standards=self.standards,
        )
        if on_bottom:
            side_drilling.extend(_generate_bottom_mount_side_holes(
                side_depth, self.thickness_mm, self.standards,
            ))
        side_drilling.extend(_generate_confirmat_holes_for_tie_beams_on_side(
            side_depth, side_height, self.thickness_mm,
            self.standards["tie_beam_height_mm"], self.standards,
        ))
        side_drilling.extend(_generate_fixed_shelf_holes(
            side_depth, side_height, self.thickness_mm, fixed_shelf_count, self.standards,
        ))
        for name in ("Боковина левая", "Боковина правая"):
            result.panels.append(PanelSpec(
                name=name, width_mm=side_depth, height_mm=side_height,
                thickness_mm=self.thickness_mm, edge_front=True,
                edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
                has_slot_for_back=True, drilling_points=list(side_drilling),
            ))
        horizontal_width = self.width_mm if on_bottom else self.inner_width
        bottom_drilling = (
            _generate_bottom_face_holes(
                horizontal_width, side_depth, self.thickness_mm, self.standards,
            )
            if on_bottom
            else _generate_confirmat_holes_for_horizontal(
                horizontal_width, side_depth, self.thickness_mm, self.standards,
            )
        )
        result.panels.append(PanelSpec(
            name="Дно", width_mm=horizontal_width, height_mm=side_depth,
            thickness_mm=self.thickness_mm, has_slot_for_back=True,
            drilling_points=bottom_drilling,
        ))
        tie_height = self.standards["tie_beam_height_mm"]
        tie_drilling = _generate_confirmat_holes_for_horizontal(
            self.inner_width, tie_height, self.thickness_mm, self.standards,
        )
        for name in ("Царга передняя", "Царга задняя"):
            result.panels.append(PanelSpec(
                name=name, width_mm=self.inner_width, height_mm=tie_height,
                thickness_mm=self.thickness_mm, drilling_points=list(tie_drilling),
            ))
        if fixed_shelf_count > 0:
            fixed_drilling = _generate_confirmat_holes_for_horizontal(
                self.inner_width, side_depth, self.thickness_mm, self.standards,
            )
            result.panels.append(PanelSpec(
                name="Полка конструкционная",
                width_mm=self.inner_width,
                height_mm=side_depth,
                thickness_mm=self.thickness_mm,
                quantity=fixed_shelf_count,
                edge_front=True,
                edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
                notes="Конструкционная полка в распор",
                drilling_points=fixed_drilling,
            ))
        if shelf_count > 0:
            shelf_gap = self.standards["shelf_gap_mm"]
            result.panels.append(PanelSpec(
                name="Полка", width_mm=self.inner_width - 2 * shelf_gap,
                height_mm=side_depth - shelf_gap, thickness_mm=self.thickness_mm,
                quantity=shelf_count, edge_front=True, edge_back=True, edge_top=True, edge_bottom=True,
                edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            ))
        _append_facades(
            result, self.width_mm, self.height_mm, self.thickness_mm, door_count,
            self.standards["facade_gap_mm"], self.include_facades, self.facade_color,
        )
        if self.standards["legs_height_mm"] > 0:
            legs = self.standards["legs_height_mm"]
            result.warnings.append(
                f"Корпус {self.height_mm:.0f} мм плюс ножки {legs:.0f} мм — "
                f"высота до столешницы {self.height_mm + legs:.0f} мм"
            )
        return result
class BaseSinkCabinetTemplate(CabinetTemplate):
    """Тумба под мойку (без дна, только связи)."""

    def calculate(
        self,
        shelf_count: int = 0,
        fixed_shelf_count: int = 0,
        door_count: int = 2,
        drawer_count: int = 0,
    ) -> CalculationResult:
        result = CalculationResult(
            cabinet_type="base_sink",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        side_depth = self.depth_mm - DEFAULT_BACK_SLOT_DEPTH_MM

        # Присадка для боковин: только конфирматы под связи (нет дна и верха)
        # Минимальная присадка - конфирматы под верхние и нижние связи
        side_drilling: list[dict] = []
        # Верхние связи
        for x in [CONFIRMAT_FRONT_OFFSET_MM, side_depth - CONFIRMAT_FRONT_OFFSET_MM]:
            side_drilling.append({
                "x": x,
                "y": self.height_mm - self.thickness_mm / 2,
                "diameter": CONFIRMAT_DIAMETER_MM,
                "depth": CONFIRMAT_DEPTH_FACE_MM,
                "side": "face",
                "hardware_type": "confirmat",
            })
        # Нижние связи
        for x in [CONFIRMAT_FRONT_OFFSET_MM, side_depth - CONFIRMAT_FRONT_OFFSET_MM]:
            side_drilling.append({
                "x": x,
                "y": self.thickness_mm / 2,
                "diameter": CONFIRMAT_DIAMETER_MM,
                "depth": CONFIRMAT_DEPTH_FACE_MM,
                "side": "face",
                "hardware_type": "confirmat",
            })

        # Боковины
        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            drilling_points=list(side_drilling),
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            drilling_points=list(side_drilling),
        ))

        horizontal_width = self.inner_width

        # Только связи (царги), без дна
        result.panels.append(PanelSpec(
            name="Связь верхняя передняя",
            width_mm=horizontal_width,
            height_mm=self.standards["tie_beam_height_mm"],
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Связь верхняя задняя",
            width_mm=horizontal_width,
            height_mm=self.standards["tie_beam_height_mm"],
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Связь нижняя передняя",
            width_mm=horizontal_width,
            height_mm=self.standards["tie_beam_height_mm"],
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Связь нижняя задняя",
            width_mm=horizontal_width,
            height_mm=self.standards["tie_beam_height_mm"],
            thickness_mm=self.thickness_mm,
        ))


        # Фасады тумбы под мойку.
        _append_facades(
            result, self.width_mm, self.height_mm, self.thickness_mm, door_count,
            self.standards["facade_gap_mm"], self.include_facades, self.facade_color,
        )
        result.warnings.append("Тумба под мойку - учтите вырез под сифон и подводку воды")
        return result



class DrawerCabinetTemplate(CabinetTemplate):
    """Тумба с ящиками."""

    def calculate(
        self,
        shelf_count: int = 0,
        fixed_shelf_count: int = 0,
        door_count: int = 0,
        drawer_count: int = 3,
    ) -> CalculationResult:
        if drawer_count < 1:
            drawer_count = 3  # По умолчанию 3 ящика

        result = CalculationResult(
            cabinet_type="drawer",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        side_depth = self.depth_mm - DEFAULT_BACK_SLOT_DEPTH_MM
        on_bottom = self.standards["bottom_mount"] == "on_bottom"
        side_height = self.height_mm - self.thickness_mm if on_bottom else self.height_mm

        # Присадка для боковин: конфирматы под дно и под царги
        # (полкодержателей нет — тут ящики).
        side_drilling = _generate_confirmat_holes_for_side(
            panel_width=side_depth,
            panel_height=side_height,
            thickness=self.thickness_mm,
            top_panel=False,
            bottom_panel=not on_bottom,
            standards=self.standards,
        )
        if on_bottom:
            side_drilling.extend(_generate_bottom_mount_side_holes(
                side_depth, self.thickness_mm, self.standards,
            ))
        side_drilling.extend(_generate_confirmat_holes_for_tie_beams_on_side(
            panel_width=side_depth,
            panel_height=side_height,
            thickness=self.thickness_mm,
            beam_height=self.standards["tie_beam_height_mm"],
            standards=self.standards,
        ))

        # Боковины
        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=side_height,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            drilling_points=list(side_drilling),
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=side_height,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            drilling_points=list(side_drilling),
        ))

        horizontal_width = self.width_mm if on_bottom else self.inner_width
        horizontal_depth = side_depth

        # Присадка для дна: при боковинах на дне сверлится пласть дна,
        # при вкладном дне — его торцы.
        bottom_drilling = (
            _generate_bottom_face_holes(
                horizontal_width, horizontal_depth, self.thickness_mm, self.standards,
            )
            if on_bottom
            else _generate_confirmat_holes_for_horizontal(
                panel_width=horizontal_width,
                panel_height=horizontal_depth,
                thickness=self.thickness_mm,
                standards=self.standards,
            )
        )

        # Дно корпуса
        result.panels.append(PanelSpec(
            name="Дно",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
            drilling_points=bottom_drilling,
        ))

        # Царги: та же присадка в торцы, что и у напольной тумбы.
        tie_beam_drilling = _generate_confirmat_holes_for_horizontal(
            panel_width=horizontal_width,
            panel_height=self.standards["tie_beam_height_mm"],
            thickness=self.thickness_mm,
            standards=self.standards,
        )

        result.panels.append(PanelSpec(
            name="Царга передняя",
            width_mm=horizontal_width,
            height_mm=self.standards["tie_beam_height_mm"],
            thickness_mm=self.thickness_mm,
            drilling_points=list(tie_beam_drilling),
        ))

        result.panels.append(PanelSpec(
            name="Царга задняя",
            width_mm=horizontal_width,
            height_mm=self.standards["tie_beam_height_mm"],
            thickness_mm=self.thickness_mm,
            drilling_points=list(tie_beam_drilling),
        ))

        # Ящики
        # Ширина ящика = внутренняя ширина - 26мм (зазор под направляющие)
        drawer_outer_width = horizontal_width - DEFAULT_DRAWER_GAP_MM
        drawer_inner_width = drawer_outer_width - 2 * self.thickness_mm

        # Высота ящика: равномерно делим внутреннюю высоту
        drawer_front_height = (self.height_mm - 2 * self.thickness_mm) / drawer_count - 4  # 4мм зазор между фасадами

        # Глубина боковины ящика
        drawer_depth = horizontal_depth - 50  # Минус 50мм на зазор сзади

        for i in range(drawer_count):
            num = i + 1

            # Фасад ящика
            result.panels.append(PanelSpec(
                name=f"Фасад ящика {num}",
                width_mm=self.width_mm - 4,  # Зазоры по бокам
                height_mm=drawer_front_height,
                thickness_mm=self.thickness_mm,
                edge_front=True,
                edge_back=True,
                edge_top=True,
                edge_bottom=True,
                edge_thickness_mm=DEFAULT_FACADE_EDGE_THICKNESS_MM,
            ))

            # Боковины ящика (2 шт)
            result.panels.append(PanelSpec(
                name=f"Боковина ящика {num}",
                width_mm=drawer_depth,
                height_mm=drawer_front_height - 30,  # Ниже фасада
                thickness_mm=self.thickness_mm,
                quantity=2,
            ))

            # Передняя и задняя стенки ящика (2 шт)
            result.panels.append(PanelSpec(
                name=f"Стенка ящика {num}",
                width_mm=drawer_inner_width,
                height_mm=drawer_front_height - 30,
                thickness_mm=self.thickness_mm,
                quantity=2,
            ))

            # Дно ящика (ДВП)
            result.panels.append(PanelSpec(
                name=f"Дно ящика {num} (ДВП)",
                width_mm=drawer_outer_width - 10,
                height_mm=drawer_front_height - 30,
                thickness_mm=3.0,
                notes="ДВП 3мм",
            ))

        return result


class TallCabinetTemplate(CabinetTemplate):
    """Пенал (высокий шкаф)."""

    def calculate(
        self,
        shelf_count: int = 4,
        fixed_shelf_count: int = 0,
        door_count: int = 2,
        drawer_count: int = 0,
    ) -> CalculationResult:
        result = CalculationResult(
            cabinet_type="tall",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        side_depth = self.depth_mm - DEFAULT_BACK_SLOT_DEPTH_MM

        # Присадка для боковин пенала: конфирматы + полкодержатели
        side_drilling = _generate_confirmat_holes_for_side(
            panel_width=side_depth,
            panel_height=self.height_mm,
            thickness=self.thickness_mm,
            top_panel=True,
            bottom_panel=True,
        )
        if shelf_count > 0:
            side_drilling.extend(_generate_shelf_pin_holes(
                panel_width=side_depth,
                panel_height=self.height_mm,
                thickness=self.thickness_mm,
                shelf_count=shelf_count,
            ))
        side_drilling.extend(_generate_fixed_shelf_holes(
            panel_width=side_depth,
            panel_height=self.height_mm,
            thickness=self.thickness_mm,
            fixed_shelf_count=fixed_shelf_count,
        ))
        
        # Боковины

        # Боковины
        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            drilling_points=list(side_drilling),
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            drilling_points=list(side_drilling),
        ))

        horizontal_width = self.inner_width
        horizontal_depth = side_depth

        # Присадка для горизонтальных панелей
        horizontal_drilling = _generate_confirmat_holes_for_horizontal(
            panel_width=horizontal_width,
            panel_height=horizontal_depth,
            thickness=self.thickness_mm,
        )

        # Верх и низ
        result.panels.append(PanelSpec(
            name="Верх",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
            drilling_points=list(horizontal_drilling),
        ))

        result.panels.append(PanelSpec(
            name="Низ",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
            drilling_points=list(horizontal_drilling),
        ))

        # Полки
        if shelf_count > 0:
            shelf_width = horizontal_width - 2 * DEFAULT_SHELF_GAP_MM
            shelf_depth = horizontal_depth - DEFAULT_SHELF_GAP_MM

        if fixed_shelf_count > 0:
            result.panels.append(PanelSpec(
                name="Полка конструкционная",
                width_mm=horizontal_width,
                height_mm=horizontal_depth,
                thickness_mm=self.thickness_mm,
                quantity=fixed_shelf_count,
                edge_front=True,
                edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
                notes="Конструкционная полка в распор",
                drilling_points=list(horizontal_drilling),
            ))

            result.panels.append(PanelSpec(
                name="Полка",
                width_mm=shelf_width,
                height_mm=shelf_depth,
                thickness_mm=self.thickness_mm,
                quantity=shelf_count,
                edge_front=True,
                edge_back=True,
                edge_top=True,
                edge_bottom=True,
                edge_thickness_mm=DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
            ))

            if shelf_width > DEFAULT_MAX_SHELF_SPAN_MM:
                result.warnings.append(f"Полка {shelf_width:.0f}мм может провиснуть")

        # Для высоких шкафов рекомендуем крепление к стене
        if self.height_mm > 2000:
            result.warnings.append("Пенал выше 2м - обязательно крепление к стене")

        # Фасады пенала: высокие створки, петель больше.
        _append_facades(
            result, self.width_mm, self.height_mm, self.thickness_mm, door_count,
            self.standards["facade_gap_mm"], self.include_facades, self.facade_color,
        )

        return result


# ============================================================================
# Фабрика шаблонов
# ============================================================================

CABINET_TEMPLATES = {
    "wall": WallCabinetTemplate,
    "base": BaseCabinetTemplate,
    "base_sink": BaseSinkCabinetTemplate,
    "drawer": DrawerCabinetTemplate,
    "tall": TallCabinetTemplate,
}


def _apply_standard_fasteners(result: CalculationResult, standards: dict[str, Any]) -> None:
    settings = _merge_standards(standards)
    for panel in result.panels:
        panel.drilling_points = _convert_fasteners(panel.drilling_points, settings)
    cups = [
        point for panel in result.panels
        for point in panel.drilling_points
        if point.get("hardware_type") == "hinge_cup"
    ]
    mounts = _generate_hinge_mount_holes(cups) if settings["hardware_mount"] == "euro_screw" else []
    for panel in result.panels:
        if "боковина" not in panel.name.lower() or "ящика" in panel.name.lower():
            continue
        if settings["hardware_mount"] != "euro_screw":
            panel.drilling_points = [
                point for point in panel.drilling_points
                if point.get("hardware_type") not in {"hinge_mount", "slide"}
            ]
        panel.drilling_points.extend(mounts)

def calculate_panels(
    cabinet_type: str,
    width_mm: int,
    height_mm: int,
    depth_mm: int,
    thickness_mm: float = DEFAULT_THICKNESS_MM,
    edge_thickness_mm: float = DEFAULT_EDGE_THICKNESS_MM,
    shelf_count: int = 1,
    fixed_shelf_count: int = 0,
    door_count: int = 1,
    drawer_count: int = 0,
    standards: dict[str, Any] | None = None,
    include_facades: bool = True,
    facade_color: str | None = None,
) -> CalculationResult:
    """
    Рассчитать панели для корпусной мебели.

    Args:
        cabinet_type: Тип корпуса (wall, base, base_sink, drawer, tall)
        width_mm: Ширина корпуса
        height_mm: Высота корпуса
        depth_mm: Глубина корпуса
        thickness_mm: Толщина материала
        edge_thickness_mm: Толщина кромки по умолчанию
        shelf_count: Количество полок
        door_count: Количество дверей
        drawer_count: Количество ящиков

    Returns:
        CalculationResult с панелями и предупреждениями
    """
    template_class = CABINET_TEMPLATES.get(cabinet_type)

    if not template_class:
        raise ValueError(f"Неизвестный тип корпуса: {cabinet_type}. "
                        f"Доступные: {', '.join(CABINET_TEMPLATES.keys())}")

    template = template_class(
        width_mm=width_mm,
        height_mm=height_mm,
        depth_mm=depth_mm,
        thickness_mm=thickness_mm,
        edge_thickness_mm=edge_thickness_mm,
        standards=standards,
        include_facades=include_facades,
        facade_color=facade_color,
    )

    log.info(f"[PanelCalculator] Расчёт {cabinet_type} {width_mm}x{height_mm}x{depth_mm}")

    result = template.calculate(
        shelf_count=shelf_count,
        fixed_shelf_count=fixed_shelf_count,
        door_count=door_count,
        drawer_count=drawer_count,
    )
    if (
        fixed_shelf_count <= 0
        and (height_mm > 1600 or width_mm > 900)
    ):
        result.warnings.append(
            "Корпус такого размера обычно держат конструкционной полкой — "
            "совет технолога."
        )
    _apply_standard_fasteners(result, template.standards)

    log.info(f"[PanelCalculator] Результат: {result.total_panels} панелей, "
             f"{result.total_area_m2:.2f} м2, {len(result.warnings)} предупреждений")

    return result


# =============================================================================
# Task 6: typed domain value helpers (return contracts types, no loose dicts)
# Calculators now provide typed ops for spec_builder. Convert at boundaries only.
# =============================================================================

def _dict_hole_to_drill_op(
    hole: dict,
    face: Face,
    op_prefix: str,
    hardware_sku: str | None = None,
    template: str | None = None,
    source: str = "rule",
    idx: int = 0,
) -> DrillOperation:
    """Convert legacy hole dict from panel calc into typed DrillOperation.

    Records SKU/template/source for hardware traceability (encoded in id for compatibility).
    """
    sku = hardware_sku or "generic"
    tmpl = template or "std"
    x = float(hole.get("x", 0))
    y = float(hole.get("y", 0))
    diam = float(hole.get("diameter", 5.0))
    depth = float(hole.get("depth", 12.0))
    op_id = f"{op_prefix}_{sku}_{tmpl}_{source}_{idx}"
    return DrillOperation(
        id=op_id,
        face=face,
        x_mm=x,
        y_mm=y,
        diameter_mm=diam,
        depth_mm=depth,
    )


def build_typed_confirmat_ops_for_side(
    panel_width: float,
    panel_height: float,
    thickness: float,
    face: Face = Face.LEFT,
    hardware_sku: str | None = "confirmat_5x50",
    template: str = "confirmat_std",
    source: str = "rule",
) -> list[DrillOperation]:
    """Return typed confirmat drill ops for side panel (from panel_calculator logic)."""
    raw = _generate_confirmat_holes_for_side(
        panel_width=panel_width,
        panel_height=panel_height,
        thickness=thickness,
        top_panel=True,
        bottom_panel=True,
    )
    ops: list[DrillOperation] = []
    for i, h in enumerate(raw):
        ops.append(_dict_hole_to_drill_op(h, face, "drill_confirmat_side", hardware_sku, template, source, i))
    return ops


def build_typed_shelf_pin_ops(
    panel_width: float,
    panel_height: float,
    thickness: float,
    shelf_count: int,
    face: Face = Face.LEFT,
    hardware_sku: str | None = "shelf_pin_5mm",
    template: str = "system32",
    source: str = "rule",
) -> list[DrillOperation]:
    """Return typed shelf pin ops."""
    raw = _generate_shelf_pin_holes(
        panel_width=panel_width,
        panel_height=panel_height,
        thickness=thickness,
        shelf_count=shelf_count,
    )
    ops: list[DrillOperation] = []
    for i, h in enumerate(raw):
        ops.append(_dict_hole_to_drill_op(h, face, "drill_shelf_pin", hardware_sku, template, source, i))
    return ops


def build_typed_back_slot(
    height_mm: float,
    depth_mm: float,
    slot_width: float,
    slot_depth: float,
    face: Face = Face.BACK,
    hardware_sku: str | None = None,
    template: str = "back_dvp_slot",
    source: str = "design",
) -> SlotOperation:
    """Return typed slot for back panel (used on sides)."""
    # Position roughly on the inner face
    x = depth_mm - slot_depth / 2
    y = height_mm / 2
    op_id = f"slot_back_{template}_{source}_1"
    return SlotOperation(
        id=op_id,
        face=face,
        x_mm=x,
        y_mm=y,
        length_mm=height_mm,
        width_mm=slot_width,
        depth_mm=slot_depth,
    )
