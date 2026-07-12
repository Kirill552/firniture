"""Тесты конфигурации AI (только OpenRouter)."""

from shared.ai_settings import AISettings


def test_ai_settings_contains_openrouter_fields_only() -> None:
    """Конфиг не должен содержать fallback на Yandex."""
    settings = AISettings(
        ai_base_url="https://openrouter.ai/api/v1",
        ai_api_key="test",
    )

    assert settings.ai_base_url.startswith("https://openrouter.ai/")
    assert hasattr(settings, "ai_chat_model")
    assert hasattr(settings, "ai_vision_model")
    assert hasattr(settings, "ai_embedding_model")

    assert not hasattr(settings, "ai_provider")
    assert not hasattr(settings, "yc_api_key")
    assert not hasattr(settings, "yc_folder_id")
