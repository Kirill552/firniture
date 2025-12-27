"""
Скрипт для создания embeddings для всех позиций фурнитуры.

Использование:
    python -m api.scripts.backfill_embeddings [--limit N]
"""

import argparse
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.future import select

from api.database import SessionLocal
from api.models import HardwareItem
from shared.embeddings import embed_text, concat_hardware_item_text, _content_fingerprint, EMBED_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(limit: int | None = None) -> None:
    logger.info("Запуск создания embeddings...")

    async with SessionLocal() as session:
        # Выбираем элементы без embedding или с устаревшим content_hash/version
        q = select(HardwareItem)
        if limit:
            q = q.limit(limit)

        res = await session.execute(q)
        items: list[HardwareItem] = list(res.scalars())

        logger.info(f"Найдено {len(items)} позиций")

        processed_count = 0
        skipped_count = 0

        for item in items:
            text = concat_hardware_item_text(item)
            fingerprint = _content_fingerprint(item)

            # Пропускаем если embedding уже актуален
            if (item.embedding is not None
                and item.content_hash == fingerprint
                and item.embedding_version == EMBED_VERSION):
                skipped_count += 1
                continue

            logger.info(f"Обработка: {item.sku} - {item.name}")

            try:
                emb = await embed_text(text)
                item.embedding = emb  # type: ignore[assignment]
                item.embedding_version = EMBED_VERSION
                item.content_hash = fingerprint
                item.indexed_at = datetime.now(timezone.utc)
                await session.flush()
                processed_count += 1
            except Exception as e:
                logger.error(f"Ошибка для {item.sku}: {e}")

        await session.commit()
        logger.info(f"Готово: обработано {processed_count}, пропущено {skipped_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создание embeddings для фурнитуры")
    parser.add_argument("--limit", type=int, default=None, help="Лимит позиций")

    args = parser.parse_args()
    asyncio.run(main(args.limit))
