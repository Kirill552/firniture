"""
Импорт каталога фурнитуры Boyard 2024 в БД.
Объединяет все ETL JSON файлы и загружает в hardware_items.

Использование:
    uv run python -m api.scripts.import_boyard
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import delete, text

from api.database import SessionLocal
from api.models import HardwareItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути к ETL файлам
ETL_OUTPUT = Path(__file__).parent.parent.parent / "etl_pipeline" / "output"

# Маппинг файлов на типы фурнитуры
FILE_MAPPINGS = [
    ("Каталог функциональной фурнитуры BOYARD 2024 _hardware.json", "петля"),
    ("Каталог лицевой фурнитуры BOYARD 2024_handles.json", "ручка"),
    ("Каталог функциональной фурнитуры BOYARD 2024 _slides.json", "направляющая"),
    ("Каталог функциональной фурнитуры BOYARD 2024 _lifters.json", "подъёмник"),
    ("Каталог функциональной фурнитуры BOYARD 2024 _supports.json", "опора"),
]


def load_json(file_path: Path) -> list[dict[str, Any]]:
    """Загружает данные из JSON файла."""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def normalize_type(category: str) -> str:
    """Нормализует категорию в тип фурнитуры."""
    category_lower = category.lower()

    if "петл" in category_lower or "планка" in category_lower:
        return "петля"
    elif "ручк" in category_lower:
        return "ручка"
    elif "направляющ" in category_lower or "роликов" in category_lower or "шариков" in category_lower:
        return "направляющая"
    elif "подъём" in category_lower or "газлифт" in category_lower:
        return "подъёмник"
    elif "опор" in category_lower or "колёс" in category_lower or "ножк" in category_lower:
        return "опора"
    else:
        return category_lower


def build_description(item: dict[str, Any], hw_type: str) -> str:
    """Формирует описание для поиска."""
    parts = []

    name = item.get("name", "")
    category = item.get("category", "")
    series = item.get("series", "")

    if name:
        parts.append(name)
    if series and series != name:
        parts.append(f"серия {series}")
    if category:
        parts.append(category)

    # Технические характеристики
    if hw_type == "петля":
        if item.get("cup_diameter"):
            parts.append(f"чашка {item['cup_diameter']}мм")
        if item.get("drilling_depth"):
            parts.append(f"глубина сверления {item['drilling_depth']}мм")
        if item.get("hinge_type"):
            parts.append(item["hinge_type"].replace("_", " "))
        if item.get("features"):
            parts.extend(item["features"])

    elif hw_type == "ручка":
        if item.get("center_distance"):
            parts.append(f"межцентровое {item['center_distance']}мм")
        if item.get("length"):
            parts.append(f"длина {item['length']}мм")
        if item.get("color"):
            parts.append(item["color"])

    elif hw_type == "направляющая":
        if item.get("length"):
            parts.append(f"длина {item['length']}мм")
        if item.get("load_capacity"):
            parts.append(f"нагрузка {item['load_capacity']}кг")
        if item.get("slide_type"):
            parts.append(item["slide_type"])
        if item.get("soft_close"):
            parts.append("с доводчиком")
        if item.get("color"):
            parts.append(item["color"])

    elif hw_type == "подъёмник":
        if item.get("force"):
            parts.append(f"усилие {item['force']}Н")
        if item.get("opening_angle"):
            parts.append(f"угол {item['opening_angle']}°")
        if item.get("color"):
            parts.append(item["color"])

    elif hw_type == "опора":
        if item.get("height"):
            parts.append(f"высота {item['height']}мм")
        if item.get("load_capacity"):
            parts.append(f"нагрузка {item['load_capacity']}кг")
        if item.get("color"):
            parts.append(item["color"])

    return " | ".join(parts) if parts else f"Фурнитура BOYARD {hw_type}"


def convert_item(item: dict[str, Any], default_type: str) -> dict[str, Any]:
    """Конвертирует ETL item в формат HardwareItem."""
    article = item.get("article", "")
    if not article:
        return None

    category = item.get("category", default_type)
    hw_type = normalize_type(category)

    # Собираем все технические параметры в params
    params = {}
    exclude_keys = {"article", "name", "category", "source_page", "source_file"}

    for key, value in item.items():
        if key not in exclude_keys and value is not None:
            params[key] = value

    return {
        "sku": article,
        "brand": "BOYARD",
        "type": hw_type,
        "name": item.get("name", ""),
        "description": build_description(item, hw_type),
        "category": category,
        "params": params,
        "compat": [],  # TODO: добавить совместимость по толщине
        "is_active": True,
    }


async def clear_hardware_items(db) -> int:
    """Очищает таблицу hardware_items. Возвращает количество удалённых."""
    result = await db.execute(text("SELECT COUNT(*) FROM hardware_items"))
    count = result.scalar()

    await db.execute(delete(HardwareItem))
    await db.commit()

    return count


async def import_items(items: list[dict[str, Any]], db) -> tuple[int, int]:
    """Импортирует позиции в БД. Возвращает (created, skipped)."""
    created = 0
    skipped = 0

    for item_data in items:
        if not item_data:
            skipped += 1
            continue

        try:
            new_item = HardwareItem(**item_data)
            db.add(new_item)
            created += 1
        except Exception as e:
            logger.warning(f"Ошибка для {item_data.get('sku')}: {e}")
            skipped += 1

    await db.commit()
    return created, skipped


async def main():
    """Главная функция импорта."""
    logger.info("=" * 60)
    logger.info("Импорт каталога Boyard 2024")
    logger.info("=" * 60)

    # Собираем все данные
    all_items = []
    stats = {}

    for filename, default_type in FILE_MAPPINGS:
        file_path = ETL_OUTPUT / filename
        if not file_path.exists():
            logger.warning(f"Файл не найден: {filename}")
            continue

        raw_items = load_json(file_path)
        converted = [convert_item(item, default_type) for item in raw_items]
        converted = [x for x in converted if x]  # Убираем None

        all_items.extend(converted)
        stats[default_type] = len(converted)
        logger.info(f"  {default_type}: {len(converted)} позиций")

    logger.info(f"Всего подготовлено: {len(all_items)} позиций")

    # Проверяем дубликаты SKU
    skus = [item["sku"] for item in all_items]
    duplicates = len(skus) - len(set(skus))
    if duplicates > 0:
        logger.warning(f"Найдено дубликатов SKU: {duplicates}")
        # Убираем дубликаты, оставляя первый
        seen = set()
        unique_items = []
        for item in all_items:
            if item["sku"] not in seen:
                seen.add(item["sku"])
                unique_items.append(item)
        all_items = unique_items
        logger.info(f"После дедупликации: {len(all_items)} позиций")

    # Импорт в БД
    async with SessionLocal() as db:
        # Очистка
        deleted = await clear_hardware_items(db)
        logger.info(f"Удалено старых записей: {deleted}")

        # Импорт
        created, skipped = await import_items(all_items, db)
        logger.info(f"Создано: {created}, пропущено: {skipped}")

    logger.info("=" * 60)
    logger.info("Импорт завершён!")
    logger.info("Следующий шаг: uv run python -m api.scripts.backfill_embeddings")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
