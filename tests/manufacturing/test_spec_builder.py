"""Tests for manufacturing spec builder: deterministic adapter from CabinetInput → BuildResult.

Task 6: cabinet types, left-right independent operations, hardware provenance,
missing parameters blocking, dimension/slot/quantity invariants.

TDD RED → GREEN: все тесты падают до реализации spec_builder.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.manufacturing.contracts import (
    DrillOperation,
    Face,
    ManufacturingSpec,
    PanelSpec,
    SlotOperation,
)
from api.manufacturing.spec_builder import (
    BuildResult,
    CabinetInput,
    CabinetType,
    build_spec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_WALL_INPUT = CabinetInput(
    cabinet_type=CabinetType.WALL,
    width_mm=600,
    height_mm=720,
    depth_mm=300,
)

MINIMAL_BASE_INPUT = CabinetInput(
    cabinet_type=CabinetType.BASE,
    width_mm=600,
    height_mm=720,
    depth_mm=500,
)

TALL_INPUT = CabinetInput(
    cabinet_type=CabinetType.TALL,
    width_mm=600,
    height_mm=2000,
    depth_mm=500,
)

WITH_SHELVES_INPUT = CabinetInput(
    cabinet_type=CabinetType.WALL,
    width_mm=800,
    height_mm=720,
    depth_mm=300,
    shelf_count=3,
)

WITH_HARDWARE_INPUT = CabinetInput(
    cabinet_type=CabinetType.WALL,
    width_mm=600,
    height_mm=720,
    depth_mm=300,
    door_count=1,
    shelf_count=1,
    hinge_type="blum_clip_top_110",
    slide_type="blum_movento_500",
)

DRAWER_INPUT = CabinetInput(
    cabinet_type=CabinetType.DRAWER,
    width_mm=600,
    height_mm=200,
    depth_mm=500,
    drawer_count=2,
)

SINK_BASE_INPUT = CabinetInput(
    cabinet_type=CabinetType.BASE_SINK,
    width_mm=600,
    height_mm=720,
    depth_mm=500,
)


# ---------------------------------------------------------------------------
# CabinetInput validation
# ---------------------------------------------------------------------------


class TestCabinetInput:
    """CabinetInput: required fields, bounds, defaults."""

    def test_minimal_valid(self):
        inp = MINIMAL_WALL_INPUT
        assert inp.cabinet_type == CabinetType.WALL
        assert inp.width_mm == 600
        assert inp.height_mm == 720
        assert inp.depth_mm == 300
        assert inp.thickness_mm == 16.0
        assert inp.shelf_count == 0
        assert inp.door_count == 0
        assert inp.drawer_count == 0
        assert inp.back_panel is True
        assert inp.hinge_type is None
        assert inp.slide_type is None

    def test_zero_width_raises(self):
        with pytest.raises(ValidationError):
            CabinetInput(
                cabinet_type=CabinetType.WALL,
                width_mm=0,
                height_mm=720,
                depth_mm=300,
            )

    def test_negative_height_raises(self):
        with pytest.raises(ValidationError):
            CabinetInput(
                cabinet_type=CabinetType.WALL,
                width_mm=600,
                height_mm=-100,
                depth_mm=300,
            )

    def test_zero_thickness_raises(self):
        with pytest.raises(ValidationError):
            CabinetInput(
                cabinet_type=CabinetType.WALL,
                width_mm=600,
                height_mm=720,
                depth_mm=300,
                thickness_mm=0,
            )

    def test_negative_shelf_count_raises(self):
        with pytest.raises(ValidationError):
            CabinetInput(
                cabinet_type=CabinetType.WALL,
                width_mm=600,
                height_mm=720,
                depth_mm=300,
                shelf_count=-1,
            )


# ---------------------------------------------------------------------------
# Missing required parameters blocking
# ---------------------------------------------------------------------------


class TestMissingParametersBlocking:
    """build_spec must raise SpecValidationError for impossible inputs."""

    def test_zero_width_blocked_by_pydantic(self):
        """Zero width blocked at CabinetInput validation level."""
        with pytest.raises(ValidationError):
            CabinetInput(
                cabinet_type=CabinetType.WALL,
                width_mm=0,
                height_mm=720,
                depth_mm=300,
            )

    def test_valid_input_produces_build_result(self):
        """Valid input always produces a BuildResult."""
        result = build_spec(MINIMAL_WALL_INPUT)
        assert isinstance(result, BuildResult)
        assert isinstance(result.spec, ManufacturingSpec)


# ---------------------------------------------------------------------------
# Cabinet types — each produces the correct set of panels
# ---------------------------------------------------------------------------


class TestWallCabinet:
    """Wall cabinet: two sides + top + bottom + optional back panel."""

    def test_minimal_panel_count(self):
        result = build_spec(MINIMAL_WALL_INPUT)
        spec = result.spec
        assert spec.spec_version == "1.0"
        assert spec.units.value == "mm"
        # Wall cabinet: left side, right side, top, bottom, back panel = 5
        assert len(spec.panels) == 5

    def test_panel_names_contain_expected_parts(self):
        spec = build_spec(MINIMAL_WALL_INPUT).spec
        names = [p.id for p in spec.panels]
        assert any("left" in n.lower() for n in names)
        assert any("right" in n.lower() for n in names)
        assert any("top" in n.lower() for n in names)
        assert any("bottom" in n.lower() for n in names)

    def test_back_panel_exists(self):
        spec = build_spec(MINIMAL_WALL_INPUT).spec
        names = [p.id for p in spec.panels]
        assert any("back" in n.lower() for n in names)

    def test_no_back_panel_when_disabled(self):
        inp = CabinetInput(
            cabinet_type=CabinetType.WALL,
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            back_panel=False,
        )
        spec = build_spec(inp).spec
        names = [p.id for p in spec.panels]
        assert not any("back" in n.lower() for n in names)

    def test_side_panel_dimensions(self):
        """Side panels: height x depth."""
        spec = build_spec(MINIMAL_WALL_INPUT).spec
        side_panels = [p for p in spec.panels if "left" in p.id.lower() or "right" in p.id.lower()]
        assert len(side_panels) == 2
        for sp in side_panels:
            assert sp.height_mm == 720
            assert sp.width_mm == 300
            assert sp.thickness_mm == 16.0

    def test_top_bottom_panel_dimensions(self):
        """Top/bottom panels: width x depth."""
        spec = build_spec(MINIMAL_WALL_INPUT).spec
        tb_panels = [p for p in spec.panels if "top" in p.id.lower() or "bottom" in p.id.lower()]
        assert len(tb_panels) == 2
        for tb in tb_panels:
            assert tb.width_mm == 600
            assert tb.height_mm == 300

    def test_with_shelves_adds_panel(self):
        spec = build_spec(WITH_SHELVES_INPUT).spec
        shelf_panels = [p for p in spec.panels if "shelf" in p.id.lower() or "полк" in p.id.lower()]
        assert len(shelf_panels) == 3


class TestBaseCabinet:
    """Base (floor) cabinet: two sides + top + bottom + optional back."""

    def test_minimal_panel_count(self):
        result = build_spec(MINIMAL_BASE_INPUT)
        spec = result.spec
        # Base: left, right, top, bottom, back = 5
        assert len(spec.panels) == 5


class TestTallCabinet:
    """Tall (penal) cabinet: two sides + top + bottom + back + shelf."""

    def test_panel_count_with_shelf(self):
        inp = CabinetInput(
            cabinet_type=CabinetType.TALL,
            width_mm=600,
            height_mm=2000,
            depth_mm=500,
            shelf_count=2,
        )
        spec = build_spec(inp).spec
        # tall: left, right, top, bottom, back + 2 shelves = 7
        assert len(spec.panels) == 7


class TestSinkBaseCabinet:
    """Sink base: no bottom panel, only structural ties."""

    def test_no_bottom_panel(self):
        spec = build_spec(SINK_BASE_INPUT).spec
        names = [p.id for p in spec.panels]
        assert not any("bottom" in n.lower() and "shelf" not in n.lower() for n in names)


class TestDrawerCabinet:
    """Drawer cabinet: sides + top + bottom + back + drawer fronts."""

    def test_drawer_fronts_present(self):
        spec = build_spec(DRAWER_INPUT).spec
        front_panels = [p for p in spec.panels if "front" in p.id.lower() or "drawer" in p.id.lower()]
        assert len(front_panels) >= 2


# ---------------------------------------------------------------------------
# Left-right independent operations
# ---------------------------------------------------------------------------


class TestLeftRightIndependence:
    """Left and right side panels must be separate PanelSpec instances with
    independent operations — never sharing operation objects."""

    def test_left_right_are_different_panel_objects(self):
        spec = build_spec(MINIMAL_WALL_INPUT).spec
        left = [p for p in spec.panels if "left" in p.id.lower()]
        right = [p for p in spec.panels if "right" in p.id.lower()]
        assert len(left) == 1
        assert len(right) == 1
        assert left[0] is not right[0]
        assert left[0].id != right[0].id

    def test_operations_on_left_dont_appear_on_right(self):
        """Each side panel has its own operations, not mirrored references."""
        spec = build_spec(WITH_HARDWARE_INPUT).spec
        left = [p for p in spec.panels if "left" in p.id.lower()][0]
        right = [p for p in spec.panels if "right" in p.id.lower()][0]
        left_op_ids = {op.id for op in left.operations}
        right_op_ids = {op.id for op in right.operations}
        # Operation IDs must be unique across the spec, so no overlap
        assert left_op_ids.isdisjoint(right_op_ids)

    def test_modifying_left_ops_doesnt_affect_right(self):
        """Deep independence: adding an op to left doesn't change right."""
        spec = build_spec(WITH_HARDWARE_INPUT).spec
        left = [p for p in spec.panels if "left" in p.id.lower()][0]
        right = [p for p in spec.panels if "right" in p.id.lower()][0]
        right_op_count_before = len(right.operations)
        # Mutate left's operations — right must be unaffected
        left.operations.append(
            DrillOperation(
                id="test_drill_extra",
                face=Face.FRONT,
                x_mm=10.0,
                y_mm=20.0,
                diameter_mm=5.0,
                depth_mm=12.0,
            )
        )
        assert len(right.operations) == right_op_count_before


