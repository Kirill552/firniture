"""Cutting-map domain — panel geometry, sheet layout, and bin-packing.

Extracted as a standalone artifact layer (Task 9) — no ezdxf, no DXF, no G-code.
- Panel, SheetLayout, PlacedPanel — pure data.
- optimize_layout / optimize_layout_best / _simple_layout — packing algorithms.

Dependencies: dataclasses, constants, rectpack (optional).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from api.constants import (
    DEFAULT_EDGE_THICKNESS_MM,
    DEFAULT_GAP_MM,
    DEFAULT_THICKNESS_MM,
)

try:
    from rectpack import GuillotineBssfSas, PackingAlgorithm, PackingMode, newPacker

    RECTPACK_AVAILABLE = True
except ImportError:
    RECTPACK_AVAILABLE = False

# PDF generation (Task 11) — uses PyMuPDF, no ezdxf (enforced by separation tests)
try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Panel:
    """Панель мебели для раскроя (чистые данные, без привязки к чертежу)."""

    id: str
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
    # Формат: [{"x": 50, "y": 37, "diameter": 5, "depth": 12, ...}, ...]

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


# ---------------------------------------------------------------------------
# Layout algorithms
# ---------------------------------------------------------------------------


def optimize_layout(
    panels: list[Panel],
    sheet_width: float,
    sheet_height: float,
    gap_mm: float = DEFAULT_GAP_MM,
    allow_rotation: bool = True,
    use_guillotine: bool = True,
) -> SheetLayout:
    """Оптимизирует размещение панелей на листе (bin packing).

    Args:
        panels: Список панелей для размещения
        sheet_width: Ширина листа материала (мм)
        sheet_height: Высота листа материала (мм)
        gap_mm: Зазор между панелями (мм)
        allow_rotation: Разрешить поворот панелей на 90°
        use_guillotine: Guillotine режим для форматника (только сквозные пропилы)

    Returns:
        SheetLayout с результатами размещения
    """
    if not RECTPACK_AVAILABLE:
        return _simple_layout(panels, sheet_width, sheet_height, gap_mm)

    if use_guillotine:
        packer = newPacker(
            mode=PackingMode.Offline,
            pack_algo=GuillotineBssfSas,
            rotation=allow_rotation,
        )
    else:
        packer = newPacker(
            mode=PackingMode.Offline,
            pack_algo=PackingAlgorithm.MaxRectsBssf,
            rotation=allow_rotation,
        )

    packer.add_bin(int(sheet_width), int(sheet_height))

    sorted_panels = sorted(
        enumerate(panels),
        key=lambda x: x[1].width_mm * x[1].height_mm,
        reverse=True,
    )

    panel_map: dict[int, Panel] = {}
    for i, panel in sorted_panels:
        w = int(panel.width_mm + gap_mm)
        h = int(panel.height_mm + gap_mm)
        packer.add_rect(w, h, rid=i)
        panel_map[i] = panel

    packer.pack()

    placed: list[tuple[Panel, float, float, bool]] = []
    placed_ids: set[int] = set()

    for rect in packer.rect_list():
        bid, x, y, w, h, rid = rect
        panel = panel_map[rid]
        placed_ids.add(rid)

        original_w = int(panel.width_mm + gap_mm)
        rotated = w != original_w

        placed.append((panel, float(x), float(y), rotated))

    unplaced = [p for i, p in enumerate(panels) if i not in placed_ids]

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
        {"use_guillotine": True, "allow_rotation": False},
        {"use_guillotine": True, "allow_rotation": True},
        {"use_guillotine": False, "allow_rotation": True},
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

        if x + w > sheet_width:
            x = 0
            y += row_height
            row_height = 0

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


# ---------------------------------------------------------------------------
# PDF cutting map (Task 11 Step 3) — printable, semantic, with all required fields
# ---------------------------------------------------------------------------


import io  # local import to keep top clean


def _find_cyrillic_font() -> str | None:
    """Ищет шрифт с поддержкой кириллицы (аналогично legacy, минимально)."""
    from pathlib import Path

    candidates = [
        Path(__file__).parent / "fonts" / "DejaVuSans.ttf",
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


_CYRILLIC_FONT = _find_cyrillic_font()


def generate_cutting_map_pdf(
    layout: SheetLayout,
    order_id: str = "",
    revision: str = "1",
    kerf_mm: float = DEFAULT_GAP_MM,
    margin_mm: float = 10.0,
    grain: str = "none",
    scale_note: str = "1:1 (размеры в мм)",
) -> bytes:
    """Генерирует печатную карту раскроя PDF.

    Обязательные элементы (Task 11):
    - scale (заметка + реальные размеры)
    - dimensions (лист + панели)
    - grain arrows (при grain != none рисуется стрелка направления)
    - part labels (name + WxH + rotated)
    - order/revision
    - kerf, margin
    - unplaced warnings

    Использует fitz. Не зависит от ezdxf.
    Возвращает PDF bytes (для сохранения/отдачи).
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) обязателен для генерации PDF карты раскроя")

    # Страница — A4 landscape в points, с запасом для большой раскладки
    page_w, page_h = 842.0, 595.0
    doc = fitz.open()
    page = doc.new_page(width=page_w, height=page_h)

    # Регистрация шрифта
    fontname = "helv"
    if _CYRILLIC_FONT:
        try:
            page.insert_font(fontname="F0", fontfile=_CYRILLIC_FONT)
            fontname = "F0"
        except Exception:
            fontname = "helv"

    # Отступы и заголовок
    margin = 30.0
    header_h = 70.0
    draw_area_x = margin
    draw_area_y = header_h
    draw_w = page_w - 2 * margin
    draw_h = page_h - header_h - margin - 60  # footer space

    # Вычислить масштаб отрисовки (fit sheet в область)
    sw, sh = layout.sheet_width, layout.sheet_height
    if sw <= 0 or sh <= 0:
        sw, sh = 1.0, 1.0
    sx = draw_w / sw
    sy = draw_h / sh
    scale = min(sx, sy, 1.5)  # не растягиваем слишком
    if scale <= 0:
        scale = 0.1

    # Центрируем чертёж
    disp_w = sw * scale
    disp_h = sh * scale
    ox = draw_area_x + (draw_w - disp_w) / 2
    oy = draw_area_y + (draw_h - disp_h) / 2

    # === HEADER: order, revision, kerf, margin, scale, grain ===
    title = f"Карта раскроя | Заказ: {order_id or '—'} | Ревизия: {revision}"
    page.insert_text((margin, 18), title, fontsize=11, fontname=fontname, color=(0, 0, 0))

    meta = (
        f"Лист: {sw:.0f} × {sh:.0f} мм | "
        f"Kerf (зазор/пропил): {kerf_mm:.1f} мм | "
        f"Margin (поля): {margin_mm:.1f} мм | "
        f"Зерно: {grain} | "
        f"Масштаб: {scale_note} | "
        f"Утилизация: {layout.utilization_percent:.1f}%"
    )
    page.insert_text((margin, 34), meta, fontsize=8, fontname=fontname, color=(0.2, 0.2, 0.2))

    # === SHEET boundary ===
    sheet_rect = fitz.Rect(ox, oy, ox + disp_w, oy + disp_h)
    page.draw_rect(sheet_rect, color=(0.2, 0.2, 0.2), width=1.5)
    # dimension labels on sheet
    page.insert_text((ox + disp_w / 2 - 20, oy - 4), f"{sw:.0f} мм", fontsize=7, fontname=fontname)
    page.insert_text((ox + disp_w + 3, oy + disp_h / 2), f"{sh:.0f} мм", fontsize=7, fontname=fontname)

    # === Draw placed panels ===
    for item in layout.placed_panels:
        # support both tuple (Panel, x, y, rotated) and PlacedPanel-like
        if isinstance(item, (list, tuple)):
            panel, px, py, rotated = item[0], item[1], item[2], item[3]
        else:
            panel = item  # type: ignore
            px, py, rotated = getattr(item, "x", 0), getattr(item, "y", 0), getattr(item, "rotated", False)

        pw = panel.height_mm if rotated else panel.width_mm
        ph = panel.width_mm if rotated else panel.height_mm

        rx = ox + px * scale
        ry = oy + py * scale
        rw = pw * scale
        rh = ph * scale

        # panel rect (light fill)
        r = fitz.Rect(rx, ry, rx + rw, ry + rh)
        page.draw_rect(r, color=(0.15, 0.35, 0.55), width=0.8, fill=(0.9, 0.94, 0.98))

        # label inside
        label = f"{panel.name}\n{panel.width_mm:.0f}×{panel.height_mm:.0f}"
        if rotated:
            label += " (пов)"
        # simple text (may clip on small; ok for pilot)
        page.insert_text((rx + 2, ry + 10), label[:40], fontsize=6, fontname=fontname, color=(0, 0, 0))

    # === Grain arrow (semantic indicator) ===
    if grain and grain.lower() not in ("none", "", "no"):
        # Draw arrow in top-right of draw area
        ax = ox + disp_w - 60
        ay = oy - 18
        if "vertical" in grain.lower() or grain == "V":
            # vertical arrow
            page.draw_line((ax, ay), (ax, ay - 18), color=(0.8, 0.2, 0.2), width=1.5)
            page.draw_line((ax - 4, ay - 12), (ax, ay - 18), color=(0.8, 0.2, 0.2), width=1)
            page.draw_line((ax + 4, ay - 12), (ax, ay - 18), color=(0.8, 0.2, 0.2), width=1)
            page.insert_text((ax + 6, ay - 8), "↑ зерно", fontsize=6, fontname=fontname, color=(0.6, 0.1, 0.1))
        else:
            # horizontal
            page.draw_line((ax - 18, ay - 9), (ax, ay - 9), color=(0.8, 0.2, 0.2), width=1.5)
            page.draw_line((ax - 12, ay - 13), (ax, ay - 9), color=(0.8, 0.2, 0.2), width=1)
            page.draw_line((ax - 12, ay - 5), (ax, ay - 9), color=(0.8, 0.2, 0.2), width=1)
            page.insert_text((ax + 3, ay - 6), "→ зерно", fontsize=6, fontname=fontname, color=(0.6, 0.1, 0.1))

    # === Unplaced warnings ===
    footer_y = page_h - 45
    if layout.unplaced_panels:
        warn = f"⚠ НЕ РАЗМЕЩЕНО ({len(layout.unplaced_panels)}): " + ", ".join(
            f"{p.name} ({p.width_mm:.0f}×{p.height_mm:.0f})" for p in layout.unplaced_panels[:5]
        )
        page.insert_text((margin, footer_y), warn, fontsize=7, fontname=fontname, color=(0.7, 0.1, 0.1))
    else:
        page.insert_text((margin, footer_y), "Все панели размещены.", fontsize=7, fontname=fontname, color=(0.1, 0.4, 0.1))

    # === Footer note ===
    page.insert_text(
        (margin, page_h - 18),
        "Черновик для пилота. Проверить размеры перед резом. DXF деталей — отдельно (локальные координаты).",
        fontsize=6,
        fontname=fontname,
        color=(0.4, 0.4, 0.4),
    )

    # Write to bytes
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()
