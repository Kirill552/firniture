"""Генератор DXF файлов для мебельных панелей.

Создаёт DXF чертежи с раскладкой панелей на листе материала.
Использует ezdxf для рисования; Panel, SheetLayout, PlacedPanel и алгоритмы
размещения живут в ``api.manufacturing.cutting_map`` (Task 9).
"""
from __future__ import annotations

import io

import ezdxf
from ezdxf import units
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace

from api.constants import (
    DEFAULT_GAP_MM,
    DEFAULT_SHEET_HEIGHT_MM,
    DEFAULT_SHEET_WIDTH_MM,
)

# ── Re-export cutting-map types (backward-compat) ──────────────────────
from api.manufacturing.cutting_map import (  # noqa: F401 — public re-export
    RECTPACK_AVAILABLE,
    Panel,
    PlacedPanel,
    SheetLayout,
    _simple_layout,
    optimize_layout,
    optimize_layout_best,
)

# Цвета слоёв (AutoCAD ACI)
LAYER_COLORS = {
    "CONTOUR": 7,      # белый/чёрный — внешний контур
    "EDGE": 1,         # красный — кромка
    "DRILLING": 5,     # синий — присадка (сверление)
    "TEXT": 3,         # зелёный — текстовые метки
    "SHEET": 8,        # серый — граница листа
    # Новые слои для Smart Hardware Rules v1.0
    "DRILL_V_35": 5,   # синий — вертикальное сверление ø35 (чашка петли)
    "DRILL_V_5": 4,    # циан — вертикальное сверление ø5 (крепёж петли)
    "DRILL_H_4": 3,    # зелёный — горизонтальное сверление ø4 (направляющие)
}




def create_dxf_document() -> Drawing:
    """Создаёт новый DXF документ с настройками для мебельного производства."""
    doc = ezdxf.new(dxfversion="R2010")

    # Единицы — миллиметры
    doc.header["$INSUNITS"] = units.MM
    doc.header["$MEASUREMENT"] = 1  # метрическая система

    # Создаём слои
    for layer_name, color in LAYER_COLORS.items():
        doc.layers.add(name=layer_name, color=color)

    return doc


def draw_panel(
    msp: Modelspace,
    panel: Panel,
    x: float,
    y: float,
    rotated: bool = False,
) -> None:
    """Рисует панель на чертеже."""
    w = panel.height_mm if rotated else panel.width_mm
    h = panel.width_mm if rotated else panel.height_mm

    # 1. Внешний контур (CONTOUR)
    points = [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
        (x, y),  # замыкаем
    ]
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "CONTOUR"})

    # 2. Кромка (EDGE) — красные линии вдоль сторон с кромкой
    edge_offset = 2.0  # отступ для визуализации кромки

    if panel.edge_bottom:
        msp.add_line(
            (x, y - edge_offset),
            (x + w, y - edge_offset),
            dxfattribs={"layer": "EDGE"}
        )
    if panel.edge_top:
        msp.add_line(
            (x, y + h + edge_offset),
            (x + w, y + h + edge_offset),
            dxfattribs={"layer": "EDGE"}
        )
    if panel.edge_left:
        msp.add_line(
            (x - edge_offset, y),
            (x - edge_offset, y + h),
            dxfattribs={"layer": "EDGE"}
        )
    if panel.edge_right:
        msp.add_line(
            (x + w + edge_offset, y),
            (x + w + edge_offset, y + h),
            dxfattribs={"layer": "EDGE"}
        )

    # 3. Присадка (DRILLING) — круги для отверстий
    for hole in panel.drilling_points:
        hx = hole.get("x", 0)
        hy = hole.get("y", 0)
        diameter = hole.get("diameter", 5)
        layer = hole.get("layer", "DRILLING")

        # Координаты отверстия относительно панели
        if rotated:
            abs_x = x + hy
            abs_y = y + (panel.width_mm - hx)
        else:
            abs_x = x + hx
            abs_y = y + hy

        msp.add_circle(
            center=(abs_x, abs_y),
            radius=diameter / 2,
            dxfattribs={"layer": layer}
        )

        # Аннотация с размерами (для оператора)
        depth = hole.get("depth", 12)
        if diameter >= 10:  # Только для крупных отверстий
            msp.add_text(
                f"ø{diameter:.0f}×{depth:.0f}",
                dxfattribs={
                    "layer": "TEXT",
                    "height": 4,
                    "insert": (abs_x + diameter / 2 + 2, abs_y),
                }
            )

    # 4. Текстовая метка (TEXT)
    text_height = min(w, h) * 0.05  # 5% от меньшей стороны
    text_height = max(8, min(text_height, 20))  # от 8 до 20 мм

    label = f"{panel.name}\n{panel.width_mm:.0f}x{panel.height_mm:.0f}"
    if panel.notes:
        label += f"\n{panel.notes}"

    msp.add_mtext(
        label,
        dxfattribs={
            "layer": "TEXT",
            "char_height": text_height,
            "insert": (x + w / 2, y + h / 2),
            "attachment_point": 5,  # MIDDLE_CENTER
        }
    )


