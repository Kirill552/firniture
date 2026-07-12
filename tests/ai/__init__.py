"""
Записанные (recorded) заглушки для внешних сервисов AI, SMTP, S3.

В тестах с пустым AI_API_KEY используется эта фиктивная реализация,
а не реальные HTTP-вызовы. Это explicitly domain state:
пустой ключ = mock-режим, никаких "Bearer " + retry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- Recorded AI responses ---

RECORDED_CHAT_RESPONSE: dict[str, Any] = {
    "id": "fake-chat-completion-001",
    "object": "chat.completion",
    "model": "deepseek/deepseek-chat-v3-0324",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"panels": [], "total_area_m2": 0.0}',
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 42,
        "completion_tokens": 12,
        "total_tokens": 54,
    },
}

RECORDED_VISION_RESPONSE: dict[str, Any] = {
    "id": "fake-vision-completion-001",
    "object": "chat.completion",
    "model": "google/gemini-2.0-flash-001",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"width_mm": 600, "height_mm": 720, "depth_mm": 300}',
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
    },
}

RECORDED_EMBEDDING_RESPONSE: dict[str, Any] = {
    "object": "list",
    "model": "openai/text-embedding-3-small",
    "data": [
        {
            "object": "embedding",
            "index": 0,
            "embedding": [0.001] * 1536,
        }
    ],
    "usage": {
        "prompt_tokens": 5,
        "total_tokens": 5,
    },
}

RECORDED_TOOL_CALL_RESPONSE: dict[str, Any] = {
    "id": "fake-tool-completion-001",
    "object": "chat.completion",
    "model": "deepseek/deepseek-chat-v3-0324",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_fake_001",
                        "type": "function",
                        "function": {
                            "name": "extract_cabinet_spec",
                            "arguments": '{"width_mm": 600, "height_mm": 720, "depth_mm": 300}',
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 30,
        "total_tokens": 80,
    },
}


# --- Fake AI Client (singleton replacement) ---

@dataclass
class FakeAIClient:
    """
    Минимальная подмена AIClient для тестов.
    Возвращает recorded-ответы без HTTP-вызовов.
    """
    _chat_responses: list[dict[str, Any]] = field(default_factory=lambda: [RECORDED_CHAT_RESPONSE])
    _vision_responses: list[dict[str, Any]] = field(default_factory=lambda: [RECORDED_VISION_RESPONSE])
    _embedding_responses: list[dict[str, Any]] = field(default_factory=lambda: [RECORDED_EMBEDDING_RESPONSE])
    _tool_call_responses: list[dict[str, Any]] = field(default_factory=lambda: [RECORDED_TOOL_CALL_RESPONSE])
    _call_log: list[dict[str, Any]] = field(default_factory=list)

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> Any:
        from shared.ai_client import GPTResponse
        self._call_log.append({"type": "chat", "model": model, "messages_count": len(messages)})
        data = self._chat_responses[0]
        choice = data["choices"][0]
        return GPTResponse(
            text=choice["message"]["content"],
            usage=data["usage"],
            model_version=data["model"],
        )

    async def chat_completion_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> Any:
        from shared.ai_client import GPTResponseWithTools, ToolCall
        self._call_log.append({"type": "tools", "model": model, "tools_count": len(tools)})
        data = self._tool_call_responses[0]
        choice = data["choices"][0]
        msg = choice["message"]
        tc_list = [
            ToolCall(id=tc["id"], name=tc["function"]["name"], arguments=__import__("json").loads(tc["function"]["arguments"]))
            for tc in msg.get("tool_calls", [])
        ]
        return GPTResponseWithTools(
            text=msg.get("content"),
            tool_calls=tc_list,
            usage=data["usage"],
            model_version=data["model"],
            finish_reason=choice["finish_reason"],
        )

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        self._call_log.append({"type": "embed", "model": model, "count": len(texts)})
        return [RECORDED_EMBEDDING_RESPONSE["data"][0]["embedding"]] * len(texts)

    async def close(self) -> None:
        pass
