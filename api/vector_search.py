
from typing import List, Dict, Any, Optional

from sqlalchemy.future import select

from api.database import get_db
from api.models import HardwareItem
from pgvector.sqlalchemy import Vector


async def find_similar_hardware(
    embedding: List[float],
    k: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[HardwareItem]:
    """Finds similar hardware items using k-NN search."""
    async with get_db() as db:
        query = select(HardwareItem).order_by(HardwareItem.embedding.l2_distance(embedding)).limit(k)

        if filters:
            for key, value in filters.items():
                if hasattr(HardwareItem, key):
                    query = query.filter(getattr(HardwareItem, key) == value)

        result = await db.execute(query)
        return result.scalars().all()
