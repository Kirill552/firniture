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
from shared.yandex_ai import YandexCloudSettings, create_gpt_client
from shared.spec_extraction import create_spec_extraction_service
from shared.embeddings import embed_text, concat_product_config_text
from api.vector_search import find_similar_hardware
from shared.yandex_ai import rank_hardware_with_gpt

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")
dialogue_router = APIRouter(prefix="/api/v1/dialogue", tags=["Dialogue"])


@router.post("/orders", response_model=OrderSchema)
async def create_order(order: OrderCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_order(db=db, order=order)


# ... (existing routes are kept the same, so they are omitted for brevity) ...

@router.post("/integrations/1c/export", response_model=Export1CResponse)
def export_1c(req: Export1CRequest) -> Export1CResponse:
    return Export1CResponse(success=True, **{"1c_order_id": "yc_1c_123"})


@dialogue_router.post("/clarify")
async def dialogue_clarify(req: DialogueTurnRequest, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """
    Принимает текущую историю диалога и возвращает потоковый ответ от ИИ-технолога.
    """
    order = await crud.get_order_with_history(db, req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

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

    messages = [{"role": "system", "text": system_prompt_text}]
    
    # Добавляем историю из БД
    for msg in sorted(order.dialogue_messages, key=lambda m: m.turn_number):
        messages.append({"role": msg.role, "text": msg.content})

    # Добавляем новые сообщения из запроса
    current_turn = (order.dialogue_messages[-1].turn_number + 1) if order.dialogue_messages else 1
    for user_msg in req.messages:
        messages.append({"role": user_msg.role, "text": user_msg.content})
        await crud.create_dialogue_message(db, order.id, current_turn, user_msg.role, user_msg.content)

    # 2. Готовимся к стримингу ответа
    yc_settings = YandexCloudSettings(
        yc_folder_id=os.getenv("YC_FOLDER_ID", ""),
        yc_api_key=os.getenv("YC_API_KEY", "")
    )

    async def response_generator():
        full_response = ""
        try:
            async with create_gpt_client(yc_settings) as client:
                async for chunk in client.stream_chat_completion(messages):
                    full_response += chunk
                    yield chunk
            
            # 3. Сохраняем полный ответ ассистента в БД
            await crud.create_dialogue_message(db, order.id, current_turn, "assistant", full_response)

        except Exception as e:
            log.error(f"Dialogue clarification failed for order {req.order_id}: {e}")
            yield "\n\n[ОШИБКА] Не удалось получить ответ от ИИ-ассистента."

    return StreamingResponse(response_generator(), media_type="text/plain")
