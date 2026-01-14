
import hashlib
import os

from api.models import HardwareItem, ProductConfig
from shared.yandex_ai import YandexCloudSettings, create_embeddings_client

EMBED_VERSION = "yc-text-emb-doc-latest-256"


def _content_fingerprint(item: HardwareItem) -> str:
    base = (
        (item.name or "")
        + "|" + (item.description or "")
        + "|" + (item.type or "")
        + "|" + (" ".join(item.compat or []))
        + "|" + str(item.params or {{}})
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


async def embed_text(text: str, model_type: str = "doc") -> list[float]:
    """
    Получить embedding для текста.

    Args:
        text: Текст для векторизации
        model_type: "doc" для индексации документов, "query" для поисковых запросов
                   Yandex использует асимметричный поиск — разные модели для doc/query!
    """
    folder_id = os.getenv("YC_FOLDER_ID")
    api_key = os.getenv("YC_API_KEY")
    if not folder_id or not api_key:
        # Фолбэк: детерминированный вектор по SHA256
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vals: list[float] = []
        while len(vals) < 256:
            for b in h:
                vals.append((b - 128) / 128.0)
                if len(vals) >= 256:
                    break
        return vals

    settings = YandexCloudSettings(yc_folder_id=folder_id, yc_api_key=api_key)
    async with create_embeddings_client(settings) as client:
        resp = await client.get_embedding(text, model_type=model_type)
        return resp.embedding


async def embed_query(text: str) -> list[float]:
    """
    Embedding для поискового запроса.

    Примечание: Yandex рекомендует text-search-query для запросов,
    но для коротких описаний фурнитуры симметричный поиск (doc-doc)
    даёт лучшие результаты.
    """
    return await embed_text(text, model_type="doc")


def concat_hardware_item_text(item: HardwareItem) -> str:
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


def concat_product_config_text(product_config: ProductConfig) -> str:
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
