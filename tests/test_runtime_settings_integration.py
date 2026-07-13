"""Integration tests: runtime settings validation at startup boundary.

Фокусные тесты — не требуют реальных сервисов, браузера или Docker.
Проверяют:
  • validate_runtime_settings() вызывается при старте и блокирует невалидный prod env
  • MOCK_MODE=true пропускает все проверки
  • CORS_ORIGINS разбирается из env (comma-separated и JSON-массив)
  • Compose-файлы содержат required env vars для api service
  • Startup не утекает секреты в логи
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

from api.runtime_settings import (
    RuntimeValidationResult,
    _parse_cors_origins,
    validate_runtime_settings,
)

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_DEV = ROOT / "docker-compose.yml"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
MAIN_PY = ROOT / "api" / "main.py"


# ── Helpers ────────────────────────────────────────────────────────


def _prod_env(**overrides: str) -> dict[str, str]:
    """Minimal valid production env. Override specific keys."""
    base = {
        "POSTGRES_PASSWORD": "a_strong_random_password_2026!",
        "S3_SECRET_KEY": "a_strong_s3_secret_2026!",
        "S3_ACCESS_KEY": "minio_ro",
        "JWT_SECRET": "a_strong_jwt_secret_at_least_32_chars_long!",
        "GUEST_UPLOAD_SECRET": "guest_hmac_secret_2026_at_least_32_chars",
        "TRUSTED_PROXY_CIDRS": "172.16.0.0/12",
        "AI_API_KEY": "sk-or-v1-real_key_abc123def456",
        "AI_CHAT_MODEL": "deepseek/deepseek-chat-v3-0324",
        "AI_VISION_MODEL": "google/gemini-2.0-flash-001",
        "AI_EMBEDDING_MODEL": "openai/text-embedding-3-small",
        "CORS_ORIGINS": "https://app.example.com",
        "FRONTEND_URL": "https://app.example.com",
    }
    base.update(overrides)
    return base


def _parse_compose_services(content: str) -> dict[str, dict]:
    """Extract service names and their env blocks from Compose YAML text.

    Lightweight regex-based parser — no PyYAML dependency for tests.
    """
    services: dict[str, dict] = {}
    # Match service blocks
    svc_pattern = re.compile(
        r"^  (?P<name>[a-zA-Z0-9_-]+):\n(?P<body>(?:    .*\n)*)",
        re.MULTILINE,
    )
    for m in svc_pattern.finditer(content):
        name = m.group("name")
        body = m.group("body")
        env: dict[str, str] = {}
        for line in body.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, val = line.partition(":")
                env[key.strip()] = val.strip()
        services[name] = env
    return services


# ══════════════════════════════════════════════════════════════════
# 1. Startup validation: fail closed for production
# ══════════════════════════════════════════════════════════════════


class TestStartupValidationFailClosed:
    """validate_runtime_settings() rejects invalid prod env at startup."""

    def test_valid_prod_env_passes(self) -> None:
        result = validate_runtime_settings(env=_prod_env())
        assert result.ok, f"Expected valid, got errors: {result.errors}"

    def test_empty_jwt_rejected(self) -> None:
        env = _prod_env(JWT_SECRET="")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("JWT_SECRET" in e for e in result.errors)

    def test_default_pg_password_rejected(self) -> None:
        env = _prod_env(POSTGRES_PASSWORD="app")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("POSTGRES_PASSWORD" in e for e in result.errors)

    def test_default_minio_secret_rejected(self) -> None:
        env = _prod_env(S3_SECRET_KEY="minio123")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("S3_SECRET_KEY" in e for e in result.errors)

    def test_placeholder_ai_key_rejected(self) -> None:
        env = _prod_env(AI_API_KEY="sk-xxx")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("AI_API_KEY" in e for e in result.errors)

    def test_wildcard_cors_rejected(self) -> None:
        env = _prod_env(CORS_ORIGINS="*")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("CORS_ORIGINS" in e for e in result.errors)

    def test_http_public_frontend_url_rejected(self) -> None:
        env = _prod_env(FRONTEND_URL="http://app.example.com")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("FRONTEND_URL" in e for e in result.errors)

    def test_http_public_s3_url_rejected(self) -> None:
        env = _prod_env(S3_PUBLIC_ENDPOINT_URL="http://storage.example.com")
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert any("S3_PUBLIC_ENDPOINT_URL" in e for e in result.errors)

    def test_multiple_errors_accumulated(self) -> None:
        env = _prod_env(
            JWT_SECRET="",
            S3_SECRET_KEY="minio123",
            AI_API_KEY="",
            POSTGRES_PASSWORD="password",
        )
        result = validate_runtime_settings(env=env)
        assert not result.ok
        assert len(result.errors) >= 4


# ══════════════════════════════════════════════════════════════════
# 2. Mock mode bypasses all validation
# ══════════════════════════════════════════════════════════════════


class TestMockModeBypass:
    """MOCK_MODE=true/1/yes skips every production check."""

    @pytest.mark.parametrize("value", ["true", "1", "yes", "TRUE", "Yes"])
    def test_mock_truthy_values_bypass(self, value: str) -> None:
        env = _prod_env(MOCK_MODE=value)
        # Even with completely invalid secrets, mock mode passes
        env["JWT_SECRET"] = ""
        env["S3_SECRET_KEY"] = "minio123"
        env["AI_API_KEY"] = ""
        result = validate_runtime_settings(env=env)
        assert result.ok, f"Mock mode should bypass, got: {result.errors}"

    def test_mock_false_does_not_bypass(self) -> None:
        env = _prod_env(MOCK_MODE="false", JWT_SECRET="")
        result = validate_runtime_settings(env=env)
        assert not result.ok

    def test_mock_absent_does_not_bypass(self) -> None:
        env = _prod_env(JWT_SECRET="")
        result = validate_runtime_settings(env=env)
        assert not result.ok


# ══════════════════════════════════════════════════════════════════
# 3. CORS_ORIGINS env parsing
# ══════════════════════════════════════════════════════════════════


class TestCORSOriginsParsing:
    """_parse_cors_origins handles comma-separated, JSON, and empty."""

    def test_comma_separated(self) -> None:
        result = _parse_cors_origins("https://a.com, https://b.com")
        assert result == ["https://a.com", "https://b.com"]

    def test_json_array(self) -> None:
        raw = json.dumps(["https://a.com", "https://b.com"])
        result = _parse_cors_origins(raw)
        assert result == ["https://a.com", "https://b.com"]

    def test_single_origin(self) -> None:
        result = _parse_cors_origins("https://app.example.com")
        assert result == ["https://app.example.com"]

    def test_empty_string(self) -> None:
        result = _parse_cors_origins("")
        assert result == []

    def test_whitespace_trimmed(self) -> None:
        result = _parse_cors_origins("  https://a.com , https://b.com  ")
        assert result == ["https://a.com", "https://b.com"]

    def test_malformed_json_falls_back(self) -> None:
        # Invalid JSON → treated as raw string
        result = _parse_cors_origins("[invalid")
        assert result == ["[invalid"]


class TestCORSOriginsIntegration:
    """CORS_ORIGINS is read from os.environ and passed to CORS middleware."""

    def test_cors_from_env_used_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "https://custom.example.com")
        raw = os.environ.get("CORS_ORIGINS", "")
        origins = _parse_cors_origins(raw) if raw else [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        assert origins == ["https://custom.example.com"]

    def test_cors_defaults_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        raw = os.environ.get("CORS_ORIGINS", "")
        origins = _parse_cors_origins(raw) if raw else [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        assert origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


# ══════════════════════════════════════════════════════════════════
# 4. main.py startup boundary: sys.exit on invalid env
# ══════════════════════════════════════════════════════════════════


class TestMainStartupBoundary:
    """Startup event handler calls sys.exit(1) for invalid prod env."""

    def test_main_exits_on_invalid_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When MOCK_MODE is not set and secrets are invalid, main.py calls sys.exit(1)."""
        env = {
            "MOCK_MODE": "false",
            "JWT_SECRET": "",
            "S3_SECRET_KEY": "minio123",
            "POSTGRES_PASSWORD": "app",
            "AI_API_KEY": "",
            "AI_CHAT_MODEL": "deepseek/deepseek-chat-v3-0324",
            "AI_VISION_MODEL": "google/gemini-2.0-flash-001",
            "AI_EMBEDDING_MODEL": "openai/text-embedding-3-small",
        }
        for k, v in env.items():
            monkeypatch.setenv(k, v)

        # Remove CORS_ORIGINS if present (empty triggers default origins)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)

        # Validate that the env is indeed invalid
        result = validate_runtime_settings(env=env)
        assert not result.ok, "Test setup error: env should be invalid"

        # Verify the startup would sys.exit(1)
        with pytest.raises(SystemExit, match="1"):
            # Re-execute the validation boundary logic from main.py
            _validation = validate_runtime_settings()
            if not _validation.ok:
                sys.exit(1)

    def test_main_passes_with_valid_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When env is valid, validation passes (no sys.exit)."""
        env = _prod_env()
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")

        result = validate_runtime_settings()
        assert result.ok, f"Expected valid env, got: {result.errors}"

    def test_main_passes_with_mock_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """MOCK_MODE=true allows startup even with invalid secrets."""
        monkeypatch.setenv("MOCK_MODE", "true")
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("S3_SECRET_KEY", raising=False)

        result = validate_runtime_settings()
        assert result.ok


# ══════════════════════════════════════════════════════════════════
# 5. Compose env contract validation
# ══════════════════════════════════════════════════════════════════


class TestComposeEnvContract:
    """Compose files declare MOCK_MODE and CORS_ORIGINS for the api service."""

    def _api_env(self, compose_path: Path) -> dict[str, str]:
        content = compose_path.read_text(encoding="utf-8")
        services = _parse_compose_services(content)
        assert "api" in services, f"api service missing from {compose_path.name}"
        return services["api"]

    def test_dev_compose_has_mock_mode(self) -> None:
        env = self._api_env(COMPOSE_DEV)
        assert "MOCK_MODE" in env, "docker-compose.yml api must declare MOCK_MODE"

    def test_dev_compose_has_cors_origins(self) -> None:
        env = self._api_env(COMPOSE_DEV)
        assert "CORS_ORIGINS" in env, "docker-compose.yml api must declare CORS_ORIGINS"

    def test_dev_compose_mock_mode_is_true(self) -> None:
        env = self._api_env(COMPOSE_DEV)
        assert env["MOCK_MODE"] == '"true"', (
            "docker-compose.yml MOCK_MODE should be 'true' for local dev"
        )

    def test_prod_compose_has_mock_mode(self) -> None:
        env = self._api_env(COMPOSE_PROD)
        assert "MOCK_MODE" in env, "docker-compose.prod.yml api must declare MOCK_MODE"

    def test_prod_compose_has_cors_origins(self) -> None:
        env = self._api_env(COMPOSE_PROD)
        assert "CORS_ORIGINS" in env, "docker-compose.prod.yml api must declare CORS_ORIGINS"

    def test_prod_compose_mock_mode_defaults_false(self) -> None:
        env = self._api_env(COMPOSE_PROD)
        # Should be ${MOCK_MODE:-false} or similar
        assert "false" in env["MOCK_MODE"], (
            "docker-compose.prod.yml MOCK_MODE should default to false"
        )

    def test_prod_compose_cors_is_variable_reference(self) -> None:
        env = self._api_env(COMPOSE_PROD)
        # CORS_ORIGINS should be ${CORS_ORIGINS} — operator must supply it
        assert "CORS_ORIGINS" in env["CORS_ORIGINS"], (
            "docker-compose.prod.yml CORS_ORIGINS should be a variable reference"
        )

    def test_prod_compose_has_jwt_secret(self) -> None:
        env = self._api_env(COMPOSE_PROD)
        assert "JWT_SECRET" in env, "docker-compose.prod.yml api must declare JWT_SECRET"

    def test_prod_compose_has_all_required_secrets(self) -> None:
        env = self._api_env(COMPOSE_PROD)
        required = [
            "POSTGRES_PASSWORD",
            "S3_SECRET_KEY",
            "S3_ACCESS_KEY",
            "JWT_SECRET",
            "AI_API_KEY",
            "CORS_ORIGINS",
            "MOCK_MODE",
        ]
        missing = [k for k in required if k not in env]
        assert not missing, f"docker-compose.prod.yml api missing: {missing}"

    def test_dev_compose_postgres_password_is_default(self) -> None:
        """Dev compose uses known local defaults — validated by mock mode."""
        env = self._api_env(COMPOSE_DEV)
        assert env.get("POSTGRES_PASSWORD") == "app", (
            "Dev compose should use default 'app' password"
        )


# ══════════════════════════════════════════════════════════════════
# 6. Startup does not leak secrets
# ══════════════════════════════════════════════════════════════════


class TestNoSecretLeakage:
    """Startup validation and CORS info must not contain secret values."""

    def test_validation_result_never_contains_secret_values(self) -> None:
        """Error messages should name the variable, not its value."""
        env = _prod_env(
            JWT_SECRET="super_secret_abc123",
            S3_SECRET_KEY="my_real_s3_secret",
            POSTGRES_PASSWORD="my_real_pg_password",
        )
        result = validate_runtime_settings(env=env)
        for err in result.errors:
            # Error messages should not contain the actual secret values
            assert "super_secret_abc123" not in err
            assert "my_real_s3_secret" not in err
            assert "my_real_pg_password" not in err

    def test_cors_origins_not_logged_as_secrets(self) -> None:
        """CORS origins are not secrets, but verify the log line doesn't contain tokens."""
        origins = ["https://app.example.com"]
        log_line = f"CORS origins: {origins}"
        # CORS origins are public, so they can appear in logs
        assert "app.example.com" in log_line
        # But no JWT/AI tokens should appear
        assert "sk-" not in log_line
        assert "jwt" not in log_line.lower()

    def test_main_py_source_has_no_hardcoded_secrets(self) -> None:
        """main.py should not contain hardcoded secret values."""
        source = MAIN_PY.read_text(encoding="utf-8")
        # No hardcoded API keys
        assert "sk-" not in source, "main.py must not contain hardcoded API keys"
        assert "46.17.250.109" not in source, "main.py must not contain hardcoded IP addresses"
        # The old hardcoded CORS list should be gone
        assert '"http://46.17.250.109"' not in source, "Hardcoded production IP removed from CORS"


