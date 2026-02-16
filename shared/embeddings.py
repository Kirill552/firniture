"""
Модуль для генерации embeddings через OpenRouter API.

Использует AIClient (shared/ai_client.py) для доступа к API embeddings.
Fallback: детерминированный вектор на основе SHA256 (для тестов без API).
"""

import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.models import HardwareItem, ProductConfig

logger = logging.getLogger(__name__)

# Размерность вектора
EMBEDDING_DIM = 1536

# Версия модели для отслеживания изменений
EMBED_VERSION = "openai-3-small-v1"


# ============================================================================
# Fallback (детерминированный вектор)
# ============================================================================

def _fallback_embedding(text: str, dim: int = 1536) -> list[float]:
    """Детерминированный вектор на основе SHA256 (для тестов без API)."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vals: list[float] = []
    while len(vals) < dim:
        for b in h:
            vals.append((b - 128) / 128.0)
            if len(vals) >= dim:
                break
    return vals


# ============================================================================
# Публичный API
# ============================================================================

def _content_fingerprint(item: "HardwareItem") -> str:
    """Хэш содержимого для отслеживания изменений."""
    base = (
        (item.name or "")
        + "|" + (item.description or "")
        + "|" + (item.type or "")
        + "|" + (" ".join(item.compat or []))
        + "|" + str(item.params or {})
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


async def embed_text(text: str, model_type: str = "doc") -> list[float]:
    """Получить embedding через AI API."""
    from shared.ai_client import get_ai_client
    client = get_ai_client()
    return await client.embed_text(text)


async def embed_query(text: str) -> list[float]:
    """Embedding для поискового запроса."""
    return await embed_text(text)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batch embedding через AI API."""
    from shared.ai_client import get_ai_client
    client = get_ai_client()
    return await client.embed_batch(texts)


def concat_hardware_item_text(item: "HardwareItem") -> str:
    """Подготовка текста фурнитуры для embedding."""
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


def concat_product_config_text(product_config: "ProductConfig") -> str:
    """Подготовка текста конфигурации продукта для embedding."""
    parts: list[str] = []
    if product_config.name:
        parts.append(f"Name: {product_config.name}")
    if product_config.material:
        parts.append(f"Material: {product_config.material}")
    if product_config.thickness_mm:
        parts.append(f"Thickness: {product_config.thickness_mm} mm")
    if product_config.params:
        parts.append(f"Params: {product_config.params}")
    if product_config.notes:
        parts.append(f"Notes: {product_config.notes}")

    for panel in product_config.panels:
        parts.append(f"Panel: {panel.name} ({panel.width_mm}x{panel.height_mm}x{panel.thickness_mm})")

    return "\n".join(parts)
