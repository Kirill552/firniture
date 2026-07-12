"""Фокусные тесты ``api.runtime_settings.validate_runtime_settings``.

Все тесты работают с явными dict-окружениями — ни одного реального секрета.
"""

from __future__ import annotations

import pytest

from api.runtime_settings import (
    RuntimeValidationResult,
    validate_runtime_settings,
)

# ── Production-like valid env ──────────────────────────────────────

def _prod_env(**overrides: str) -> dict[str, str]:
    """Minimal production-like env. Override specific keys as needed."""
    base = {
        "JWT_SECRET": "a3f8c1e29b4d7065ef123456789abcdef01234567890",
        "S3_SECRET_KEY": "s3_prd_s3cr3t_k3y_2026_long_enough",
        "S3_ACCESS_KEY": "s3_prd_access_key_2026",
        "S3_PUBLIC_ENDPOINT_URL": "https://storage.mebel-ai.ru",
        "POSTGRES_PASSWORD": "pg_prd_s3cur3_p4ssw0rd_2026",
        "AI_API_KEY": "sk-or-v1-real-key-here",
        "AI_CHAT_MODEL": "deepseek/deepseek-chat-v3-0324",
        "AI_VISION_MODEL": "google/gemini-2.0-flash-001",
        "AI_EMBEDDING_MODEL": "openai/text-embedding-3-small",
        "FRONTEND_URL": "https://app.mebel-ai.ru",
        "CORS_ORIGINS": "https://app.mebel-ai.ru,https://admin.mebel-ai.ru",
    }
    base.update(overrides)
    return base


# ── Mock mode ──────────────────────────────────────────────────────

class TestMockMode:
    """MOCK_MODE=true пропускает все проверки."""

    @pytest.mark.parametrize("flag", ["true", "1", "yes", "TRUE", "Yes"])
    def test_mock_mode_any_truthy_skips_all(self, flag: str) -> None:
        env = {"MOCK_MODE": flag}
        result = validate_runtime_settings(env=env)
        assert result.ok
        assert len(result.errors) == 0

    def test_mock_mode_allows_empty_jwt(self) -> None:
        env = {"MOCK_MODE": "true", "JWT_SECRET": ""}
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_mock_mode_allows_default_minio(self) -> None:
        env = {"MOCK_MODE": "true", "S3_SECRET_KEY": "minio123"}
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_mock_mode_allows_wildcard_cors(self) -> None:
        env = {"MOCK_MODE": "true", "CORS_ORIGINS": "*"}
        result = validate_runtime_settings(env=env)
        assert result.ok


class TestMockModeFalse:
    """MOCK_MODE=false или отсутствие — проверки активны."""

    def test_empty_mock_mode_is_not_mock(self) -> None:
        env: dict[str, str] = {"MOCK_MODE": ""}
        result = validate_runtime_settings(env=env)
        # Должен найти ошибки (JWT пустой и т.д.)
        assert not result.ok

    def test_mock_mode_false_is_not_mock(self) -> None:
        env = {"MOCK_MODE": "false"}
        result = validate_runtime_settings(env=env)
        assert not result.ok


# ── JWT validation ─────────────────────────────────────────────────

class TestJWTSecret:
    def test_empty_rejected(self) -> None:
        env = _prod_env(JWT_SECRET="")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("JWT_SECRET" in e for e in result.errors)

    def test_placeholder_rejected(self) -> None:
        env = _prod_env(JWT_SECRET="CHANGE_ME")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("JWT_SECRET" in e for e in result.errors)

    def test_known_unsafe_rejected(self) -> None:
        env = _prod_env(
            JWT_SECRET="CHANGE_ME_IN_PRODUCTION_super_secret_key_2026"
        )
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("JWT_SECRET" in e for e in result.errors)

    def test_valid_secret_accepted(self) -> None:
        env = _prod_env(
            JWT_SECRET="xK9mP2vL8nQ4wR7jT1yH5bF3dG6aS0cE"
        )
        result = validate_runtime_settings(env=env)
        assert result.ok
    def test_short_secret_rejected(self) -> None:
        """JWT_SECRET < 32 символов отвергается даже если не в unsafe-списке."""
        env = _prod_env(JWT_SECRET="short_but_not_in_blocklist")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("JWT_SECRET" in e and "короткий" in e for e in result.errors)

    def test_exactly_32_chars_accepted(self) -> None:
        env = _prod_env(JWT_SECRET="aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vX")
        result = validate_runtime_settings(env=env)
        assert result.ok


# ── MinIO / S3 credentials ─────────────────────────────────────────

