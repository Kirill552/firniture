from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import traceback
from collections.abc import Awaitable
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.storage import ObjectStorage

from .constants import (
    DEFAULT_EDGE_THICKNESS_MM,
    DEFAULT_GAP_MM,
    DEFAULT_SHEET_HEIGHT_MM,
    DEFAULT_SHEET_WIDTH_MM,
)
from .database import SessionLocal
from .models import Artifact, CAMJob, JobStatusEnum
from .queues import DLQ_QUEUE, DXF_QUEUE, GCODE_QUEUE, ZIP_QUEUE, enqueue, get_redis

try:
    import ezdxf  # type: ignore

    from .dxf_generator import Panel, generate_panel_dxf
    DXF_GENERATOR_AVAILABLE = True
except Exception:  # pragma: no cover - установим в контейнере
    ezdxf = None
    DXF_GENERATOR_AVAILABLE = False

try:
    from .gcode_generator import MACHINE_PROFILES, MachineProfile, dxf_to_gcode
    GCODE_GENERATOR_AVAILABLE = True
except Exception:  # pragma: no cover
    GCODE_GENERATOR_AVAILABLE = False


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

    # Узнаем вид работы и генерируем артефакт
    artifact_id = None
    context = payload.get("context", {})

    if payload.get("job_kind") == "DXF" and DXF_GENERATOR_AVAILABLE:
        # Извлекаем панели из контекста
        panels_data = context.get("panels", [])
        if not panels_data:
            # Fallback на демо-панель
            panels_data = [
                {"name": "Демо-панель", "width_mm": 600, "height_mm": 400, "thickness_mm": 16}
            ]

        # Конвертируем в объекты Panel
        panels = []
        for p in panels_data:
            panels.append(Panel(
                id=p.get("id", str(uuid4())),
                name=p.get("name", "Панель"),
                width_mm=float(p.get("width_mm", 600)),
                height_mm=float(p.get("height_mm", 400)),
                thickness_mm=float(p.get("thickness_mm", 16)),
                material=p.get("material", "ЛДСП"),
                edge_top=p.get("edge_top", False),
                edge_bottom=p.get("edge_bottom", False),
                edge_left=p.get("edge_left", False),
                edge_right=p.get("edge_right", False),
                edge_thickness_mm=float(p.get("edge_thickness_mm", DEFAULT_EDGE_THICKNESS_MM)),
                drilling_holes=p.get("drilling_holes", []),
                notes=p.get("notes", ""),
            ))

        # Параметры листа
        sheet_width = float(context.get("sheet_width", DEFAULT_SHEET_WIDTH_MM))
        sheet_height = float(context.get("sheet_height", DEFAULT_SHEET_HEIGHT_MM))
        optimize = context.get("optimize", True)
        gap_mm = float(context.get("gap_mm", DEFAULT_GAP_MM))

        log.info(f"[DXF] Generating for {len(panels)} panels on sheet {sheet_width}x{sheet_height}")

        # Генерируем DXF
        data, layout = generate_panel_dxf(
            panels=panels,
            sheet_size=(sheet_width, sheet_height),
            optimize=optimize,
            gap_mm=gap_mm,
        )

        log.info(f"[DXF] Layout: {len(layout.placed_panels)} placed, {len(layout.unplaced_panels)} unplaced, utilization: {layout.utilization_percent:.1f}%")

        # Сохраняем результат раскладки в контексте задачи
        layout_result = {
            "utilization_percent": layout.utilization_percent,
            "panels_placed": len(layout.placed_panels),
            "panels_unplaced": len(layout.unplaced_panels),
        }
        await session.execute(
            update(CAMJob)
            .where(CAMJob.id == job_id)
            .values(context={**context, "layout_result": layout_result})
        )

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
        if not GCODE_GENERATOR_AVAILABLE:
            raise RuntimeError("G-code generator not available (missing ezdxf)")

        context = payload.get("context", {})
        dxf_artifact_id = context.get("dxf_artifact_id")
        if not dxf_artifact_id:
            raise ValueError("dxf_artifact_id not found in GCODE job context")

        # Получаем DXF файл из хранилища
        dxf_artifact = await session.get(Artifact, dxf_artifact_id)
        if not dxf_artifact:
            raise ValueError(f"DXF artifact {dxf_artifact_id} not found")

        storage = ObjectStorage()
        dxf_data = storage.get_object(dxf_artifact.storage_key)

        # Получаем профиль станка
        machine_profile = context.get("machine_profile", "weihong")
        log.info(f"[GCODE] Generating G-code from DXF {dxf_artifact_id}, profile={machine_profile}")

        # Создаём кастомный профиль с переопределёнными параметрами
        base_profile = MACHINE_PROFILES.get(machine_profile)
        if not base_profile:
            log.warning(f"Unknown profile {machine_profile}, using weihong")
            base_profile = MACHINE_PROFILES["weihong"]

        # Применяем переопределения из контекста
        custom_profile = MachineProfile(
            name=base_profile.name,
            machine_type=base_profile.machine_type,
            spindle_speed=context.get("spindle_speed", base_profile.spindle_speed),
            feed_rate_cutting=context.get("feed_rate_cutting", base_profile.feed_rate_cutting),
            feed_rate_plunge=context.get("feed_rate_plunge", base_profile.feed_rate_plunge),
            feed_rate_rapid=base_profile.feed_rate_rapid,
            safe_height=context.get("safe_height", base_profile.safe_height),
            cut_depth=context.get("cut_depth", base_profile.cut_depth),
            step_down=base_profile.step_down,
            tool_diameter=context.get("tool_diameter", base_profile.tool_diameter),
            tool_number=base_profile.tool_number,
            drill_peck_depth=base_profile.drill_peck_depth,
            drill_retract=base_profile.drill_retract,
            use_coolant=base_profile.use_coolant,
            use_tool_change=base_profile.use_tool_change,
            use_line_numbers=base_profile.use_line_numbers,
            line_number_increment=base_profile.line_number_increment,
            comment_start=base_profile.comment_start,
            comment_end=base_profile.comment_end,
            program_start=base_profile.program_start,
            program_end=base_profile.program_end,
        )

        # Генерируем G-code
        gcode_text = dxf_to_gcode(
            dxf_data=dxf_data,
            custom_profile=custom_profile,
            cut_depth=context.get("cut_depth"),
        )
        gcode_data = gcode_text.encode("utf-8")

        log.info(f"[GCODE] Generated {len(gcode_data)} bytes of G-code")

        # Сохраняем в хранилище
        key = f"gcode/{job_id}.gcode"
        storage.put_object(key, gcode_data, content_type="text/plain; charset=utf-8")

        # Создаём Artifact в БД
        ins = insert(Artifact).values(type="GCODE", storage_key=key, size_bytes=len(gcode_data))
        res = await session.execute(ins.returning(Artifact.id))
        artifact_id = res.scalar_one()

        # Присваиваем артефакт задаче
        await session.execute(
            update(CAMJob)
            .where(CAMJob.id == job_id)
            .values(artifact_id=artifact_id)
        )
        await session.commit()
    elif payload.get("job_kind") == "ZIP":
        job_ids = payload.get("context", {}).get("job_ids")
        if not job_ids:
            raise ValueError("job_ids not found in ZIP job context")

        import io
        import zipfile

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

            job_id = payload.get("job_id")
            if not job_id:
                log.error("Payload without job_id, sending to DLQ")
                await cast(Awaitable[int], r.lpush(DLQ_QUEUE, json.dumps({"error": "Missing job_id", "payload": payload})))
                continue

            async with SessionLocal() as session:
                # Проверка idempotency_key
                idempotency_key = payload.get("idempotency_key")
                if idempotency_key:
                    existing_job = await session.execute(
                        select(CAMJob).where(CAMJob.idempotency_key == idempotency_key)
                    )
                    if existing_job.scalar_one_or_none():
                        log.warning(f"Job with idempotency key {idempotency_key} already processed, skipping.")
                        continue

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
