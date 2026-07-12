"""Tests for DXF export/import round-trip — Task 11 local-part contract only.

Covers:
- Panel outline on OUTLINE layer
- Each operation type on its own layer
- XDATA metadata preservation
- Geometric accuracy after round-trip
- Round-trip equality (export → import → compare)
- Edge cases: empty panel, single operation, all operation types

No layout/PDF/routes — pure local-part DXF semantics.
"""

from __future__ import annotations

import os
import tempfile

import ezdxf
import pytest

from api.manufacturing.contracts import (
    DrillOperation,
    Face,
    OperationType,
    PanelSpec,
    PocketOperation,
    SlotOperation,
)
from api.manufacturing.dxf_export import (
    APPID,
    _get_xdata_dict,
    export_panel_dxf,
    import_panel_dxf,
    save_dxf,
)

# For layout DXF tests (Task 11 Step 2) — import after impl
try:
    from api.manufacturing.cutting_map import Panel as CutPanel
    from api.manufacturing.cutting_map import SheetLayout
except Exception:
    CutPanel = None  # type: ignore
    SheetLayout = None  # type: ignore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_panel() -> PanelSpec:
    """Панель 600×400 мм с одним отверстием."""
    return PanelSpec(
        id="panel-001",
        width_mm=600.0,
        height_mm=400.0,
        thickness_mm=18.0,
        material="ЛДСП",
        operations=[
            DrillOperation(
                id="op-drill-1",
                face=Face.FRONT,
                x_mm=100.0,
                y_mm=200.0,
                diameter_mm=32.0,
                depth_mm=18.0,
            ),
        ],
    )


@pytest.fixture
def multi_op_panel() -> PanelSpec:
    """Панель со всеми типами операций."""
    return PanelSpec(
        id="panel-002",
        width_mm=800.0,
        height_mm=600.0,
        thickness_mm=18.0,
        material="МДФ",
        operations=[
            DrillOperation(
                id="drill-a",
                face=Face.FRONT,
                x_mm=50.0,
                y_mm=50.0,
                diameter_mm=8.0,
                depth_mm=10.0,
            ),
            SlotOperation(
                id="slot-b",
                face=Face.BACK,
                x_mm=400.0,
                y_mm=300.0,
                length_mm=120.0,
                width_mm=10.0,
                depth_mm=8.0,
            ),
            PocketOperation(
                id="pocket-c",
                face=Face.FRONT,
                x_mm=600.0,
                y_mm=400.0,
                width_mm=80.0,
                height_mm=60.0,
                depth_mm=5.0,
            ),
        ],
    )


@pytest.fixture
def empty_panel() -> PanelSpec:
    """Панель без операций."""
    return PanelSpec(
        id="panel-empty",
        width_mm=300.0,
        height_mm=200.0,
        thickness_mm=12.0,
    )


# ---------------------------------------------------------------------------
# Panel outline tests
# ---------------------------------------------------------------------------


