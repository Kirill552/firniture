
from typing import Any

from sqlalchemy.future import select

from api.database import SessionLocal
from api.models import HardwareItem
from shared.embeddings import embed_query


async def find_similar_hardware(
    embedding: list[float],
    k: int = 10,
    filters: dict[str, Any] | None = None
) -> list[HardwareItem]:
    """Finds similar hardware items using k-NN search."""
    async with SessionLocal() as db:
        query = select(HardwareItem).order_by(HardwareItem.embedding.cosine_distance(embedding)).limit(k)

        if filters:
            for key, value in filters.items():
                if hasattr(HardwareItem, key):
                    query = query.filter(getattr(HardwareItem, key) == value)

        result = await db.execute(query)
        return result.scalars().all()


async def search_hardware_by_text(
    query_text: str,
    k: int = 10,
    filters: dict[str, Any] | None = None
) -> list[HardwareItem]:
    """
    Поиск фурнитуры по текстовому запросу.
    Использует text-search-query модель для embedding запроса.
    """
    query_embedding = await embed_query(query_text)
    return await find_similar_hardware(query_embedding, k=k, filters=filters)
