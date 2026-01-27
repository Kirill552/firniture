"""
Генератор PDF карты раскроя для мебельного производства.

Создаёт визуальную карту раскладки панелей на листе для оператора форматника.
Используется PyMuPDF (fitz) для генерации PDF.

Карта раскроя содержит:
- Схему раскладки панелей на листе
- Названия и размеры каждой панели
- Линии реза
- Общую статистику (использование листа, количество панелей)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Путь к шрифту с кириллицей (DejaVu Sans или системный Arial)
def _find_cyrillic_font() -> str | None:
    """Ищет шрифт с поддержкой кириллицы."""
    candidates = [
        # Проект (если добавим шрифт)
        Path(__file__).parent / "fonts" / "DejaVuSans.ttf",
        # Windows
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
        # Linux
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        # macOS
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    for font_path in candidates:
        if font_path.exists():
            return str(font_path)
    return None

CYRILLIC_FONT_PATH = _find_cyrillic_font()

from api.dxf_generator import PlacedPanel


@dataclass
class PDFConfig:
    """Настройки PDF документа."""
    # Размер страницы (A4 landscape)
    page_width: float = 842  # points (A4 landscape width)
    page_height: float = 595  # points (A4 landscape height)

    # Отступы
    margin: float = 40

    # Шрифты (F0 - кириллический шрифт, регистрируется при генерации)
    font_cyrillic: str = "F0"  # Имя регистрируемого шрифта с кириллицей
    font_size_title: float = 16
    font_size_subtitle: float = 12
    font_size_panel: float = 8
    font_size_dimension: float = 7
    font_size_stats: float = 10

    # Цвета (RGB 0-1)
    color_sheet: tuple[float, float, float] = (0.9, 0.9, 0.9)  # Светло-серый фон листа
    color_panel: tuple[float, float, float] = (0.85, 0.92, 1.0)  # Светло-голубой
    color_panel_stroke: tuple[float, float, float] = (0.3, 0.3, 0.3)  # Тёмно-серый контур
    color_text: tuple[float, float, float] = (0.1, 0.1, 0.1)  # Почти чёрный
    color_dimension: tuple[float, float, float] = (0.4, 0.4, 0.4)  # Серый для размеров
    color_cut_line: tuple[float, float, float] = (0.8, 0.2, 0.2)  # Красный для линий реза


def generate_cutting_map_pdf(
    placed_panels: list[PlacedPanel],
    sheet_width_mm: float,
    sheet_height_mm: float,
    utilization_percent: float,
    order_info: str = "",
    config: PDFConfig | None = None,
) -> bytes:
    """
    Генерирует PDF карту раскроя.

    Args:
        placed_panels: Список размещённых панелей с координатами
        sheet_width_mm: Ширина листа в мм
        sheet_height_mm: Высота листа в мм
        utilization_percent: Процент использования листа
        order_info: Информация о заказе (опционально)
        config: Настройки PDF

    Returns:
        PDF документ в виде bytes
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF generation")

    cfg = config or PDFConfig()

    # Создаём документ
    doc = fitz.open()
    page = doc.new_page(width=cfg.page_width, height=cfg.page_height)

    # Регистрируем шрифт с поддержкой кириллицы
    if CYRILLIC_FONT_PATH:
        page.insert_font(fontname=cfg.font_cyrillic, fontfile=CYRILLIC_FONT_PATH)
    else:
        # Fallback на встроенный шрифт (без кириллицы, но хоть что-то)
        cfg.font_cyrillic = "helv"

    # Область для рисования схемы (с учётом отступов и места для заголовка)
    header_height = 60
    footer_height = 40
    legend_width = 150

    draw_area_x = cfg.margin
    draw_area_y = cfg.margin + header_height
    draw_area_width = cfg.page_width - 2 * cfg.margin - legend_width
    draw_area_height = cfg.page_height - 2 * cfg.margin - header_height - footer_height

    # Масштаб для отображения листа в области рисования
    scale_x = draw_area_width / sheet_width_mm
    scale_y = draw_area_height / sheet_height_mm
    scale = min(scale_x, scale_y) * 0.95  # Немного меньше для зазоров

    # Размеры листа на странице
    sheet_draw_width = sheet_width_mm * scale
    sheet_draw_height = sheet_height_mm * scale

    # Центрируем лист в области рисования
    sheet_x = draw_area_x + (draw_area_width - sheet_draw_width) / 2
    sheet_y = draw_area_y + (draw_area_height - sheet_draw_height) / 2

    # --- Заголовок ---
    _draw_header(page, cfg, order_info)

    # --- Рисуем лист (фон) ---
    sheet_rect = fitz.Rect(
        sheet_x,
        sheet_y,
        sheet_x + sheet_draw_width,
        sheet_y + sheet_draw_height
    )
    page.draw_rect(sheet_rect, color=cfg.color_panel_stroke, fill=cfg.color_sheet, width=1.5)

    # --- Размеры листа ---
    # Ширина сверху
    page.insert_text(
        fitz.Point(sheet_x + sheet_draw_width / 2 - 30, sheet_y - 8),
        f"{int(sheet_width_mm)} мм",
        fontsize=cfg.font_size_dimension,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
    )

    # Высота справа (вертикально)
    height_text_x = sheet_x + sheet_draw_width + 5
    height_text_y = sheet_y + sheet_draw_height / 2
    page.insert_text(
        fitz.Point(height_text_x, height_text_y),
        f"{int(sheet_height_mm)} мм",
        fontsize=cfg.font_size_dimension,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
        rotate=90,
    )

    # --- Рисуем панели ---
    panel_colors = [
        (0.85, 0.92, 1.0),   # Светло-голубой
        (0.85, 1.0, 0.85),   # Светло-зелёный
        (1.0, 0.95, 0.85),   # Светло-жёлтый
        (1.0, 0.85, 0.85),   # Светло-красный
        (0.92, 0.85, 1.0),   # Светло-фиолетовый
        (1.0, 0.9, 0.85),    # Светло-оранжевый
        (0.85, 1.0, 0.95),   # Светло-бирюзовый
        (1.0, 0.85, 0.95),   # Светло-розовый
    ]

    for i, panel in enumerate(placed_panels):
        color = panel_colors[i % len(panel_colors)]

        # Координаты панели на странице
        # В DXF y=0 внизу, в PDF y=0 сверху — инвертируем
        panel_x = sheet_x + panel.x * scale
        panel_y = sheet_y + sheet_draw_height - (panel.y + panel.height_mm) * scale
        panel_w = panel.width_mm * scale
        panel_h = panel.height_mm * scale

        panel_rect = fitz.Rect(panel_x, panel_y, panel_x + panel_w, panel_y + panel_h)

        # Заливка и контур
        page.draw_rect(panel_rect, color=cfg.color_panel_stroke, fill=color, width=0.8)

        # Название панели (если помещается)
        if panel_w > 30 and panel_h > 15:
            name_text = panel.name[:12] + "..." if len(panel.name) > 15 else panel.name
            text_x = panel_x + 3
            text_y = panel_y + 12
            page.insert_text(
                fitz.Point(text_x, text_y),
                name_text,
                fontsize=cfg.font_size_panel,
                fontname=cfg.font_cyrillic,
                color=cfg.color_text,
            )

        # Размеры панели (если помещается)
        if panel_w > 40 and panel_h > 25:
            dim_text = f"{int(panel.width_mm)}×{int(panel.height_mm)}"
            dim_x = panel_x + 3
            dim_y = panel_y + panel_h - 5
            page.insert_text(
                fitz.Point(dim_x, dim_y),
                dim_text,
                fontsize=cfg.font_size_dimension,
                fontname=cfg.font_cyrillic,
                color=cfg.color_dimension,
            )

        # Индикатор поворота
        if panel.rotated and panel_w > 20 and panel_h > 20:
            rotate_x = panel_x + panel_w - 12
            rotate_y = panel_y + 10
            page.insert_text(
                fitz.Point(rotate_x, rotate_y),
                "↻",
                fontsize=10,
                fontname=cfg.font_cyrillic,
                color=cfg.color_dimension,
            )

    # --- Легенда и статистика ---
    _draw_legend(
        page, cfg,
        placed_panels,
        sheet_width_mm, sheet_height_mm,
        utilization_percent,
        cfg.page_width - cfg.margin - legend_width + 10,
        draw_area_y,
        legend_width - 20,
    )

    # --- Футер ---
    _draw_footer(page, cfg)

    # Сохраняем в bytes
    pdf_bytes = doc.tobytes()
    doc.close()

    return pdf_bytes


