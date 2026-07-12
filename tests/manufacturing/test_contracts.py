"""Failing tests for manufacturing contracts: Face, operations, PanelSpec, ManufacturingSpec.

TDD RED phase — все тесты падают до реализации.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Face enum
# ---------------------------------------------------------------------------

class TestFace:
    """Face enum: FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM."""

    def test_face_values(self):
        from api.manufacturing.contracts import Face
        assert set(Face) == {
            Face.FRONT, Face.BACK, Face.LEFT,
            Face.RIGHT, Face.TOP, Face.BOTTOM,
        }

    def test_face_str_values(self):
        from api.manufacturing.contracts import Face
        assert Face.FRONT.value == "front"
        assert Face.BACK.value == "back"
        assert Face.LEFT.value == "left"
        assert Face.RIGHT.value == "right"
        assert Face.TOP.value == "top"
        assert Face.BOTTOM.value == "bottom"

    def test_face_from_string(self):
        from api.manufacturing.contracts import Face
        assert Face("front") is Face.FRONT
        assert Face("back") is Face.BACK

    def test_face_invalid_raises(self):
        from api.manufacturing.contracts import Face
        with pytest.raises(ValueError):
            Face("diagonal")


# ---------------------------------------------------------------------------
# DrillOperation
# ---------------------------------------------------------------------------

class TestDrillOperation:
    """DrillOperation: x_mm, y_mm, diameter_mm, depth_mm."""

    def test_create_basic(self):
        from api.manufacturing.contracts import DrillOperation, Face
        op = DrillOperation(
            id="drill-1",
            face=Face.FRONT,
            x_mm=50.0,
            y_mm=100.0,
            diameter_mm=5.0,
            depth_mm=12.0,
        )
        assert op.id == "drill-1"
        assert op.face is Face.FRONT
        assert op.x_mm == 50.0
        assert op.diameter_mm == 5.0

    def test_invalid_diameter_zero_raises(self):
        from api.manufacturing.contracts import DrillOperation, Face
        with pytest.raises(ValidationError):
            DrillOperation(
                id="drill-bad", face=Face.FRONT,
                x_mm=0, y_mm=0, diameter_mm=0, depth_mm=5,
            )

    def test_invalid_diameter_negative_raises(self):
        from api.manufacturing.contracts import DrillOperation, Face
        with pytest.raises(ValidationError):
            DrillOperation(
                id="drill-bad", face=Face.FRONT,
                x_mm=0, y_mm=0, diameter_mm=-3, depth_mm=5,
            )

    def test_invalid_depth_negative_raises(self):
        from api.manufacturing.contracts import DrillOperation, Face
        with pytest.raises(ValidationError):
            DrillOperation(
                id="drill-bad", face=Face.FRONT,
                x_mm=0, y_mm=0, diameter_mm=5, depth_mm=-1,
            )

    def test_nan_coordinate_raises(self):
        from api.manufacturing.contracts import DrillOperation, Face
        with pytest.raises(ValidationError):
            DrillOperation(
                id="drill-bad", face=Face.FRONT,
                x_mm=float("nan"), y_mm=0, diameter_mm=5, depth_mm=5,
            )

    def test_inf_coordinate_raises(self):
        from api.manufacturing.contracts import DrillOperation, Face
        with pytest.raises(ValidationError):
            DrillOperation(
                id="drill-bad", face=Face.FRONT,
                x_mm=float("inf"), y_mm=0, diameter_mm=5, depth_mm=5,
            )

    def test_empty_id_raises(self):
        from api.manufacturing.contracts import DrillOperation, Face
        with pytest.raises(ValidationError):
            DrillOperation(
                id="", face=Face.FRONT,
                x_mm=0, y_mm=0, diameter_mm=5, depth_mm=5,
            )

    def test_negative_coordinates_allowed(self):
        """Отрицательные координаты допустимы (относительно начала грани)."""
        from api.manufacturing.contracts import DrillOperation, Face
        op = DrillOperation(
            id="drill-neg", face=Face.FRONT,
            x_mm=-10.0, y_mm=-5.0, diameter_mm=5.0, depth_mm=5.0,
        )
        assert op.x_mm == -10.0


# ---------------------------------------------------------------------------
# SlotOperation
# ---------------------------------------------------------------------------

class TestSlotOperation:
    """SlotOperation: x_mm, y_mm, length_mm, width_mm, depth_mm."""

    def test_create_basic(self):
        from api.manufacturing.contracts import Face, SlotOperation
        op = SlotOperation(
            id="slot-1",
            face=Face.BACK,
            x_mm=20.0,
            y_mm=0.0,
            length_mm=200.0,
            width_mm=4.0,
            depth_mm=10.0,
        )
        assert op.length_mm == 200.0
        assert op.width_mm == 4.0

    def test_invalid_length_zero_raises(self):
        from api.manufacturing.contracts import Face, SlotOperation
        with pytest.raises(ValidationError):
            SlotOperation(
                id="slot-bad", face=Face.BACK,
                x_mm=0, y_mm=0, length_mm=0, width_mm=4, depth_mm=10,
            )

    def test_invalid_width_negative_raises(self):
        from api.manufacturing.contracts import Face, SlotOperation
        with pytest.raises(ValidationError):
            SlotOperation(
                id="slot-bad", face=Face.BACK,
                x_mm=0, y_mm=0, length_mm=100, width_mm=-1, depth_mm=10,
            )

    def test_nan_in_dimension_raises(self):
        from api.manufacturing.contracts import Face, SlotOperation
        with pytest.raises(ValidationError):
            SlotOperation(
                id="slot-bad", face=Face.BACK,
                x_mm=0, y_mm=0, length_mm=float("nan"), width_mm=4, depth_mm=10,
            )


# ---------------------------------------------------------------------------
# PocketOperation
# ---------------------------------------------------------------------------

class TestPocketOperation:
    """PocketOperation: x_mm, y_mm, width_mm, height_mm, depth_mm."""

    def test_create_basic(self):
        from api.manufacturing.contracts import Face, PocketOperation
        op = PocketOperation(
            id="pocket-1",
            face=Face.TOP,
            x_mm=10.0,
            y_mm=20.0,
            width_mm=80.0,
            height_mm=60.0,
            depth_mm=3.0,
        )
        assert op.width_mm == 80.0
        assert op.height_mm == 60.0

    def test_invalid_width_zero_raises(self):
        from api.manufacturing.contracts import Face, PocketOperation
        with pytest.raises(ValidationError):
            PocketOperation(
                id="pocket-bad", face=Face.TOP,
                x_mm=0, y_mm=0, width_mm=0, height_mm=60, depth_mm=3,
            )

    def test_invalid_height_negative_raises(self):
        from api.manufacturing.contracts import Face, PocketOperation
        with pytest.raises(ValidationError):
            PocketOperation(
                id="pocket-bad", face=Face.TOP,
                x_mm=0, y_mm=0, width_mm=80, height_mm=-5, depth_mm=3,
            )

    def test_inf_dimension_raises(self):
        from api.manufacturing.contracts import Face, PocketOperation
        with pytest.raises(ValidationError):
            PocketOperation(
                id="pocket-bad", face=Face.TOP,
                x_mm=0, y_mm=0, width_mm=80, height_mm=float("inf"), depth_mm=3,
            )


# ---------------------------------------------------------------------------
# Operation type discriminator
# ---------------------------------------------------------------------------

class TestOperationTypeField:
    """Each operation carries an op_type discriminator."""

    def test_drill_op_type(self):
        from api.manufacturing.contracts import DrillOperation, Face
        d = DrillOperation(id="d1", face=Face.FRONT, x_mm=0, y_mm=0, diameter_mm=5, depth_mm=5)
        assert d.op_type.value == "drill"

    def test_slot_op_type(self):
        from api.manufacturing.contracts import Face, SlotOperation
        s = SlotOperation(id="s1", face=Face.BACK, x_mm=0, y_mm=0, length_mm=100, width_mm=4, depth_mm=10)
        assert s.op_type.value == "slot"

    def test_pocket_op_type(self):
        from api.manufacturing.contracts import Face, PocketOperation
        p = PocketOperation(id="p1", face=Face.TOP, x_mm=0, y_mm=0, width_mm=80, height_mm=60, depth_mm=3)
        assert p.op_type.value == "pocket"


# ---------------------------------------------------------------------------
# PanelSpec
# ---------------------------------------------------------------------------

class TestPanelSpec:
    """PanelSpec: width_mm, height_mm, thickness_mm, material, operations."""

    def test_create_minimal(self):
        from api.manufacturing.contracts import PanelSpec
        panel = PanelSpec(
            id="panel-1",
            width_mm=600.0,
            height_mm=720.0,
            thickness_mm=16.0,
        )
        assert panel.width_mm == 600.0
        assert panel.operations == []

    def test_create_with_operations(self):
        from api.manufacturing.contracts import DrillOperation, Face, PanelSpec
        ops = [
            DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=12),
        ]
        panel = PanelSpec(
            id="panel-2",
            width_mm=400,
            height_mm=500,
            thickness_mm=18,
            material="ЛДСП",
            operations=ops,
        )
        assert len(panel.operations) == 1

    def test_invalid_width_zero_raises(self):
        from api.manufacturing.contracts import PanelSpec
        with pytest.raises(ValidationError):
            PanelSpec(id="p", width_mm=0, height_mm=500, thickness_mm=16)

    def test_invalid_thickness_negative_raises(self):
        from api.manufacturing.contracts import PanelSpec
        with pytest.raises(ValidationError):
            PanelSpec(id="p", width_mm=600, height_mm=500, thickness_mm=-1)

    def test_duplicate_operation_ids_raises(self):
        from api.manufacturing.contracts import DrillOperation, Face, PanelSpec
        ops = [
            DrillOperation(id="same", face=Face.FRONT, x_mm=0, y_mm=0, diameter_mm=5, depth_mm=5),
            DrillOperation(id="same", face=Face.BACK, x_mm=10, y_mm=10, diameter_mm=5, depth_mm=5),
        ]
        with pytest.raises(ValidationError, match="дублирующиеся"):
            PanelSpec(id="p", width_mm=600, height_mm=500, thickness_mm=16, operations=ops)

    def test_material_optional(self):
        from api.manufacturing.contracts import PanelSpec
        panel = PanelSpec(id="p", width_mm=600, height_mm=500, thickness_mm=16)
        assert panel.material is None


# ---------------------------------------------------------------------------
# Unit enum
# ---------------------------------------------------------------------------

class TestUnit:
    """Unit enum: MM, INCH."""

    def test_unit_values(self):
        from api.manufacturing.contracts import Unit
        assert Unit.MM.value == "mm"
        assert Unit.INCH.value == "inch"

    def test_unsupported_unit_raises(self):
        from api.manufacturing.contracts import Unit
        with pytest.raises(ValueError):
            Unit("cm")


# ---------------------------------------------------------------------------
# ManufacturingSpec
# ---------------------------------------------------------------------------

class TestManufacturingSpec:
    """Top-level: panels, units, spec_version."""

    def test_create_minimal(self):
        from api.manufacturing.contracts import ManufacturingSpec
        spec = ManufacturingSpec(panels=[])
        assert spec.panels == []
        assert spec.units.value == "mm"
        assert spec.spec_version == "1.0"

    def test_create_with_panels(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        panels = [
            PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16),
        ]
        spec = ManufacturingSpec(panels=panels)
        assert len(spec.panels) == 1

    def test_invalid_spec_version_empty_raises(self):
        from api.manufacturing.contracts import ManufacturingSpec
        with pytest.raises(ValidationError):
            ManufacturingSpec(panels=[], spec_version="")

    def test_unsupported_units_raises(self):
        from api.manufacturing.contracts import ManufacturingSpec
        with pytest.raises(ValidationError):
            ManufacturingSpec(panels=[], units="cm")

    def test_duplicate_panel_ids_raises(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        panels = [
            PanelSpec(id="dup", width_mm=600, height_mm=500, thickness_mm=16),
            PanelSpec(id="dup", width_mm=400, height_mm=300, thickness_mm=18),
        ]
        with pytest.raises(ValidationError, match="дублирующиеся"):
            ManufacturingSpec(panels=panels)

from api.manufacturing.coordinates import canonical_json, spec_hash

# ---------------------------------------------------------------------------
# Canonical determinism: permutation invariance
# ---------------------------------------------------------------------------


class TestCanonicalDeterminism:
    """Panels and operations sorted by id → same canonical output regardless of input order."""

    def test_panel_permutation_same_canonical_dict(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        p1 = PanelSpec(id="a", width_mm=600, height_mm=720, thickness_mm=16)
        p2 = PanelSpec(id="b", width_mm=400, height_mm=500, thickness_mm=18)
        spec1 = ManufacturingSpec(panels=[p1, p2])
        spec2 = ManufacturingSpec(panels=[p2, p1])
        assert spec1.to_canonical_dict() == spec2.to_canonical_dict()

    def test_operation_permutation_same_canonical_dict(self):
        from api.manufacturing.contracts import (
            DrillOperation,
            Face,
            ManufacturingSpec,
            PanelSpec,
            SlotOperation,
        )
        op1 = DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=12)
        op2 = SlotOperation(id="s1", face=Face.BACK, x_mm=10, y_mm=20, length_mm=100, width_mm=4, depth_mm=10)
        panel_a = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, operations=[op1, op2])
        panel_b = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, operations=[op2, op1])
        spec1 = ManufacturingSpec(panels=[panel_a])
        spec2 = ManufacturingSpec(panels=[panel_b])
        assert spec1.to_canonical_dict() == spec2.to_canonical_dict()

    def test_combined_permutation_same_canonical_dict(self):
        from api.manufacturing.contracts import (
            DrillOperation,
            Face,
            ManufacturingSpec,
            PanelSpec,
        )
        op1 = DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=12)
        op2 = DrillOperation(id="d2", face=Face.BACK, x_mm=10, y_mm=20, diameter_mm=3, depth_mm=8)
        p1 = PanelSpec(id="a", width_mm=600, height_mm=720, thickness_mm=16, operations=[op1])
        p2 = PanelSpec(id="b", width_mm=400, height_mm=500, thickness_mm=18, operations=[op2])
        spec1 = ManufacturingSpec(panels=[p1, p2])
        spec2 = ManufacturingSpec(panels=[p2, p1])
        assert spec1.to_canonical_dict() == spec2.to_canonical_dict()

    def test_panel_permutation_same_json(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        p1 = PanelSpec(id="a", width_mm=600, height_mm=720, thickness_mm=16)
        p2 = PanelSpec(id="b", width_mm=400, height_mm=500, thickness_mm=18)
        spec1 = ManufacturingSpec(panels=[p1, p2])
        spec2 = ManufacturingSpec(panels=[p2, p1])
        assert canonical_json(spec1) == canonical_json(spec2)

    def test_operation_permutation_same_json(self):
        from api.manufacturing.contracts import (
            DrillOperation,
            Face,
            ManufacturingSpec,
            PanelSpec,
            SlotOperation,
        )
        op1 = DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=12)
        op2 = SlotOperation(id="s1", face=Face.BACK, x_mm=10, y_mm=20, length_mm=100, width_mm=4, depth_mm=10)
        panel_a = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, operations=[op1, op2])
        panel_b = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, operations=[op2, op1])
        spec1 = ManufacturingSpec(panels=[panel_a])
        spec2 = ManufacturingSpec(panels=[panel_b])
        assert canonical_json(spec1) == canonical_json(spec2)

    def test_panel_permutation_same_hash(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        p1 = PanelSpec(id="a", width_mm=600, height_mm=720, thickness_mm=16)
        p2 = PanelSpec(id="b", width_mm=400, height_mm=500, thickness_mm=18)
        spec1 = ManufacturingSpec(panels=[p1, p2])
        spec2 = ManufacturingSpec(panels=[p2, p1])
        assert spec_hash(spec1) == spec_hash(spec2)

    def test_operation_permutation_same_hash(self):
        from api.manufacturing.contracts import (
            DrillOperation,
            Face,
            ManufacturingSpec,
            PanelSpec,
        )
        op1 = DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=12)
        op2 = DrillOperation(id="d2", face=Face.BACK, x_mm=10, y_mm=20, diameter_mm=3, depth_mm=8)
        panel_a = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, operations=[op1, op2])
        panel_b = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, operations=[op2, op1])
        spec1 = ManufacturingSpec(panels=[panel_a])
        spec2 = ManufacturingSpec(panels=[panel_b])
        assert spec_hash(spec1) == spec_hash(spec2)

    def test_no_mutation_of_input_models(self):
        from api.manufacturing.contracts import (
            DrillOperation,
            Face,
            ManufacturingSpec,
            PanelSpec,
            SlotOperation,
        )
        op1 = DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=12)
        op2 = SlotOperation(id="s1", face=Face.BACK, x_mm=10, y_mm=20, length_mm=100, width_mm=4, depth_mm=10)
        panel = PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16, operations=[op1, op2])
        spec = ManufacturingSpec(panels=[panel])
        original_ops = list(spec.panels[0].operations)
        _ = spec.to_canonical_dict()
        _ = canonical_json(spec)
        assert spec.panels[0].operations[0].id == original_ops[0].id
        assert spec.panels[0].operations[1].id == original_ops[1].id
        assert len(spec.panels) == 1