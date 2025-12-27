"""
Экспорт заказов в форматы для 1С.

Поддерживаемые форматы:
- Excel (.xlsx) - рекомендуется для ручной загрузки
- CSV (.csv) - альтернатива для автоматизации

Формат Excel содержит листы:
1. Заказ - общая информация о заказе
2. Изделия - список изделий с размерами
3. Панели - детали панелей каждого изделия
4. Фурнитура - спецификация фурнитуры (BOM)
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from api.models import Order, ProductConfig, Panel, BOMItem

log = logging.getLogger(__name__)


# Стили для Excel
HEADER_FONT = Font(bold=True, size=11)
HEADER_FILL = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin")
)


def _apply_header_style(cell):
    """Применить стиль заголовка к ячейке."""
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = HEADER_ALIGNMENT
    cell.border = THIN_BORDER


def _apply_cell_style(cell):
    """Применить стиль к обычной ячейке."""
    cell.border = THIN_BORDER
    cell.alignment = Alignment(vertical="center")


def _auto_column_width(ws, min_width: int = 10, max_width: int = 50):
    """Автоматически подобрать ширину колонок."""
    for column_cells in ws.columns:
        max_length = 0
        column = None
        for cell in column_cells:
            # Пропускаем MergedCell
            if hasattr(cell, 'column_letter'):
                if column is None:
                    column = cell.column_letter
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
        if column:
            adjusted_width = min(max(max_length + 2, min_width), max_width)
            ws.column_dimensions[column].width = adjusted_width


def generate_order_excel(
    order: Order,
    products: List[ProductConfig],
    bom_items: Optional[List[BOMItem]] = None
) -> bytes:
    """
    Генерация Excel файла для заказа.

    Args:
        order: Объект заказа
        products: Список изделий
        bom_items: Список позиций спецификации (опционально)

    Returns:
        Байты Excel файла
    """
    log.info(f"Генерация Excel для заказа {order.id}")

    wb = Workbook()

    # ========== Лист 1: Заказ ==========
    ws_order = wb.active
    ws_order.title = "Заказ"

    # Заголовок
    ws_order.merge_cells("A1:D1")
    ws_order["A1"] = f"Заказ #{str(order.id)[:8]}"
    ws_order["A1"].font = Font(bold=True, size=14)

    # Информация о заказе
    order_info = [
        ("ID заказа:", str(order.id)),
        ("Дата создания:", order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "-"),
        ("Внешний номер:", order.customer_ref or "-"),
        ("Примечания:", order.notes or "-"),
        ("Кол-во изделий:", str(len(products))),
    ]

    for i, (label, value) in enumerate(order_info, start=3):
        ws_order[f"A{i}"] = label
        ws_order[f"A{i}"].font = Font(bold=True)
        ws_order[f"B{i}"] = value

    _auto_column_width(ws_order)

    # ========== Лист 2: Изделия ==========
    ws_products = wb.create_sheet("Изделия")

    headers = ["№", "Наименование", "Ширина, мм", "Высота, мм", "Глубина, мм", "Материал", "Толщина, мм", "Примечания"]
    for col, header in enumerate(headers, start=1):
        cell = ws_products.cell(row=1, column=col, value=header)
        _apply_header_style(cell)

    for row, product in enumerate(products, start=2):
        data = [
            row - 1,
            product.name or f"Изделие {row - 1}",
            product.width_mm,
            product.height_mm,
            product.depth_mm,
            product.material or "-",
            product.thickness_mm or "-",
            product.notes or "-"
        ]
        for col, value in enumerate(data, start=1):
            cell = ws_products.cell(row=row, column=col, value=value)
            _apply_cell_style(cell)

    _auto_column_width(ws_products)

    # ========== Лист 3: Панели ==========
    ws_panels = wb.create_sheet("Панели")

    headers = ["№", "Изделие", "Название панели", "Ширина, мм", "Высота, мм", "Толщина, мм", "Материал", "Кромка, мм", "Примечания"]
    for col, header in enumerate(headers, start=1):
        cell = ws_panels.cell(row=1, column=col, value=header)
        _apply_header_style(cell)

    panel_row = 2
    for product in products:
        product_name = product.name or f"Изделие"
        for panel in (product.panels or []):
            data = [
                panel_row - 1,
                product_name,
                panel.name,
                panel.width_mm,
                panel.height_mm,
                panel.thickness_mm,
                panel.material or "-",
                panel.edge_band_mm or "-",
                panel.notes or "-"
            ]
            for col, value in enumerate(data, start=1):
                cell = ws_panels.cell(row=panel_row, column=col, value=value)
                _apply_cell_style(cell)
            panel_row += 1

    if panel_row == 2:
        ws_panels.cell(row=2, column=1, value="Нет панелей")

    _auto_column_width(ws_panels)

    # ========== Лист 4: Фурнитура (BOM) ==========
    ws_bom = wb.create_sheet("Фурнитура")

    headers = ["№", "Артикул (SKU)", "Наименование", "Кол-во", "Ед. изм.", "Артикул поставщика", "Параметры"]
    for col, header in enumerate(headers, start=1):
        cell = ws_bom.cell(row=1, column=col, value=header)
        _apply_header_style(cell)

    if bom_items:
        for row, item in enumerate(bom_items, start=2):
            params_str = ", ".join(f"{k}={v}" for k, v in (item.params or {}).items()) if item.params else "-"
            data = [
                row - 1,
                item.sku,
                item.name,
                item.qty,
                item.unit,
                item.supplier_sku or "-",
                params_str
            ]
            for col, value in enumerate(data, start=1):
                cell = ws_bom.cell(row=row, column=col, value=value)
                _apply_cell_style(cell)
    else:
        ws_bom.cell(row=2, column=1, value="Спецификация не сформирована")

    _auto_column_width(ws_bom)

    # Сохраняем в байты
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    log.info(f"Excel для заказа {order.id} сгенерирован успешно")
    return output.getvalue()


def generate_order_csv(
    order: Order,
    products: List[ProductConfig],
    bom_items: Optional[List[BOMItem]] = None
) -> Dict[str, bytes]:
    """
    Генерация CSV файлов для заказа.

    Returns:
        Словарь {имя_файла: байты}
    """
    log.info(f"Генерация CSV для заказа {order.id}")

    files = {}

    # CSV с изделиями
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["№", "Наименование", "Ширина_мм", "Высота_мм", "Глубина_мм", "Материал", "Толщина_мм", "Примечания"])

    for i, product in enumerate(products, start=1):
        writer.writerow([
            i,
            product.name or f"Изделие {i}",
            product.width_mm,
            product.height_mm,
            product.depth_mm,
            product.material or "",
            product.thickness_mm or "",
            product.notes or ""
        ])

    files["products.csv"] = output.getvalue().encode("utf-8-sig")  # BOM для Excel

    # CSV с панелями
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["№", "Изделие", "Панель", "Ширина_мм", "Высота_мм", "Толщина_мм", "Материал", "Кромка_мм"])

    panel_num = 1
    for product in products:
        for panel in (product.panels or []):
            writer.writerow([
                panel_num,
                product.name or "Изделие",
                panel.name,
                panel.width_mm,
                panel.height_mm,
                panel.thickness_mm,
                panel.material or "",
                panel.edge_band_mm or ""
            ])
            panel_num += 1

    files["panels.csv"] = output.getvalue().encode("utf-8-sig")

    # CSV с BOM
    if bom_items:
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["№", "Артикул", "Наименование", "Количество", "Ед_изм", "Артикул_поставщика"])

        for i, item in enumerate(bom_items, start=1):
            writer.writerow([
                i,
                item.sku,
                item.name,
                item.qty,
                item.unit,
                item.supplier_sku or ""
            ])

        files["bom.csv"] = output.getvalue().encode("utf-8-sig")

    log.info(f"CSV для заказа {order.id} сгенерирован: {list(files.keys())}")
    return files


def generate_1c_filename(order: Order, extension: str = "xlsx") -> str:
    """Генерация имени файла для 1С."""
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    order_short = str(order.id)[:8]
    return f"order_{order_short}_{date_str}.{extension}"
