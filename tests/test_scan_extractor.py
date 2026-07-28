"""Точечные тесты разбора ответов Vision для сканов каталогов."""
import json

import pytest

from pathlib import Path

import fitz

from etl_pipeline import scan_extractor
from shared.ai_client import GPTResponse
class FakeVisionClient:
    async def vision_extract(self, image_base64, prompt, **kwargs):
        return GPTResponse(text='{"positions":[]}', usage={}, model_version="fake")


def test_scan_render_and_vision_use_selected_page_without_network(tmp_path, monkeypatch):
    pdf_path = Path(tmp_path) / "scan.pdf"
    document = fitz.open()
    document.new_page(width=100, height=100)
    document.save(pdf_path)
    document.close()
    monkeypatch.setattr(scan_extractor, "AISettings", lambda: type("Settings", (), {"ai_api_key": "test"})())
    result = __import__("asyncio").run(
        scan_extractor.extract_scanned_pdf(pdf_path, "AKS", pages=[1], client=FakeVisionClient())
    )
    assert result[0]["validation_errors"] == ["no_positions"]
from etl_pipeline.scan_extractor import parse_vision_response, validate_position


def test_parse_valid_position_keeps_contract_fields():
    result = parse_vision_response(json.dumps({
        "positions": [{
            "sku": "H123",
            "name": "Петля",
            "type": "петля",
            "brand": "AKS",
            "params": {"cup_diameter_mm": 35, "opening_angle_deg": 110,
                       "drill_depth_mm": 12, "drill_offset_mm": 5},
            "page": 2,
            "needs_review": False,
        }]
    }), page=2, brand="AKS")
    assert result[0]["params"]["cup_diameter_mm"] == 35
    assert result[0]["needs_review"] is False


def test_sanity_rejects_impossible_cup_and_angle_with_reasons():
    position = {
        "sku": "H123", "name": "Петля", "type": "петля", "brand": "AKS",
        "params": {"cup_diameter_mm": 40, "opening_angle_deg": 2600,
                    "drill_depth_mm": 12, "drill_offset_mm": 5},
        "page": 1, "needs_review": False,
    }
    result = validate_position(position)
    assert result["params"]["cup_diameter_mm"] is None
    assert result["params"]["opening_angle_deg"] is None
    assert result["needs_review"] is True
    assert "cup_diameter_mm" in result["validation_errors"]
    assert "opening_angle_deg" in result["validation_errors"]


def test_parse_invalid_json_returns_review_item():
    result = parse_vision_response("not json", page=3, brand="AKS")
    assert result[0]["page"] == 3
    assert result[0]["needs_review"] is True
    assert result[0]["validation_errors"] == ["invalid_json"]


def test_reasoning_prefix_does_not_break_parsing():
    """Модель пишет служебный блок размышлений перед JSON — он не должен ломать разбор."""
    text = (
        "<think>Смотрю на чертёж, вижу чашку 35 и угол 105.</think>\n"
        '{"positions":[{"sku":"H09","name":"Петля накладная","type":"петля",'
        '"params":{"cup_diameter_mm":35,"opening_angle_deg":105,"mount_type":"накладная"},'
        '"needs_review":false}]}'
    )
    result = parse_vision_response(text, page=3, brand="AKS")
    assert len(result) == 1
    assert result[0]["params"]["cup_diameter_mm"] == 35
    assert result[0]["params"]["mount_type"] == "накладная"
    assert result[0]["validation_errors"] == []


def test_unclosed_reasoning_block_is_reported_not_guessed():
    """Лимит токенов оборвал ответ на середине размышлений — это не данные, а брак."""
    result = parse_vision_response("<think>Размышляю про размеры, но не дошёл", page=4, brand="AKS")
    assert result[0]["needs_review"] is True
    assert result[0]["validation_errors"] == ["invalid_json"]


def test_mount_type_synonym_maps_to_calculator_type():
    """AKS называет вкладную петлю внутренней — расчёт присадки знает только вкладную."""
    text = '{"positions":[{"sku":"H07","name":"Петля внутренняя","type":"петля","params":{"mount_type":"внутренняя"}}]}'
    result = parse_vision_response(text, page=6, brand="AKS")
    assert result[0]["params"]["mount_type"] == "вкладная"
    assert "mount_type" not in result[0]["validation_errors"]


def test_unknown_mount_type_is_dropped_with_reason():
    """Незнакомое наложение не подставляется наугад: пустое поле честнее выдуманного."""
    text = '{"positions":[{"sku":"H01","name":"Петля","type":"петля","params":{"mount_type":"хитрая"}}]}'
    result = parse_vision_response(text, page=6, brand="AKS")
    assert result[0]["params"]["mount_type"] is None
    assert "mount_type" in result[0]["validation_errors"]
    assert result[0]["needs_review"] is True
