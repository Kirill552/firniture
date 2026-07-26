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

    # Embeddings: отдельный провайдер (опционально). Если не задано — ai_base_url.
    # Нужно, когда chat/vision и embeddings живут у разных провайдеров
    # (напр. Gonka для LLM + Cloud.ru bge-m3 для векторов).
    ai_embedding_base_url: str | None = None
    ai_embedding_api_key: str | None = None
    # Размерность векторной колонки hardware_items.embedding (миграция 1536→1024 под bge-m3)
    ai_embedding_dim: int = 1024

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