def draw_sheet_boundary(msp: Modelspace, width: float, height: float) -> None:
    """Рисует границу листа материала."""
    points = [
        (0, 0),
        (width, 0),
        (width, height),
        (0, height),
        (0, 0),
    ]
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "SHEET"})




def generate_panel_dxf(
    panels: list[Panel],
    sheet_size: tuple[float, float] | None = None,
    optimize: bool = True,
    gap_mm: float = DEFAULT_GAP_MM,
) -> tuple[bytes, SheetLayout]:
    """
    Генерирует DXF файл с раскладкой панелей.

    Args:
        panels: Список панелей для раскроя
        sheet_size: Размер листа (ширина, высота) в мм.
                   Если None — выбирается автоматически.
        optimize: Использовать оптимизацию раскроя
        gap_mm: Зазор между панелями (на пропил)

    Returns:
        Tuple из (bytes DXF файла, SheetLayout с информацией о раскладке)
    """
    # Выбираем размер листа
    if sheet_size is None:
        sheet_size = (DEFAULT_SHEET_WIDTH_MM, DEFAULT_SHEET_HEIGHT_MM)

    sheet_width, sheet_height = sheet_size

    # Оптимизируем раскладку
    if optimize:
        layout = optimize_layout(panels, sheet_width, sheet_height, gap_mm)
    else:
        layout = _simple_layout(panels, sheet_width, sheet_height, gap_mm)

    # Создаём DXF документ
    doc = create_dxf_document()
    msp = doc.modelspace()

    # Рисуем границу листа
    draw_sheet_boundary(msp, sheet_width, sheet_height)

    # Рисуем панели
    for panel, x, y, rotated in layout.placed_panels:
        draw_panel(msp, panel, x, y, rotated)

    # Добавляем информацию о раскрое
    info_text = (
        f"Лист: {sheet_width:.0f}x{sheet_height:.0f} мм\n"
        f"Панелей: {len(layout.placed_panels)}\n"
        f"Утилизация: {layout.utilization_percent:.1f}%"
    )
    if layout.unplaced_panels:
        info_text += f"\nНе размещено: {len(layout.unplaced_panels)}"

    msp.add_mtext(
        info_text,
        dxfattribs={
            "layer": "TEXT",
            "char_height": 30,
            "insert": (sheet_width + 50, sheet_height - 50),
        }
    )

    # Сохраняем в bytes
    buf = io.StringIO()
    try:
        doc.write(buf)
        text = buf.getvalue()
    finally:
        buf.close()

    encoding = getattr(doc, "output_encoding", "utf-8")
    data = text.encode(encoding or "utf-8")

    return data, layout


def generate_single_panel_dxf(panel: Panel) -> bytes:
    """
    Генерирует DXF для одной панели (без раскроя на листе).
    Полезно для просмотра отдельной детали.
    """
    doc = create_dxf_document()
    msp = doc.modelspace()

    # Рисуем панель в начале координат
    draw_panel(msp, panel, 0, 0, False)

    # Добавляем размеры
    msp.add_aligned_dim(
        p1=(0, -30),
        p2=(panel.width_mm, -30),
        distance=20,
        dxfattribs={"layer": "TEXT"}
    ).render()

    msp.add_aligned_dim(
        p1=(-30, 0),
        p2=(-30, panel.height_mm),
        distance=20,
        dxfattribs={"layer": "TEXT"}
    ).render()

    # Сохраняем
    buf = io.StringIO()
    try:
        doc.write(buf)
        text = buf.getvalue()
    finally:
        buf.close()

    encoding = getattr(doc, "output_encoding", "utf-8")
    return text.encode(encoding or "utf-8")
