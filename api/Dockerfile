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

# Конвейер разбора каталогов: нужен на сервере, чтобы заливать фурнитуру
# в базу одной командой, без копирования файлов в живой контейнер.
# Выгрузки и PDF в образ не попадают, они отсечены в .dockerignore.
COPY etl_pipeline ./etl_pipeline

# Копируем alembic для миграций
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000

# Используем .venv напрямую вместо uv run (избегаем editable install)
CMD [".venv/bin/python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
