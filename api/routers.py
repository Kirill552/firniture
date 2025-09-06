from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
import base64
import uuid

from .database import get_db
from .models import (
    CAMJob, Artifact, Validation, ValidationItem, ValidationStatusEnum, ProductConfig
)
from .queues import enqueue, DXF_QUEUE, GCODE_QUEUE, ZIP_QUEUE
from .schemas import (
    SpecExtractRequest, SpecExtractResponse,
    HardwareSelectRequest, HardwareSelectResponse,
    SpecValidateRequest, SpecValidateResponse,
    ValidationApproveRequest, ValidationApproveResponse,
    CAMJobRequest, CAMJobResponse,
    CAMJobStatusResponse,
    ArtifactDownloadResponse,
    Export1CRequest, Export1CResponse,
    ZIPJobRequest
)

@router.post("/cam/zip", response_model=CAMJobResponse)
async def cam_zip(req: ZIPJobRequest, db: AsyncSession = Depends(get_db)) -> CAMJobResponse:
    idempotency_key = str(uuid.uuid4())
    stmt = insert(CAMJob).values(job_kind="ZIP", status="Created", context={"job_ids": req.job_ids}, attempt=0, idempotency_key=idempotency_key)
    res = await db.execute(stmt.returning(CAMJob.id))
    job_id = res.scalar_one()
    await db.commit()

    await enqueue(ZIP_QUEUE, {"job_id": str(job_id), "job_kind": "ZIP", "order_id": req.order_id, "context": {"job_ids": req.job_ids}, "idempotency_key": idempotency_key})
    return CAMJobResponse(gcode_job_id=str(job_id), status="processing")
from shared.storage import ObjectStorage
from shared.yandex_ai import YandexCloudSettings
from shared.spec_extraction import create_spec_extraction_service

router = APIRouter(prefix="/api/v1")