class TestMinioCredentials:
    def test_default_secret_key_rejected(self) -> None:
        env = _prod_env(S3_SECRET_KEY="minio123")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("S3_SECRET_KEY" in e for e in result.errors)

    def test_default_access_key_rejected(self) -> None:
        env = _prod_env(S3_ACCESS_KEY="minio")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("S3_ACCESS_KEY" in e for e in result.errors)

    def test_minioadmin_rejected(self) -> None:
        env = _prod_env(S3_SECRET_KEY="minioadmin")
        result = validate_runtime_settings(env=env)
        assert not result.ok

    def test_valid_credentials_accepted(self) -> None:
        env = _prod_env()
        result = validate_runtime_settings(env=env)
        assert result.ok


# ── Public URL HTTPS enforcement ───────────────────────────────────

class TestPublicURLSecurity:
    def test_http_public_s3_url_rejected(self) -> None:
        env = _prod_env(S3_PUBLIC_ENDPOINT_URL="http://storage.example.com")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("S3_PUBLIC_ENDPOINT_URL" in e for e in result.errors)

    def test_https_public_s3_url_accepted(self) -> None:
        env = _prod_env(S3_PUBLIC_ENDPOINT_URL="https://storage.example.com")
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_http_public_frontend_rejected(self) -> None:
        env = _prod_env(FRONTEND_URL="http://app.example.com")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("FRONTEND_URL" in e for e in result.errors)

    def test_https_frontend_accepted(self) -> None:
        env = _prod_env(FRONTEND_URL="https://app.example.com")
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_localhost_http_allowed(self) -> None:
        env = _prod_env(
            S3_PUBLIC_ENDPOINT_URL="http://localhost:9002",
            FRONTEND_URL="http://localhost:3000",
        )
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_127_0_0_1_http_allowed(self) -> None:
        env = _prod_env(
            S3_PUBLIC_ENDPOINT_URL="http://127.0.0.1:9002",
            FRONTEND_URL="http://127.0.0.1:3000",
        )
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_empty_public_url_ok(self) -> None:
        env = _prod_env(S3_PUBLIC_ENDPOINT_URL="")
        result = validate_runtime_settings(env=env)
        assert result.ok


# ── CORS ───────────────────────────────────────────────────────────

class TestCORSValidation:
    def test_wildcard_rejected(self) -> None:
        env = _prod_env(CORS_ORIGINS="*")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("CORS_ORIGINS" in e for e in result.errors)

    def test_wildcard_in_list_rejected(self) -> None:
        env = _prod_env(CORS_ORIGINS="https://app.example.com, *")
        result = validate_runtime_settings(env=env)
        assert not result.ok

    def test_json_wildcard_rejected(self) -> None:
        env = _prod_env(CORS_ORIGINS='["*"]')
        result = validate_runtime_settings(env=env)
        assert not result.ok

    def test_specific_origins_accepted(self) -> None:
        env = _prod_env(
            CORS_ORIGINS="https://app.example.com,https://admin.example.com"
        )
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_json_array_accepted(self) -> None:
        env = _prod_env(
            CORS_ORIGINS='["https://app.example.com","https://admin.example.com"]'
        )
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_empty_cors_ok(self) -> None:
        env = _prod_env(CORS_ORIGINS="")
        result = validate_runtime_settings(env=env)
        assert result.ok


# ── Postgres password ──────────────────────────────────────────────

class TestPostgresPassword:
    def test_default_password_rejected(self) -> None:
        env = _prod_env(POSTGRES_PASSWORD="app")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("POSTGRES_PASSWORD" in e for e in result.errors)

    def test_empty_password_rejected(self) -> None:
        env = _prod_env(POSTGRES_PASSWORD="")
        result = validate_runtime_settings(env=env)
        assert not result.ok

    def test_valid_password_accepted(self) -> None:
        env = _prod_env(POSTGRES_PASSWORD="pg_prd_s3cur3_p4ssw0rd_2026")
        result = validate_runtime_settings(env=env)
        assert result.ok


# ── AI API key ─────────────────────────────────────────────────────

class TestAIApiKey:
    def test_empty_rejected(self) -> None:
        env = _prod_env(AI_API_KEY="")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("AI_API_KEY" in e for e in result.errors)

    def test_placeholder_rejected(self) -> None:
        env = _prod_env(AI_API_KEY="sk-xxx")
        result = validate_runtime_settings(env=env)
        assert not result.ok

    def test_valid_key_accepted(self) -> None:
        env = _prod_env(AI_API_KEY="sk-or-v1-real-key-here")
        result = validate_runtime_settings(env=env)
        assert result.ok
    def test_openrouter_placeholder_rejected(self) -> None:
        """sk-or-v1-your-key-here — known .env.example placeholder."""
        env = _prod_env(AI_API_KEY="sk-or-v1-your-key-here")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("AI_API_KEY" in e for e in result.errors)

    def test_short_key_rejected(self) -> None:
        """AI_API_KEY < 20 символов отвергается даже если не в placeholder-списке."""
        env = _prod_env(AI_API_KEY="sk-short")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("AI_API_KEY" in e and "короткий" in e for e in result.errors)

    def test_exactly_20_chars_accepted(self) -> None:
        env = _prod_env(AI_API_KEY="sk-1234567890abcdef12")
        result = validate_runtime_settings(env=env)
        assert result.ok


