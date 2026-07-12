import copy
import json

import pytest
from pydantic import ValidationError

from api.ai.vision import (
    HumanReviewAdvice,
    HumanReviewReason,
    VisionDimensions,
    parse_vision_response,
)
from tests.ai.fakes import RECORDED_VISION_RESPONSE


def test_parses_recorded_vision_fixture_without_a_provider_call() -> None:
    result = parse_vision_response(RECORDED_VISION_RESPONSE)

    assert result.dimensions == VisionDimensions(width_mm=600, height_mm=720, depth_mm=300)
    assert result.human_review.status == "advisory"
    assert result.human_review.required is True
    assert result.human_review.reasons == (HumanReviewReason.LOW_CONFIDENCE,)


def test_does_not_recommend_human_review_for_complete_high_confidence_result() -> None:
    response = copy.deepcopy(RECORDED_VISION_RESPONSE)
    response["choices"][0]["message"]["content"] = json.dumps(
        {"width_mm": 600, "height_mm": 720, "depth_mm": 300, "confidence": 0.98}
    )

    result = parse_vision_response(response)

    assert result.human_review == HumanReviewAdvice(required=False)


@pytest.mark.parametrize(
    "content",
    [
        {"width_mm": "600", "height_mm": 720, "depth_mm": 300},
        {"width_mm": float("inf"), "height_mm": 720, "depth_mm": 300},
        {"width_mm": 600, "height_mm": 720, "depth_mm": 300, "confidence": True},
    ],
)
def test_rejects_invalid_machine_dimensions_and_confidence(content: dict[str, object]) -> None:
    response = copy.deepcopy(RECORDED_VISION_RESPONSE)
    response["choices"][0]["message"]["content"] = json.dumps(content)

    with pytest.raises(ValidationError):
        parse_vision_response(response)


def test_requires_advisory_review_for_each_missing_dimension() -> None:
    response = copy.deepcopy(RECORDED_VISION_RESPONSE)
    response["choices"][0]["message"]["content"] = json.dumps(
        {"width_mm": 600, "confidence": 0.98}
    )

    result = parse_vision_response(response)

    assert result.human_review.required is True
    assert result.human_review.reasons == (
        HumanReviewReason.MISSING_HEIGHT,
        HumanReviewReason.MISSING_DEPTH,
    )


def test_rejects_an_inconsistent_human_review_contract() -> None:
    with pytest.raises(ValidationError, match="required"):
        HumanReviewAdvice(required=False, reasons=(HumanReviewReason.LOW_CONFIDENCE,))