def _draw_header(page: fitz.Page, cfg: PDFConfig, order_info: str) -> None:
    """Рисует заголовок страницы."""
    # Название
    page.insert_text(
        fitz.Point(cfg.margin, cfg.margin + 20),
        "Карта раскроя",
        fontsize=cfg.font_size_title,
        fontname=cfg.font_cyrillic,
        color=cfg.color_text,
    )

    # Подзаголовок с информацией о заказе
    if order_info:
        page.insert_text(
            fitz.Point(cfg.margin, cfg.margin + 38),
            order_info,
            fontsize=cfg.font_size_subtitle,
            fontname=cfg.font_cyrillic,
            color=cfg.color_dimension,
            )

    # Дата
    date_text = datetime.now().strftime("%d.%m.%Y %H:%M")
    page.insert_text(
        fitz.Point(cfg.page_width - cfg.margin - 100, cfg.margin + 20),
        date_text,
        fontsize=cfg.font_size_stats,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
    )


def _draw_legend(
    page: fitz.Page,
    cfg: PDFConfig,
    panels: list[PlacedPanel],
    sheet_w: float,
    sheet_h: float,
    utilization: float,
    x: float,
    y: float,
    width: float,
) -> None:
    """Рисует легенду и статистику."""
    line_height = 14
    current_y = y

    # Заголовок легенды
    page.insert_text(
        fitz.Point(x, current_y),
        "Статистика",
        fontsize=cfg.font_size_subtitle,
        fontname=cfg.font_cyrillic,
        color=cfg.color_text,
    )
    current_y += line_height + 8

    # Размер листа
    page.insert_text(
        fitz.Point(x, current_y),
        f"Лист: {int(sheet_w)}x{int(sheet_h)} мм",
        fontsize=cfg.font_size_stats,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
    )
    current_y += line_height

    # Площадь листа
    sheet_area = (sheet_w * sheet_h) / 1_000_000
    page.insert_text(
        fitz.Point(x, current_y),
        f"Площадь: {sheet_area:.2f} м2",
        fontsize=cfg.font_size_stats,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
    )
    current_y += line_height

    # Количество панелей
    page.insert_text(
        fitz.Point(x, current_y),
        f"Панелей: {len(panels)} шт",
        fontsize=cfg.font_size_stats,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
    )
    current_y += line_height

    # Использование
    util_color = (0.2, 0.6, 0.2) if utilization >= 50 else (0.8, 0.4, 0.1)
    page.insert_text(
        fitz.Point(x, current_y),
        f"Использование: {utilization:.1f}%",
        fontsize=cfg.font_size_stats,
        fontname=cfg.font_cyrillic,
        color=util_color,
    )
    current_y += line_height * 2

    # Список панелей
    page.insert_text(
        fitz.Point(x, current_y),
        "Панели:",
        fontsize=cfg.font_size_subtitle,
        fontname=cfg.font_cyrillic,
        color=cfg.color_text,
    )
    current_y += line_height + 4

    for i, panel in enumerate(panels[:10]):  # Максимум 10 панелей в легенде
        name = panel.name[:18] + "..." if len(panel.name) > 20 else panel.name
        rotated = " R" if panel.rotated else ""
        text = f"{i+1}. {name}{rotated}"
        page.insert_text(
            fitz.Point(x, current_y),
            text,
            fontsize=cfg.font_size_panel,
            fontname=cfg.font_cyrillic,
            color=cfg.color_dimension,
            )
        current_y += line_height - 2

        # Размеры
        dim_text = f"   {int(panel.width_mm)}×{int(panel.height_mm)} мм"
        page.insert_text(
            fitz.Point(x, current_y),
            dim_text,
            fontsize=cfg.font_size_dimension,
            fontname=cfg.font_cyrillic,
            color=cfg.color_dimension,
        )
        current_y += line_height - 2

    if len(panels) > 10:
        page.insert_text(
            fitz.Point(x, current_y),
            f"... и ещё {len(panels) - 10} панелей",
            fontsize=cfg.font_size_dimension,
            fontname=cfg.font_cyrillic,
            color=cfg.color_dimension,
        )


def _draw_footer(page: fitz.Page, cfg: PDFConfig) -> None:
    """Рисует футер страницы."""
    footer_y = cfg.page_height - cfg.margin

    page.insert_text(
        fitz.Point(cfg.margin, footer_y),
        "Сгенерировано: Мебель-ИИ",
        fontsize=cfg.font_size_dimension,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
    )

    page.insert_text(
        fitz.Point(cfg.page_width - cfg.margin - 80, footer_y),
        "mebel-ai.ru",
        fontsize=cfg.font_size_dimension,
        fontname=cfg.font_cyrillic,
        color=cfg.color_dimension,
    )
