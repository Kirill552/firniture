FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy asyncpg alembic redis boto3 pydantic-settings "psycopg[binary]" ezdxf==1.4.2 aiohttp>=3.10.0 numpy>=1.26.0 scipy>=1.13.0 pgvector>=0.4.1 openpyxl>=3.1.0

COPY api ./api
COPY shared ./shared
COPY docs ./docs
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
