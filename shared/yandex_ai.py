"""
Yandex Cloud AI клиенты для мебель-ИИ проекта.

Поддерживаемые сервисы:
- YandexGPT (текстовая генерация) - нативный и OpenAI-совместимый API
- Yandex Embeddings (векторизация текста)
- Yandex Vision OCR (распознавание текста с изображений)

OpenAI-совместимый API дает доступ к:
- Дополнительным параметрам (top_p, frequency_penalty, presence_penalty)
- Стандартному SSE streaming
- Будущим моделям (Alice AI LLM)
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

# Ленивый импорт concat_product_config_text для избежания circular import
import aiohttp
from pydantic_settings import BaseSettings

from api.models import HardwareItem, ProductConfig

log = logging.getLogger(__name__)


class YandexCloudSettings(BaseSettings):
    """Настройки Yandex Cloud API."""

    yc_folder_id: str
    yc_api_key: str

    # Endpoints
    yc_llm_endpoint: str = "https://llm.api.cloud.yandex.net"
    yc_openai_endpoint: str = "https://llm.api.cloud.yandex.net/v1"  # OpenAI-совместимый
    yc_ocr_endpoint: str = "https://ocr.api.cloud.yandex.net"

    # Модели (нативный API)
    yc_gpt_model: str = "gpt://{folder_id}/yandexgpt/latest"
    yc_embedding_doc_model: str = "emb://{folder_id}/text-search-doc/latest"
    yc_embedding_query_model: str = "emb://{folder_id}/text-search-query/latest"

    # Модели (OpenAI-совместимый API)
    yc_openai_model: str = "yandexgpt"  # yandexgpt, yandexgpt-lite, или alice (когда появится)

    # Параметры генерации по умолчанию
    yc_default_temperature: float = 0.3
    yc_default_top_p: float = 0.9
    yc_default_max_tokens: int = 2000

    # Retry/timeout
    yc_timeout_seconds: int = 60  # Увеличил для длинных ответов
    yc_max_retries: int = 3
    yc_backoff_factor: float = 1.5

    class Config:
        env_prefix = ""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Игнорируем POSTGRES_*, S3_* и другие переменные


@dataclass
class EmbeddingResponse:
    """Ответ от Embeddings API."""
    embedding: list[float]
    num_tokens: int
    model_version: str


@dataclass
class GPTResponse:
    """Ответ от YandexGPT."""
    text: str
    usage: dict[str, int]
    model_version: str


@dataclass
class OCRResponse:
    """Ответ от Vision OCR."""
    text: str
    confidence: float
    blocks: list[dict[str, Any]]


class YandexCloudClient:
    """Базовый клиент для работы с Yandex Cloud API."""
    
    def __init__(self, settings: YandexCloudSettings):
        self.settings = settings
        self.session: aiohttp.ClientSession | None = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.settings.yc_timeout_seconds)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> dict[str, str]:
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
        json_data: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
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
            
            except (TimeoutError, aiohttp.ClientError) as e:
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
        dim: int | None = None
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
        messages: list[dict[str, str]],
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
        
        url = f"{self.settings.yc_llm_endpoint}/foundationModels/v1/completion"
        
        async with self.session.post(url, json=payload, headers=self._get_headers()) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                log.error(f"YandexGPT streaming failed with status {resp.status}: {error_text}")
                raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")

            # YandexGPT возвращает полный текст в каждом чанке (кумулятивно)
            # Отслеживаем предыдущий текст, чтобы отправлять только дельту
            previous_text = ""

            async for chunk in resp.content.iter_any():
                try:
                    chunk_str = chunk.decode('utf-8')
                    for part in chunk_str.split('\n'):
                        if part.strip():
                            data = json.loads(part)
                            alternatives = data.get("result", {}).get("alternatives", [])
                            if alternatives and "text" in alternatives[0]["message"]:
                                full_text = alternatives[0]["message"]["text"]
                                # Вычисляем дельту - только новые символы
                                if len(full_text) > len(previous_text):
                                    delta = full_text[len(previous_text):]
                                    previous_text = full_text
                                    yield delta
                except (json.JSONDecodeError, KeyError) as e:
                    log.warning(f"Could not decode or parse streaming chunk: {chunk}, error: {e}")
                    continue


@dataclass
class ToolCall:
    """Вызов инструмента от модели."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class GPTResponseWithTools:
    """Ответ от YandexGPT с поддержкой tool calls."""
    text: str | None
    tool_calls: list[ToolCall]
    usage: dict[str, int]
    model_version: str
    finish_reason: str


