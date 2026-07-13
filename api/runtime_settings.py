"""Runtime production-safety validation.

Проверяет переменные окружения при старте и отвергает небезопасные
дефолты: placeholder-ключи, пароли MinIO по умолчанию, HTTP вместо
HTTPS, пустой JWT-секрет, wildcard CORS, отсутствующие model/profile IDs.

Explicit ``MOCK_MODE=true`` (или ``MOCK_MODE=1``) разрешает
локальную разработку без реальных секретов — все проверки пропускаются.

Не импортирует ``api.settings`` или ``shared.ai_settings`` —
читает ``env`` dict напрямую для полной изолируемости тестов.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

# ── Unsafe value registries ────────────────────────────────────────

_UNSAFE_MINIO_SECRET_KEYS: frozenset[str] = frozenset({
    "minio",
    "minio123",
    "minioadmin",
    "password",
})

_UNSAFE_JWT_SECRETS: frozenset[str] = frozenset({
    "",
    "CHANGE_ME",
    "CHANGE_ME_IN_PRODUCTION",
    "CHANGE_ME_IN_PRODUCTION_super_secret_key_2026",
    "secret",
    "jwt_secret",
    "super_secret",
})

_UNSAFE_POSTGRES_PASSWORDS: frozenset[str] = frozenset({
    "",
    "password",
    "postgres",
    "admin",
    "app",  # docker-compose local default
})

_PLACEHOLDER_API_KEYS: frozenset[str] = frozenset({
    "",
    "sk-xxx",
    "sk-or-v1-your-key-here",
    "CHANGE_ME",
    "YOUR_API_KEY",
    "placeholder",
})

_PLACEHOLDER_MODEL_IDS: frozenset[str] = frozenset({
    "",
    "fake-model",
    "fake-vision-model",
    "fake-embedding-model",
    "placeholder",
})


# ── Result type ────────────────────────────────────────────────────

@dataclass(frozen=True)
class RuntimeValidationResult:
    """Результат валидации runtime settings."""

    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def __bool__(self) -> bool:
        return self.ok


# ── Helpers ────────────────────────────────────────────────────────

def _get(env: dict[str, str], key: str, default: str = "") -> str:
    return env.get(key, default).strip()


def _is_mock(env: dict[str, str]) -> bool:
    val = _get(env, "MOCK_MODE", "false").lower()
    return val in ("true", "1", "yes")


def _is_public_url(value: str) -> bool:
    """True если URL явно指向 публичный (не localhost/127.0.0.1)."""
    if not value:
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname or ""
    return host not in ("localhost", "127.0.0.1", "0.0.0.0", "")


def _parse_cors_origins(raw: str) -> list[str]:
    """Разбирает CORS_ORIGINS: comma-separated или JSON-массив."""
    raw = raw.strip()
    if raw.startswith("["):
        import json
        try:
            parsed = json.loads(raw)
            return [str(o).strip() for o in parsed if isinstance(o, str)]
        except (json.JSONDecodeError, TypeError):
            return [raw]
    return [o.strip() for o in raw.split(",") if o.strip()]


# ── Core validator ─────────────────────────────────────────────────

def validate_runtime_settings(
    *,
    env: dict[str, str] | None = None,
) -> RuntimeValidationResult:
    """Validate env for production safety.

    Parameters
    ----------
    env:
        Mapping ``str → str``. Defaults to ``os.environ``.

    Returns
    -------
    RuntimeValidationResult
        ``.ok`` is ``True`` when all checks pass.
    """
    if env is None:
        env = dict(os.environ)

    # Mock mode — skip all production checks
    if _is_mock(env):
        return RuntimeValidationResult()

    errors: list[str] = []

    # ── JWT secret ──────────────────────────────────────────────────
    jwt_secret = _get(env, "JWT_SECRET")
    if jwt_secret in _UNSAFE_JWT_SECRETS:
        errors.append(
            "JWT_SECRET: пустой или placeholder-значение. "
            "Сгенерируйте длинный случайный ключ для production."
        )
    if jwt_secret and jwt_secret not in _UNSAFE_JWT_SECRETS and len(jwt_secret) < 32:
        errors.append(
            "JWT_SECRET: слишком короткий (< 32 символа). "
            "Используйте не менее 32 символов для безопасности HS256."
        )

    # ── MinIO / S3 credentials ──────────────────────────────────────
    s3_secret = _get(env, "S3_SECRET_KEY")
    if s3_secret in _UNSAFE_MINIO_SECRET_KEYS:
        errors.append(
            "S3_SECRET_KEY: используется дефолтный пароль MinIO. "
            "Замените на уникальный секрет."
        )

    s3_access = _get(env, "S3_ACCESS_KEY")
    if s3_access in _UNSAFE_MINIO_SECRET_KEYS:
        errors.append(
            "S3_ACCESS_KEY: значение совпадает с "
            "дефолтным пользователем MinIO. Замените."
        )

    # ── Public S3 URL — must be HTTPS ───────────────────────────────
    s3_public_url = _get(env, "S3_PUBLIC_ENDPOINT_URL")
    if s3_public_url and _is_public_url(s3_public_url):
        parsed = urlparse(s3_public_url)
        if parsed.scheme == "http":
            errors.append(
                "S3_PUBLIC_ENDPOINT_URL: публичный URL использует HTTP. "
                "Для production необходим HTTPS."
            )

    # ── Public frontend URL — must be HTTPS ─────────────────────────
    frontend_url = _get(env, "FRONTEND_URL")
    if frontend_url and _is_public_url(frontend_url):
        parsed = urlparse(frontend_url)
        if parsed.scheme == "http":
            errors.append(
                "FRONTEND_URL: публичный URL использует HTTP. "
                "Для production необходим HTTPS."
            )

    # ── CORS wildcard ───────────────────────────────────────────────
    cors_raw = _get(env, "CORS_ORIGINS")
    if cors_raw:
        origins = _parse_cors_origins(cors_raw)
        if "*" in origins:
            errors.append(
                "CORS_ORIGINS: wildcard «*» запрещён в production. "
                "Укажите конкретные домены."
            )

    # ── Postgres password ───────────────────────────────────────────
    pg_password = _get(env, "POSTGRES_PASSWORD")
    if pg_password in _UNSAFE_POSTGRES_PASSWORDS:
        errors.append(
            "POSTGRES_PASSWORD: пароль совпадает с небезопасным "
            "дефолтом. Замените на уникальный."
        )

    # ── AI API key ──────────────────────────────────────────────────
    ai_key = _get(env, "AI_API_KEY")
    if ai_key in _PLACEHOLDER_API_KEYS:
        errors.append(
            "AI_API_KEY: пустой или placeholder-ключ. "
            "Установите реальный ключ провайдера."
        )
    if ai_key and ai_key not in _PLACEHOLDER_API_KEYS and len(ai_key) < 20:
        errors.append(
            "AI_API_KEY: слишком короткий (< 20 символов). "
            "Проверьте, что ключ скопирован полностью."
        )

    # ── AI model IDs ────────────────────────────────────────────────
    for model_var in ("AI_CHAT_MODEL", "AI_VISION_MODEL", "AI_EMBEDDING_MODEL"):
        model_val = _get(env, model_var)
        if model_val in _PLACEHOLDER_MODEL_IDS:
            errors.append(
                f"{model_var}: отсутствует или placeholder-значение. "
                "Укажите валидный ID модели."
            )

    # ── Секреты защиты гостевой загрузки (Task 1) ───────────────────
    guest_secret = _get(env, "GUEST_UPLOAD_SECRET")
    if guest_secret in ("", "CHANGE_ME", "secret"):
        errors.append(
            "GUEST_UPLOAD_SECRET: пустой или placeholder. "
            "Установите сильный HMAC secret для guest grants и session."
        )
    if guest_secret and len(guest_secret) < 32:
        errors.append(
            "GUEST_UPLOAD_SECRET: слишком короткий (<32 символов)."
        )

    # В production список доверенных прокси обязателен для защиты от подмены адреса.
    trusted = _get(env, "TRUSTED_PROXY_CIDRS")
    if not trusted:
        errors.append(
            "TRUSTED_PROXY_CIDRS: обязательно для production. "
            "Укажите CIDR сети reverse-proxy (Caddy), иначе spoofed X-Forwarded-For разрешены."
        )

    return RuntimeValidationResult(errors=tuple(errors))