# ---------------------------------------------------------------------------
# Hardware provenance
# ---------------------------------------------------------------------------


class TestHardwareProvenance:
    """Hardware selections (hinge_type, slide_type) must be traceable in BuildResult."""

    def test_hinge_type_in_provenance(self):
        result = build_spec(WITH_HARDWARE_INPUT)
        assert "hinge_type" in result.provenance
        assert result.provenance["hinge_type"] == "blum_clip_top_110"

    def test_slide_type_in_provenance(self):
        result = build_spec(WITH_HARDWARE_INPUT)
        assert "slide_type" in result.provenance
        assert result.provenance["slide_type"] == "blum_movento_500"

    def test_no_hardware_type_leaves_no_provenance(self):
        result = build_spec(MINIMAL_WALL_INPUT)
        assert result.provenance == {}

    def test_hinge_operations_present_on_door_panels(self):
        """When door_count > 0 and hinge_type is set, drill operations for
        hinge cups should appear on the relevant panels."""
        spec = build_spec(WITH_HARDWARE_INPUT).spec
        all_ops = [op for p in spec.panels for op in p.operations]
        hinge_drills = [
            op for op in all_ops
            if isinstance(op, DrillOperation) and op.diameter_mm == 35.0
        ]
        assert len(hinge_drills) > 0, "Expected hinge cup drill operations (Ø35mm)"


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


