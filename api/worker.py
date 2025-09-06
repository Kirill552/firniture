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
        # Set units to millimeters
        doc.header['$INSUNITS'] = ezdxf.units.MM

        # Add metadata
        doc.header['$AUTHOR'] = "Мебель-ИИ"
        doc.header['$DATETIME'] = ezdxf.ezdxf_datetime_to_header_str(ezdxf.now())

        msp = doc.modelspace()

        # Add layers
        outline_layer = doc.layers.new(name="OUTLINE", dxfattribs={'color': 7}) # White/Black
        annotations_layer = doc.layers.new(name="ANNOTATIONS", dxfattribs={'color': 1}) # Red

        width, height = 1000.0, 500.0  # мм

        # CAM checks
        if width <= 0 or height <= 0:
            raise ValueError("Panel dimensions must be positive")
        
        tool_diameter = 3.175 # мм
        if tool_diameter >= width or tool_diameter >= height:
            raise ValueError("Tool diameter is too large for the panel")

        msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)], close=True, dxfattribs={'layer': outline_layer.name})

        # Add a simple dimension annotation
        dim = msp.add_aligned_dim(p1=(0, 0), p2=(width, 0), distance=20, dxfattribs={'layer': annotations_layer.name})
        dim.render()

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
    elif payload.get("job_kind") == "GCODE":
        dxf_artifact_id = payload.get("context", {}).get("dxf_artifact_id")
        if not dxf_artifact_id:
            raise ValueError("dxf_artifact_id not found in GCODE job context")

        # Get DXF file from storage
        dxf_artifact = await session.get(Artifact, dxf_artifact_id)
        if not dxf_artifact:
            raise ValueError(f"DXF artifact {dxf_artifact_id} not found")

        storage = ObjectStorage()
        dxf_data = storage.get_object(dxf_artifact.storage_key)

        # Write DXF data to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as dxf_file:
            dxf_file.write(dxf_data)
            dxf_file_path = dxf_file.name

        # Generate G-code
        gcode_file_path = tempfile.mktemp(suffix=".gcode")
        freecad_cmd = "freecadcmd"
        script_path = "cad-cam/freecad_gcode.py"

        process = await asyncio.create_subprocess_exec(
            freecad_cmd, script_path, dxf_file_path, gcode_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"FreeCAD G-code generation failed: {stderr.decode()}")

        # Read G-code data
        with open(gcode_file_path, "rb") as gcode_file:
            gcode_data = gcode_file.read()

        # Save G-code to storage
        key = f"gcode/{job_id}.gcode"
        storage.put_object(key, gcode_data, content_type="text/plain")

        # Create Artifact in DB
        ins = insert(Artifact).values(type="GCODE", storage_key=key, size_bytes=len(gcode_data))
        res = await session.execute(ins.returning(Artifact.id))
        artifact_id = res.scalar_one()

        # Assign artifact to job
        await session.execute(
            update(CAMJob)
            .where(CAMJob.id == job_id)
            .values(artifact_id=artifact_id)
        )
        await session.commit()

        # Clean up temporary files
        os.remove(dxf_file_path)
        os.remove(gcode_file_path)
    elif payload.get("job_kind") == "ZIP":
        job_ids = payload.get("context", {}).get("job_ids")
        if not job_ids:
            raise ValueError("job_ids not found in ZIP job context")

        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for job_id_to_zip in job_ids:
                job_to_zip = await session.get(CAMJob, job_id_to_zip)
                if job_to_zip and job_to_zip.artifact_id:
                    artifact_to_zip = await session.get(Artifact, job_to_zip.artifact_id)
                    if artifact_to_zip:
                        storage = ObjectStorage()
                        file_data = storage.get_object(artifact_to_zip.storage_key)
                        zip_file.writestr(artifact_to_zip.storage_key, file_data)

        # Save ZIP to storage
        storage = ObjectStorage()
        key = f"zip/{job_id}.zip"
        storage.put_object(key, zip_buffer.getvalue(), content_type="application/zip")

        # Create Artifact in DB
        ins = insert(Artifact).values(type="ZIP", storage_key=key, size_bytes=len(zip_buffer.getvalue()))
        res = await session.execute(ins.returning(Artifact.id))
        artifact_id = res.scalar_one()

        # Assign artifact to job
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


MAX_RETRIES = 3
BACKOFF_FACTOR = 2

async def run_worker(stop_event: asyncio.Event) -> None:
    r = get_redis()
    log.info("Worker started. Listening queues: %s, %s, %s", DXF_QUEUE, GCODE_QUEUE, ZIP_QUEUE)
    while not stop_event.is_set():
        try:
            # Блокирующее ожидание события из любой очереди
            # Pylance: указываем, что это awaitable и возвращает пару [queue, payload]
            res = await cast(Awaitable[list[str] | None], r.blpop([DXF_QUEUE, GCODE_QUEUE, ZIP_QUEUE], timeout=5))
            if not res:
                continue
            queue, raw = res
            payload = json.loads(raw)

            idempotency_key = payload.get("idempotency_key")
            if idempotency_key:
                existing_job = await session.execute(
                    select(CAMJob).where(CAMJob.idempotency_key == idempotency_key)
                )
                if existing_job.scalar_one_or_none():
                    log.warning(f"Job with idempotency key {idempotency_key} already processed, skipping.")
                    continue

            job_id = payload.get("job_id")
            if not job_id:
                log.error("Payload without job_id, sending to DLQ")
                await cast(Awaitable[int], r.lpush(DLQ_QUEUE, json.dumps({"error": "Missing job_id", "payload": payload})))
                continue

            async with SessionLocal() as session:
                session_typed: AsyncSession = cast(AsyncSession, session)
                try:
                    await process_job(session_typed, payload)
                    log.info("Processed %s job: %s", queue, job_id)
                except Exception as e:
                    # На DLQ и пометить Failed
                    log.error(f"Failed job {job_id}: {e}")
                    job = await session.get(CAMJob, job_id)
                    if job and job.attempt < MAX_RETRIES:
                        # Retry with exponential backoff
                        delay = BACKOFF_FACTOR ** job.attempt
                        log.info(f"Retrying job {job_id} in {delay} seconds...")
                        await asyncio.sleep(delay)
                        await session.execute(
                            update(CAMJob)
                            .where(CAMJob.id == job_id)
                            .values(attempt=job.attempt + 1, status=JobStatusEnum.Created)
                        )
                        await session.commit()
                        await enqueue(queue, payload) # Re-enqueue the job
                    else:
                        tb = traceback.format_exc(limit=3)
                        await cast(Awaitable[int], r.lpush(DLQ_QUEUE, json.dumps({"error": str(e), "payload": payload, "trace": tb})))
                        await session_typed.execute(
                            update(CAMJob)
                            .where(CAMJob.id == job_id)
                            .values(status=JobStatusEnum.Failed, error=str(e))
                        )
                        await session_typed.commit()
                        log.error("Job %s moved to DLQ after %s retries", job_id, MAX_RETRIES)
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
