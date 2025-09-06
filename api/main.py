from fastapi import FastAPI
from .routers import router as api_v1, dialogue_router

app = FastAPI(title="Furniture AI API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Простейшая проверка доступности сервиса."""
    return {"status": "ok"}


app.include_router(api_v1)
app.include_router(dialogue_router)
