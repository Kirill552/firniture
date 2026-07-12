"""Настройки AI для OpenRouter."""

from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    """Настройки AI-клиента (OpenRouter)."""

    ai_base_url: str = "https://openrouter.ai/api/v1"
    ai_api_key: str = ""

    # Модели
    ai_chat_model: str = "deepseek/deepseek-chat-v3-0324"
    ai_vision_model: str = "google/gemini-2.0-flash-001"
    ai_embedding_model: str = "openai/text-embedding-3-small"

    # Параметры генерации
    ai_temperature: float = 0.3
    ai_max_tokens: int = 2000
    ai_timeout_seconds: int = 60
    ai_max_retries: int = 3

    class Config:
        env_prefix = ""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
