from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
import base64

from .database import get_db
from .models import CAMJob, Artifact
from .queues import enqueue, DXF_QUEUE, GCODE_QUEUE
from .schemas import (
    SpecExtractRequest, SpecExtractResponse,
    HardwareSelectRequest, HardwareSelectResponse,
    SpecValidateRequest, SpecValidateResponse,
    ValidationApproveRequest, ValidationApproveResponse,
    CAMJobRequest, CAMJobResponse,
    CAMJobStatusResponse,
    ArtifactDownloadResponse,
    Export1CRequest, Export1CResponse,
)
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


@router.post("/hardware/select", response_model=HardwareSelectResponse)
def hardware_select(req: HardwareSelectRequest) -> HardwareSelectResponse:
    return HardwareSelectResponse(bom_id="bom_123", items=[])


@router.post("/cam/dxf", response_model=CAMJobResponse)
async def cam_dxf(req: CAMJobRequest, db: AsyncSession = Depends(get_db)) -> CAMJobResponse:
    # создаём CAMJob в БД
    stmt = insert(CAMJob).values(job_kind="DXF", status="Created", context=req.context or {}, attempt=0)
    res = await db.execute(stmt.returning(CAMJob.id))
    job_id = res.scalar_one()
    await db.commit()

    # кладём в очередь Redis
    await enqueue(DXF_QUEUE, {"job_id": str(job_id), "job_kind": "DXF", "order_id": req.order_id, "product_config_id": req.product_config_id})
    return CAMJobResponse(dxf_job_id=str(job_id), status="processing")


@router.post("/cam/gcode", response_model=CAMJobResponse)
async def cam_gcode(req: CAMJobRequest, db: AsyncSession = Depends(get_db)) -> CAMJobResponse:
    stmt = insert(CAMJob).values(job_kind="GCODE", status="Created", context=req.context or {}, attempt=0)
    res = await db.execute(stmt.returning(CAMJob.id))
    job_id = res.scalar_one()
    await db.commit()

    await enqueue(GCODE_QUEUE, {"job_id": str(job_id), "job_kind": "GCODE", "order_id": req.order_id, "product_config_id": req.product_config_id})
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
def spec_validate(req: SpecValidateRequest) -> SpecValidateResponse:
    needed = len(req.required_approvals)
    return SpecValidateResponse(validation_required=True, approvals_needed=needed, next_step_allowed=False)


@router.post("/validation/approve", response_model=ValidationApproveResponse)
def validation_approve(req: ValidationApproveRequest) -> ValidationApproveResponse:
    return ValidationApproveResponse(validation_id=req.validation_id, status="completed", next_step_allowed=True)


@router.post("/integrations/1c/export", response_model=Export1CResponse)
def export_1c(req: Export1CRequest) -> Export1CResponse:
    return Export1CResponse(success=True, **{"1c_order_id": "yc_1c_123"})
