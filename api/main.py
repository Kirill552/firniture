import io
import logging
import sys

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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .routers import dialogue_router
from .routers import router as api_v1

app = FastAPI(title="Furniture AI API", version="0.1.0")

log = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """Предзагрузка тяжёлых моделей при старте."""
    log.info("[STARTUP] Предзагрузка модели FRIDA...")
    try:
        from shared.embeddings import _get_frida_model
        _get_frida_model()  # Загрузит модель в память
        log.info("[STARTUP] Модель FRIDA загружена успешно")
    except Exception as e:
        log.warning(f"[STARTUP] Не удалось загрузить FRIDA: {e}")


# CORS для фронтенда (локалка + прод)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://46.17.250.109",
        "http://46.17.250.109:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Простейшая проверка доступности сервиса."""
    return {"status": "ok"}


app.include_router(api_v1)
app.include_router(dialogue_router)
app.include_router(auth_router, prefix="/api/v1")
