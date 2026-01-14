from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from alembic import context  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api import models  # noqa: F401,E402  # ensure models imported
from api.database import Base  # noqa: E402
from api.settings import settings  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)  # type: ignore[arg-type]

target_metadata = Base.metadata

# На Windows используем SelectorEventLoopPolicy, чтобы избежать проблем Proactor/asyncpg
if os.name == "nt":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # безопасно игнорируем, если политика уже установлена или недоступна
        pass


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Используем синхронный драйвер psycopg для миграций (на Windows стабильнее)
    url = (
        f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    print("[alembic] connecting:", url)

    attempts = 10
    delay = 0.5
    last_error: BaseException | None = None

    for i in range(attempts):
        try:
            connectable = create_engine(url, pool_pre_ping=True)
            with connectable.connect() as connection:
                do_run_migrations(connection)
            connectable.dispose()
            last_error = None
            break
        except BaseException as e:  # noqa: BLE001
            last_error = e
            if i == attempts - 1:
                break
            # задержка с экспоненциальной паузой
            import time

            time.sleep(delay)
            delay = min(delay * 2, 5.0)

    if last_error is not None:
        raise last_error


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
