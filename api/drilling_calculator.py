"""
Калькулятор координат присадки для DXF.

Генерирует точные координаты отверстий для:
- Петель на фасадах
- Направляющих на боковинах

Координаты используются в dxf_generator.py для отрисовки слоёв DRILL_*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from api.drilling_templates import (
    HINGE_TEMPLATES,
    SLIDE_TEMPLATES,
    HingeTemplate,
    SlideTemplate,
    get_hinge_template,
    get_slide_template,
)
from api.hardware_rules import (
    calculate_hinge_count,
    calculate_hinge_positions,
    calculate_slide_length,
)


@dataclass
class DrillPoint:
    """Точка сверления."""
    x: float  # Координата X (мм) от левого края панели
    y: float  # Координата Y (мм) от нижнего края панели
    diameter: float  # Диаметр отверстия (мм)
    depth: float  # Глубина сверления (мм)
    layer: str  # DXF слой (DRILL_V_35, DRILL_V_5, DRILL_H_4)
    hardware_id: str = ""  # ID связанной фурнитуры для highlight в UI
    hardware_type: Literal["hinge_cup", "hinge_mount", "slide"] = "hinge_cup"
    notes: str = ""


@dataclass
class DrillingResult:
    """Результат расчёта присадки для панели."""
    panel_name: str
    panel_width_mm: float
    panel_height_mm: float
    drill_points: list[DrillPoint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def calculate_hinge_drill_points(
    panel_height_mm: float,
    hinge_count: int | None = None,
    template_id: str = "hinge_35mm_overlay",
    hardware_id: str = "",
    top_margin_mm: float = 100.0,
    bottom_margin_mm: float = 100.0,
) -> list[DrillPoint]:
    """
    Рассчитать координаты присадки для петель на фасаде.

    Петли располагаются по левому краю фасада (x = edge_offset_mm).
    Y-координаты распределяются равномерно с отступами от краёв.

    Args:
        panel_height_mm: Высота фасада
        hinge_count: Количество петель (если None — рассчитывается автоматически)
        template_id: ID шаблона петли
        hardware_id: ID для связи с UI
        top_margin_mm: Отступ от верха
        bottom_margin_mm: Отступ от низа

    Returns:
        Список точек сверления
    """
    template = get_hinge_template(template_id)
    if template is None:
        template = HINGE_TEMPLATES["hinge_35mm_overlay"]

    # Количество петель
    if hinge_count is None:
        hinge_count = calculate_hinge_count(panel_height_mm)

    # Позиции петель (от верха)
    positions_from_top = calculate_hinge_positions(
        panel_height_mm, hinge_count, top_margin_mm, bottom_margin_mm
    )

    points: list[DrillPoint] = []

    for i, y_from_top in enumerate(positions_from_top):
        # Конвертируем Y от верха в Y от низа (для DXF)
        y_from_bottom = panel_height_mm - y_from_top

        # Центр чашки петли
        cup_x = template.edge_offset_mm
        cup_y = y_from_bottom

        points.append(DrillPoint(
            x=cup_x,
            y=cup_y,
            diameter=template.cup_diameter_mm,
            depth=template.cup_depth_mm,
            layer=template.dxf_layer_cup,
            hardware_id=f"{hardware_id}_hinge_{i+1}",
            hardware_type="hinge_cup",
            notes=f"Чашка петли #{i+1}",
        ))

        # Крепёжные отверстия
        for j, hole in enumerate(template.mounting_holes):
            points.append(DrillPoint(
                x=cup_x + hole.dx_mm,
                y=cup_y + hole.dy_mm,
                diameter=hole.diameter_mm,
                depth=hole.depth_mm,
                layer=template.dxf_layer_mount,
                hardware_id=f"{hardware_id}_hinge_{i+1}_mount_{j+1}",
                hardware_type="hinge_mount",
                notes=f"Крепёж петли #{i+1}",
            ))

    return points


def calculate_slide_drill_points(
    panel_height_mm: float,
    panel_depth_mm: float,
    drawer_positions_mm: list[float],
    template_id: str = "slide_ball_h45",
    hardware_id: str = "",
    front_margin_mm: float = 37.0,  # Отступ от фасадной кромки
) -> list[DrillPoint]:
    """
    Рассчитать координаты присадки для направляющих на боковине.

    Направляющие крепятся горизонтально на внутренней стороне боковины.
    Отверстия располагаются по линии с шагом 32мм (система 32).

    Args:
        panel_height_mm: Высота боковины
        panel_depth_mm: Глубина боковины (= глубина корпуса)
        drawer_positions_mm: Y-позиции ящиков от низа боковины
        template_id: ID шаблона направляющих
        hardware_id: ID для связи с UI
        front_margin_mm: Отступ от переднего края

    Returns:
        Список точек сверления
    """
    template = get_slide_template(template_id)
    if template is None:
        template = SLIDE_TEMPLATES["slide_ball_h45"]

    # Длина направляющих
    slide_length = calculate_slide_length(panel_depth_mm)

    # Количество отверстий на направляющую
    # От переднего отступа до конца направляющих с шагом 32мм
    available_length = slide_length - front_margin_mm
    hole_count = max(2, int(available_length / template.hole_spacing_mm) + 1)

    points: list[DrillPoint] = []

    for drawer_idx, drawer_y in enumerate(drawer_positions_mm):
        # Y линии крепления = низ ящика + offset от шаблона
        line_y = drawer_y + template.line_offset_from_bottom_mm

        # Отверстия вдоль линии
        for hole_idx in range(hole_count):
            hole_x = front_margin_mm + hole_idx * template.hole_spacing_mm

            # Проверяем, не выходит ли за пределы панели
            if hole_x > panel_depth_mm - 20:
                break

            points.append(DrillPoint(
                x=hole_x,
                y=line_y,
                diameter=template.hole_diameter_mm,
                depth=template.hole_depth_mm,
                layer=template.dxf_layer,
                hardware_id=f"{hardware_id}_slide_{drawer_idx+1}_{hole_idx+1}",
                hardware_type="slide",
                notes=f"Направляющая ящика #{drawer_idx+1}",
            ))

    return points


def calculate_drilling_for_facade(
    width_mm: float,
    height_mm: float,
    hinge_template_id: str = "hinge_35mm_overlay",
    hinge_count: int | None = None,
) -> DrillingResult:
    """
    Рассчитать присадку для фасада (двери).

    Args:
        width_mm: Ширина фасада
        height_mm: Высота фасада
        hinge_template_id: Шаблон петли
        hinge_count: Количество петель (auto если None)

    Returns:
        DrillingResult с координатами
    """
    warnings = []

    # Проверки
    if height_mm > 2200:
        warnings.append("Высота фасада >2200мм: проверьте конструкцию")

    drill_points = calculate_hinge_drill_points(
        panel_height_mm=height_mm,
        hinge_count=hinge_count,
        template_id=hinge_template_id,
        hardware_id="facade",
    )

    return DrillingResult(
        panel_name="Фасад",
        panel_width_mm=width_mm,
        panel_height_mm=height_mm,
        drill_points=drill_points,
        warnings=warnings,
    )


def calculate_drilling_for_side_panel(
    height_mm: float,
    depth_mm: float,
    drawer_count: int,
    drawer_height_mm: float = 150.0,
    bottom_offset_mm: float = 50.0,
    slide_template_id: str = "slide_ball_h45",
) -> DrillingResult:
    """
    Рассчитать присадку для боковины с ящиками.

    Args:
        height_mm: Высота боковины
        depth_mm: Глубина боковины
        drawer_count: Количество ящиков
        drawer_height_mm: Высота одного ящика
        bottom_offset_mm: Отступ от низа до первого ящика
        slide_template_id: Шаблон направляющих

    Returns:
        DrillingResult с координатами
    """
    warnings = []

    # Расчёт позиций ящиков
    drawer_positions = []
    for i in range(drawer_count):
        y = bottom_offset_mm + i * drawer_height_mm
        if y + drawer_height_mm > height_mm:
            warnings.append(f"Ящик #{i+1} не помещается по высоте")
            break
        drawer_positions.append(y)

    drill_points = calculate_slide_drill_points(
        panel_height_mm=height_mm,
        panel_depth_mm=depth_mm,
        drawer_positions_mm=drawer_positions,
        template_id=slide_template_id,
        hardware_id="side_panel",
    )

    return DrillingResult(
        panel_name="Боковина",
        panel_width_mm=depth_mm,  # Для боковины width = depth
        panel_height_mm=height_mm,
        drill_points=drill_points,
        warnings=warnings,
    )
