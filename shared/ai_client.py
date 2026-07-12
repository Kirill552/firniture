"""
Универсальный AI-клиент для OpenRouter (OpenAI-совместимый API).

Заменяет legacy-клиенты единым классом AIClient.
Поддерживает: chat, function calling, streaming, vision, embeddings.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import aiohttp

from shared.ai_settings import AISettings

log = logging.getLogger(__name__)


# --- Датаклассы ответов (совместимы со старым API) ---

@dataclass
class GPTResponse:
    """Ответ от LLM (текст)."""
    text: str
    usage: dict[str, int]
    model_version: str


@dataclass
class ToolCall:
    """Вызов инструмента от модели."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class GPTResponseWithTools:
    """Ответ от LLM с поддержкой tool calls."""
    text: str | None
    tool_calls: list[ToolCall]
    usage: dict[str, int]
    model_version: str
    finish_reason: str


# --- Основной клиент ---

class AIClient:
    """
    Универсальный AI-клиент OpenRouter.

    Singleton — получать через get_ai_client().
    Сессия создаётся лениво и живёт до закрытия.
    """

    def __init__(self, settings: AISettings) -> None:
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ленивое создание aiohttp-сессии."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.ai_timeout_seconds),
            )
        return self._session

    async def close(self) -> None:
        """Закрыть сессию (вызывать при shutdown приложения)."""
        if self._session and not self._session.closed:
            await self._session.close()

    # --- Заголовки, URL и модель ---

    def _headers(self) -> dict[str, str]:
        """Заголовки авторизации OpenRouter."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.ai_api_key}",
        }

    def _api_url(self, path: str) -> str:
        """Собрать URL API без двойных слешей."""
        base = self.settings.ai_base_url.rstrip("/")
        suffix = path.lstrip("/")
        return f"{base}/{suffix}"

    def _model(self, model: str | None, kind: str = "chat") -> str:
        """Получить имя модели по типу задачи."""
        if model:
            return model
        if kind == "vision":
            return self.settings.ai_vision_model
        if kind == "embedding":
            return self.settings.ai_embedding_model
        return self.settings.ai_chat_model

    # --- HTTP с retry ---

    async def _request(
        self,
        method: str,
        url: str,
        json_data: dict[str, Any],
    ) -> dict[str, Any]:
        """HTTP-запрос с retry (5xx — повтор, 4xx — сразу ошибка)."""
        session = await self._ensure_session()
        last_error: Exception | None = None

        for attempt in range(self.settings.ai_max_retries + 1):
            try:
                async with session.request(
                    method, url, json=json_data, headers=self._headers(),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()

                    error_text = await resp.text()
                    log.warning(f"AI API {resp.status}: {error_text[:300]}")

                    if resp.status >= 500:
                        last_error = aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")
                    else:
                        raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")

            except (TimeoutError, aiohttp.ClientError) as exc:
                last_error = exc
                log.warning(f"Попытка {attempt + 1} не удалась: {exc}")

            if attempt < self.settings.ai_max_retries:
                delay = 1.5 ** attempt
                await asyncio.sleep(delay)

        raise last_error or RuntimeError("Все попытки исчерпаны")

    # --- Chat Completion ---

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> GPTResponse:
        """Синхронная генерация текста (без streaming)."""
        resolved = self._model(model)
        payload = {
            "model": resolved,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.settings.ai_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.settings.ai_max_tokens,
            "stream": False,
        }
        url = self._api_url("/chat/completions")
        log.info(f"[AI] chat model={resolved}, messages={len(messages)}")

        data = await self._request("POST", url, payload)
        choice = data["choices"][0]

        return GPTResponse(
            text=choice["message"]["content"],
            usage=data.get("usage", {}),
            model_version=data.get("model", "unknown"),
        )

    # --- Chat Completion с инструментами ---

    async def chat_completion_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> GPTResponseWithTools:
        """Генерация с поддержкой Function Calling."""
        resolved = self._model(model)
        payload: dict[str, Any] = {
            "model": resolved,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.settings.ai_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.settings.ai_max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        url = self._api_url("/chat/completions")
        log.info(f"[AI] tools model={resolved}, tools={len(tools or [])}, messages={len(messages)}")

        data = await self._request("POST", url, payload)
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        # Парсим tool_calls с защитой от prompt-injection через typed dialogue contract
        tool_calls: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            func = tc.get("function") or {}
            raw_name = func.get("name") or ""
            raw_args_str = func.get("arguments") or "{}"
            args: dict[str, Any] = {}
            try:
                parsed_args_obj = json.loads(raw_args_str)
                if not isinstance(parsed_args_obj, dict):
                    parsed_args_obj = {}
                from api.ai.dialogue import ToolCall as DialogueToolCall
                from api.ai.dialogue import ToolError
                safe = DialogueToolCall.from_json(
                    json.dumps({"name": raw_name, "arguments": parsed_args_obj})
                )
                if isinstance(safe, ToolError):
                    log.warning(f"[AI] prompt-injection guard rejected tool call: {safe.code}")
                    args = {}
                else:
                    args = dict(safe.arguments)  # unfreeze for legacy dataclass
            except Exception:
                try:
                    args = json.loads(raw_args_str) if raw_args_str else {}
                except Exception:
                    args = {}
            tool_calls.append(ToolCall(
                id=tc.get("id", ""),
                name=raw_name,
                arguments=args,
            ))

        log.info(f"[AI] ответ: finish={finish_reason}, tools={len(tool_calls)}")

        return GPTResponseWithTools(
            text=message.get("content"),
            tool_calls=tool_calls,
            usage=data.get("usage", {}),
            model_version=data.get("model", "unknown"),
            finish_reason=finish_reason,
        )

    # --- Streaming ---

    async def stream_chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Потоковая генерация (SSE). Возвращает дельты текста."""
        session = await self._ensure_session()
        resolved = self._model(model)
        payload = {
            "model": resolved,
            "messages": messages,
            "temperature": temperature or self.settings.ai_temperature,
            "max_tokens": max_tokens or self.settings.ai_max_tokens,
            "stream": True,
        }
        url = self._api_url("/chat/completions")
        log.info(f"[AI] stream model={resolved}, messages={len(messages)}")

        async with session.post(url, json=payload, headers=self._headers()) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise aiohttp.ClientError(f"HTTP {resp.status}: {error_text}")

            async for line in resp.content:
                try:
                    line_str = line.decode("utf-8").strip()
                    if not line_str or line_str.startswith(":"):
                        continue
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            content = choices[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as exc:
                    log.warning(f"Ошибка парсинга SSE: {exc}")
                    continue

    # --- Vision (мультимодальный запрос) ---

    async def vision_extract(
        self,
        image_base64: str,
        prompt: str,
        model: str | None = None,
    ) -> GPTResponse:
        """Отправить изображение + промпт, получить текстовый ответ."""
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            ],
        }]
        return await self.chat_completion(messages, model=self._model(model, "vision"))

    # --- Embeddings ---

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """Получить эмбеддинг одного текста."""
        resolved = self._model(model, "embedding")
        payload = {"model": resolved, "input": text}
        url = self._api_url("/embeddings")

        data = await self._request("POST", url, payload)
        return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Получить эмбеддинги для списка текстов."""
        resolved = self._model(model, "embedding")
        payload = {"model": resolved, "input": texts}
        url = self._api_url("/embeddings")

        data = await self._request("POST", url, payload)
        # Сортируем по index, т.к. API может вернуть в другом порядке
        sorted_data = sorted(data["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in sorted_data]


# --- Singleton ---

_ai_client: AIClient | None = None


def get_ai_client() -> AIClient:
    """Получить singleton AI-клиент."""
    global _ai_client
    if _ai_client is None:
        settings = AISettings()
        _ai_client = AIClient(settings)
    return _ai_client
