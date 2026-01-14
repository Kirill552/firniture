"""
Импорт фурнитуры из JSON файла в БД.
Не требует pandas - только стандартные библиотеки + SQLAlchemy.

Использование:
    python -m api.scripts.import_hardware_json data/hardware_catalog.json
"""

import argparse
import asyncio
import json
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from api.database import SessionLocal
from api.models import HardwareItem as HardwareItemModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json(file_path: str) -> list[dict[str, Any]]:
    """Загружает данные из JSON файла."""
    with open(file_path, encoding='utf-8') as f:
        return json.load(f)


async def import_items(items: list[dict[str, Any]]) -> tuple[int, int]:
    """
    Импортирует позиции в БД.
    Возвращает (created, updated).
    """
    created = 0
    updated = 0

    async with SessionLocal() as db:
        for item_data in items:
            sku = item_data.get('sku')
            if not sku:
                logger.warning(f"Пропуск позиции без SKU: {item_data}")
                continue

            try:
                # Проверяем, существует ли позиция
                result = await db.execute(
                    select(HardwareItemModel).filter_by(sku=sku)
                )
                existing = result.scalars().first()

                # Преобразуем url в строку если это не None
                if 'url' in item_data and item_data['url'] is not None:
                    item_data['url'] = str(item_data['url'])

                if existing:
                    # Обновляем существующую позицию
                    for key, value in item_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    updated += 1
                    logger.info(f"Обновлено: {sku}")
                else:
                    # Создаём новую позицию
                    new_item = HardwareItemModel(**item_data)
                    db.add(new_item)
                    created += 1
                    logger.info(f"Создано: {sku}")

            except IntegrityError as e:
                await db.rollback()
                logger.error(f"Ошибка целостности для {sku}: {e}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Ошибка для {sku}: {e}")

        await db.commit()

    return created, updated


async def main(file_path: str):
    """Главная функция импорта."""
    logger.info(f"Загрузка данных из {file_path}")

    items = load_json(file_path)
    logger.info(f"Загружено {len(items)} позиций")

    created, updated = await import_items(items)

    logger.info(f"Импорт завершён: создано {created}, обновлено {updated}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Импорт фурнитуры из JSON")
    parser.add_argument("file_path", type=str, help="Путь к JSON файлу")

    args = parser.parse_args()
    asyncio.run(main(args.file_path))