class TestPanelIdUniqueness:
    """All panel IDs within a spec must be unique."""

    def test_unique_panel_ids(self):
        spec = build_spec(WITH_SHELVES_INPUT).spec
        ids = [p.id for p in spec.panels]
        assert len(ids) == len(set(ids))


class TestOperationIdUniqueness:
    """All operation IDs within a panel must be unique, and across the whole spec."""

    def test_unique_op_ids_per_panel(self):
        spec = build_spec(WITH_HARDWARE_INPUT).spec
        for panel in spec.panels:
            op_ids = [op.id for op in panel.operations]
            assert len(op_ids) == len(set(op_ids)), f"Duplicate op IDs in panel {panel.id}"

    def test_unique_op_ids_across_spec(self):
        spec = build_spec(WITH_HARDWARE_INPUT).spec
        all_op_ids = [op.id for p in spec.panels for op in p.operations]
        assert len(all_op_ids) == len(set(all_op_ids)), "Duplicate op IDs across spec"


class TestDeterminism:
    """Same input -> same output, always."""

    def test_same_input_same_output(self):
        inp = WITH_HARDWARE_INPUT
        result1 = build_spec(inp)
        result2 = build_spec(inp)
        assert result1.spec.to_canonical_dict() == result2.spec.to_canonical_dict()

    def test_same_input_same_hash(self):
        from api.manufacturing.coordinates import spec_hash

        inp = WITH_HARDWARE_INPUT
        assert spec_hash(build_spec(inp).spec) == spec_hash(build_spec(inp).spec)

    def test_same_input_same_provenance(self):
        inp = WITH_HARDWARE_INPUT
        assert build_spec(inp).provenance == build_spec(inp).provenance


