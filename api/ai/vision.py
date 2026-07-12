"""Структурированный результат Vision без транспорта, маршрутов и settings."""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum
from math import isfinite
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

MINIMUM_AUTOMATION_CONFIDENCE = 0.9


class VisionResponseValidationError(ValueError):
    """Ответ vision-источника не содержит поддерживаемый структурированный результат."""


class HumanReviewReason(StrEnum):
    """Причины, которые нужно показать человеку вместе с результатом."""

    LOW_CONFIDENCE = "low_confidence"
    MISSING_WIDTH = "missing_width"
    MISSING_HEIGHT = "missing_height"
    MISSING_DEPTH = "missing_depth"


class VisionDimensions(BaseModel):
    """Размеры, извлечённые из эскиза; все значения выражены в миллиметрах."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width_mm: float | None = None
    height_mm: float | None = None
    depth_mm: float | None = None

    @field_validator("width_mm", "height_mm", "depth_mm", mode="before")
    @classmethod
    def _validate_dimension(cls, value: object, info: ValidationInfo) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"{info.field_name} должен быть конечным числом или null")
        if value <= 0:
            raise ValueError(f"{info.field_name} должен быть больше нуля")
        return float(value)


class _ValidatedVisionPayload(BaseModel):
    """Внутренний тип для валидации output-модели до вычисления review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimensions: VisionDimensions
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def _validate_confidence(cls, value: object) -> float:
        return _finite_confidence(value)



class HumanReviewAdvice(BaseModel):
    """Рекомендация проверки человеком, не являющаяся решением об одобрении."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["advisory"] = "advisory"
    required: bool
    reasons: tuple[HumanReviewReason, ...] = ()

    @model_validator(mode="after")
    def _require_consistent_reasons(self) -> HumanReviewAdvice:
        if self.required != bool(self.reasons):
            raise ValueError("required должен соответствовать наличию причин review")
        return self


class VisionResult(BaseModel):
    """Проверенный результат распознавания с вычисленной рекомендацией review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimensions: VisionDimensions
    confidence: float = Field(ge=0.0, le=1.0)
    human_review: HumanReviewAdvice

    @field_validator("confidence", mode="before")
    @classmethod
    def _validate_confidence(cls, value: object) -> float:
        return _finite_confidence(value)

    @model_validator(mode="after")
    def _require_computed_review_advice(self) -> VisionResult:
        expected = _human_review_advice(self.dimensions, self.confidence)
        if self.human_review != expected:
            raise ValueError("human_review должен быть вычислен из dimensions и confidence")
        return self


def parse_vision_response(response: Mapping[str, Any]) -> VisionResult:
    """Разобрать recorded-совместимый ответ в типизированный domain result без вызова сети."""

    content = _assistant_content(response)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise VisionResponseValidationError("Vision content должен быть JSON-объектом") from error
    if not isinstance(payload, Mapping):
        raise VisionResponseValidationError("Vision content должен быть JSON-объектом")

    return _vision_result_from_payload(payload)


def _assistant_content(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise VisionResponseValidationError("Vision response должен содержать непустой choices")
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise VisionResponseValidationError("Первый choice vision response должен быть объектом")
    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise VisionResponseValidationError("Vision response должен содержать message")
    content = message.get("content")
    if not isinstance(content, str):
        raise VisionResponseValidationError("Vision response должен содержать текстовый JSON content")
    return content


def _vision_result_from_payload(payload: Mapping[str, Any]) -> VisionResult:
    values = dict(payload)
    confidence = values.pop("confidence", 0.0)
    payload_result = _ValidatedVisionPayload(
        dimensions=VisionDimensions.model_validate(values),
        confidence=confidence,
    )
    advice = _human_review_advice(payload_result.dimensions, payload_result.confidence)
    return VisionResult(
        dimensions=payload_result.dimensions,
        confidence=payload_result.confidence,
        human_review=advice,
    )


def _human_review_advice(dimensions: VisionDimensions, confidence: float) -> HumanReviewAdvice:
    reasons: list[HumanReviewReason] = []
    if confidence < MINIMUM_AUTOMATION_CONFIDENCE:
        reasons.append(HumanReviewReason.LOW_CONFIDENCE)
    if dimensions.width_mm is None:
        reasons.append(HumanReviewReason.MISSING_WIDTH)
    if dimensions.height_mm is None:
        reasons.append(HumanReviewReason.MISSING_HEIGHT)
    if dimensions.depth_mm is None:
        reasons.append(HumanReviewReason.MISSING_DEPTH)
    return HumanReviewAdvice(required=bool(reasons), reasons=tuple(reasons))


def _finite_confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("confidence должен быть конечным числом от 0 до 1")
    return float(value)
