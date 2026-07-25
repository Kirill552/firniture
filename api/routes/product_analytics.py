import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.observability import RedactLevel, create_event, event_to_dict

router = APIRouter(prefix="/product-analytics", tags=["analytics"])
_obs_logger = logging.getLogger("observability.events")

ALLOWLISTED_EVENTS = {
    "order_created",
    "order_reviewed",
    "bom_approved",
    "cam_validation_completed",
    "artifact_downloaded",
    "landing_cta_clicked",
    "guest_analysis_completed",
    "guest_draft_created",
    "clarification_completed",
    "auth_gate_viewed",
    "auth_mode_selected",
    "magic_link_requested",
    "magic_link_verified",
    "guest_draft_claimed",
    "guest_draft_claim_failed",
    "pilot_artifact_requested",
}

REDACTED_KEYS = frozenset({
    "email", "factory_name", "prompt", "ocr_text", "dialogue", "token", "cookie", "session_id",
    "width_mm", "height_mm", "depth_mm", "sketch_url", "sketch_data", "sketch_content", "image_url", "image_data",
})

class AnalyticsEventPayload(BaseModel):
    name: str = Field(..., description="Имя события аналитики")
    properties: dict[str, Any] = Field(default_factory=dict, description="Свойства события")

@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def track_product_event(payload: AnalyticsEventPayload):
    if payload.name not in ALLOWLISTED_EVENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Событие '{payload.name}' не разрешено.",
        )
    
    event = create_event(
        event_type=f"product.{payload.name}",
        data=payload.properties,
        severity="info",
        level=RedactLevel.STANDARD,
        additional_redact_fields=REDACTED_KEYS,
    )
    
    _obs_logger.info("%s", json.dumps(event_to_dict(event), ensure_ascii=False))
    return {"status": "accepted"}
