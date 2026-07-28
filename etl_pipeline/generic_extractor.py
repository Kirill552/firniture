"""Извлечение номенклатуры из PDF по профилю каталога."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz

from .catalog_profile import CatalogProfile
from .param_extraction import extract_parameters


def _line_name(lines: list[str], index: int, sku: str) -> str:
    candidates = [lines[index]]
    candidates.extend(lines[index - 1::-1])
    candidates.extend(lines[index + 1:])
    for line in candidates:
        clean = " ".join(line.split())
        if len(clean) < 3 or clean.isdigit() or clean == sku:
            continue
        if re.fullmatch(r"[\d\s.,°ø×x/+-]+", clean):
            continue
        return clean
    return sku


def _position_type(text: str, start: int, markers: dict[str, list[str]]) -> str | None:
    context = text[max(0, start - 180):start + 180].lower()
    for position_type, words in markers.items():
        if any(word.lower() in context for word in words):
            return position_type
    return None


def _parameters(text: str, patterns: dict[str, str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            params[name] = match.group(1) if match.lastindex else match.group(0)
    return params


def extract(pdf_path: str | Path, profile: CatalogProfile) -> list[dict[str, Any]]:
    """Извлекает позиции, не подставляя отсутствующие параметры."""
    sku_re = re.compile(profile.sku_pattern, re.IGNORECASE)
    positions: dict[str, dict[str, Any]] = {}
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text()
            if not text:
                continue
            lines = text.splitlines()
            try:
                tables = page.find_tables().tables
            except (AttributeError, RuntimeError):
                tables = []
            marker_words = [word for words in profile.section_markers.values() for word in words]
            section_text = "\n".join(
                line for line in lines[:30]
                if any(word.lower() in line.lower() for word in marker_words)
            )
            page_params = extract_parameters(text, tables, section_text)
            page_params.update(
                {key: value for key, value in _parameters(text, profile.param_patterns).items()
                 if key not in page_params}
            )
            for match in sku_re.finditer(text):
                sku = match.group(0)
                kind = _position_type(text, match.start(), profile.type_markers)
                params = dict(page_params)
                candidate = {
                    "sku": sku,
                    "name": _line_name(lines, text[:match.start()].count("\n"), sku),
                    "type": kind or "не определён",
                    "brand": profile.brand,
                    "params": params,
                    "page": page_number,
                    "needs_review": not params or kind is None,
                }
                current = positions.get(sku)
                if current is None or (len(candidate["params"]), candidate["type"] != "не определён") > (
                    len(current["params"]), current["type"] != "не определён"
                ):
                    positions[sku] = candidate
    return list(positions.values())
