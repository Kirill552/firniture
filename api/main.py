from fastapi import FastAPI

app = FastAPI(title="Furniture AI API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Простейшая проверка доступности сервиса."""
    return {"status": "ok"}
