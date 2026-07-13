import io
import json
import logging
import os
import sys
import time

# Фикс кодировки для Windows консоли (cp1251 -> utf-8)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Уменьшаем шум от библиотек
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

from dotenv import load_dotenv

# Загружаем .env ДО импорта остальных модулей
load_dotenv()

log = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.observability import create_event, event_to_dict
from api.runtime_settings import _parse_cors_origins, validate_runtime_settings

from .auth import router as auth_router
from .routers import dialogue_router
from .routers import router as api_v1
from .routes.manufacturing import router as manufacturing_router

app = FastAPI(title="Furniture AI API", version="0.1.0")

# ── Observability context: release/environment from env ───────────
_RELEASE = os.environ.get("APP_RELEASE", "dev")
_ENVIRONMENT = os.environ.get("APP_ENVIRONMENT", "dev")
_OBS_CONTEXT: dict[str, str] = {
    "release": _RELEASE,
    "environment": _ENVIRONMENT,
}

_obs_logger = logging.getLogger("observability.events")


def _configure_observability_logger() -> None:
    """Гарантировать доставку structured events в настроенный logging sink."""
    _obs_logger.disabled = False
    _obs_logger.setLevel(logging.INFO)
    _obs_logger.propagate = True


def _emit_event(
    event_type: str,
    data: dict,
    *,
    severity: str = "info",
    context: dict | None = None,
) -> None:
    """Create a redacted structured event and log it via the structured logger.

    Merges runtime environment/release context.  The event is safe for
    any downstream sink (Sentry, structlog, plain logs).
    """
    _configure_observability_logger()
    merged_ctx = {**_OBS_CONTEXT}
    if context:
        merged_ctx.update(context)
    event = create_event(
        event_type=event_type,
        data=data,
        severity=severity,
        context=merged_ctx,
    )
    _obs_logger.info("%s", json.dumps(event_to_dict(event), ensure_ascii=False))


# ── CORS: from env, local defaults for mock mode ────────────────
_cors_raw = os.environ.get("CORS_ORIGINS", "")
_cors_origins = _parse_cors_origins(_cors_raw) if _cors_raw else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
log.info("CORS origins: %s", _cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Раннее ограничение тела публичной загрузки (Task 1) ────────────
# Выполняется до разбора тела запроса и возвращает 413 без полного чтения.
from starlette.types import ASGIApp, Receive, Scope, Send


class _EarlyUploadSizeLimit:
    """ASGI middleware: 413 on oversized Content-Length for extract-from-image before body read."""

    def __init__(self, app: ASGIApp, max_bytes: int = 14 * 1024 * 1024) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.target_path = "/api/v1/spec/extract-from-image"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == self.target_path or path.startswith(self.target_path):
            headers = dict(scope.get("headers", []))
            cl = headers.get(b"content-length")
            if cl:
                try:
                    if int(cl) > self.max_bytes:
                        # Немедленно возвращаем 413.
                        from starlette.responses import JSONResponse
                        resp = JSONResponse(
                            {"detail": {"code": "payload_too_large", "message": "Payload too large", "retry_after_seconds": None}},
                            status_code=413,
                        )
                        await resp(scope, receive, send)
                        return
                except Exception:
                    pass
        await self.app(scope, receive, send)


app.add_middleware(_EarlyUploadSizeLimit)  # type: ignore[arg-type]


# ── Observability middleware: structured request events ───────────
@app.middleware("http")
async def _observability_middleware(request: Request, call_next):
    """Log structured redacted event for every HTTP request."""
    method = request.method
    path = request.url.path
    start = time.monotonic()
    try:
        response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        _emit_event(
            "api.request",
            {
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
            },
            severity="warning" if response.status_code >= 400 else "info",
        )
        return response
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        _emit_event(
            "api.request.exception",
            {
                "method": method,
                "path": path,
                "error": type(exc).__name__,
                "elapsed_ms": elapsed_ms,
            },
            severity="error",
        )
        raise


# ── Startup validation: fail closed for production ───────────────
@app.on_event("startup")
async def _validate_runtime():
    """Validate env at startup boundary. Fail closed for production."""
    result = validate_runtime_settings()
    if not result.ok:
        _emit_event(
            "app.startup.failed",
            {"errors": list(result.errors)},
            severity="error",
        )
        log.error("Runtime validation failed — refusing to start:")
        for err in result.errors:
            log.error("  • %s", err)
        log.error(
            "Set MOCK_MODE=true to bypass (dev/test only). "
            "See .env.example for production values."
        )
        sys.exit(1)
    _emit_event("app.startup.success", {"version": app.version})


@app.get("/health")
def health() -> dict:
    """Простейшая проверка доступности сервиса."""
    return {"status": "ok"}


@app.on_event("shutdown")
async def shutdown_event():
    """Закрыть AI-клиент при остановке сервера."""
    _emit_event("app.shutdown", {})
    from shared.ai_client import get_ai_client
    await get_ai_client().close()


app.include_router(api_v1)
app.include_router(dialogue_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(manufacturing_router)