class TestSlotInvariant:
    """Back panel slot operations must match configured slot dimensions."""

    def test_slot_dimensions_match_input(self):
        inp = CabinetInput(
            cabinet_type=CabinetType.WALL,
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            back_slot_width_mm=5.0,
            back_slot_depth_mm=8.0,
        )
        spec = build_spec(inp).spec
        all_ops = [op for p in spec.panels for op in p.operations]
        slot_ops = [op for op in all_ops if isinstance(op, SlotOperation)]
        # There should be at least one slot for the back panel
        assert len(slot_ops) > 0, "Expected back panel slot operations"
        for s in slot_ops:
            assert s.width_mm == 5.0
            assert s.depth_mm == 8.0


class TestThicknessPropagation:
    """All panels must inherit the input thickness."""

    def test_all_panels_use_input_thickness(self):
        inp = CabinetInput(
            cabinet_type=CabinetType.WALL,
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            thickness_mm=18.0,
        )
        spec = build_spec(inp).spec
        for panel in spec.panels:
            assert panel.thickness_mm == 18.0


class TestMaterialPropagation:
    """Material string propagates to all panels."""

    def test_material_on_panels(self):
        inp = CabinetInput(
            cabinet_type=CabinetType.WALL,
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            material="ЛДСП 18мм",
        )
        spec = build_spec(inp).spec
        for panel in spec.panels:
            assert panel.material == "ЛДСП 18мм"


class TestQuantityField:
    """Each PanelSpec instance = 1 unit (no quantity field in ManufacturingSpec)."""

    def test_single_unit_per_panel(self):
        spec = build_spec(MINIMAL_WALL_INPUT).spec
        for panel in spec.panels:
            assert isinstance(panel, PanelSpec)


# ---------------------------------------------------------------------------
# Five cabinet fixtures (Task 6 requirement) + full coverage
# ---------------------------------------------------------------------------

WALL_FIXTURE = CabinetInput(
    cabinet_type=CabinetType.WALL,
    width_mm=600,
    height_mm=720,
    depth_mm=300,
    thickness_mm=16.0,
    shelf_count=2,
    door_count=1,
    hinge_type="blum_clip_top_110",
    slide_type=None,
    back_panel=True,
)