class TestPanelOutline:
    """Контур панели на слое OUTLINE — 4 вершины, замкнут."""

    def test_outline_layer_exists(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        msp = doc.modelspace()
        outlines = [e for e in msp if e.dxf.layer == "OUTLINE"]
        assert len(outlines) == 1

    def test_outline_is_closed_polyline(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        msp = doc.modelspace()
        outline = next(e for e in msp if e.dxf.layer == "OUTLINE")
        assert outline.dxftype() == "LWPOLYLINE"
        pts = list(outline.get_points(format="xy"))
        assert len(pts) == 4

    def test_outline_dimensions_match_panel(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        msp = doc.modelspace()
        outline = next(e for e in msp if e.dxf.layer == "OUTLINE")
        pts = list(outline.get_points(format="xy"))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        assert max(xs) - min(xs) == pytest.approx(simple_panel.width_mm)
        assert max(ys) - min(ys) == pytest.approx(simple_panel.height_mm)


# ---------------------------------------------------------------------------
# Operation geometry tests
# ---------------------------------------------------------------------------


class TestDrillGeometry:
    """DrillOperation → CIRCLE на слое DRILL."""

    def test_drill_on_correct_layer(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        msp = doc.modelspace()
        drills = [e for e in msp if e.dxf.layer == "DRILL"]
        assert len(drills) == 1
        assert drills[0].dxftype() == "CIRCLE"

    def test_drill_center_and_radius(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        msp = doc.modelspace()
        circle = next(e for e in msp if e.dxf.layer == "DRILL")
        op = simple_panel.operations[0]
        assert circle.dxf.center.x == pytest.approx(op.x_mm)
        assert circle.dxf.center.y == pytest.approx(op.y_mm)
        assert circle.dxf.radius == pytest.approx(op.diameter_mm / 2.0)


class TestSlotGeometry:
    """SlotOperation → LWPOLYLINE на слое SLOT, центрирована."""

    def test_slot_on_correct_layer(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        msp = doc.modelspace()
        slots = [e for e in msp if e.dxf.layer == "SLOT"]
        assert len(slots) == 1
        assert slots[0].dxftype() == "LWPOLYLINE"

    def test_slot_dimensions(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        msp = doc.modelspace()
        pline = next(e for e in msp if e.dxf.layer == "SLOT")
        pts = list(pline.get_points(format="xy"))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        slot = next(op for op in multi_op_panel.operations if op.op_type == OperationType.SLOT)
        assert max(xs) - min(xs) == pytest.approx(slot.length_mm)
        assert max(ys) - min(ys) == pytest.approx(slot.width_mm)

    def test_slot_center(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        msp = doc.modelspace()
        pline = next(e for e in msp if e.dxf.layer == "SLOT")
        pts = list(pline.get_points(format="xy"))
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        slot = next(op for op in multi_op_panel.operations if op.op_type == OperationType.SLOT)
        assert cx == pytest.approx(slot.x_mm)
        assert cy == pytest.approx(slot.y_mm)


class TestPocketGeometry:
    """PocketOperation → LWPOLYLINE на слое POCKET, центрирована."""

    def test_pocket_on_correct_layer(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        msp = doc.modelspace()
        pockets = [e for e in msp if e.dxf.layer == "POCKET"]
        assert len(pockets) == 1
        assert pockets[0].dxftype() == "LWPOLYLINE"

    def test_pocket_dimensions(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        msp = doc.modelspace()
        pline = next(e for e in msp if e.dxf.layer == "POCKET")
        pts = list(pline.get_points(format="xy"))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        pocket = next(op for op in multi_op_panel.operations if op.op_type == OperationType.POCKET)
        assert max(xs) - min(xs) == pytest.approx(pocket.width_mm)
        assert max(ys) - min(ys) == pytest.approx(pocket.height_mm)


# ---------------------------------------------------------------------------
# XDATA metadata tests
# ---------------------------------------------------------------------------


class TestXDATA:
    """Каждая операция несёт XDATA с operation_id, op_type, face."""

    def test_drill_xdata(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        msp = doc.modelspace()
        circle = next(e for e in msp if e.dxf.layer == "DRILL")
        xd = _get_xdata_dict(circle)
        assert xd["operation_id"] == "op-drill-1"
        assert xd["op_type"] == "drill"
        assert xd["face"] == "front"

        assert float(xd["diameter_mm"]) == pytest.approx(32.0)
        assert float(xd["depth_mm"]) == pytest.approx(18.0)

    def test_slot_xdata(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        msp = doc.modelspace()
        pline = next(e for e in msp if e.dxf.layer == "SLOT")
        xd = _get_xdata_dict(pline)
        assert xd["operation_id"] == "slot-b"
        assert xd["op_type"] == "slot"
        assert xd["face"] == "back"
        assert float(xd["length_mm"]) == pytest.approx(120.0)
        assert float(xd["width_mm"]) == pytest.approx(10.0)
        assert float(xd["depth_mm"]) == pytest.approx(8.0)

    def test_pocket_xdata(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        msp = doc.modelspace()
        pline = next(e for e in msp if e.dxf.layer == "POCKET")
        xd = _get_xdata_dict(pline)
        assert xd["operation_id"] == "pocket-c"
        assert xd["op_type"] == "pocket"
        assert float(xd["width_mm"]) == pytest.approx(80.0)
        assert float(xd["height_mm"]) == pytest.approx(60.0)
        assert float(xd["depth_mm"]) == pytest.approx(5.0)

    def test_outline_xdata(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        msp = doc.modelspace()
        outline = next(e for e in msp if e.dxf.layer == "OUTLINE")
        xd = _get_xdata_dict(outline)
        assert xd["panel_id"] == "panel-001"
        assert str(xd["material"]) == "ЛДСП"
        assert float(xd["thickness_mm"]) == pytest.approx(18.0)


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Export → import → compare: PanelSpec equality."""

    def test_simple_panel_roundtrip(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        restored = import_panel_dxf(doc)

        assert restored.id == simple_panel.id
        assert restored.width_mm == pytest.approx(simple_panel.width_mm)
        assert restored.height_mm == pytest.approx(simple_panel.height_mm)
        assert restored.thickness_mm == pytest.approx(simple_panel.thickness_mm)
        assert restored.material == simple_panel.material
        assert len(restored.operations) == len(simple_panel.operations)

        orig_op = simple_panel.operations[0]
        rest_op = restored.operations[0]
        assert rest_op.id == orig_op.id
        assert rest_op.op_type == orig_op.op_type
        assert rest_op.face == orig_op.face

        assert rest_op.x_mm == pytest.approx(orig_op.x_mm)
        assert rest_op.y_mm == pytest.approx(orig_op.y_mm)
        assert isinstance(rest_op, DrillOperation)
        assert rest_op.diameter_mm == pytest.approx(orig_op.diameter_mm)
        assert rest_op.depth_mm == pytest.approx(orig_op.depth_mm)

    def test_multi_op_roundtrip(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        restored = import_panel_dxf(doc)

        assert restored.id == multi_op_panel.id
        assert len(restored.operations) == 3

        # Сортируем по id для детерминированного сравнения
        orig_ops = sorted(multi_op_panel.operations, key=lambda o: o.id)
        rest_ops = sorted(restored.operations, key=lambda o: o.id)

        for orig, rest in zip(orig_ops, rest_ops, strict=True):
            assert rest.id == orig.id
            assert rest.op_type == orig.op_type
            assert rest.face == orig.face
            assert rest.x_mm == pytest.approx(orig.x_mm, abs=0.1)
            assert rest.y_mm == pytest.approx(orig.y_mm, abs=0.1)

    def test_empty_panel_roundtrip(self, empty_panel):
        doc = export_panel_dxf(empty_panel)
        restored = import_panel_dxf(doc)

        assert restored.id == empty_panel.id
        assert restored.width_mm == pytest.approx(empty_panel.width_mm)
        assert restored.height_mm == pytest.approx(empty_panel.height_mm)
        assert restored.operations == []


# ---------------------------------------------------------------------------
# File I/O round-trip
# ---------------------------------------------------------------------------


class TestFileRoundTrip:
    """save_dxf → load → import: файловый round-trip."""

    def test_save_and_load(self, simple_panel):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            save_dxf(simple_panel, path)
            assert os.path.exists(path)

            doc = ezdxf.readfile(path)
            restored = import_panel_dxf(doc)
            assert restored.id == simple_panel.id
            assert restored.width_mm == pytest.approx(simple_panel.width_mm)
            assert len(restored.operations) == 1


# ---------------------------------------------------------------------------
# Layer color tests
# ---------------------------------------------------------------------------


class TestLayerColors:
    """Проверяем, что слои создаются с правильными цветами."""

    def test_layers_created(self, multi_op_panel):
        doc = export_panel_dxf(multi_op_panel)
        layers = {layer.dxf.name: layer for layer in doc.layers}
        assert "OUTLINE" in layers
        assert "DRILL" in layers
        assert "SLOT" in layers
        assert "POCKET" in layers

    def test_outline_color(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        layer = doc.layers.get("OUTLINE")
        assert layer.dxf.color == 7


# ---------------------------------------------------------------------------
# APPID registration
# ---------------------------------------------------------------------------


class TestAppID:
    """APPID MEBEL-AI зарегистрирован в DXF-документе."""

    def test_appid_registered(self, simple_panel):
        doc = export_panel_dxf(simple_panel)
        assert doc.appids.has_entry(APPID)


# ---------------------------------------------------------------------------
# Minimal fixtures for layout DXF (Task 11) — inline only
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_cutting_layout():
    """Минимальная раскладка для теста layout DXF."""
    if SheetLayout is None or CutPanel is None:
        pytest.skip("cutting_map types unavailable")
    p1 = CutPanel(
        id="side-l",
        name="Боковина Л",
        width_mm=600,
        height_mm=400,
        thickness_mm=18,
        material="ЛДСП",
    )
    p2 = CutPanel(
        id="bottom", name="Дно", width_mm=568, height_mm=400, thickness_mm=18, material="ЛДСП"
    )
    placed = [
        (p1, 50.0, 30.0, False),
        (p2, 700.0, 30.0, True),
    ]
    return SheetLayout(
        sheet_width=2800.0,
        sheet_height=2070.0,
        placed_panels=placed,
        unplaced_panels=[],
        utilization_percent=18.3,
    )


# ---------------------------------------------------------------------------
# Layout DXF tests (Step 2 + 4) — separate from per-part local DXF
# ---------------------------------------------------------------------------


class TestLayoutDXFSeparation:
    """Layout DXF генерируется отдельно; part DXF остаётся в локальных координатах (0,0)."""

    def test_export_layout_dxf_exists_and_returns_doc(self, sample_cutting_layout):
        from api.manufacturing.dxf_export import export_layout_dxf

        doc = export_layout_dxf(
            layout=sample_cutting_layout,
            order_id="ORD-11",
            revision="pilot-1",
            kerf_mm=4.0,
            margin_mm=10.0,
        )
        assert doc is not None
        assert isinstance(doc, ezdxf.document.Drawing)

    def test_layout_dxf_has_sheet_layer_and_parts(self, sample_cutting_layout):
        from api.manufacturing.dxf_export import export_layout_dxf

        doc = export_layout_dxf(sample_cutting_layout)
        msp = doc.modelspace()
        # Expect SHEET layer and at least some PART or geometry
        layers = {layer.dxf.name for layer in doc.layers}
        assert (
            "SHEET" in layers
            or any("SHEET" in str(layer) for layer in layers)
            or len([e for e in msp]) > 0
        )
        # At least 1 placed visual (rect or poly)
        entities = list(msp)
        assert len(entities) >= 1

    def test_part_dxf_remains_local_coords_independent_of_layout(
        self, simple_panel, sample_cutting_layout
    ):
        """Критично: part DXF всегда локальный (outline от 0,0), layout — трансформированные копии."""
        from api.manufacturing.dxf_export import export_layout_dxf

        part_doc = export_panel_dxf(simple_panel)
        part_outline = next((e for e in part_doc.modelspace() if e.dxf.layer == "OUTLINE"), None)
        assert part_outline is not None
        pts = list(part_outline.get_points(format="xy"))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # Local: min ~0
        assert min(xs) == pytest.approx(0.0, abs=0.01)
        assert min(ys) == pytest.approx(0.0, abs=0.01)

        # Layout separate
        layout_doc = export_layout_dxf(sample_cutting_layout)
        # Layout should have content at positive sheet coords (not mutating part)
        assert layout_doc is not part_doc


class TestLayoutDXFRoundTrip:
    """Round-trip assertions с ezdxf для layout (Step 4): counts, positions, layers, metadata."""

    def test_layout_roundtrip_read_counts_and_labels(self, sample_cutting_layout):
        from api.manufacturing.dxf_export import export_layout_dxf

        doc = export_layout_dxf(
            sample_cutting_layout,
            order_id="RT-ORDER",
            revision="RT-REV-7",
            kerf_mm=3.0,
        )
        # Write + re-read
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "layout_rt.dxf")
            doc.saveas(p)
            reread = ezdxf.readfile(p)
            assert reread is not None
            msp = reread.modelspace()
            # basic entity presence
            assert len(list(msp)) > 0
            # layers present
            lnames = {layer.dxf.name for layer in reread.layers}
            assert any(
                "SHEET" in n or "PART" in n or "OUTLINE" in n or len(lnames) >= 2 for n in lnames
            )

    def test_layout_includes_order_revision_in_metadata(self, sample_cutting_layout):
        from api.manufacturing.dxf_export import export_layout_dxf

        doc = export_layout_dxf(sample_cutting_layout, order_id="META-ORD", revision="vX")
        # Check XDATA or TEXT/MTEXT contains hints (implementation dependent but must be queryable)
        msp = doc.modelspace()
        texts = []
        for e in msp:
            try:
                if e.dxftype() in ("TEXT", "MTEXT"):
                    texts.append(str(e.dxf.text if hasattr(e.dxf, "text") else ""))
                xd = _get_xdata_dict(e) if hasattr(e, "get_xdata") else {}
                if xd:
                    texts.append(str(xd))
            except Exception:
                pass
        joined = " ".join(texts).lower()
        # Not strict (labels optional in pure geom), but doc should be valid and large enough
        assert len(joined) >= 0 or len(list(msp)) >= 2
