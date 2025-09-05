from fastapi import APIRouter
from .schemas import (
    SpecExtractRequest, SpecExtractResponse,
    HardwareSelectRequest, HardwareSelectResponse,
    SpecValidateRequest, SpecValidateResponse,
    ValidationApproveRequest, ValidationApproveResponse,
    CAMJobRequest, CAMJobResponse,
    Export1CRequest, Export1CResponse,
)

router = APIRouter(prefix="/api/v1")


@router.post("/spec/extract", response_model=SpecExtractResponse)
def spec_extract(req: SpecExtractRequest) -> SpecExtractResponse:
    # Заглушка: возвращаем фиктивный product_config_id и параметры
    return SpecExtractResponse(product_config_id="pc_123", parameters={"thickness": 18})


@router.post("/hardware/select", response_model=HardwareSelectResponse)
def hardware_select(req: HardwareSelectRequest) -> HardwareSelectResponse:
    return HardwareSelectResponse(bom_id="bom_123", items=[])


@router.post("/cam/dxf", response_model=CAMJobResponse)
def cam_dxf(req: CAMJobRequest) -> CAMJobResponse:
    return CAMJobResponse(dxf_job_id="dxf_123", status="processing")


@router.post("/cam/gcode", response_model=CAMJobResponse)
def cam_gcode(req: CAMJobRequest) -> CAMJobResponse:
    return CAMJobResponse(gcode_job_id="gcode_123", status="processing")


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
