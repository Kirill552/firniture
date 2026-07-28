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
from shared.ai_client import GPTResponse
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


class TestModelVocabulary:
    """Модель говорит своими словами — это не должно обнулять распознавание."""

    def test_wood_becomes_solid_material(self):
        """На рендере кухни модель ответила «дерево» и весь разбор упал в нули."""
        from api.vision_extraction import MATERIAL_SYNONYMS, _normalized

        assert _normalized("дерево", MATERIAL_SYNONYMS) == "массив"
        assert _normalized("ДСП", MATERIAL_SYNONYMS) == "ЛДСП"
        assert _normalized("MDF", MATERIAL_SYNONYMS) == "МДФ"

    def test_unknown_material_is_other_not_crash(self):
        """Незнакомое слово становится «другое», а не рушит ответ целиком."""
        from api.vision_extraction import MATERIAL_SYNONYMS, _normalized

        assert _normalized("ротанг", MATERIAL_SYNONYMS) == "другое"
        assert _normalized(None, MATERIAL_SYNONYMS) is None

    def test_category_synonyms(self):
        """«Навесной шкаф» без подчёркивания — тот же навесной шкаф."""
        from api.vision_extraction import CATEGORY_SYNONYMS, _normalized

        assert _normalized("навесной шкаф", CATEGORY_SYNONYMS) == "навесной_шкаф"
        assert _normalized("шкаф-пенал", CATEGORY_SYNONYMS) == "пенал"
        assert _normalized("кухонный гарнитур", CATEGORY_SYNONYMS) == "другое"


class TestDimensionsSurviveParsing:
    """Размеры с выносок обязаны доехать до ответа, а не потеряться по пути."""

    @pytest.mark.asyncio
    async def test_read_dimensions_reach_response(self, monkeypatch):
        """Модель вернула 600/720/300/16 с источником ocr — значения должны быть на месте.

        Настоящий дефект: поля схемы называются width_mm, а код передавал width,
        pydantic молча отбрасывал их, и мебельщик видел «размеры не распознаны»
        при том, что модель прочитала выноски правильно.
        """
        from api import vision_extraction as module

        answer = (
            '<think>Вижу выноски 600, 720, 300 и подпись ЛДСП 16 мм.</think>'
            '{"furniture_type":{"category":"навесной_шкаф","source":"ocr"},'
            '"dimensions":{"width_mm":600,"width_source":"ocr","height_mm":720,"height_source":"ocr",'
            '"depth_mm":300,"depth_source":"ocr","thickness_mm":16,"thickness_source":"ocr"},'
            '"body_material":{"type":"ЛДСП","color":"белый","source":"ocr"},'
            '"door_count":1,"door_count_source":"ocr","shelf_count":2,"shelf_count_source":"ocr",'
            '"confidence":1.0}'
        )

        class FakeClient:
            async def vision_extract(self, image_base64, prompt, **kwargs):
                return GPTResponse(text=answer, usage={}, model_version="fake")

        monkeypatch.setattr(module, "get_ai_client", lambda: FakeClient())
        params, sources, _need, recognized, _prompt = await module.parse_ocr_text_to_params(
            "", image_bytes=b"\xff\xd8\xff fake jpeg", mime_type="image/jpeg"
        )

        assert params.dimensions.width_mm == 600
        assert params.dimensions.height_mm == 720
        assert params.dimensions.depth_mm == 300
        assert params.dimensions.thickness_mm == 16
        assert sources["width_mm"] == "ocr"
        assert recognized >= 8
