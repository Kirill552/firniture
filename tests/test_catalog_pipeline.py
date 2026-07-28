import json
from pathlib import Path

import pytest

from etl_pipeline.catalog_profile import CatalogProfile
from etl_pipeline.generic_extractor import extract


def profile_data():
    return {
        "catalog_id": "synthetic",
        "brand": "X",
        "source": "synthetic.pdf",
        "sku_pattern": r"\bH\d{3}[A-Z]\d{2}\b",
        "sku_examples": ["H305B02"],
        "type_markers": {"петля": ["hinge"], "направляющая": ["slide"]},
        "param_patterns": {"cup_diameter_mm": r"cup\s*(\d{2})"},
        "notes": "тест",
    }


def test_invalid_regex_rejected():
    data = profile_data()
    data["sku_pattern"] = "["
    with pytest.raises(ValueError, match="sku_pattern"):
        CatalogProfile.from_dict(data)


def test_examples_must_match_own_pattern():
    data = profile_data()
    data["sku_examples"] = ["BAD"]
    with pytest.raises(ValueError, match="sku_examples"):
        CatalogProfile.from_dict(data)


def test_extracts_sku_and_type_from_synthetic_pdf(tmp_path):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), "Furniture hinge\nHinge H305B02\ncup 35")
    doc.save(path)
    doc.close()
    result = extract(path, CatalogProfile.from_dict(profile_data()))
    assert result[0]["sku"] == "H305B02"
    assert result[0]["type"] == "петля"
    assert result[0]["params"]["cup_diameter_mm"] == "35"
    assert result[0]["needs_review"] is False


def test_position_without_parameter_needs_review(tmp_path):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), "Furniture hinge\nHinge H305B02")
    doc.save(path)
    doc.close()
    result = extract(path, CatalogProfile.from_dict(profile_data()))
    assert result[0]["needs_review"] is True


def test_profile_json_roundtrip(tmp_path):
    profile = CatalogProfile.from_dict(profile_data())
    path = tmp_path / "profile.json"
    profile.save(path)
    assert CatalogProfile.load(path) == profile
