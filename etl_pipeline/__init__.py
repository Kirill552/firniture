"""
ETL pipeline для парсинга каталогов фурнитуры Boyard.

Стратегия:
1. Стандартные параметры присадки захардкожены (из каталога стр. 8-13)
2. Артикулы извлекаются бесплатно через PyMuPDF
3. Параметры применяются к артикулам по категории (петля/направляющая/etc)

Использование:
    uv run python -m etl_pipeline.run extract
    uv run python -m etl_pipeline.run stats
    uv run python -m etl_pipeline.run params
"""
from .config import STANDARD_DRILLING_PARAMS, HINGE_TYPES
from .article_extractor import process_catalog, HardwareItem

__all__ = [
    "STANDARD_DRILLING_PARAMS",
    "HINGE_TYPES",
    "process_catalog",
    "HardwareItem",
]
