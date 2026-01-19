import sys
import io

# Фикс кодировки для Windows консоли (cp1251 -> utf-8)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv

# Загружаем .env ДО импорта остальных модулей
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .routers import dialogue_router
from .routers import router as api_v1

app = FastAPI(title="Furniture AI API", version="0.1.0")

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
