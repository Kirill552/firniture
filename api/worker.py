from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import traceback
from typing import Any, Awaitable, cast

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from uuid import uuid4

from .database import SessionLocal
from .models import CAMJob, JobStatusEnum, Artifact
from .queues import get_redis, DXF_QUEUE, GCODE_QUEUE, DLQ_QUEUE
from shared.storage import ObjectStorage
import io

try:
    import ezdxf  # type: ignore
except Exception:  # pragma: no cover - установим в контейнере
    ezdxf = None


log = logging.getLogger("cam-worker")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def process_job(session: AsyncSession, payload: dict[str, Any]) -> None:
    job_id = payload.get("job_id")
    if not job_id:
        raise ValueError("payload without job_id")

    # → Processing
    await session.execute(
        update(CAMJob)
        .where(CAMJob.id == job_id)
        .values(status=JobStatusEnum.Processing)
    )
    await session.commit()

    # Обработка: если DXF — сгенерировать простой DXF и сохранить в S3 как артефакт
    # (GCODE пока пропускаем: имитация задержки)
    # небольшая задержка для имитации работы
    await asyncio.sleep(0.1)

    # Узнаем вид работы
    # (в простом MVP берём из контекста только для DXF)
    # Если DXF — генерируем прямоугольник 1000x500 мм
    artifact_id = None
    if payload.get("job_kind") == "DXF" and ezdxf is not None:
        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()
        width, height = 1000.0, 500.0  # мм
        msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)], close=True)
        # ezdxf.write пишет ТЕКСТ в поток, получаем str и кодируем по правильной кодировке
        buf = io.StringIO()
        try:
            doc.write(buf)
            text = buf.getvalue()
        finally:
            buf.close()
        encoding = getattr(doc, "output_encoding", "utf-8")
        data = text.encode(encoding or "utf-8")
        # Сохраняем в хранилище
        storage = ObjectStorage()
        storage.ensure_bucket()
        key = f"dxf/{job_id}.dxf"
        storage.put_object(key, data, content_type="application/dxf")
        # Создаем Artifact в БД
        ins = insert(Artifact).values(type="DXF", storage_key=key, size_bytes=len(data))
        res = await session.execute(ins.returning(Artifact.id))
        artifact_id = res.scalar_one()
        # Присвоим артефакт задаче
        await session.execute(
            update(CAMJob)
            .where(CAMJob.id == job_id)
            .values(artifact_id=artifact_id)
        )
        await session.commit()

    # → Completed
    await session.execute(
        update(CAMJob)
        .where(CAMJob.id == job_id)
        .values(status=JobStatusEnum.Completed)
    )
    await session.commit()


async def run_worker(stop_event: asyncio.Event) -> None:
    r = get_redis()
    log.info("Worker started. Listening queues: %s, %s", DXF_QUEUE, GCODE_QUEUE)
    while not stop_event.is_set():
        try:
            # Блокирующее ожидание события из любой очереди
            # Pylance: указываем, что это awaitable и возвращает пару [queue, payload]
            res = await cast(Awaitable[list[str] | None], r.blpop([DXF_QUEUE, GCODE_QUEUE], timeout=5))
            if not res:
                continue
            queue, raw = res
            payload = json.loads(raw)

            async with SessionLocal() as session:
                session_typed: AsyncSession = cast(AsyncSession, session)
                try:
                    await process_job(session_typed, payload)
                    log.info("Processed %s job: %s", queue, payload.get("job_id"))
                except Exception as e:
                    # На DLQ и пометить Failed
                    tb = traceback.format_exc(limit=3)
                    await cast(Awaitable[int], r.lpush(DLQ_QUEUE, json.dumps({"error": str(e), "payload": payload, "trace": tb})))
                    await session_typed.execute(
                        update(CAMJob)
                        .where(CAMJob.id == payload.get("job_id"))
                        .values(status=JobStatusEnum.Failed, error=str(e))
                    )
                    await session_typed.commit()
                    log.error("Failed job %s: %s", payload.get("job_id"), e)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Loop error: %s", e)
            await asyncio.sleep(1)

    log.info("Worker stopped")


def _install_signal_handlers(loop: asyncio.AbstractEventLoop, event: asyncio.Event) -> None:
    if os.name != "nt":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, event.set)


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event: asyncio.Event = asyncio.Event()
    _install_signal_handlers(loop, stop_event)
    try:
        loop.run_until_complete(run_worker(stop_event))
    finally:
        loop.stop()
        loop.close()


if __name__ == "__main__":
    main()
