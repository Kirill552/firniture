"""
Yandex Cloud AI клиенты для мебель-ИИ проекта.

Поддерживаемые сервисы:
- YandexGPT (текстовая генерация)
- Yandex Embeddings (векторизация текста)
- Yandex Vision OCR (распознавание текста с изображений)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass
import json

from api.models import HardwareItem, ProductConfig
from shared.embeddings import concat_product_config_text

import aiohttp
from pydantic import BaseModel
from pydantic_settings import BaseSettings


log = logging.getLogger(__name__)


class YandexCloudSettings(BaseSettings):
    """Настройки Yandex Cloud API."""
    
    yc_folder_id: str
    yc_api_key: str
    
    # Endpoints
    yc_llm_endpoint: str = "https://llm.api.cloud.yandex.net"
    yc_ocr_endpoint: str = "https://ocr.api.cloud.yandex.net"
    
    # Модели
    yc_gpt_model: str = "gpt://{folder_id}/yandexgpt/latest"
    yc_embedding_doc_model: str = "emb://{folder_id}/text-search-doc/latest"
    yc_embedding_query_model: str = "emb://{folder_id}/text-search-query/latest"
    
    # Retry/timeout
    yc_timeout_seconds: int = 30
    yc_max_retries: int = 3
    yc_backoff_factor: float = 1.5
    
    class Config:
        env_prefix = ""


@dataclass
class EmbeddingResponse:
    """Ответ от Embeddings API."""
    embedding: List[float]
    num_tokens: int
    model_version: str


@dataclass
class GPTResponse:
    """Ответ от YandexGPT."""
    text: str
    usage: Dict[str, int]
    model_version: str


@dataclass
class OCRResponse:
    """Ответ от Vision OCR."""
    text: str
    confidence: float
    blocks: List[Dict[str, Any]]


class YandexCloudClient:
    """Базовый клиент для работы с Yandex Cloud API."""
    
    def __init__(self, settings: YandexCloudSettings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.settings.yc_timeout_seconds)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Заголовки авторизации."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.yc_api_key}",
            "x-folder-id": self.settings.yc_folder_id,
        }
    
    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """HTTP запрос с retry логикой."""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")
        
        last_error = None
        
        for attempt in range(self.settings.yc_max_retries + 1):
            try:
                log.debug(f"Yandex Cloud API {method} {url}, attempt {attempt + 1}")
                
                async with self.session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=self._get_headers(),
                    **kwargs
                ) as resp:
                    
                    if resp.status == 200:
                        result = await resp.json()
                        log.debug(f"Yandex Cloud API success: {method} {url}")
                        return result
                    
                    error_text = await resp.text()
                    log.warning(f"Yandex Cloud API error {resp.status}: {error_text}")
                    
                    if resp.status >= 500:  # Server errors -> retry
                        last_error = aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")
                    else:  # Client errors -> no retry
                        raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                log.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < self.settings.yc_max_retries:
                delay = self.settings.yc_backoff_factor ** attempt
                await asyncio.sleep(delay)
        
        raise last_error or RuntimeError("All retry attempts failed")


class YandexEmbeddingsClient(YandexCloudClient):
    """Клиент для Yandex Embeddings API."""
    
    async def get_embedding(
        self,
        text: str,
        model_type: str = "doc",  # "doc" или "query"
        dim: Optional[int] = None
    ) -> EmbeddingResponse:
        """Получить эмбеддинг для текста."""
        
        if model_type == "doc":
            model_uri = self.settings.yc_embedding_doc_model.replace("{folder_id}", self.settings.yc_folder_id)
        elif model_type == "query":
            model_uri = self.settings.yc_embedding_query_model.replace("{folder_id}", self.settings.yc_folder_id)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
        
        payload = {
            "modelUri": model_uri,
            "text": text
        }
        if dim:
            payload["dim"] = str(dim)
        
        url = f"{self.settings.yc_llm_endpoint}/foundationModels/v1/textEmbedding"
        
        response = await self._request_with_retry("POST", url, json_data=payload)
        
        return EmbeddingResponse(
            embedding=response["embedding"],
            num_tokens=int(response["numTokens"]),
            model_version=response["modelVersion"]
        )


class YandexGPTClient(YandexCloudClient):
    """Клиент для YandexGPT API."""
    
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> GPTResponse:
        """Генерация текста через YandexGPT."""
        
        model_uri = self.settings.yc_gpt_model.replace("{folder_id}", self.settings.yc_folder_id)
        
        payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "messages": [
                {"role": "user", "text": prompt}
            ]
        }
        
        url = f"{self.settings.yc_llm_endpoint}/foundationModels/v1/completion"
        
        response = await self._request_with_retry("POST", url, json_data=payload)
        
        result = response["result"]
        alternatives = result["alternatives"]
        if not alternatives:
            raise ValueError("Empty response from YandexGPT")
        
        message = alternatives[0]["message"]
        usage = result["usage"]
        
        return GPTResponse(
            text=message["text"],
            usage=usage,
            model_version=result.get("modelVersion", "unknown")
        )

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> AsyncGenerator[str, None]:
        """
        Генерация текста в режиме диалога с потоковой передачей.
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")

        model_uri = self.settings.yc_gpt_model.replace("{folder_id}", self.settings.yc_folder_id)
        
        payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": True,
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "messages": messages
        }
        
        url = f"{self.settings.yc_llm_endpoint}/foundationModels/v1/completionStream"
        
        async with self.session.post(url, json=payload, headers=self._get_headers()) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                log.error(f"YandexGPT streaming failed with status {resp.status}: {error_text}")
                raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")

            async for chunk in resp.content.iter_any():
                try:
                    chunk_str = chunk.decode('utf-8')
                    for part in chunk_str.split('\n'):
                        if part.strip():
                            data = json.loads(part)
                            alternatives = data.get("result", {}).get("alternatives", [])
                            if alternatives and "text" in alternatives[0]["message"]:
                                yield alternatives[0]["message"]["text"]
                except (json.JSONDecodeError, KeyError) as e:
                    log.warning(f"Could not decode or parse streaming chunk: {chunk}, error: {e}")
                    continue


