FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости (без dev группы)
RUN uv sync --frozen --no-dev

# Копируем код
COPY api ./api
COPY shared ./shared
COPY docs ./docs
COPY data ./data

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
