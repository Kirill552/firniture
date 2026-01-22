"""
Генератор DXF файлов для мебельных панелей.

Создаёт DXF чертежи с раскладкой панелей на листе материала.
Использует ezdxf для создания файлов и rectpack для оптимизации раскроя.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from uuid import UUID

import ezdxf
from ezdxf import units
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace

from api.constants import (
    DEFAULT_EDGE_THICKNESS_MM,
    DEFAULT_GAP_MM,
    DEFAULT_SHEET_HEIGHT_MM,
    DEFAULT_SHEET_WIDTH_MM,
    DEFAULT_THICKNESS_MM,
)

try:
    from rectpack import GuillotineBssfSas, PackingAlgorithm, PackingMode, newPacker
    RECTPACK_AVAILABLE = True
except ImportError:
    RECTPACK_AVAILABLE = False

# Цвета слоёв (AutoCAD ACI)
LAYER_COLORS = {
    "CONTOUR": 7,      # белый/чёрный — внешний контур
    "EDGE": 1,         # красный — кромка
    "DRILLING": 5,     # синий — присадка (сверление)
    "TEXT": 3,         # зелёный — текстовые метки
    "SHEET": 8,        # серый — граница листа
}


@dataclass
class Panel:
    """Панель мебели для раскроя."""
    id: str | UUID
    name: str
    width_mm: float
    height_mm: float
    thickness_mm: float = DEFAULT_THICKNESS_MM
    material: str = "ЛДСП"

    # Кромка (какие стороны)
    edge_top: bool = False
    edge_bottom: bool = False
    edge_left: bool = False
    edge_right: bool = False
    edge_thickness_mm: float = DEFAULT_EDGE_THICKNESS_MM

    # Присадка (точки сверления для фурнитуры)
    drilling_points: list[dict] = field(default_factory=list)
    # Формат: [{"x": 50, "y": 37, "diameter": 5, "depth": 12, "side": "face", "hardware_type": "confirmat"}, ...]

    # Комментарий
    notes: str = ""


@dataclass
class SheetLayout:
    """Результат размещения панелей на листе."""
    sheet_width: float
    sheet_height: float
    placed_panels: list[tuple[Panel, float, float, bool]]  # (panel, x, y, rotated)
    unplaced_panels: list[Panel]
    utilization_percent: float

    @property
    def utilization(self) -> float:
        """Alias для совместимости с routers.py."""
        return self.utilization_percent


@dataclass
class PlacedPanel:
    """Размещённая панель с координатами на листе."""
    name: str
    x: float
    y: float
    width_mm: float
    height_mm: float
    rotated: bool = False


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
            dxfattribs={"layer": "DRILLING"}
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


def optimize_layout(
    panels: list[Panel],
    sheet_width: float,
    sheet_height: float,
    gap_mm: float = DEFAULT_GAP_MM,  # зазор между панелями (на пропил)
    allow_rotation: bool = True,
    use_guillotine: bool = True,  # использовать Guillotine для форматника (только сквозные пропилы)
) -> SheetLayout:
    """
    Оптимизирует размещение панелей на листе (bin packing).

    Args:
        panels: Список панелей для размещения
        sheet_width: Ширина листа материала (мм)
        sheet_height: Высота листа материала (мм)
        gap_mm: Зазор между панелями (мм)
        allow_rotation: Разрешить поворот панелей на 90°
        use_guillotine: Guillotine режим для форматно-раскроечного станка (только сквозные пропилы)

    Returns:
        SheetLayout с результатами размещения
    """
    if not RECTPACK_AVAILABLE:
        # Fallback: простое последовательное размещение
        return _simple_layout(panels, sheet_width, sheet_height, gap_mm)

    if use_guillotine:
        # Guillotine — только сквозные пропилы (для форматника)
        packer = newPacker(
            mode=PackingMode.Offline,
            pack_algo=GuillotineBssfSas,
            rotation=allow_rotation,
        )
    else:
        # MaxRects — более гибкий (для фрезера ЧПУ)
        packer = newPacker(
            mode=PackingMode.Offline,
            pack_algo=PackingAlgorithm.MaxRectsBssf,
            rotation=allow_rotation,
        )

    # Добавляем лист
    packer.add_bin(int(sheet_width), int(sheet_height))

    # Сортировка панелей по площади (большие первыми) для лучшей упаковки
    sorted_panels = sorted(
        enumerate(panels),
        key=lambda x: x[1].width_mm * x[1].height_mm,
        reverse=True
    )

    # Добавляем панели с учётом зазора
    panel_map = {}
    for i, panel in sorted_panels:
        # Добавляем зазор к размерам
        w = int(panel.width_mm + gap_mm)
        h = int(panel.height_mm + gap_mm)
        packer.add_rect(w, h, rid=i)
        panel_map[i] = panel

    # Запускаем упаковку
    packer.pack()

    # Собираем результаты
    placed: list[tuple[Panel, float, float, bool]] = []
    placed_ids = set()

    for rect in packer.rect_list():
        bid, x, y, w, h, rid = rect
        panel = panel_map[rid]
        placed_ids.add(rid)

        # Проверяем, была ли панель повёрнута
        original_w = int(panel.width_mm + gap_mm)
        rotated = (w != original_w)

        placed.append((panel, float(x), float(y), rotated))

    # Неразмещённые панели
    unplaced = [p for i, p in enumerate(panels) if i not in placed_ids]

    # Расчёт утилизации
    total_panel_area = sum(p.width_mm * p.height_mm for p, _, _, _ in placed)
    sheet_area = sheet_width * sheet_height
    utilization = (total_panel_area / sheet_area) * 100 if sheet_area > 0 else 0

    return SheetLayout(
        sheet_width=sheet_width,
        sheet_height=sheet_height,
        placed_panels=placed,
        unplaced_panels=unplaced,
        utilization_percent=utilization,
    )


def optimize_layout_best(
    panels: list[Panel],
    sheet_width: float,
    sheet_height: float,
    gap_mm: float = DEFAULT_GAP_MM,
) -> SheetLayout:
    """Пробует несколько стратегий и выбирает лучшую по utilization."""

    strategies = [
        {"use_guillotine": True, "allow_rotation": False},  # Без поворота (учёт текстуры)
        {"use_guillotine": True, "allow_rotation": True},   # С поворотом
        {"use_guillotine": False, "allow_rotation": True},  # MaxRects с поворотом
    ]

    best_layout: SheetLayout | None = None
    best_utilization = 0.0

    for strategy in strategies:
        layout = optimize_layout(
            panels=panels,
            sheet_width=sheet_width,
            sheet_height=sheet_height,
            gap_mm=gap_mm,
            **strategy,
        )
        if layout.utilization_percent > best_utilization:
            best_utilization = layout.utilization_percent
            best_layout = layout

    # Fallback если ничего не нашли
    if best_layout is None:
        best_layout = optimize_layout(panels, sheet_width, sheet_height, gap_mm)

    return best_layout


def _simple_layout(
    panels: list[Panel],
    sheet_width: float,
    sheet_height: float,
    gap_mm: float,
) -> SheetLayout:
    """Простое последовательное размещение (без оптимизации)."""
    placed: list[tuple[Panel, float, float, bool]] = []
    unplaced: list[Panel] = []

    x, y = 0.0, 0.0
    row_height = 0.0

    for panel in sorted(panels, key=lambda p: -p.height_mm):
        w = panel.width_mm + gap_mm
        h = panel.height_mm + gap_mm

        # Проверяем, помещается ли в текущий ряд
        if x + w > sheet_width:
            # Переходим на новый ряд
            x = 0
            y += row_height
            row_height = 0

        # Проверяем, помещается ли по высоте
        if y + h > sheet_height:
            unplaced.append(panel)
            continue

        placed.append((panel, x, y, False))
        row_height = max(row_height, h)
        x += w

    total_panel_area = sum(p.width_mm * p.height_mm for p, _, _, _ in placed)
    sheet_area = sheet_width * sheet_height
    utilization = (total_panel_area / sheet_area) * 100 if sheet_area > 0 else 0

    return SheetLayout(
        sheet_width=sheet_width,
        sheet_height=sheet_height,
        placed_panels=placed,
        unplaced_panels=unplaced,
        utilization_percent=utilization,
    )


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
