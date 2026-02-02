"""
Генератор G-code присадки для мебельных панелей.

Генерирует G-code напрямую из BOM, минуя DXF.
Поддерживает профили станков: weihong, syntec, fanuc, dsp, homag.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DrillingSide(str, Enum):
    """Сторона сверления."""
    FACE = "face"      # Пласть (лицевая сторона)
    EDGE = "edge"      # Торец


class HardwareType(str, Enum):
    """Тип крепежа."""
    CONFIRMAT = "confirmat"       # Конфирмат (евровинт)
    SHELF_PIN = "shelf_pin"       # Полкодержатель
    HINGE = "hinge"               # Петля (чашка 35мм)
    MINIFIX = "minifix"           # Минификс
    DOWEL = "dowel"               # Шкант


@dataclass
class DrillHole:
    """Отверстие под крепёж."""
    x: float                      # Координата X на панели (мм)
    y: float                      # Координата Y на панели (мм)
    diameter: float               # Диаметр сверла (мм): 5, 8, 15, 35
    depth: float                  # Глубина сверления (мм)
    side: DrillingSide            # Пласть или торец
    hardware_type: HardwareType   # Тип крепежа


@dataclass
class Slot:
    """Паз под заднюю стенку."""
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    width: float = 4.0            # Ширина паза (мм) — под ДВП
    depth: float = 10.0           # Глубина паза (мм)


@dataclass
class PanelDrilling:
    """Присадка одной панели."""
    panel_id: str
    panel_name: str               # "Боковина левая"
    width_mm: float               # 720
    height_mm: float              # 560
    thickness_mm: float           # 16

    holes: list[DrillHole] = field(default_factory=list)
    slots: list[Slot] = field(default_factory=list)

    # Метаданные для G-code
    order_id: str | None = None
    order_date: str | None = None


# =============================================================================
# Генератор G-code присадки
# =============================================================================

from api.gcode_generator import MACHINE_PROFILES


def _transliterate(text: str) -> str:
    """Транслитерация кириллицы для G-code комментариев."""
    table = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        ' ': '_',
    }
    result = []
    for char in text.lower():
        result.append(table.get(char, char))
    return ''.join(result)


def generate_panel_gcode(
    panel: PanelDrilling,
    profile_name: str = "weihong",
) -> str:
    """
    Генерация G-code присадки для одной панели.

    Args:
        panel: Данные панели с отверстиями и пазами
        profile_name: Имя профиля станка (weihong, syntec, fanuc, dsp, homag)

    Returns:
        Строка G-code
    """
    profile = MACHINE_PROFILES.get(profile_name)
    if not profile:
        raise ValueError(f"Неизвестный профиль станка: {profile_name}")

    lines: list[str] = []

    # Заголовок программы
    lines.extend(profile.program_start)
    panel_name_ascii = _transliterate(panel.panel_name)
    lines.append(f"({panel_name_ascii} {panel.width_mm:.0f}x{panel.height_mm:.0f}x{panel.thickness_mm:.0f})")
    if panel.order_id:
        lines.append(f"(Zakaz: {panel.order_id})")
    lines.append("")

    # Группируем отверстия по диаметру и стороне
    holes_by_tool: dict[tuple[float, DrillingSide], list[DrillHole]] = {}
    for hole in panel.holes:
        key = (hole.diameter, hole.side)
        if key not in holes_by_tool:
            holes_by_tool[key] = []
        holes_by_tool[key].append(hole)

    tool_number = 1

    # Генерируем G-code для каждой группы отверстий
    for (diameter, side), holes in sorted(holes_by_tool.items()):
        side_name = "plast" if side == DrillingSide.FACE else "torec"
        lines.append(f"(=== D{diameter:.0f} {side_name} ===)")

        # Смена инструмента
        lines.append(f"T{tool_number:02d} M06 (sverlo D{diameter:.0f})")
        lines.append(f"S{profile.spindle_speed} M03")

        # Пауза на разгон шпинделя
        if profile.dwell_unit == "milliseconds":
            lines.append("G04 P500")  # 0.5 сек для Weihong
        else:
            lines.append("G04 P0.5")  # 0.5 сек для остальных

        # Первое отверстие — полный цикл
        first_hole = holes[0]
        lines.append(f"G00 X{first_hole.x:.3f} Y{first_hole.y:.3f} Z{profile.safe_height:.1f}")
        lines.append("G99")  # Возврат на R-плоскость
        lines.append(f"G81 Z{-first_hole.depth:.3f} R{profile.drill_retract:.1f} F{profile.feed_rate_drilling}")

        # Остальные отверстия — только координаты (цикл повторяется)
        for hole in holes[1:]:
            lines.append(f"X{hole.x:.3f} Y{hole.y:.3f}")

        lines.append("G80")  # Отмена цикла
        lines.append("")
        tool_number += 1

    # Пазы под заднюю стенку
    if panel.slots:
        lines.append("(=== PAZ pod zadnyuyu stenku ===)")
        lines.append(f"T{tool_number:02d} M06 (freza D4)")
        lines.append(f"S{profile.spindle_speed} M03")

        if profile.dwell_unit == "milliseconds":
            lines.append("G04 P500")
        else:
            lines.append("G04 P0.5")

        for slot in panel.slots:
            lines.append(f"G00 X{slot.start_x:.3f} Y{slot.start_y:.3f} Z{profile.safe_height:.1f}")
            lines.append(f"G01 Z{-slot.depth:.3f} F{profile.feed_rate_plunge}")
            lines.append(f"G01 X{slot.end_x:.3f} Y{slot.end_y:.3f} F{profile.feed_rate_cutting}")
            lines.append(f"G00 Z{profile.safe_height:.1f}")

        lines.append("")

    # Завершение программы
    lines.extend(profile.program_end)

    return "\n".join(lines)


def generate_drilling_zip(
    panels: list[PanelDrilling],
    profile_name: str = "weihong",
    order_id: str | None = None,
) -> tuple[bytes, list[str]]:
    """
    Генерация ZIP архива с G-code для всех панелей.

    Args:
        panels: Список панелей с присадкой
        profile_name: Имя профиля станка
        order_id: ID заказа для README

    Returns:
        Tuple[bytes, list[str]]: (ZIP архив в байтах, список имён файлов)
    """
    buffer = io.BytesIO()
    filenames: list[str] = []

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for panel in panels:
            # Генерируем G-code
            gcode = generate_panel_gcode(panel, profile_name)

            # Формируем имя файла (транслит + размеры)
            name_ascii = _transliterate(panel.panel_name)
            filename = f"{name_ascii}_{panel.width_mm:.0f}x{panel.height_mm:.0f}.nc"
            filenames.append(filename)

            # Добавляем в архив
            zf.writestr(filename, gcode.encode('utf-8'))

        # README
        readme_lines = [
            f"Присадка для заказа: {order_id or 'N/A'}",
            f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Профиль станка: {profile_name}",
            f"Количество панелей: {len(panels)}",
            "",
            "Файлы:",
        ]
        for fn in filenames:
            readme_lines.append(f"  - {fn}")

        readme_lines.extend([
            "",
            "Сгенерировано: АвтоРаскрой (https://avtoraskroy.ru)",
        ])

        zf.writestr("README.txt", "\n".join(readme_lines).encode('utf-8'))
        filenames.append("README.txt")

    return buffer.getvalue(), filenames
