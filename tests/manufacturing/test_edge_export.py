"""Tests for edge banding export core — Task 12.

Focused tests for stable IDs, Russian CSV output, and export decision domain.
"""
from __future__ import annotations

import csv
import io

import pytest

from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
from api.manufacturing.edge_export import (
    EdgeExportRecord,
    EdgeMaterial,
    EdgePosition,
    EdgeSpec,
    ExportStatus,
    assert_production_export_allowed,
    build_edge_records,
    build_panel_edge_summary,
    export_edge_csv,
    export_edge_csv_bytes,
    get_cam_identifier_contract,
    make_edge_record_id,
)

# ── Fixtures ──────────────────────────────────────────────────────────

SIMPLE_SPEC = ManufacturingSpec(
    spec_version="1.0",
    panels=[
        PanelSpec(id="panel_1", width_mm=600, height_mm=720, thickness_mm=16, material="ЛДСП"),
        PanelSpec(id="panel_2", width_mm=300, height_mm=720, thickness_mm=16, material="ЛДСП"),
    ],
)

EMPTY_SPEC = ManufacturingSpec(spec_version="1.0", panels=[])

SINGLE_PANEL_SPEC = ManufacturingSpec(
    spec_version="1.0",
    panels=[
        PanelSpec(id="side_left", width_mm=500, height_mm=800, thickness_mm=18),
    ],
)


# ── EdgePosition enum ─────────────────────────────────────────────────


class TestEdgePosition:
    def test_values(self):
        assert set(EdgePosition) == {
            EdgePosition.FRONT,
            EdgePosition.BACK,
            EdgePosition.LEFT,
            EdgePosition.RIGHT,
        }

    def test_str_values(self):
        assert EdgePosition.FRONT.value == "front"
        assert EdgePosition.BACK.value == "back"
        assert EdgePosition.LEFT.value == "left"
        assert EdgePosition.RIGHT.value == "right"

    def test_from_string(self):
        assert EdgePosition("front") is EdgePosition.FRONT

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            EdgePosition("top")


# ── EdgeMaterial enum ─────────────────────────────────────────────────


class TestEdgeMaterial:
    def test_has_common_types(self):
        assert EdgeMaterial.PVC_04.value == "PVC 0.4"
        assert EdgeMaterial.PVC_10.value == "PVC 1.0"
        assert EdgeMaterial.MELAMINE.value == "Меламин"
        assert EdgeMaterial.NONE.value == "Без кромки"

    def test_from_string(self):
        assert EdgeMaterial("PVC 0.4") is EdgeMaterial.PVC_04


# ── ExportStatus enum ─────────────────────────────────────────────────


class TestExportStatus:
    def test_draft_and_approved(self):
        assert ExportStatus.DRAFT.value == "draft"
        assert ExportStatus.APPROVED.value == "approved"

    def test_default_is_draft(self):
        rec = EdgeExportRecord(
            record_id="r1",
            panel_id="p1",
            position=EdgePosition.FRONT,
            material=EdgeMaterial.PVC_04,
            width_mm=22.0,
            length_mm=600.0,
        )
        assert rec.status is ExportStatus.DRAFT


# ── Stable IDs ────────────────────────────────────────────────────────


class TestStableIds:
    def test_deterministic(self):
        id1 = make_edge_record_id("panel_1", EdgePosition.FRONT)
        id2 = make_edge_record_id("panel_1", EdgePosition.FRONT)
        assert id1 == id2

    def test_different_positions_different_ids(self):
        id_front = make_edge_record_id("panel_1", EdgePosition.FRONT)
        id_back = make_edge_record_id("panel_1", EdgePosition.BACK)
        assert id_front != id_back

    def test_different_panels_different_ids(self):
        id_p1 = make_edge_record_id("panel_1", EdgePosition.FRONT)
        id_p2 = make_edge_record_id("panel_2", EdgePosition.FRONT)
        assert id_p1 != id_p2

    def test_format(self):
        rid = make_edge_record_id("panel_1", EdgePosition.FRONT)
        # revision-aware stable id (default rev=1)
        assert rid.startswith("edge_panel_1_front_r1_")
        assert len(rid.split("_")[-1]) == 12  # 12 hex chars


# ── EdgeSpec ──────────────────────────────────────────────────────────


class TestEdgeSpec:
    def test_defaults(self):
        spec = EdgeSpec(position=EdgePosition.FRONT)
        assert spec.material is EdgeMaterial.PVC_04
        assert spec.width_mm == 22.0

    def test_custom(self):
        spec = EdgeSpec(position=EdgePosition.LEFT, material=EdgeMaterial.ABS_20, width_mm=30.0)
        assert spec.material is EdgeMaterial.ABS_20
        assert spec.width_mm == 30.0

    def test_invalid_width_raises(self):
        with pytest.raises(ValueError):
            EdgeSpec(position=EdgePosition.FRONT, width_mm=0)

    def test_negative_width_raises(self):
        with pytest.raises(ValueError):
            EdgeSpec(position=EdgePosition.FRONT, width_mm=-5)