class YandexVisionClient(YandexCloudClient):
    """Клиент для Yandex Vision OCR API."""
    
    async def extract_text_from_image(
        self,
        image_bytes: bytes,
        language_codes: Optional[List[str]] = None
    ) -> OCRResponse:
        """Извлечение текста из изображения."""
        
        if language_codes is None:
            language_codes = ["ru", "en"]
        
        import base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        payload = {
            "mimeType": "image/jpeg",
            "languageCodes": language_codes,
            "model": "page",
            "content": image_base64
        }
        
        url = f"{self.settings.yc_ocr_endpoint}/ocr/v1/recognizeText"
        
        response = await self._request_with_retry("POST", url, json_data=payload)
        
        result = response["result"]
        text_annotation = result.get("textAnnotation", {})
        
        full_text = text_annotation.get("fullText", "")
        
        blocks = text_annotation.get("blocks", [])
        total_confidence = 0.0
        confidence_count = 0
        
        for block in blocks:
            for line in block.get("lines", []):
                for word in line.get("words", []):
                    if "confidence" in word:
                        total_confidence += word["confidence"]
                        confidence_count += 1
        
        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        return OCRResponse(
            text=full_text,
            confidence=avg_confidence,
            blocks=blocks
        )


async def rank_hardware_with_gpt(
    product_config: ProductConfig,
    hardware_items: List[HardwareItem],
    settings: YandexCloudSettings
) -> List[HardwareItem]:
    """Ranks hardware items using YandexGPT."""
    
    prompt = f"""Given the following product configuration:
{concat_product_config_text(product_config)}

Rank the following hardware items based on their suitability for this product, from most to least suitable. Return a comma-separated list of SKUs.

Hardware items:
"""

    for item in hardware_items:
        prompt += f"- SKU: {item.sku}, Name: {item.name}, Params: {item.params}\n"

    async with create_gpt_client(settings) as client:
        response = await client.generate_text(prompt)
        ranked_skus = [sku.strip() for sku in response.text.split(',')]

    ranked_items = sorted(hardware_items, key=lambda item: ranked_skus.index(item.sku) if item.sku in ranked_skus else len(ranked_skus))
    return ranked_items

# Удобные фабрики

def create_embeddings_client(settings: YandexCloudSettings) -> YandexEmbeddingsClient:
    """Создать клиент эмбеддингов."""
    return YandexEmbeddingsClient(settings)


def create_gpt_client(settings: YandexCloudSettings) -> YandexGPTClient:
    """Создать клиент YandexGPT."""
    return YandexGPTClient(settings)


def create_vision_client(settings: YandexCloudSettings) -> YandexVisionClient:
    """Создать клиент Vision OCR."""
    return YandexVisionClient(settings)
