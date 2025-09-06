from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from datetime import datetime


class SpecExtractRequest(BaseModel):
    input_type: Literal["text", "image", "sketch"]
    content: str


class SpecExtractResponse(BaseModel):
    product_config_id: str
    parameters: Dict[str, Any]


class HardwareSelectCriteria(BaseModel):
    material: Optional[str] = None
    thickness: Optional[float] = Field(None, description="Толщина в мм")


class HardwareSelectRequest(BaseModel):
    product_config_id: str
    criteria: HardwareSelectCriteria


class BOMItem(BaseModel):
    hardware_item_id: str
    sku: str
    name: Optional[str] = None
    quantity: int
    supplier: Optional[str] = None
    version: Optional[str] = None


class HardwareSelectResponse(BaseModel):
    bom_id: str
    items: List[BOMItem]


class SpecValidateItem(BaseModel):
    parameter: str
    value: Any
    confidence: Optional[float] = None
    question: Optional[str] = None


class SpecValidateRequest(BaseModel):
    product_config_id: str
    stage: Literal["extraction_review", "rag_review"]
    required_approvals: List[SpecValidateItem]


class SpecValidateResponse(BaseModel):
    validation_id: str
    validation_required: bool
    approvals_needed: int
    next_step_allowed: bool


class ValidationApproveItem(BaseModel):
    validation_item_id: str
    approved: bool
    comment: Optional[str] = None


class ValidationApproveRequest(BaseModel):
    validation_id: str
    approvals: List[ValidationApproveItem]


class ValidationApproveResponse(BaseModel):
    validation_id: str
    status: Literal["completed", "failed"]
    next_step_allowed: bool


class CAMJobRequest(BaseModel):
    product_config_id: str
    order_id: Optional[str] = None
    dxf_job_id: Optional[str] = None # For G-code jobs
    context: Dict[str, Any] = Field(default_factory=dict)


class CAMJobResponse(BaseModel):
    dxf_job_id: Optional[str] = None
    gcode_job_id: Optional[str] = None
    status: Literal["processing", "created"]


class CAMJobStatusResponse(BaseModel):
    job_id: str
    job_kind: Literal["DXF", "GCODE"]
    status: Literal["Created", "Processing", "Completed", "Failed"]
    artifact_id: Optional[str] = None
    error: Optional[str] = None


class ArtifactDownloadResponse(BaseModel):
    artifact_id: str
    url: str


class DialogueMessageBase(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class DialogueMessageCreate(DialogueMessageBase):
    pass

class DialogueMessage(DialogueMessageBase):
    id: UUID
    order_id: UUID
    turn_number: int
    timestamp: datetime

    class Config:
        orm_mode = True

class DialogueTurnRequest(BaseModel):
    order_id: UUID
    messages: list[DialogueMessageCreate]


class Export1CRequest(BaseModel):
    order_id: str

class ZIPJobRequest(BaseModel):
    order_id: str
    job_ids: List[str]



class Export1CResponse(BaseModel):
    success: bool
    one_c_order_id: Optional[str] = Field(None, alias="1c_order_id")