# ── build_panel_edge_summary ──────────────────────────────────────────


class TestBuildPanelEdgeSummary:
    def test_returns_4_edges(self):
        panel = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16)
        summary = build_panel_edge_summary(panel)
        assert len(summary.edges) == 4
        positions = {e.position for e in summary.edges}
        assert positions == set(EdgePosition)

    def test_preserves_panel_data(self):
        panel = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, material="МДФ")
        summary = build_panel_edge_summary(panel)
        assert summary.panel_id == "p1"
        assert summary.width_mm == 600
        assert summary.height_mm == 720
        assert summary.material == "МДФ"


# ── build_edge_records ────────────────────────────────────────────────


class TestBuildEdgeRecords:
    def test_empty_spec(self):
        records = build_edge_records(EMPTY_SPEC)
        assert records == []

    def test_single_panel_4_records(self):
        records = build_edge_records(SINGLE_PANEL_SPEC)
        assert len(records) == 4

    def test_two_panels_8_records(self):
        records = build_edge_records(SIMPLE_SPEC)
        assert len(records) == 8

    def test_deterministic_order(self):
        r1 = build_edge_records(SIMPLE_SPEC)
        r2 = build_edge_records(SIMPLE_SPEC)
        ids1 = [r.record_id for r in r1]
        ids2 = [r.record_id for r in r2]
        assert ids1 == ids2

    def test_sorted_by_panel_id(self):
        records = build_edge_records(SIMPLE_SPEC)
        panel_ids = [r.panel_id for r in records]
        assert panel_ids == sorted(panel_ids)

    def test_front_back_length_equals_width(self):
        records = build_edge_records(SINGLE_PANEL_SPEC)
        for r in records:
            if r.position in (EdgePosition.FRONT, EdgePosition.BACK):
                assert r.length_mm == 500.0  # width_mm

    def test_left_right_length_equals_height(self):
        records = build_edge_records(SINGLE_PANEL_SPEC)
        for r in records:
            if r.position in (EdgePosition.LEFT, EdgePosition.RIGHT):
                assert r.length_mm == 800.0  # height_mm

    def test_all_records_have_stable_ids(self):
        records = build_edge_records(SIMPLE_SPEC)
        for r in records:
            assert r.record_id.startswith("edge_")
            assert len(r.record_id) > 10


# ── CSV export ────────────────────────────────────────────────────────


class TestExportEdgeCsv:
    def test_starts_with_bom(self):
        csv_str = export_edge_csv(build_edge_records(SIMPLE_SPEC))
        assert csv_str.startswith("\ufeff")

    def test_semicolon_delimiter(self):
        csv_str = export_edge_csv(build_edge_records(SINGLE_PANEL_SPEC))
        lines = csv_str.strip().split("\n")
        assert ";" in lines[1]  # data line has semicolons

    def test_header_row(self):
        csv_str = export_edge_csv(build_edge_records(SINGLE_PANEL_SPEC))
        lines = csv_str.strip().split("\n")
        # Skip BOM
        header = lines[0][1:]  # remove BOM char
        assert "ID записи" in header
        assert "ID панели" in header
        assert "Позиция" in header
        assert "Материал кромки" in header
        assert "Статус" in header

    def test_russian_position_names(self):
        records = build_edge_records(SINGLE_PANEL_SPEC)
        csv_str = export_edge_csv(records)
        assert "Передняя" in csv_str
        assert "Задняя" in csv_str
        assert "Левая" in csv_str
        assert "Правая" in csv_str

    def test_draft_status_by_default(self):
        records = build_edge_records(SIMPLE_SPEC)
        csv_str = export_edge_csv(records)
        assert "Черновик" in csv_str

    def test_approved_status(self):
        records = build_edge_records(SIMPLE_SPEC)
        for r in records:
            r.status = ExportStatus.APPROVED
        csv_str = export_edge_csv(records)
        assert "Утверждено" in csv_str
        assert "Черновик" not in csv_str

    def test_parseable_csv(self):
        records = build_edge_records(SIMPLE_SPEC)
        csv_str = export_edge_csv(records)
        # Remove BOM, parse with semicolon
        reader = csv.reader(io.StringIO(csv_str[1:]), delimiter=";")
        rows = list(reader)
        # Header + 8 data rows
        assert len(rows) == 9

    def test_empty_records(self):
        csv_str = export_edge_csv([])
        lines = csv_str.strip().split("\n")
        assert len(lines) == 1  # header only

    def test_bytes_output(self):
        records = build_edge_records(SINGLE_PANEL_SPEC)
        csv_bytes = export_edge_csv_bytes(records)
        assert isinstance(csv_bytes, bytes)
        decoded = csv_bytes.decode("utf-8")
        assert decoded.startswith("\ufeff")


