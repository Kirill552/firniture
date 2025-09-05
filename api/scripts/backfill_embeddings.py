from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import SessionLocal
from api.models import HardwareItem
from pgvector.sqlalchemy import Vector
from shared.yandex_ai import YandexCloudSettings, create_embeddings_client


EMBED_VERSION = "yc-text-emb-doc-latest-256"


def _content_fingerprint(item: HardwareItem) -> str:
    base = (
        (item.name or "")
        + "|" + (item.description or "")
        + "|" + (item.type or "")
        + "|" + (" ".join((item.compat or [])))
        + "|" + str(item.params or {})
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


async def _embed_text(text: str) -> list[float]:
    # Читаем ключи из env; если отсутствуют — используем фолбэк (детерминированный)
    folder_id = os.getenv("yc_folder_id")
    api_key = os.getenv("yc_api_key")
    if not folder_id or not api_key:
        # Фолбэк: детерминированный вектор по SHA256
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # растянем до 256 значений
        vals: list[float] = []
        while len(vals) < 256:
            for b in h:
                vals.append((b - 128) / 128.0)
                if len(vals) >= 256:
                    break
        return vals

    settings = YandexCloudSettings(yc_folder_id=folder_id, yc_api_key=api_key)
    async with create_embeddings_client(settings) as client:
        resp = await client.get_embedding(text, model_type="doc")
        return resp.embedding


def _concat_item_text(item: HardwareItem) -> str:
    parts: list[str] = []
    parts.append(f"SKU: {item.sku}")
    if item.brand:
        parts.append(f"Brand: {item.brand}")
    parts.append(f"Type: {item.type}")
    if item.name:
        parts.append(f"Name: {item.name}")
    if item.description:
        parts.append(f"Desc: {item.description}")
    if item.category:
        parts.append(f"Category: {item.category}")
    if item.material_type:
        parts.append(f"Material: {item.material_type}")
    if item.thickness_min_mm is not None or item.thickness_max_mm is not None:
        parts.append(
            f"Thickness: {item.thickness_min_mm or ''}-{item.thickness_max_mm or ''} mm"
        )
    if item.params:
        parts.append(f"Params: {item.params}")
    if item.compat:
        parts.append("Compat: " + ", ".join(item.compat))
    return "\n".join(parts)


async def backfill(limit: int | None = None) -> None:
    async with SessionLocal() as session:
        # Выбираем элементы без embedding или с устаревшим content_hash/version
        q = select(HardwareItem)
        if limit:
            q = q.limit(limit)
        res = await session.execute(q)
        items: list[HardwareItem] = list(res.scalars())

        for item in items:
            text = _concat_item_text(item)
            fingerprint = _content_fingerprint(item)
            if item.embedding and item.content_hash == fingerprint and item.embedding_version == EMBED_VERSION:
                continue
            emb = await _embed_text(text)
            item.embedding = emb  # type: ignore[assignment]
            item.embedding_version = EMBED_VERSION
            item.content_hash = fingerprint
            item.indexed_at = datetime.now(timezone.utc)
            await session.flush()

        await session.commit()


if __name__ == "__main__":
    asyncio.run(backfill())