class YandexOpenAIClient(YandexCloudClient):
    """
    Клиент для YandexGPT через OpenAI-совместимый API.

    Преимущества:
    - Стандартный SSE streaming
    - Дополнительные параметры (top_p, frequency_penalty, presence_penalty)
    - Совместимость с OpenAI SDK и LangChain
    - Поддержка Function Calling (tools)
    - Готовность к Alice AI LLM
    """

    def _get_openai_headers(self) -> dict[str, str]:
        """Заголовки для OpenAI-совместимого API."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.settings.yc_api_key}",
            "x-folder-id": self.settings.yc_folder_id,
        }

    def _get_model_uri(self) -> str:
        """Получить полный URI модели для OpenAI API."""
        # OpenAI-совместимый API требует полный URI: gpt://<folder_id>/<model>
        model = self.settings.yc_openai_model
        if not model.startswith("gpt://"):
            model = f"gpt://{self.settings.yc_folder_id}/{model}/latest"
        return model

    async def chat_completion_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> GPTResponseWithTools:
        """
        Генерация с поддержкой Function Calling (tools).

        Args:
            messages: История сообщений (включая tool results)
            tools: Список доступных инструментов в формате OpenAI
            tool_choice: "auto", "none", или {"type": "function", "function": {"name": "..."}}
            temperature: Температура генерации
            top_p: Nucleus sampling
            max_tokens: Максимум токенов

        Returns:
            GPTResponseWithTools с текстом и/или вызовами инструментов
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")

        payload = {
            "model": self._get_model_uri(),
            "messages": messages,
            "temperature": temperature or self.settings.yc_default_temperature,
            "top_p": top_p or self.settings.yc_default_top_p,
            "max_tokens": max_tokens or self.settings.yc_default_max_tokens,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        url = f"{self.settings.yc_openai_endpoint}/chat/completions"
        log.info(f"OpenAI API request with tools: model={payload['model']}, tools_count={len(tools or [])}")

        async with self.session.post(url, json=payload, headers=self._get_openai_headers()) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                log.error(f"YandexGPT OpenAI API with tools failed: {resp.status}: {error_text}")
                raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")

            data = await resp.json()
            choice = data["choices"][0]
            message = choice["message"]

            # Парсим tool_calls если есть
            tool_calls = []
            if "tool_calls" in message and message["tool_calls"]:
                for tc in message["tool_calls"]:
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        args = {}

                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc["function"]["name"],
                        arguments=args
                    ))

            return GPTResponseWithTools(
                text=message.get("content"),
                tool_calls=tool_calls,
                usage=data.get("usage", {}),
                model_version=data.get("model", "unknown"),
                finish_reason=choice.get("finish_reason", "stop")
            )

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
    ) -> GPTResponse:
        """
        Синхронная генерация через OpenAI-совместимый API.

        Args:
            messages: Список сообщений в формате [{"role": "system/user/assistant", "content": "..."}]
            temperature: Температура генерации (0.0-1.0)
            top_p: Nucleus sampling (0.0-1.0)
            max_tokens: Максимальное количество токенов
            frequency_penalty: Штраф за повторение токенов
            presence_penalty: Штраф за упоминание тем
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")

        payload = {
            "model": self._get_model_uri(),
            "messages": messages,
            "temperature": temperature or self.settings.yc_default_temperature,
            "top_p": top_p or self.settings.yc_default_top_p,
            "max_tokens": max_tokens or self.settings.yc_default_max_tokens,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "stream": False,
        }

        url = f"{self.settings.yc_openai_endpoint}/chat/completions"

        async with self.session.post(url, json=payload, headers=self._get_openai_headers()) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                log.error(f"YandexGPT OpenAI API failed with status {resp.status}: {error_text}")
                raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")

            data = await resp.json()
            choice = data["choices"][0]

            return GPTResponse(
                text=choice["message"]["content"],
                usage=data.get("usage", {}),
                model_version=data.get("model", "unknown")
            )

    async def stream_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
    ) -> AsyncGenerator[str, None]:
        """
        Потоковая генерация через OpenAI-совместимый API (SSE).

        Использует стандартный формат Server-Sent Events.
        Возвращает дельты (только новые символы).
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")

        payload = {
            "model": self._get_model_uri(),
            "messages": messages,
            "temperature": temperature or self.settings.yc_default_temperature,
            "top_p": top_p or self.settings.yc_default_top_p,
            "max_tokens": max_tokens or self.settings.yc_default_max_tokens,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "stream": True,
        }

        url = f"{self.settings.yc_openai_endpoint}/chat/completions"
        log.info(f"OpenAI API request: model={payload['model']}, url={url}")

        async with self.session.post(url, json=payload, headers=self._get_openai_headers()) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                log.error(f"YandexGPT OpenAI streaming failed with status {resp.status}: {error_text}")
                raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")

            # SSE формат: data: {...}\n\n
            async for line in resp.content:
                try:
                    line_str = line.decode('utf-8').strip()

                    # Пропускаем пустые строки и комментарии
                    if not line_str or line_str.startswith(':'):
                        continue

                    # SSE data event
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Убираем 'data: '

                        # Конец потока
                        if data_str == '[DONE]':
                            break

                        data = json.loads(data_str)
                        choices = data.get("choices", [])

                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content

                except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                    log.warning(f"Could not parse SSE chunk: {line}, error: {e}")
                    continue


class YandexVisionClient(YandexCloudClient):
    """Клиент для Yandex Vision OCR API."""
    
    async def extract_text_from_image(
        self,
        image_bytes: bytes,
        language_codes: list[str] | None = None
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
    hardware_items: list[HardwareItem],
    settings: YandexCloudSettings
) -> list[HardwareItem]:
    """Ranks hardware items using YandexGPT."""
    # Ленивый импорт для избежания circular import
    from shared.embeddings import concat_product_config_text

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
    """Создать клиент YandexGPT (нативный API)."""
    return YandexGPTClient(settings)


def create_openai_client(settings: YandexCloudSettings) -> YandexOpenAIClient:
    """
    Создать клиент YandexGPT через OpenAI-совместимый API.

    Рекомендуется использовать этот клиент для:
    - Тонкой настройки генерации (top_p, penalties)
    - Стандартного SSE streaming
    - Совместимости с OpenAI экосистемой
    """
    return YandexOpenAIClient(settings)


def create_vision_client(settings: YandexCloudSettings) -> YandexVisionClient:
    """Создать клиент Vision OCR."""
    return YandexVisionClient(settings)
