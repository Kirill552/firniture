# API сервис (FastAPI)

Локальный запуск (Python 3.12):

1) Установка зависимостей
2) Запуск инфраструктуры (docker compose)
3) Создание `.env` из шаблона
4) Миграции БД (Alembic)
5) Запуск сервера

Пример (Windows PowerShell):

```powershell
# установка
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -U pip
pip install -e .

# инфраструктура (Postgres/Redis/MinIO)
docker compose up -d

# переменные окружения
Copy-Item .env.example .env -Force

# миграции
alembic -c api/alembic.ini upgrade head

# запуск
uvicorn api.main:app --reload
```

Swagger UI: http://localhost:8000/docs

Примечания
- Все размеры — мм; без ПДн в логах/промптах.
- Presigned URL TTL ≤ 15 мин (см. settings).

## Запуск в Docker

```powershell
docker compose up -d --build api
```

После старта: http://localhost:8000/docs
