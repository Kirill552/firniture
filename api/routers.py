import json
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.ai_tools import execute_tool_call, get_tools_schema
from api.mocks.dialogue_mocks import are_yc_keys_available, generate_mock_dialogue_response
from api.vision_extraction import (
    extract_furniture_params_from_image,
    extract_furniture_params_mock,
)
from shared.storage import ObjectStorage
from shared.yandex_ai import (
    GPTResponseWithTools,
    YandexCloudSettings,
    create_openai_client,
)

from . import crud, models
from .auth import get_current_user_optional
from .database import get_db
from .models import (
    Artifact,
    CAMJob,
    JobStatusEnum,
    User,
)
from .queues import DXF_QUEUE, GCODE_QUEUE, enqueue
from .schemas import (
    DialogueTurnRequest,
    Export1CRequest,
    Export1CResponse,
    ImageExtractRequest,
    ImageExtractResponse,
    OrderCreate,
)
from .schemas import Order as OrderSchema

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")
dialogue_router = APIRouter(prefix="/api/v1/dialogue", tags=["Dialogue"])


@router.post("/orders", response_model=OrderSchema)
async def create_order(
    order: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Создать новый заказ.

    Если пользователь авторизован — заказ привязывается к его фабрике.
    Если нет — заказ создаётся без привязки (для анонимных демо).
    """
    factory_id = current_user.factory_id if current_user else None
    created_by_id = current_user.id if current_user else None

    return await crud.create_order(
        db=db,
        order=order,
        factory_id=factory_id,
        created_by_id=created_by_id
    )


@router.get("/orders", response_model=list[OrderSchema])
async def list_orders(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Получить список заказов текущей фабрики.

    Если пользователь не авторизован — возвращает пустой список.
    """
    if not current_user:
        return []

    return await crud.get_orders_by_factory(
        db=db,
        factory_id=current_user.factory_id,
        limit=limit,
        offset=offset
    )


# ... (existing routes are kept the same, so they are omitted for brevity) ...

@router.post("/integrations/1c/export", response_model=Export1CResponse)
async def export_1c(req: Export1CRequest, db: AsyncSession = Depends(get_db)) -> Export1CResponse:
    """
    Экспорт заказа в формате для 1С.

    Поддерживаемые форматы:
    - excel: Excel файл (.xlsx) с листами Заказ, Изделия, Панели, Фурнитура
    - csv: Набор CSV файлов в ZIP архиве

    Возвращает presigned URL для скачивания (действует 15 минут).
    """
    import io
    import zipfile

    from api.export_1c import generate_1c_filename, generate_order_csv, generate_order_excel

    # Получаем заказ с продуктами
    order = await crud.get_order_with_products(db, req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Получаем BOM items если есть
    bom_result = await db.execute(
        select(models.BOMItem).where(models.BOMItem.order_id == req.order_id)
    )
    bom_items = list(bom_result.scalars().all())

    storage = ObjectStorage()
    storage.ensure_bucket()

    if req.format == "excel":
        # Генерируем Excel
        excel_bytes = generate_order_excel(order, order.products, bom_items)
        filename = generate_1c_filename(order, "xlsx")
        storage_key = f"exports/1c/{filename}"

        storage.put_object(
            key=storage_key,
            data=excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:  # csv
        # Генерируем CSV файлы и пакуем в ZIP
        csv_files = generate_order_csv(order, order.products, bom_items)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in csv_files.items():
                zf.writestr(name, content)

        zip_buffer.seek(0)
        filename = generate_1c_filename(order, "zip")
        storage_key = f"exports/1c/{filename}"

        storage.put_object(
            key=storage_key,
            data=zip_buffer.getvalue(),
            content_type="application/zip"
        )

    # Генерируем presigned URL
    download_url = storage.presign_get(storage_key, ttl_seconds=900)

    log.info(f"[1C Export] Order {req.order_id} exported as {req.format}: {filename}")

    return Export1CResponse(
        success=True,
        format=req.format,
        filename=filename,
        download_url=download_url,
        expires_in_seconds=900
    )


# ============================================================================
# Vision OCR - извлечение параметров из изображений
# ============================================================================

@router.post("/spec/extract-from-image", response_model=ImageExtractResponse)
async def extract_from_image(req: ImageExtractRequest) -> ImageExtractResponse:
    """
    Извлечение параметров мебели из фото или эскиза.

    Процесс:
    1. Vision OCR: распознавание текста с изображения
    2. GPT: парсинг текста в структурированные параметры
    3. При низкой уверенности — рекомендация перейти в диалог

    ## Пример запроса:
    ```json
    {
        "image_base64": "base64_encoded_image...",
        "image_mime_type": "image/jpeg",
        "language_hint": "ru"
    }
    ```

    ## Пример ответа:
    ```json
    {
        "success": true,
        "parameters": {
            "furniture_type": {"category": "навесной_шкаф", ...},
            "dimensions": {"width_mm": 600, "height_mm": 720, ...},
            "body_material": {"type": "ЛДСП", "color": "белый"},
            ...
        },
        "fallback_to_dialogue": false,
        "ocr_confidence": 0.85,
        "processing_time_ms": 1500
    }
    ```

    При `fallback_to_dialogue: true` рекомендуется перенаправить пользователя
    в диалог с ИИ-технологом для уточнения параметров.
    """
    # Проверяем наличие Yandex Cloud ключей
    use_mock = not are_yc_keys_available()

    if use_mock:
        log.warning("[Vision OCR] Mock mode: YC keys not found")
        return await extract_furniture_params_mock(req.image_base64)

    log.info(f"[Vision OCR] Processing image, mime: {req.image_mime_type}, lang: {req.language_hint}")

    result = await extract_furniture_params_from_image(
        image_base64=req.image_base64,
        language_hint=req.language_hint,
    )

    log.info(f"[Vision OCR] Result: success={result.success}, confidence={result.ocr_confidence:.2f}, fallback={result.fallback_to_dialogue}")

    return result


# ============================================================================
# CAM - генерация DXF и G-code (P1)
# ============================================================================

from .gcode_generator import get_available_profiles
from .schemas import (
    ArtifactDownload,
    CAMJobStatus,
    DXFJobRequest,
    DXFJobResponse,
    GCodeJobRequest,
    GCodeJobResponse,
    MachineProfileInfo,
    MachineProfilesList,
)


@router.post("/cam/dxf", response_model=DXFJobResponse)
async def create_dxf_job(req: DXFJobRequest, db: AsyncSession = Depends(get_db)) -> DXFJobResponse:
    """
    Создаёт задачу генерации DXF файла для раскроя панелей.

    ## Пример запроса:
    ```json
    {
        "panels": [
            {"name": "Боковина левая", "width_mm": 720, "height_mm": 560, "edge_left": true},
            {"name": "Боковина правая", "width_mm": 720, "height_mm": 560, "edge_right": true},
            {"name": "Дно", "width_mm": 568, "height_mm": 560, "edge_top": true}
        ],
        "optimize_layout": true
    }
    ```

    Задача ставится в очередь и обрабатывается worker'ом.
    Проверяйте статус через GET /cam/jobs/{job_id}.
    """
    # Определяем размер листа
    sheet_width = req.sheet_width_mm or 2800
    sheet_height = req.sheet_height_mm or 2070

    # Создаём CAM задачу в БД
    job_id = uuid.uuid4()
    context = {
        "panels": [p.model_dump() for p in req.panels],
        "sheet_width": sheet_width,
        "sheet_height": sheet_height,
        "optimize": req.optimize_layout,
        "gap_mm": req.gap_mm,
    }

    stmt = insert(CAMJob).values(
        id=job_id,
        order_id=req.order_id,
        job_kind="DXF",
        status=JobStatusEnum.Created,
        context=context,
        idempotency_key=req.idempotency_key,
    )
    await db.execute(stmt)
    await db.commit()

    # Отправляем в очередь
    await enqueue(DXF_QUEUE, {
        "job_id": str(job_id),
        "job_kind": "DXF",
        "context": context,
        "idempotency_key": req.idempotency_key,
    })

    log.info(f"[CAM] Created DXF job {job_id} with {len(req.panels)} panels")

    return DXFJobResponse(
        job_id=job_id,
        status="created",
        panels_count=len(req.panels),
        sheet_size=(sheet_width, sheet_height),
    )


@router.get("/cam/jobs/{job_id}", response_model=CAMJobStatus)
async def get_cam_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CAMJobStatus:
    """
    Получить статус CAM задачи.

    Статусы:
    - Created: задача создана, ожидает обработки
    - Processing: задача выполняется
    - Completed: задача завершена, доступен артефакт
    - Failed: ошибка выполнения

    При статусе Completed используйте /cam/jobs/{job_id}/download для скачивания.
    """
    job = await db.get(CAMJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="CAM job not found")

    # Извлекаем информацию о раскладке из контекста (если есть)
    layout_info = job.context.get("layout_result", {}) if job.context else {}

    return CAMJobStatus(
        job_id=job.id,
        job_kind=job.job_kind,
        status=job.status,
        artifact_id=job.artifact_id,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        utilization_percent=layout_info.get("utilization_percent"),
        panels_placed=layout_info.get("panels_placed"),
        panels_unplaced=layout_info.get("panels_unplaced"),
    )


@router.get("/cam/jobs/{job_id}/download", response_model=ArtifactDownload)
async def download_cam_artifact(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ArtifactDownload:
    """
    Получить ссылку для скачивания результата CAM задачи.

    Возвращает presigned URL, действительный 15 минут.
    """
    job = await db.get(CAMJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="CAM job not found")

    if job.status != JobStatusEnum.Completed:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status.value}"
        )

    if not job.artifact_id:
        raise HTTPException(status_code=404, detail="No artifact for this job")

    artifact = await db.get(Artifact, job.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Генерируем presigned URL
    storage = ObjectStorage()
    url = storage.presign_get(artifact.storage_key, ttl_seconds=900)

    # Определяем имя файла
    ext = "dxf" if job.job_kind == "DXF" else "gcode" if job.job_kind == "GCODE" else "zip"
    filename = f"order_{job.order_id}_{job.job_kind.lower()}.{ext}" if job.order_id else f"job_{job_id}.{ext}"

    return ArtifactDownload(
        artifact_id=artifact.id,
        type=job.job_kind,
        filename=filename,
        download_url=url,
        size_bytes=artifact.size_bytes or 0,
        expires_in_seconds=900,
    )


# ============================================================================
# G-code генерация (P2)
# ============================================================================

@router.get("/cam/machine-profiles", response_model=MachineProfilesList)
async def list_machine_profiles() -> MachineProfilesList:
    """
    Получить список доступных профилей станков ЧПУ.

    Профили включают настройки для популярных систем управления:
    - **fanuc** — Fanuc (ISO 6983, ГОСТ 20999-83) — промышленный стандарт
    - **mach3** — Mach3 — популярен для малого/среднего бизнеса
    - **nc_studio** — NC Studio (Weihong) — китайские станки, массовый сегмент в России
    - **grbl** — GRBL — любительские станки
    - **homag** — Homag — премиум мебельное оборудование
    """
    profiles = get_available_profiles()
    return MachineProfilesList(
        profiles=[MachineProfileInfo(**p) for p in profiles]
    )


@router.post("/cam/gcode", response_model=GCodeJobResponse)
async def create_gcode_job(req: GCodeJobRequest, db: AsyncSession = Depends(get_db)) -> GCodeJobResponse:
    """
    Создаёт задачу генерации G-code из DXF артефакта.

    ## Процесс:
    1. Получает DXF файл по artifact_id
    2. Применяет профиль станка и пользовательские параметры
    3. Конвертирует геометрию DXF в G-code
    4. Сохраняет результат как новый артефакт

    ## Пример запроса:
    ```json
    {
        "dxf_artifact_id": "550e8400-e29b-41d4-a716-446655440000",
        "machine_profile": "mach3",
        "cut_depth": 18.0
    }
    ```

    Задача ставится в очередь. Проверяйте статус через GET /cam/jobs/{job_id}.
    """
    # Проверяем что DXF артефакт существует
    dxf_artifact = await db.get(Artifact, req.dxf_artifact_id)
    if not dxf_artifact:
        raise HTTPException(status_code=404, detail=f"DXF artifact {req.dxf_artifact_id} not found")

    if dxf_artifact.type != "DXF":
        raise HTTPException(status_code=400, detail=f"Artifact is not DXF type: {dxf_artifact.type}")

    # Создаём CAM задачу
    job_id = uuid.uuid4()

    # Собираем контекст с переопределением параметров
    context = {
        "dxf_artifact_id": str(req.dxf_artifact_id),
        "machine_profile": req.machine_profile,
    }

    # Добавляем переопределения параметров если заданы
    if req.spindle_speed is not None:
        context["spindle_speed"] = req.spindle_speed
    if req.feed_rate_cutting is not None:
        context["feed_rate_cutting"] = req.feed_rate_cutting
    if req.feed_rate_plunge is not None:
        context["feed_rate_plunge"] = req.feed_rate_plunge
    if req.cut_depth is not None:
        context["cut_depth"] = req.cut_depth
    if req.safe_height is not None:
        context["safe_height"] = req.safe_height
    if req.tool_diameter is not None:
        context["tool_diameter"] = req.tool_diameter

    stmt = insert(CAMJob).values(
        id=job_id,
        order_id=req.order_id,
        job_kind="GCODE",
        status=JobStatusEnum.Created,
        context=context,
        idempotency_key=req.idempotency_key,
    )
    await db.execute(stmt)
    await db.commit()

    # Отправляем в очередь
    await enqueue(GCODE_QUEUE, {
        "job_id": str(job_id),
        "job_kind": "GCODE",
        "context": context,
        "idempotency_key": req.idempotency_key,
    })

    log.info(f"[CAM] Created GCODE job {job_id} from DXF {req.dxf_artifact_id}, profile={req.machine_profile}")

    return GCodeJobResponse(
        job_id=job_id,
        status="created",
        machine_profile=req.machine_profile,
        dxf_artifact_id=req.dxf_artifact_id,
    )


@dialogue_router.post("/clarify")
async def dialogue_clarify(req: DialogueTurnRequest, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """
    Принимает текущую историю диалога и возвращает потоковый ответ от ИИ-технолога.

    Если YC_FOLDER_ID и YC_API_KEY не заданы — использует mock ответы для локальной разработки.
    """
    order = await crud.get_order_with_history(db, req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Проверяем наличие Yandex Cloud ключей
    use_mock_mode = not are_yc_keys_available()

    if use_mock_mode:
        log.warning(f"[MOCK MODE] YC keys not found. Using mock dialogue responses for order {req.order_id}")

    # Добавляем новые сообщения из запроса в БД
    current_turn = (order.dialogue_messages[-1].turn_number + 1) if order.dialogue_messages else 1
    user_message_text = ""
    for user_msg in req.messages:
        user_message_text = user_msg.content  # Сохраняем последнее сообщение пользователя
        await crud.create_dialogue_message(db, order.id, current_turn, user_msg.role, user_msg.content)

    # MOCK РЕЖИМ - используем заготовленные ответы
    if use_mock_mode:
        async def mock_response_generator():
            full_response = ""
            is_first_message = current_turn == 1

            try:
                async for chunk in generate_mock_dialogue_response(
                    order_id=order.id,
                    user_message=user_message_text,
                    is_first_message=is_first_message,
                    extracted_context=req.extracted_context
                ):
                    full_response += chunk
                    yield chunk

                # Сохраняем полный mock ответ в БД
                await crud.create_dialogue_message(db, order.id, current_turn, "assistant", full_response)
                log.info(f"[MOCK MODE] Mock response saved to DB for order {order.id}")

            except Exception as e:
                log.error(f"[MOCK MODE] Mock dialogue generation failed for order {req.order_id}: {e}")
                yield "\n\n[ОШИБКА] Не удалось сгенерировать mock ответ."

        return StreamingResponse(mock_response_generator(), media_type="text/plain")

    # PRODUCTION РЕЖИМ - используем YandexGPT через OpenAI-совместимый API
    # 1. Собираем историю для YandexGPT
    try:
        with open("docs/ai_dialogue_spec.md", encoding="utf-8") as f:
            # Пропускаем до системного промпта
            for line in f:
                if "Ты — «Технолог-GPT»" in line:
                    system_prompt_text = line + f.read()
                    break
            else:
                raise FileNotFoundError("System prompt not found in spec")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="AI dialogue spec file not found.")

    # OpenAI-совместимый формат: "content" вместо "text"
    # Если есть извлечённый контекст из Vision OCR — добавляем в системный промпт
    if req.extracted_context:
        system_prompt_text += f"\n\n## Данные из загруженного изображения/эскиза:\n{req.extracted_context}\n\nИспользуй эти данные как отправную точку. Подтверди их с пользователем и уточни недостающие детали."

    messages = [{"role": "system", "content": system_prompt_text}]

    # Добавляем историю из БД (предыдущие сообщения)
    for msg in sorted(order.dialogue_messages, key=lambda m: m.turn_number):
        messages.append({"role": msg.role, "content": msg.content})

    # ВАЖНО: Добавляем текущее сообщение пользователя (оно уже сохранено в БД, но ещё не в order.dialogue_messages)
    if user_message_text:
        messages.append({"role": "user", "content": user_message_text})

    # 2. Готовимся к стримингу ответа через OpenAI-совместимый API
    yc_settings = YandexCloudSettings(
        yc_folder_id=os.getenv("YC_FOLDER_ID", ""),
        yc_api_key=os.getenv("YC_API_KEY", "")
    )

    async def response_generator():
        full_response = ""
        try:
            log.info(f"[PRODUCTION MODE] Using YandexGPT (OpenAI API) for order {req.order_id}")
            async with create_openai_client(yc_settings) as client:
                async for chunk in client.stream_chat_completion(
                    messages,
                    temperature=0.4,  # Немного выше для более естественных ответов
                    top_p=0.9,
                    frequency_penalty=0.3,  # Уменьшаем повторения
                ):
                    full_response += chunk
                    yield chunk

            # 3. Сохраняем полный ответ ассистента в БД
            await crud.create_dialogue_message(db, order.id, current_turn, "assistant", full_response)

        except Exception as e:
            log.error(f"Dialogue clarification failed for order {req.order_id}: {e}")
            yield "\n\n[ОШИБКА] Не удалось получить ответ от ИИ-ассистента."

    return StreamingResponse(response_generator(), media_type="text/plain")


@dialogue_router.post("/clarify-with-tools")
async def dialogue_clarify_with_tools(req: DialogueTurnRequest, db: AsyncSession = Depends(get_db)):
    """
    Диалог с ИИ-технологом с поддержкой Function Calling.

    Модель может вызывать инструменты для:
    - Поиска фурнитуры в каталоге (find_hardware)
    - Проверки совместимости (check_hardware_compatibility)
    - Получения детальной информации (get_hardware_details)
    - Расчёта количества (calculate_hardware_qty)

    Возвращает JSON с результатами, включая вызовы инструментов.
    """
    order = await crud.get_order_with_history(db, req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Проверяем наличие Yandex Cloud ключей
    if not are_yc_keys_available():
        log.warning(f"[MOCK MODE] YC keys not found for order {req.order_id}")
        return {
            "success": False,
            "error": "YC_FOLDER_ID и YC_API_KEY не настроены",
            "mock_mode": True
        }

    # Добавляем новые сообщения из запроса в БД
    current_turn = (order.dialogue_messages[-1].turn_number + 1) if order.dialogue_messages else 1
    user_message_text = ""
    for user_msg in req.messages:
        user_message_text = user_msg.content
        await crud.create_dialogue_message(db, order.id, current_turn, user_msg.role, user_msg.content)

    # Загружаем системный промпт
    try:
        with open("docs/ai_dialogue_spec.md", encoding="utf-8") as f:
            for line in f:
                if "Ты — «Технолог-GPT»" in line:
                    system_prompt_text = line + f.read()
                    break
            else:
                raise FileNotFoundError("System prompt not found in spec")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="AI dialogue spec file not found.")

    # Дополняем системный промпт информацией об инструментах
    tools_info = """

## Доступные инструменты

У тебя есть доступ к каталогу фурнитуры. Используй инструменты для:
- Поиска подходящей фурнитуры по запросу клиента
- Проверки совместимости фурнитуры с материалом и толщиной
- Получения детальной информации о позициях
- Расчёта необходимого количества фурнитуры

Когда клиент спрашивает о фурнитуре или нужно подобрать комплектующие - вызывай соответствующие инструменты.
"""
    system_prompt_text += tools_info

    # Собираем историю сообщений
    messages = [{"role": "system", "content": system_prompt_text}]

    for msg in sorted(order.dialogue_messages, key=lambda m: m.turn_number):
        messages.append({"role": msg.role, "content": msg.content})

    if user_message_text:
        messages.append({"role": "user", "content": user_message_text})

    # Инициализируем клиент
    yc_settings = YandexCloudSettings(
        yc_folder_id=os.getenv("YC_FOLDER_ID", ""),
        yc_api_key=os.getenv("YC_API_KEY", "")
    )

    tools = get_tools_schema()
    max_iterations = 5  # Максимум итераций для предотвращения бесконечного цикла
    tool_calls_log = []
    final_response = None

    try:
        async with create_openai_client(yc_settings) as client:
            for iteration in range(max_iterations):
                log.info(f"[Function Calling] Iteration {iteration + 1}, messages: {len(messages)}")

                # Вызываем модель с инструментами
                response: GPTResponseWithTools = await client.chat_completion_with_tools(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.4,
                )

                log.info(f"[Function Calling] finish_reason: {response.finish_reason}, tool_calls: {len(response.tool_calls)}")

                # Если модель не вызвала инструменты - это финальный ответ
                if not response.tool_calls:
                    final_response = response.text
                    break

                # Добавляем ответ ассистента с tool_calls в историю
                assistant_message = {
                    "role": "assistant",
                    "content": response.text or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                            }
                        }
                        for tc in response.tool_calls
                    ]
                }
                messages.append(assistant_message)

                # Выполняем каждый вызов инструмента
                for tool_call in response.tool_calls:
                    log.info(f"[Function Calling] Executing tool: {tool_call.name}")

                    tool_result = await execute_tool_call(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments
                    )

                    tool_calls_log.append({
                        "tool": tool_call.name,
                        "arguments": tool_call.arguments,
                        "result": tool_result
                    })

                    # Добавляем результат в историю
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })

            else:
                # Превышено максимальное количество итераций
                log.warning(f"[Function Calling] Max iterations reached for order {req.order_id}")
                final_response = "Извините, не удалось получить ответ. Попробуйте переформулировать вопрос."

        # Сохраняем финальный ответ в БД
        if final_response:
            await crud.create_dialogue_message(db, order.id, current_turn, "assistant", final_response)

        return {
            "success": True,
            "response": final_response,
            "tool_calls": tool_calls_log,
            "iterations": min(iteration + 1, max_iterations) if 'iteration' in dir() else 1
        }

    except Exception as e:
        log.error(f"[Function Calling] Error for order {req.order_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_calls": tool_calls_log
        }