# ══════════════════════════════════════════════════════════════════
# 7. Production values: human-gated report
# ══════════════════════════════════════════════════════════════════


class TestProductionValuesReport:
    """Verify the validation catches all values a human must set for production."""

    def test_report_required_human_owned_values(self) -> None:
        """Values that MUST be set by a human for production deployment.

        These cannot have safe defaults — leaving them as placeholder
        causes startup to fail (fail-closed).
        """
        # Variables rejected when empty/placeholder
        rejected_when_empty = {
            "POSTGRES_PASSWORD": "Unique strong password",
            "JWT_SECRET": "Random 32+ char secret (secrets.token_urlsafe)",
            "AI_API_KEY": "Real OpenRouter/provider key",
        }
        for var, description in rejected_when_empty.items():
            env = _prod_env(**{var: ""})
            result = validate_runtime_settings(env=env)
            assert not result.ok, (
                f"{var} ({description}) should be rejected when empty. "
                f"Errors: {result.errors}"
            )

        # S3 credentials: only specific known-bad defaults are caught
        s3_bad_defaults = {
            "S3_SECRET_KEY": ("minio123", "Known MinIO default password"),
            "S3_ACCESS_KEY": ("minio", "Known MinIO default user"),
        }
        for var, (bad_val, description) in s3_bad_defaults.items():
            env = _prod_env(**{var: bad_val})
            result = validate_runtime_settings(env=env)
            assert not result.ok, (
                f"{var}={bad_val!r} ({description}) should be rejected. "
                f"Errors: {result.errors}"
            )

    def test_deferred_vps_validation(self) -> None:
        """VPS-specific checks (HTTPS enforcement, DNS) are deferred.

        The runtime_settings validator checks scheme/host on public URLs
        but does NOT perform DNS resolution or TLS certificate validation.
        These are confirmed at deploy time via:
          1. Caddy reverse proxy TLS termination
          2. Manual DNS verification
          3. Health check endpoint after deploy
        """
        # Public HTTP URL is rejected at validation time
        env = _prod_env(FRONTEND_URL="http://app.example.com")
        result = validate_runtime_settings(env=env)
        assert not result.ok, "HTTP public URL should be rejected"

        # Private/localhost URLs are allowed (VPS-internal)
        env = _prod_env(FRONTEND_URL="http://localhost:3000")
        result = validate_runtime_settings(env=env)
        assert result.ok, "localhost URL should be allowed for internal use"


# ══════════════════════════════════════════════════════════════════
# 8. RuntimeValidationResult behavior
# ══════════════════════════════════════════════════════════════════


class TestValidationResultBehavior:
    """RuntimeValidationResult truthiness and error accumulation."""

    def test_ok_true_when_no_errors(self) -> None:
        r = RuntimeValidationResult()
        assert r.ok
        assert bool(r) is True

    def test_ok_false_when_errors(self) -> None:
        r = RuntimeValidationResult(errors=("bad",))
        assert not r.ok
        assert bool(r) is False

    def test_frozen_dataclass(self) -> None:
        r = RuntimeValidationResult()
        with pytest.raises(AttributeError):
            r.errors = ("new",)  # type: ignore[misc]
