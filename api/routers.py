from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
import base64
import uuid
import os
import logging
from fastapi.responses import StreamingResponse
import asyncio
import json

from .database import get_db
from . import models
from .models import (
    CAMJob, Artifact, Validation, ValidationItem, ValidationStatusEnum, ProductConfig, JobStatusEnum, Order, DialogueMessage
)
from .queues import enqueue, DXF_QUEUE, GCODE_QUEUE, ZIP_QUEUE
from .schemas import (
    OrderCreate, Order as OrderSchema,
    SpecExtractRequest, SpecExtractResponse,
    HardwareSelectRequest, HardwareSelectResponse,
    SpecValidateRequest, SpecValidateResponse,
    ValidationApproveRequest, ValidationApproveResponse,
    CAMJobRequest, CAMJobResponse,
    CAMJobStatusResponse,
    ArtifactDownloadResponse,
    Export1CRequest, Export1CResponse,
    ZIPJobRequest,
    DialogueTurnRequest
)
from . import crud
from shared.storage import ObjectStorage
from shared.yandex_ai import YandexCloudSettings, create_gpt_client, create_openai_client
from shared.spec_extraction import create_spec_extraction_service
from shared.embeddings import embed_text, concat_product_config_text
from api.vector_search import find_similar_hardware
from shared.yandex_ai import rank_hardware_with_gpt
from api.mocks.dialogue_mocks import (
    are_yc_keys_available,
    generate_mock_dialogue_response
)
from api.ai_tools import get_tools_schema, execute_tool_call
from shared.yandex_ai import ToolCall, GPTResponseWithTools

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")
dialogue_router = APIRouter(prefix="/api/v1/dialogue", tags=["Dialogue"])


@router.post("/orders", response_model=OrderSchema)
async def create_order(order: OrderCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_order(db=db, order=order)


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
    from api.export_1c import generate_order_excel, generate_order_csv, generate_1c_filename
    import zipfile
    import io

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
                    is_first_message=is_first_message
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
        with open("docs/ai_dialogue_spec.md", "r", encoding="utf-8") as f:
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
        with open("docs/ai_dialogue_spec.md", "r", encoding="utf-8") as f:
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