# ── EdgeExportRecord validation ───────────────────────────────────────


class TestEdgeExportRecord:
    def test_empty_record_id_raises(self):
        with pytest.raises(ValueError):
            EdgeExportRecord(
                record_id="",
                panel_id="p1",
                position=EdgePosition.FRONT,
                material=EdgeMaterial.PVC_04,
                width_mm=22.0,
                length_mm=600.0,
            )

    def test_whitespace_record_id_raises(self):
        with pytest.raises(ValueError):
            EdgeExportRecord(
                record_id="   ",
                panel_id="p1",
                position=EdgePosition.FRONT,
                material=EdgeMaterial.PVC_04,
                width_mm=22.0,
                length_mm=600.0,
            )


# ── Task 12: revision in stable ids, CAM contract, decimal, block, watermark ──


class TestStableIdentifiersRevisionAndCAMContract:
    """Stable export identifiers must match across BOM/Excel/CSV/CAM (contract only)."""

    def test_revision_included_in_edge_record_id(self):
        rid = make_edge_record_id("panel_x", EdgePosition.LEFT, revision=42)
        assert "r42" in rid
        assert rid.startswith("edge_panel_x_left_r42_")

    def test_revision_changes_id(self):
        id_rev1 = make_edge_record_id("p1", EdgePosition.FRONT, 1)
        id_rev2 = make_edge_record_id("p1", EdgePosition.FRONT, 2)
        assert id_rev1 != id_rev2

    def test_build_edge_respects_revision(self):
        recs = build_edge_records(SIMPLE_SPEC, revision=7)
        assert all("r7" in r.record_id for r in recs)
        assert recs[0].status is ExportStatus.DRAFT

    def test_build_edge_allows_approved_status(self):
        recs = build_edge_records(SIMPLE_SPEC, revision=1, status=ExportStatus.APPROVED)
        assert recs[0].status is ExportStatus.APPROVED

    def test_cam_contract_mentions_revision_and_panel(self):
        contract = get_cam_identifier_contract()
        assert contract["revision_in_record_id"] is True
        assert "panel_id" in str(contract).lower() or "panel" in contract.get("description", "").lower()


class TestRussianCSVFixturesDecimalEncodingColumns:
    """Russian Excel/CSV fixtures: decimal sep, encoding BOM, column names, 1C expectations."""

    def test_decimal_comma_in_edge_csv(self):
        records = build_edge_records(SINGLE_PANEL_SPEC)
        csv_str = export_edge_csv(records, decimal_sep=",")
        # Russian style decimal separator
        assert "500,0" in csv_str  # front/back length = width
        assert "800,0" in csv_str  # left/right = height
        assert "22,0" in csv_str   # default width

    def test_bom_and_russian_headers(self):
        csv_str = export_edge_csv(build_edge_records(SINGLE_PANEL_SPEC))
        assert csv_str.startswith("\ufeff")
        header = csv_str.split("\n")[0][1:]
        assert "ID записи" in header
        assert "Позиция" in header
        assert "Материал кромки" in header
        assert "Длина кромки, мм" in header

    def test_semicolon_1c_style(self):
        csv_str = export_edge_csv(build_edge_records(SIMPLE_SPEC))
        # 1C/Excel RU use ; delimiter
        assert ";" in csv_str.split("\n")[1]


class TestProductionBlockAndWatermarkForDrafts:
    """Block production for stale drafts, watermark for preview drafts."""

    def test_production_block_raises_for_not_approved(self):
        with pytest.raises(PermissionError) as excinfo:
            assert_production_export_allowed(False)
        assert "заблокирован" in str(excinfo.value) or "stale draft" in str(excinfo.value).lower()

    def test_production_allowed_for_approved(self):
        # does not raise
        assert_production_export_allowed(True)

    def test_watermark_in_edge_preview_csv(self):
        csv_str = export_edge_csv(build_edge_records(SIMPLE_SPEC), watermark=True)
        assert "ВОДЯНОЙ_ЗНАК" in csv_str
        assert "ПРЕДВАРИТЕЛЬНЫЙ ЧЕРНОВИК" in csv_str
        assert "НЕ ДЛЯ ПРОИЗВОДСТВА" in csv_str

    def test_build_status_draft_by_default_for_preview(self):
        recs = build_edge_records(SIMPLE_SPEC)
        assert all(r.status == ExportStatus.DRAFT for r in recs)