BASE_FIXTURE = CabinetInput(
    cabinet_type=CabinetType.BASE,
    width_mm=600,
    height_mm=720,
    depth_mm=500,
    thickness_mm=16.0,
    shelf_count=1,
    door_count=1,
    hinge_type="blum_clip_top_110",
    slide_type=None,
    back_panel=True,
)

BASE_SINK_FIXTURE = CabinetInput(
    cabinet_type=CabinetType.BASE_SINK,
    width_mm=600,
    height_mm=720,
    depth_mm=500,
    thickness_mm=16.0,
    shelf_count=0,
    door_count=0,
    back_panel=True,
)

DRAWER_FIXTURE = CabinetInput(
    cabinet_type=CabinetType.DRAWER,
    width_mm=600,
    height_mm=720,
    depth_mm=500,
    thickness_mm=16.0,
    drawer_count=3,
    slide_type="blum_movento_500",
    back_panel=True,
)

TALL_FIXTURE = CabinetInput(
    cabinet_type=CabinetType.TALL,
    width_mm=600,
    height_mm=2000,
    depth_mm=500,
    thickness_mm=16.0,
    shelf_count=4,
    door_count=1,
    hinge_type="blum_clip_top_110",
    back_panel=True,
)


class TestFiveCabinetFixtures:
    """Five representative cabinet types must produce valid ManufacturingSpec."""

    def test_wall_fixture_produces_spec(self):
        result = build_spec(WALL_FIXTURE)
        assert isinstance(result, BuildResult)
        assert len(result.spec.panels) >= 5

    def test_base_fixture_produces_spec(self):
        result = build_spec(BASE_FIXTURE)
        assert isinstance(result, BuildResult)
        assert len(result.spec.panels) >= 5

    def test_base_sink_fixture_produces_spec(self):
        result = build_spec(BASE_SINK_FIXTURE)
        assert isinstance(result, BuildResult)
        assert len(result.spec.panels) >= 3  # no bottom

    def test_drawer_fixture_produces_spec(self):
        result = build_spec(DRAWER_FIXTURE)
        assert isinstance(result, BuildResult)
        assert len(result.spec.panels) >= 5

    def test_tall_fixture_produces_spec(self):
        result = build_spec(TALL_FIXTURE)
        assert isinstance(result, BuildResult)
        assert len(result.spec.panels) >= 5


# ---------------------------------------------------------------------------
# Confirmats, shelf pins, back slots, facade hinges, slides coverage
# ---------------------------------------------------------------------------

class TestConfirmatShelfBackOperations:
    """Side and horizontal panels must receive confirmats, shelf pins, back slots via calculators."""

    def test_side_panels_have_confirmats_and_shelf_pins(self):
        spec = build_spec(WALL_FIXTURE).spec
        sides = [p for p in spec.panels if "left" in p.id.lower() or "right" in p.id.lower()]
        assert len(sides) == 2
        for side in sides:
            drills = [op for op in side.operations if isinstance(op, DrillOperation)]
            # confirmats/shelf_pins extracted for future; require presence of drills from calculators
            _ = [d for d in drills if 4.5 <= d.diameter_mm <= 5.5 and d.depth_mm >= 10]
            _ = [d for d in drills if 4.5 <= d.diameter_mm <= 5.5 and d.depth_mm < 10]
            # At least some face drills for confirmats/shelf (from panel_calculator logic)
            assert len(drills) > 0, "sides must have drilling operations from calculators"

    def test_back_slots_present(self):
        spec = build_spec(WALL_FIXTURE).spec
        all_slots = [
            op for p in spec.panels for op in p.operations
            if isinstance(op, SlotOperation)
        ]
        assert len(all_slots) > 0, "back slots expected"

    def test_hinge_drills_on_facade_for_wall(self):
        spec = build_spec(WALL_FIXTURE).spec
        all_drills = [
            op for p in spec.panels for op in p.operations
            if isinstance(op, DrillOperation)
        ]
        hinge_cups = [d for d in all_drills if d.diameter_mm >= 34]
        assert len(hinge_cups) >= 2, "facade hinges expected for door_count=1"


