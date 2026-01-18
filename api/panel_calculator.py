"""
Калькулятор панелей для корпусной мебели.

Использует технические стандарты из etl_pipeline/knowledge_base/tech_standards_ldsp_16mm.md:
- Конфирмат 5x40: отступ от края 8мм, от передней кромки 50мм
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

log = logging.getLogger(__name__)


# ============================================================================
# Константы из технических стандартов
# ============================================================================

# Толщина материалов
DEFAULT_THICKNESS_MM = 16.0
DEFAULT_EDGE_THICKNESS_MM = 0.4  # Скрытая кромка
VISIBLE_EDGE_THICKNESS_MM = 1.0  # Видимая кромка
FACADE_EDGE_THICKNESS_MM = 2.0  # Фасады

# Зазоры
SHELF_GAP_MM = 3.0  # Зазор съёмной полки с каждой стороны (итого 6мм)
DRAWER_TOTAL_GAP_MM = 26.0  # Зазор для ящика ВСЕГО (не с каждой стороны!)
BACK_PANEL_INSET_MM = 10.0  # Отступ задней стенки от края

# Паз под заднюю стенку
BACK_SLOT_WIDTH_MM = 4.0
BACK_SLOT_DEPTH_MM = 10.0

# Провис полки
MAX_SHELF_SPAN_MM = 600.0  # Максимальная ширина без провиса

# Связи (царги) для тумб под мойку
TIE_BEAM_HEIGHT_MM = 100.0


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
    ):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.depth_mm = depth_mm
        self.thickness_mm = thickness_mm
        self.edge_thickness_mm = edge_thickness_mm

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
        return self.depth_mm - BACK_SLOT_DEPTH_MM

    def calculate(self, shelf_count: int = 1, door_count: int = 1, drawer_count: int = 0) -> CalculationResult:
        """Рассчитать панели. Переопределяется в подклассах."""
        raise NotImplementedError


class WallCabinetTemplate(CabinetTemplate):
    """Навесной шкаф."""

    def calculate(self, shelf_count: int = 1, door_count: int = 1, drawer_count: int = 0) -> CalculationResult:
        result = CalculationResult(
            cabinet_type="wall",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        # Боковины (2 шт)
        # Высота = полная высота корпуса
        # Глубина = глубина корпуса - паз под заднюю стенку
        side_depth = self.depth_mm - BACK_SLOT_DEPTH_MM

        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,  # Видимая кромка спереди
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            notes="Паз под ДВП 4x10мм",
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
            notes="Паз под ДВП 4x10мм",
        ))

        # Верх и низ
        # Ширина = ширина корпуса - 2 x толщина боковин
        horizontal_width = self.inner_width
        horizontal_depth = side_depth

        result.panels.append(PanelSpec(
            name="Верх",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
        ))

        result.panels.append(PanelSpec(
            name="Низ",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
        ))

        # Полки (съёмные)
        if shelf_count > 0:
            # Ширина полки = внутренняя ширина - 2 x зазор
            shelf_width = horizontal_width - 2 * SHELF_GAP_MM
            shelf_depth = horizontal_depth - SHELF_GAP_MM  # Зазор сзади

            result.panels.append(PanelSpec(
                name="Полка",
                width_mm=shelf_width,
                height_mm=shelf_depth,
                thickness_mm=self.thickness_mm,
                quantity=shelf_count,
                edge_front=True,
                edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
                notes="Съёмная полка на полкодержателях",
            ))

            # Проверка провиса
            if shelf_width > MAX_SHELF_SPAN_MM:
                result.warnings.append(
                    f"Полка {shelf_width:.0f}мм может провиснуть (макс {MAX_SHELF_SPAN_MM:.0f}мм). "
                    "Рекомендуется вертикальная перегородка."
                )

        return result


class BaseCabinetTemplate(CabinetTemplate):
    """Напольная тумба (с дном, без верха - накрывается столешницей)."""

    def calculate(self, shelf_count: int = 1, door_count: int = 1, drawer_count: int = 0) -> CalculationResult:
        result = CalculationResult(
            cabinet_type="base",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        side_depth = self.depth_mm - BACK_SLOT_DEPTH_MM

        # Боковины (2 шт)
        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        horizontal_width = self.inner_width
        horizontal_depth = side_depth

        # Дно
        result.panels.append(PanelSpec(
            name="Дно",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
        ))

        # Верхние планки (царги) вместо сплошного верха
        result.panels.append(PanelSpec(
            name="Царга передняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Царга задняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        # Полки
        if shelf_count > 0:
            shelf_width = horizontal_width - 2 * SHELF_GAP_MM
            shelf_depth = horizontal_depth - SHELF_GAP_MM

            result.panels.append(PanelSpec(
                name="Полка",
                width_mm=shelf_width,
                height_mm=shelf_depth,
                thickness_mm=self.thickness_mm,
                quantity=shelf_count,
                edge_front=True,
                edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            ))

            if shelf_width > MAX_SHELF_SPAN_MM:
                result.warnings.append(
                    f"Полка {shelf_width:.0f}мм может провиснуть"
                )

        return result


class BaseSinkCabinetTemplate(CabinetTemplate):
    """Тумба под мойку (без дна, только связи)."""

    def calculate(self, shelf_count: int = 0, door_count: int = 2, drawer_count: int = 0) -> CalculationResult:
        result = CalculationResult(
            cabinet_type="base_sink",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        side_depth = self.depth_mm - BACK_SLOT_DEPTH_MM

        # Боковины
        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        horizontal_width = self.inner_width

        # Только связи (царги), без дна
        result.panels.append(PanelSpec(
            name="Связь верхняя передняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Связь верхняя задняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Связь нижняя передняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Связь нижняя задняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        result.warnings.append("Тумба под мойку - учтите вырез под сифон и подводку воды")

        return result


class DrawerCabinetTemplate(CabinetTemplate):
    """Тумба с ящиками."""

    def calculate(self, shelf_count: int = 0, door_count: int = 0, drawer_count: int = 3) -> CalculationResult:
        if drawer_count < 1:
            drawer_count = 3  # По умолчанию 3 ящика

        result = CalculationResult(
            cabinet_type="drawer",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        side_depth = self.depth_mm - BACK_SLOT_DEPTH_MM

        # Боковины
        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        horizontal_width = self.inner_width
        horizontal_depth = side_depth

        # Дно корпуса
        result.panels.append(PanelSpec(
            name="Дно",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
        ))

        # Царги
        result.panels.append(PanelSpec(
            name="Царга передняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        result.panels.append(PanelSpec(
            name="Царга задняя",
            width_mm=horizontal_width,
            height_mm=TIE_BEAM_HEIGHT_MM,
            thickness_mm=self.thickness_mm,
        ))

        # Ящики
        # Ширина ящика = внутренняя ширина - 26мм (зазор под направляющие)
        drawer_outer_width = horizontal_width - DRAWER_TOTAL_GAP_MM
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
                edge_thickness_mm=FACADE_EDGE_THICKNESS_MM,
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
                height_mm=drawer_depth - 10,
                thickness_mm=3.0,
                notes="ДВП 3мм",
            ))

        return result


class TallCabinetTemplate(CabinetTemplate):
    """Пенал (высокий шкаф)."""

    def calculate(self, shelf_count: int = 4, door_count: int = 2, drawer_count: int = 0) -> CalculationResult:
        result = CalculationResult(
            cabinet_type="tall",
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            depth_mm=self.depth_mm,
        )

        side_depth = self.depth_mm - BACK_SLOT_DEPTH_MM

        # Боковины
        result.panels.append(PanelSpec(
            name="Боковина левая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        result.panels.append(PanelSpec(
            name="Боковина правая",
            width_mm=side_depth,
            height_mm=self.height_mm,
            thickness_mm=self.thickness_mm,
            edge_front=True,
            edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            has_slot_for_back=True,
        ))

        horizontal_width = self.inner_width
        horizontal_depth = side_depth

        # Верх и низ
        result.panels.append(PanelSpec(
            name="Верх",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
        ))

        result.panels.append(PanelSpec(
            name="Низ",
            width_mm=horizontal_width,
            height_mm=horizontal_depth,
            thickness_mm=self.thickness_mm,
            has_slot_for_back=True,
        ))

        # Полки
        if shelf_count > 0:
            shelf_width = horizontal_width - 2 * SHELF_GAP_MM
            shelf_depth = horizontal_depth - SHELF_GAP_MM

            result.panels.append(PanelSpec(
                name="Полка",
                width_mm=shelf_width,
                height_mm=shelf_depth,
                thickness_mm=self.thickness_mm,
                quantity=shelf_count,
                edge_front=True,
                edge_thickness_mm=VISIBLE_EDGE_THICKNESS_MM,
            ))

            if shelf_width > MAX_SHELF_SPAN_MM:
                result.warnings.append(f"Полка {shelf_width:.0f}мм может провиснуть")

        # Для высоких шкафов рекомендуем крепление к стене
        if self.height_mm > 2000:
            result.warnings.append("Пенал выше 2м - обязательно крепление к стене")

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


def calculate_panels(
    cabinet_type: str,
    width_mm: int,
    height_mm: int,
    depth_mm: int,
    thickness_mm: float = DEFAULT_THICKNESS_MM,
    edge_thickness_mm: float = DEFAULT_EDGE_THICKNESS_MM,
    shelf_count: int = 1,
    door_count: int = 1,
    drawer_count: int = 0,
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
    )

    log.info(f"[PanelCalculator] Расчёт {cabinet_type} {width_mm}x{height_mm}x{depth_mm}")

    result = template.calculate(
        shelf_count=shelf_count,
        door_count=door_count,
        drawer_count=drawer_count,
    )

    log.info(f"[PanelCalculator] Результат: {result.total_panels} панелей, "
             f"{result.total_area_m2:.2f} м2, {len(result.warnings)} предупреждений")

    return result
