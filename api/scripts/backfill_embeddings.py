"""
Скрипт для создания embeddings для всех позиций фурнитуры.

Использует FRIDA (ai-forever/FRIDA) — лучшую модель для русского языка.
Batch-генерация для максимальной скорости.

Использование:
    uv run python -m api.scripts.backfill_embeddings [--limit N] [--batch-size N] [--force]
"""

import argparse
import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.future import select

from api.database import SessionLocal
from api.models import HardwareItem
from shared.embeddings import (
    EMBED_VERSION,
    EMBEDDING_PROVIDER,
    _content_fingerprint,
    concat_hardware_item_text,
    embed_batch_frida,
    embed_text,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(
    limit: int | None = None,
    batch_size: int = 64,
    force: bool = False
) -> None:
    """
    Генерация embeddings для фурнитуры.

    Args:
        limit: Максимальное количество позиций (None = все)
        batch_size: Размер батча для FRIDA (по умолчанию 64)
        force: Перегенерировать все, даже актуальные
    """
    logger.info(f"Запуск создания embeddings (провайдер: {EMBEDDING_PROVIDER})...")
    logger.info(f"Версия модели: {EMBED_VERSION}")

    async with SessionLocal() as session:
        # Выбираем элементы
        q = select(HardwareItem)
        if limit:
            q = q.limit(limit)

        res = await session.execute(q)
        items: list[HardwareItem] = list(res.scalars())

        logger.info(f"Найдено {len(items)} позиций")

        # Фильтруем — нужно обновить только те, у кого нет актуального embedding
        items_to_process: list[HardwareItem] = []
        texts: list[str] = []
        fingerprints: list[str] = []

        for item in items:
            text = concat_hardware_item_text(item)
            fingerprint = _content_fingerprint(item)

            # Пропускаем если embedding уже актуален (и не force)
            if not force and (
                item.embedding is not None
                and item.content_hash == fingerprint
                and item.embedding_version == EMBED_VERSION
            ):
                continue

            items_to_process.append(item)
            texts.append(text)
            fingerprints.append(fingerprint)

        skipped_count = len(items) - len(items_to_process)
        logger.info(f"К обработке: {len(items_to_process)}, пропущено: {skipped_count}")

        if not items_to_process:
            logger.info("Все embeddings актуальны!")
            return

        # Генерация embeddings
        if EMBEDDING_PROVIDER == "frida":
            # Batch-генерация для FRIDA — намного быстрее
            logger.info(f"Batch-генерация FRIDA (batch_size={batch_size})...")

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                batch_items = items_to_process[i : i + batch_size]
                batch_fingerprints = fingerprints[i : i + batch_size]

                logger.info(
                    f"Обработка батча {i // batch_size + 1}/"
                    f"{(len(texts) + batch_size - 1) // batch_size} "
                    f"({len(batch_texts)} позиций)..."
                )

                try:
                    embeddings = embed_batch_frida(batch_texts)

                    for item, emb, fingerprint in zip(
                        batch_items, embeddings, batch_fingerprints
                    ):
                        item.embedding = emb  # type: ignore[assignment]
                        item.embedding_version = EMBED_VERSION
                        item.content_hash = fingerprint
                        item.indexed_at = datetime.now(UTC)

                    await session.flush()
                    logger.info(f"Батч обработан успешно")

                except Exception as e:
                    logger.error(f"Ошибка батча: {e}")
                    # Продолжаем со следующим батчем

        else:
            # По одному для Yandex API
            logger.info("Последовательная генерация (Yandex API)...")

            for item, text, fingerprint in zip(
                items_to_process, texts, fingerprints
            ):
                logger.info(f"Обработка: {item.sku} - {item.name}")

                try:
                    emb = await embed_text(text)
                    item.embedding = emb  # type: ignore[assignment]
                    item.embedding_version = EMBED_VERSION
                    item.content_hash = fingerprint
                    item.indexed_at = datetime.now(UTC)
                    await session.flush()
                except Exception as e:
                    logger.error(f"Ошибка для {item.sku}: {e}")

        await session.commit()
        logger.info(f"Готово! Обработано: {len(items_to_process)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создание embeddings для фурнитуры")
    parser.add_argument("--limit", type=int, default=None, help="Лимит позиций")
    parser.add_argument(
        "--batch-size", type=int, default=64, help="Размер батча для FRIDA"
    )
    parser.add_argument(
        "--force", action="store_true", help="Перегенерировать все embeddings"
    )

    args = parser.parse_args()
    asyncio.run(main(args.limit, args.batch_size, args.force))