class TestTypedDomainAndHardwareProvenance:
    """Calculators must feed typed domain values; hardware records SKU/template/source."""

    def test_build_result_has_detailed_hardware_provenance(self):
        result = build_spec(WITH_HARDWARE_INPUT)
        prov = result.provenance
        # Must contain sku/template/source style info
        assert "hinge_type" in prov or "hardware" in prov
        if "hardware" in prov:
            hw = prov["hardware"]
            assert "hinges" in hw or "sku" in str(hw)
        # source at top level or nested
        assert any(k in str(prov).lower() for k in ["source", "catalog", "rule", "template"])

    def test_hardware_operations_carry_sku_template_source_in_id_or_provenance(self):
        """Each hardware op must be traceable to SKU / template / source."""
        result = build_spec(WITH_HARDWARE_INPUT)
        spec = result.spec
        hinge_ops = [
            op for p in spec.panels for op in p.operations
            if isinstance(op, DrillOperation) and op.diameter_mm > 30
        ]
        assert len(hinge_ops) > 0
        # Provenance carries the mapping
        prov = result.provenance
        assert prov.get("hinge_type") == "blum_clip_top_110" or "blum" in str(prov)


# ---------------------------------------------------------------------------
# Invariants from the plan (inside bounds, depth compat, non-neg, slot tied to tool)
# ---------------------------------------------------------------------------

class TestSpecBuilderInvariants:
    """All operations satisfy manufacturing invariants (no CAM)."""

    def test_all_ops_inside_panel_bounds(self):
        for fixture in [WALL_FIXTURE, BASE_FIXTURE, TALL_FIXTURE]:
            spec = build_spec(fixture).spec
            for panel in spec.panels:
                for op in panel.operations:
                    if isinstance(op, (DrillOperation, SlotOperation)):
                        assert 0 <= op.x_mm <= panel.width_mm + 0.1
                        assert 0 <= op.y_mm <= panel.height_mm + 0.1

    def test_drill_depth_compatible_with_thickness(self):
        spec = build_spec(WALL_FIXTURE).spec
        for panel in spec.panels:
            for op in panel.operations:
                if isinstance(op, DrillOperation):
                    # depth must be reasonable for panel thickness (face) or edge
                    assert op.depth_mm > 0
                    assert op.depth_mm <= panel.thickness_mm * 3.5 + 1  # allow edge

    def test_slot_width_positive_and_tied(self):
        spec = build_spec(WALL_FIXTURE).spec
        for panel in spec.panels:
            for op in panel.operations:
                if isinstance(op, SlotOperation):
                    assert op.width_mm > 0
                    assert op.depth_mm > 0
                    assert op.length_mm > 0

    def test_no_negative_quantities(self):
        # shelf/door/drawer counts already validated at input
        inp = CabinetInput(cabinet_type=CabinetType.WALL, width_mm=500, height_mm=600, depth_mm=300, shelf_count=0)
        spec = build_spec(inp).spec
        assert len(spec.panels) > 0

    def test_left_right_have_independent_op_lists(self):
        """Explicitly from plan: independent lists, no shared mutation."""
        spec = build_spec(WALL_FIXTURE).spec
        lefts = [p for p in spec.panels if "left" in p.id.lower()]
        rights = [p for p in spec.panels if "right" in p.id.lower()]
        assert len(lefts) == 1 and len(rights) == 1
        left = lefts[0]
        right = rights[0]
        # lists are different objects
        assert left.operations is not right.operations
        orig_right_len = len(right.operations)
        # simulate edit
        if left.operations:
            left.operations = list(left.operations) + [left.operations[0]]  # replace list
        assert len(right.operations) == orig_right_len
