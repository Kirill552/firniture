"""
Модуль для генерации embeddings.

Поддерживает два провайдера:
- FRIDA (ai-forever/FRIDA) — локальная модель, лучшее качество для русского языка
- Yandex Embeddings — облачный API (fallback)

Провайдер выбирается через переменную EMBEDDING_PROVIDER:
- "frida" (по умолчанию) — локальная модель FRIDA
- "yandex" — Yandex Cloud API
"""

import hashlib
import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.models import HardwareItem, ProductConfig

logger = logging.getLogger(__name__)

# Размерность вектора
EMBEDDING_DIM = 1536  # FRIDA использует 1536 (основана на FRED-T5)

# Версия модели для отслеживания изменений
EMBED_VERSION = "frida-1536-v1"

# Провайдер по умолчанию
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "frida").lower()


# ============================================================================
# FRIDA (локальная модель)
# ============================================================================

_frida_model = None


@lru_cache(maxsize=1)
def _get_frida_model():
    """Ленивая загрузка модели FRIDA (singleton)."""
    global _frida_model
    if _frida_model is None:
        logger.info("Загрузка модели FRIDA (ai-forever/FRIDA)...")
        try:
            from sentence_transformers import SentenceTransformer
            _frida_model = SentenceTransformer("ai-forever/FRIDA")
            logger.info("Модель FRIDA загружена успешно")
        except Exception as e:
            logger.error(f"Ошибка загрузки FRIDA: {e}")
            raise
    return _frida_model


def embed_text_frida(text: str) -> list[float]:
    """
    Получить embedding через FRIDA (синхронно).

    FRIDA — лидер ruMTEB бенчмарка, оптимизирована для русского языка.
    Размерность: 768
    """
    model = _get_frida_model()
    # FRIDA рекомендует использовать CLS pooling (по умолчанию)
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_batch_frida(texts: list[str]) -> list[list[float]]:
    """
    Batch embedding через FRIDA — эффективнее для больших объёмов.
    """
    model = _get_frida_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    return embeddings.tolist()


# ============================================================================
# Yandex Embeddings (облачный API) — fallback
# ============================================================================

async def embed_text_yandex(text: str, model_type: str = "doc") -> list[float]:
    """
    Получить embedding через Yandex Cloud API.

    Args:
        text: Текст для векторизации
        model_type: "doc" для индексации, "query" для поиска
    """
    from shared.yandex_ai import YandexCloudSettings, create_embeddings_client

    folder_id = os.getenv("YC_FOLDER_ID")
    api_key = os.getenv("YC_API_KEY")

    if not folder_id or not api_key:
        # Fallback: детерминированный вектор по SHA256
        return _fallback_embedding(text, dim=256)

    settings = YandexCloudSettings(yc_folder_id=folder_id, yc_api_key=api_key)
    async with create_embeddings_client(settings) as client:
        resp = await client.get_embedding(text, model_type=model_type)
        return resp.embedding


# ============================================================================
# Fallback (детерминированный вектор)
# ============================================================================

def _fallback_embedding(text: str, dim: int = 768) -> list[float]:
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
    """
    Получить embedding для текста.

    Провайдер выбирается через EMBEDDING_PROVIDER:
    - "frida" — локальная модель (768 dim)
    - "yandex" — Yandex Cloud API (256 dim)
    """
    if EMBEDDING_PROVIDER == "frida":
        # FRIDA — синхронная, но быстрая локально
        return embed_text_frida(text)
    else:
        return await embed_text_yandex(text, model_type)


def embed_text_sync(text: str) -> list[float]:
    """
    Синхронная версия embed_text (только для FRIDA).
    Удобно для batch-обработки без asyncio.
    """
    if EMBEDDING_PROVIDER == "frida":
        return embed_text_frida(text)
    else:
        raise RuntimeError("Синхронный режим доступен только для FRIDA")


async def embed_query(text: str) -> list[float]:
    """
    Embedding для поискового запроса.

    Для FRIDA используется та же модель (симметричный поиск).
    """
    return await embed_text(text, model_type="doc")


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