@router.post("/spec/extract", response_model=SpecExtractResponse)
async def spec_extract(req: SpecExtractRequest) -> SpecExtractResponse:
    """Извлечение параметров из ТЗ, изображения или эскиза."""
    import os
    
    # Настройки Yandex Cloud (из env)
    yc_settings = YandexCloudSettings(
        yc_folder_id=os.getenv("YC_FOLDER_ID", ""),
        yc_api_key=os.getenv("YC_API_KEY", "")
    )
    
    if not yc_settings.yc_folder_id or not yc_settings.yc_api_key:
        # Fallback для разработки - возвращаем заглушку
        return SpecExtractResponse(
            product_config_id="pc_fallback", 
            parameters={"message": "YC credentials not configured", "type": req.input_type}
        )
    
    # Создаём сервис извлечения
    extraction_service = create_spec_extraction_service(yc_settings)
    
    try:
        if req.input_type == "text":
            # Обработка текстового ТЗ
            result = await extraction_service.extract_from_text(req.content)
            
        elif req.input_type in ("image", "sketch"):
            # Декодируем base64 изображение
            try:
                image_bytes = base64.b64decode(req.content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid base64 image: {e}")
            
            result = await extraction_service.extract_from_image(image_bytes)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported input_type: {req.input_type}")
        
        # Конвертируем в формат API ответа
        parameters_dict = {}
        for param in result.parameters:
            key = param.name
            if param.unit:
                parameters_dict[key] = f"{param.value} {param.unit}"
            else:
                parameters_dict[key] = param.value
            
            # Добавляем метаданные
            parameters_dict[f"{key}_confidence"] = param.confidence
            if param.question:
                parameters_dict[f"{key}_question"] = param.question
        
        # Добавляем общие метаданные
        parameters_dict["_processing_time"] = result.processing_time_seconds
        parameters_dict["_confidence_overall"] = result.confidence_overall
        parameters_dict["_source_type"] = result.source_type
        
        return SpecExtractResponse(
            product_config_id=result.product_config_id,
            parameters=parameters_dict
        )
        
    except Exception as e:
        # Логируем ошибку и возвращаем fallback
        import logging
        log = logging.getLogger(__name__)
        log.error(f"Spec extraction failed: {e}")
        
        return SpecExtractResponse(
            product_config_id="pc_error",
            parameters={"error": str(e), "input_type": req.input_type}
        )


from shared.embeddings import embed_text, concat_product_config_text
from api.vector_search import find_similar_hardware

from shared.yandex_ai import rank_hardware_with_gpt

@router.post("/hardware/select", response_model=HardwareSelectResponse)
async def hardware_select(req: HardwareSelectRequest, db: AsyncSession = Depends(get_db)) -> HardwareSelectResponse:
    product_config = await db.get(ProductConfig, uuid.UUID(req.product_config_id))
    if not product_config:
        raise HTTPException(status_code=404, detail="ProductConfig not found")

    # Generate embedding for the product config
    product_text = concat_product_config_text(product_config)
    embedding = await embed_text(product_text)

    # Find similar hardware
    similar_hardware = await find_similar_hardware(embedding, k=20, filters=req.criteria.model_dump(exclude_none=True))

    # Rank hardware with GPT
    import os
    yc_settings = YandexCloudSettings(
        yc_folder_id=os.getenv("YC_FOLDER_ID", ""),
        yc_api_key=os.getenv("YC_API_KEY", "")
    )
    ranked_hardware = await rank_hardware_with_gpt(product_config, similar_hardware, yc_settings)

    # Format response
    bom_items = []
    for item in ranked_hardware:
        bom_items.append(
            {
                "hardware_item_id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "quantity": 1, # Placeholder
                "supplier": item.brand, # Placeholder
                "version": item.version
            }
        )

    return HardwareSelectResponse(bom_id=f"bom_{uuid.uuid4()[:8]}", items=bom_items)


@router.post("/cam/dxf", response_model=CAMJobResponse)
async def cam_dxf(req: CAMJobRequest, db: AsyncSession = Depends(get_db)) -> CAMJobResponse:
    # создаём CAMJob в БД
    idempotency_key = str(uuid.uuid4())
    stmt = insert(CAMJob).values(job_kind="DXF", status="Created", context=req.context or {}, attempt=0, idempotency_key=idempotency_key)
    res = await db.execute(stmt.returning(CAMJob.id))
    job_id = res.scalar_one()
    await db.commit()

    # кладём в очередь Redis
    await enqueue(DXF_QUEUE, {"job_id": str(job_id), "job_kind": "DXF", "order_id": req.order_id, "product_config_id": req.product_config_id, "idempotency_key": idempotency_key})
    return CAMJobResponse(dxf_job_id=str(job_id), status="processing")


@router.post("/cam/gcode", response_model=CAMJobResponse)
async def cam_gcode(req: CAMJobRequest, db: AsyncSession = Depends(get_db)) -> CAMJobResponse:
    if not req.dxf_job_id:
        raise HTTPException(status_code=400, detail="dxf_job_id is required for G-code jobs")

    # Get the artifact_id from the DXF job
    dxf_job = await db.get(CAMJob, uuid.UUID(req.dxf_job_id))
    if not dxf_job or not dxf_job.artifact_id:
        raise HTTPException(status_code=404, detail="DXF job or its artifact not found")

    context = req.context or {}
    context["dxf_artifact_id"] = str(dxf_job.artifact_id)

    idempotency_key = str(uuid.uuid4())
    stmt = insert(CAMJob).values(job_kind="GCODE", status="Created", context=context, attempt=0, idempotency_key=idempotency_key)
    res = await db.execute(stmt.returning(CAMJob.id))
    job_id = res.scalar_one()
    await db.commit()

    await enqueue(GCODE_QUEUE, {"job_id": str(job_id), "job_kind": "GCODE", "order_id": req.order_id, "product_config_id": req.product_config_id, "context": context, "idempotency_key": idempotency_key})
    return CAMJobResponse(gcode_job_id=str(job_id), status="processing")


@router.get("/cam/jobs/{job_id}", response_model=CAMJobStatusResponse)
async def cam_job_status(job_id: str, db: AsyncSession = Depends(get_db)) -> CAMJobStatusResponse:
    stmt = select(CAMJob).where(CAMJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    kind: str = job.job_kind
    status: str = job.status
    if kind not in ("DXF", "GCODE"):
        raise HTTPException(status_code=500, detail="Invalid job kind")
    if status not in ("Created", "Processing", "Completed", "Failed"):
        raise HTTPException(status_code=500, detail="Invalid job status")
    return CAMJobStatusResponse(
        job_id=str(job.id),
        job_kind=kind,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        artifact_id=str(job.artifact_id) if job.artifact_id else None,
        error=job.error,
    )


@router.get("/artifacts/{artifact_id}/download", response_model=ArtifactDownloadResponse)
async def artifact_download(artifact_id: str, db: AsyncSession = Depends(get_db)) -> ArtifactDownloadResponse:
    stmt = select(Artifact).where(Artifact.id == artifact_id)
    res = await db.execute(stmt)
    art = res.scalar_one_or_none()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    storage = ObjectStorage()
    url = storage.presign_get(art.storage_key)
    return ArtifactDownloadResponse(artifact_id=str(art.id), url=url)


@router.post("/spec/validate", response_model=SpecValidateResponse)
async def spec_validate(req: SpecValidateRequest, db: AsyncSession = Depends(get_db)) -> SpecValidateResponse:
    """Создаёт сессию валидации для параметров, извлечённых из ТЗ."""
    try:
        product_config_uuid = uuid.UUID(req.product_config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product_config_id format")

    # Проверяем, существует ли ProductConfig
    product_config = await db.get(ProductConfig, product_config_uuid)
    if not product_config:
        raise HTTPException(status_code=404, detail=f"ProductConfig with id {req.product_config_id} not found")

    # Создаём запись о валидации
    validation = Validation(
        related_entity="ProductConfig",
        related_id=product_config_uuid,
        status=ValidationStatusEnum.Pending
    )
    db.add(validation)
    await db.flush()  # Flush для получения ID валидации

    # Создаём элементы валидации
    validation_items = []
    for item in req.required_approvals:
        validation_item = ValidationItem(
            validation_id=validation.id,
            key=item.parameter,
            proposed_value=item.value,
            description=item.question,
            status=ValidationStatusEnum.Pending
        )
        validation_items.append(validation_item)
    
    db.add_all(validation_items)
    await db.commit()

    return SpecValidateResponse(
        validation_id=str(validation.id),
        validation_required=True,
        approvals_needed=len(validation_items),
        next_step_allowed=False
    )


@router.post("/validation/approve", response_model=ValidationApproveResponse)
async def validation_approve(req: ValidationApproveRequest, db: AsyncSession = Depends(get_db)) -> ValidationApproveResponse:
    """Подтверждение или отклонение элементов валидации."""
    try:
        validation_uuid = uuid.UUID(req.validation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid validation_id format")

    # Получаем валидацию и связанные с ней элементы
    stmt = select(Validation).where(Validation.id == validation_uuid)
    result = await db.execute(stmt)
    validation = result.scalar_one_or_none()

    if not validation:
        raise HTTPException(status_code=404, detail=f"Validation with id {req.validation_id} not found")

    if validation.status != ValidationStatusEnum.Pending:
        raise HTTPException(status_code=400, detail=f"Validation is already in status '{validation.status}'")

    # Обновляем статусы элементов
    all_approved = True
    for approval in req.approvals:
        item_uuid = uuid.UUID(approval.validation_item_id)
        item_stmt = select(ValidationItem).where(ValidationItem.id == item_uuid, ValidationItem.validation_id == validation_uuid)
        item_result = await db.execute(item_stmt)
        validation_item = item_result.scalar_one_or_none()

        if not validation_item:
            raise HTTPException(status_code=404, detail=f"ValidationItem with id {approval.validation_item_id} not found in this validation")

        if approval.approved:
            validation_item.status = ValidationStatusEnum.Approved
        else:
            validation_item.status = ValidationStatusEnum.Rejected
            all_approved = False
        
        validation_item.comment = approval.comment
        db.add(validation_item)

    # Обновляем статус основной записи валидации
    if all_approved:
        validation.status = ValidationStatusEnum.Approved
        next_step_allowed = True
        response_status = "completed"
    else:
        validation.status = ValidationStatusEnum.Rejected
        next_step_allowed = False
        response_status = "failed"

    db.add(validation)
    await db.commit()

    return ValidationApproveResponse(
        validation_id=req.validation_id,
        status=response_status,
        next_step_allowed=next_step_allowed
    )


@router.post("/integrations/1c/export", response_model=Export1CResponse)
def export_1c(req: Export1CRequest) -> Export1CResponse:
    return Export1CResponse(success=True, **{"1c_order_id": "yc_1c_123"})
