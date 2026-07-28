"""Извлечение и проверка параметров присадки из PDF-контекста."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


_LIMITS = {
    "cup_diameter_mm": (26, 35),
    "opening_angle_deg": (90, 180),
    "drill_offset_mm": (3, 30),
    "drill_depth_mm": (0, 16),
}


def _table_text(tables: Iterable[Any]) -> str:
    parts: list[str] = []
    for table in tables:
        rows = table.extract() if hasattr(table, "extract") else table
        for row in rows or []:
            if isinstance(row, str):
                parts.append(row)
            else:
                parts.append(" ".join(str(cell or "") for cell in row))
    return "\n".join(parts)


def _number_after(label: str, text: str) -> int | None:
    match = re.search(label + r"[^\d]{0,30}(\d{1,4})(?:\s*°|\s*мм)?", text, re.I)
    return int(match.group(1)) if match else None


def _valid(name: str, value: int | None) -> str | None:
    if value is None:
        return None
    low, high = _LIMITS[name]
    if not low <= value <= high:
        return None
    return str(value)
def extract_parameters(text: str, tables: Iterable[Any] = (), section_text: str = "") -> dict[str, str]:
    tabular = _table_text(tables)
    combined = "\n".join((text, tabular, section_text))
    params: dict[str, str] = {}
    cup = _number_after(r"(?:диаметр\s+чашки|чашк\w*|cup\s+diameter|cup)", combined)
    if cup is None:
        match = re.search(r"(?<!\d)(26|35)(?!\d)", tabular)
        cup = int(match.group(1)) if match else None
    value = _valid("cup_diameter_mm", cup)
    if value:
        params["cup_diameter_mm"] = value

    angle = _number_after(r"(?:угол\s+открывания|opening\s+(?:angle|corner)|installation\s+angle)", combined)
    if angle is None:
        match = re.search(r"\b(\d{2,3})\s*°", combined)
        angle = int(match.group(1)) if match else None
    value = _valid("opening_angle_deg", angle)
    if value:
        params["opening_angle_deg"] = value

    for name, label in (("drill_offset_mm", r"(?:отступ|смещени\w*|offset)"), ("drill_depth_mm", r"(?:глубин\w*|depth)")):
        value = _valid(name, _number_after(label, combined))
        if value:
            params[name] = value

    lowered = section_text.lower() + "\n" + text.lower()
    mount_markers = (("угловая-45", ("угловая", "45°", "45 °")), ("полунакладная", ("полунаклад",)),
                     ("вкладная", ("вкладн", "внутренняя")), ("накладная", ("накладн", "наружная")))
    for mount, markers in mount_markers:
        if any(marker in lowered for marker in markers):
            params["mount_type"] = mount
            break
    if re.search(r"\bclip[- ]?on\b|быстрого\s+монтажа", lowered):
        params["hinge_type"] = "clip_on"
    elif re.search(r"\bslide[- ]?on\b|шлицем\s+вводится", lowered):
        params["hinge_type"] = "slide_on"
    return params