# ── AI model IDs ───────────────────────────────────────────────────

class TestAIModelIDs:
    def test_empty_chat_model_rejected(self) -> None:
        env = _prod_env(AI_CHAT_MODEL="")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("AI_CHAT_MODEL" in e for e in result.errors)

    def test_fake_chat_model_rejected(self) -> None:
        env = _prod_env(AI_CHAT_MODEL="fake-model")
        result = validate_runtime_settings(env=env)
        assert not result.ok

    def test_empty_vision_model_rejected(self) -> None:
        env = _prod_env(AI_VISION_MODEL="")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("AI_VISION_MODEL" in e for e in result.errors)

    def test_empty_embedding_model_rejected(self) -> None:
        env = _prod_env(AI_EMBEDDING_MODEL="")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("AI_EMBEDDING_MODEL" in e for e in result.errors)


# ── Multi-error accumulation ───────────────────────────────────────

# ── Error messages must not leak secrets ──────────────────────────

class TestNoSecretsInErrors:
    """Ошибка не должна содержать значение секрета."""

    def test_s3_secret_key_not_in_error(self) -> None:
        env = _prod_env(S3_SECRET_KEY="minio123")
        result = validate_runtime_settings(env=env)
        for err in result.errors:
            assert "minio123" not in err

    def test_s3_access_key_not_in_error(self) -> None:
        env = _prod_env(S3_ACCESS_KEY="minio")
        result = validate_runtime_settings(env=env)
        for err in result.errors:
            # "minio" may appear as part of "MinIO" — check no raw value leak
            assert err.count("minio") == 0 or err.count("MinIO") >= err.count("minio")


# ── MOCK_MODE bypasses new format checks ─────────────────────────

class TestMockModeBypassesFormatChecks:
    """MOCK_MODE=true пропускает проверки длины JWT и AI ключа."""

    def test_mock_allows_short_jwt(self) -> None:
        env = {"MOCK_MODE": "true", "JWT_SECRET": "short"}
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_mock_allows_short_ai_key(self) -> None:
        env = {"MOCK_MODE": "true", "AI_API_KEY": "sk-short"}
        result = validate_runtime_settings(env=env)
        assert result.ok

    def test_mock_allows_openrouter_placeholder(self) -> None:
        env = {"MOCK_MODE": "true", "AI_API_KEY": "sk-or-v1-your-key-here"}
        result = validate_runtime_settings(env=env)
        assert result.ok

class TestMultipleErrors:
    def test_all_unsafe_defaults_captured(self) -> None:
        """Каждое небезопасное значение генерирует свою ошибку."""
        env = {
            "JWT_SECRET": "",
            "S3_SECRET_KEY": "minio123",
            "S3_ACCESS_KEY": "minio",
            "POSTGRES_PASSWORD": "app",
            "AI_API_KEY": "",
            "AI_CHAT_MODEL": "fake-model",
            "AI_VISION_MODEL": "fake-vision-model",
            "AI_EMBEDDING_MODEL": "fake-embedding-model",
            "CORS_ORIGINS": "*",
            "S3_PUBLIC_ENDPOINT_URL": "http://storage.example.com",
            "FRONTEND_URL": "http://app.example.com",
        }
        result = validate_runtime_settings(env=env)
        assert not result.ok
        # Минимум 10 ошибок (некоторые могут совпадать по группе)
        assert len(result.errors) >= 10


# ── Result type ────────────────────────────────────────────────────

class TestRuntimeValidationResult:
    def test_ok_property_true_when_empty(self) -> None:
        r = RuntimeValidationResult()
        assert r.ok is True
        assert bool(r) is True

    def test_ok_property_false_when_errors(self) -> None:
        r = RuntimeValidationResult(errors=("error one",))
        assert r.ok is False
        assert bool(r) is False

    def test_frozen(self) -> None:
        r = RuntimeValidationResult()
        with pytest.raises(AttributeError):
            r.errors = ("new",)  # type: ignore[misc]


# ── None env defaults to os.environ ────────────────────────────────

class TestDefaultEnv:
    def test_none_uses_os_environ(self) -> None:
        """validate_runtime_settings(env=None) должен прочитать os.environ."""
        # Не мокаем os.environ целиком — просто проверяем что
        # вызов с None не падает (в тестовом окружении есть MOCK_MODE или нет)
        result = validate_runtime_settings(env=None)
        assert isinstance(result, RuntimeValidationResult)
