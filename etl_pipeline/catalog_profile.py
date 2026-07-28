"""Профиль каталога и подготовка страниц для его определения."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import fitz


@dataclass(frozen=True)
class CatalogProfile:
    catalog_id: str
    brand: str
    source: str
    sku_pattern: str
    sku_examples: list[str]
    type_markers: dict[str, list[str]]
    param_patterns: dict[str, str]
    notes: str = ""
    section_markers: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._compile(self.sku_pattern, "sku_pattern")
        if not self.catalog_id or not self.brand or not self.source:
            raise ValueError("catalog_id, brand и source не могут быть пустыми")
        if not self.sku_examples:
            raise ValueError("sku_examples не могут быть пустыми")
        for example in self.sku_examples:
            if not re.fullmatch(self.sku_pattern, example):
                raise ValueError(f"sku_examples содержит код вне sku_pattern: {example}")
        if not self.type_markers or any(not key or not values or any(not value for value in values)
                                        for key, values in self.type_markers.items()):
            raise ValueError("type_markers не могут содержать пустые маркеры")
        for name, pattern in self.param_patterns.items():
            self._compile(pattern, f"param_patterns.{name}")

    @staticmethod
    def _compile(pattern: str, field: str) -> None:
        try:
            re.compile(pattern)
        except re.error as error:
            raise ValueError(f"Некорректная регулярка {field}: {error}") from error

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CatalogProfile":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(cls, path: str | Path) -> "CatalogProfile":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_pages(pdf_path: str | Path, count: int) -> list[str]:
    """Возвращает тексты первых подходящих страниц с петлями и направляющими."""
    if count < 1:
        return []
    result: list[str] = []
    with fitz.open(pdf_path) as document:
        for page in document:
            text = page.get_text()
            lowered = text.lower()
            if "петл" in lowered or "направляющ" in lowered:
                result.append(text)
                if len(result) >= count:
                    break
    return result
