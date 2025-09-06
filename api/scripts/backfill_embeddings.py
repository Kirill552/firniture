from shared.embeddings import embed_text, concat_hardware_item_text, _content_fingerprint, EMBED_VERSION


import logging

logger = logging.getLogger(__name__)

async def main(limit: int | None = None) -> None:
    logger.info("Starting embedding backfill...")
    async with SessionLocal() as session:
        # Выбираем элементы без embedding или с устаревшим content_hash/version
        q = select(HardwareItem)
        if limit:
            q = q.limit(limit)
        res = await session.execute(q)
        items: list[HardwareItem] = list(res.scalars())
        
        processed_count = 0
        for item in items:
            text = concat_hardware_item_text(item)
            fingerprint = _content_fingerprint(item)
            if item.embedding is not None and item.content_hash == fingerprint and item.embedding_version == EMBED_VERSION:
                continue
            
            logger.info(f"Processing item {item.sku}...")
            emb = await embed_text(text)
            item.embedding = emb  # type: ignore[assignment]
            item.embedding_version = EMBED_VERSION
            item.content_hash = fingerprint
            item.indexed_at = datetime.now(timezone.utc)
            await session.flush()
            processed_count += 1

        await session.commit()
        logger.info(f"Embedding backfill finished. Processed {processed_count} items.")



