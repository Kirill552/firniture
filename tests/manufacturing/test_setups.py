"""Tests for Task 16: Setup transforms — top/bottom/four-edge CNC mounting.

Covers:
  - SetupType enum values and classification
  - Flat transform (top identity, bottom Y-mirror)
  - Edge transforms (four edge setups)
  - Unified apply_setup_transform dispatch
  - validate_setup_for_profile (3-axis gate, certification gate)
  - validate_setup_or_raise (raises SetupError)
  - transform_operations (batch operation transform)
  - setup_local_to_canonical (coordinate.py integration)
  - accessible_face mapping
"""
from __future__ import annotations

import math

import pytest

from api.manufacturing.contracts import (
    DrillOperation,
    Face,
    OperationType,
)
from api.manufacturing.coordinates import setup_local_to_canonical
from api.manufacturing.machine_profiles import (
    AxisLimits,
    CertificationStatus,
    ControllerType,
    DwellSyntax,
    LineEnding,
    MachineProfile,
    SpindleConfig,
    Units,
)
from api.manufacturing.setups import (
    SetupError,
    SetupType,
    accessible_face,
    apply_edge_transform,
    apply_flat_transform,
    apply_setup_transform,
    is_flat_setup,
    setup_requires_aggregate,
    transform_operations,
    validate_setup_for_profile,
    validate_setup_or_raise,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(
    *,
    profile_id: str = "test-machine",
    certification: CertificationStatus = CertificationStatus.VERIFIED,
) -> MachineProfile:
    """Build a minimal valid MachineProfile for testing."""
    return MachineProfile(
        profile_id=profile_id,
        controller=ControllerType.OTHER,
        controller_version="1.0",
        units=Units.MM,
        work_offset="G54",
        supported_faces=[Face.FRONT, Face.BACK],
        spindles=[
            SpindleConfig(spindle_id=1, name="main", max_rpm=24000, max_power_kw=5.5),
        ],
        axis_limits=AxisLimits(
            x_min=0, x_max=3000,
            y_min=0, y_max=2000,
            z_min=-100, z_max=0,
        ),
        safe_z=25.0,
        feed_min=100,
        feed_max=15000,
        rpm_min=6000,
        rpm_max=24000,
        dwell_syntax=DwellSyntax.G4_P_MILLISECONDS,
        line_ending=LineEnding.LF,
        certification=certification,
        postprocessor_version="1.0",
    )


def _make_op(
    *,
    op_id: str = "op1",
    face: Face = Face.FRONT,
    x_mm: float = 100.0,
    y_mm: float = 200.0,
) -> DrillOperation:
    """Build a minimal DrillOperation."""
    return DrillOperation(
        id=op_id,
        op_type=OperationType.DRILL,
        face=face,
        x_mm=x_mm,
        y_mm=y_mm,
        diameter_mm=5.0,
        depth_mm=15.0,
    )


# ═══════════════════════════════════════════════════════════════════════
# SetupType enum
# ═══════════════════════════════════════════════════════════════════════


class TestSetupType:
    """Enum values and string representation."""

    def test_six_values(self) -> None:
        assert len(SetupType) == 6

    def test_flat_values(self) -> None:
        assert SetupType.TOP.value == "top"
        assert SetupType.BOTTOM.value == "bottom"

    def test_edge_values(self) -> None:
        assert SetupType.LEFT_EDGE.value == "left_edge"
        assert SetupType.RIGHT_EDGE.value == "right_edge"
        assert SetupType.FRONT_EDGE.value == "front_edge"
        assert SetupType.BACK_EDGE.value == "back_edge"

    def test_from_string(self) -> None:
        assert SetupType("top") is SetupType.TOP
        assert SetupType("left_edge") is SetupType.LEFT_EDGE

    def test_invalid_string(self) -> None:
        with pytest.raises(ValueError):
            SetupType("diagonal")


# ═══════════════════════════════════════════════════════════════════════
# Classification helpers
# ═══════════════════════════════════════════════════════════════════════


class TestIsFlatSetup:
    def test_top_is_flat(self) -> None:
        assert is_flat_setup(SetupType.TOP) is True

    def test_bottom_is_flat(self) -> None:
        assert is_flat_setup(SetupType.BOTTOM) is True

    @pytest.mark.parametrize(
        "edge",
        [
            SetupType.LEFT_EDGE,
            SetupType.RIGHT_EDGE,
            SetupType.FRONT_EDGE,
            SetupType.BACK_EDGE,
        ],
    )
    def test_edges_are_not_flat(self, edge: SetupType) -> None:
        assert is_flat_setup(edge) is False


class TestSetupRequiresAggregate:
    def test_top_no_aggregate(self) -> None:
        assert setup_requires_aggregate(SetupType.TOP) is False

    def test_bottom_no_aggregate(self) -> None:
        assert setup_requires_aggregate(SetupType.BOTTOM) is False

    @pytest.mark.parametrize(
        "edge",
        [
            SetupType.LEFT_EDGE,
            SetupType.RIGHT_EDGE,
            SetupType.FRONT_EDGE,
            SetupType.BACK_EDGE,
        ],
    )
    def test_edge_requires_aggregate(self, edge: SetupType) -> None:
        assert setup_requires_aggregate(edge) is True


class TestAccessibleFace:
    def test_top_exposes_front(self) -> None:
        assert accessible_face(SetupType.TOP) == "front"

    def test_bottom_exposes_back(self) -> None:
        assert accessible_face(SetupType.BOTTOM) == "back"

    def test_left_edge_exposes_left(self) -> None:
        assert accessible_face(SetupType.LEFT_EDGE) == "left"

    def test_right_edge_exposes_right(self) -> None:
        assert accessible_face(SetupType.RIGHT_EDGE) == "right"

    def test_front_edge_exposes_front(self) -> None:
        assert accessible_face(SetupType.FRONT_EDGE) == "front"

    def test_back_edge_exposes_back(self) -> None:
        assert accessible_face(SetupType.BACK_EDGE) == "back"


# ═══════════════════════════════════════════════════════════════════════
# Flat transforms
# ═══════════════════════════════════════════════════════════════════════


class TestApplyFlatTransform:
    """Flat setup coordinate transforms."""

    def test_top_identity(self) -> None:
        x, y = apply_flat_transform(100.0, 200.0, SetupType.TOP, panel_h=600.0)
        assert math.isclose(x, 100.0)
        assert math.isclose(y, 200.0)

    def test_bottom_y_mirror(self) -> None:
        x, y = apply_flat_transform(100.0, 200.0, SetupType.BOTTOM, panel_h=600.0)
        assert math.isclose(x, 100.0)
        assert math.isclose(y, 400.0)  # 600 - 200

    def test_bottom_at_origin(self) -> None:
        """Point at y=0 → y=panel_h after mirror."""
        x, y = apply_flat_transform(0.0, 0.0, SetupType.BOTTOM, panel_h=500.0)
        assert math.isclose(y, 500.0)

    def test_bottom_at_top_edge(self) -> None:
        """Point at y=panel_h → y=0 after mirror."""
        x, y = apply_flat_transform(50.0, 500.0, SetupType.BOTTOM, panel_h=500.0)
        assert math.isclose(y, 0.0)

    def test_rejects_edge_setup(self) -> None:
        with pytest.raises(ValueError, match="non-flat"):
            apply_flat_transform(0, 0, SetupType.LEFT_EDGE, panel_h=600.0)


# ═══════════════════════════════════════════════════════════════════════
# Edge transforms
# ═══════════════════════════════════════════════════════════════════════


class TestApplyEdgeTransform:
    """Edge setup coordinate transforms — panel rotated 90°."""

    W, H = 1200.0, 600.0

    def test_left_edge_swap(self) -> None:
        """LEFT_EDGE: (x, y) → (y, x)."""
        nx, ny = apply_edge_transform(
            100.0, 200.0, SetupType.LEFT_EDGE,
            panel_w=self.W, panel_h=self.H,
        )
        assert math.isclose(nx, 200.0)
        assert math.isclose(ny, 100.0)

    def test_right_edge_swap_mirror(self) -> None:
        """RIGHT_EDGE: (x, y) → (panel_h - y, x)."""
        nx, ny = apply_edge_transform(
            100.0, 200.0, SetupType.RIGHT_EDGE,
            panel_w=self.W, panel_h=self.H,
        )
        assert math.isclose(nx, 400.0)  # 600 - 200
        assert math.isclose(ny, 100.0)

    def test_front_edge_mirror(self) -> None:
        """FRONT_EDGE: (x, y) → (panel_w - x, y)."""
        nx, ny = apply_edge_transform(
            100.0, 200.0, SetupType.FRONT_EDGE,
            panel_w=self.W, panel_h=self.H,
        )
        assert math.isclose(nx, 1100.0)  # 1200 - 100
        assert math.isclose(ny, 200.0)

    def test_back_edge_identity(self) -> None:
        """BACK_EDGE: (x, y) → (x, y) — no transform."""
        nx, ny = apply_edge_transform(
            100.0, 200.0, SetupType.BACK_EDGE,
            panel_w=self.W, panel_h=self.H,
        )
        assert math.isclose(nx, 100.0)
        assert math.isclose(ny, 200.0)

    def test_rejects_flat_setup(self) -> None:
        with pytest.raises(ValueError, match="non-edge"):
            apply_edge_transform(0, 0, SetupType.TOP, panel_w=100, panel_h=100)

    def test_left_edge_at_origin(self) -> None:
        nx, ny = apply_edge_transform(0.0, 0.0, SetupType.LEFT_EDGE, panel_w=100, panel_h=100)
        assert math.isclose(nx, 0.0)
        assert math.isclose(ny, 0.0)

    def test_right_edge_at_max(self) -> None:
        """Point at (panel_w, panel_h) on RIGHT_EDGE → (0, panel_w)."""
        nx, ny = apply_edge_transform(
            self.W, self.H, SetupType.RIGHT_EDGE,
            panel_w=self.W, panel_h=self.H,
        )
        assert math.isclose(nx, 0.0)
        assert math.isclose(ny, self.W)


# ═══════════════════════════════════════════════════════════════════════
# Unified dispatch
# ═══════════════════════════════════════════════════════════════════════


class TestApplySetupTransform:
    """Unified transform dispatch."""

    def test_top_dispatches_to_flat(self) -> None:
        x, y = apply_setup_transform(
            50.0, 100.0, SetupType.TOP,
            panel_w=800, panel_h=600, thickness_mm=18.0,
        )
        assert math.isclose(x, 50.0)
        assert math.isclose(y, 100.0)

    def test_bottom_dispatches_to_flat(self) -> None:
        x, y = apply_setup_transform(
            50.0, 100.0, SetupType.BOTTOM,
            panel_w=800, panel_h=600, thickness_mm=18.0,
        )
        assert math.isclose(y, 500.0)  # 600 - 100

    def test_left_edge_dispatches_to_edge(self) -> None:
        x, y = apply_setup_transform(
            50.0, 100.0, SetupType.LEFT_EDGE,
            panel_w=800, panel_h=600, thickness_mm=18.0,
        )
        assert math.isclose(x, 100.0)
        assert math.isclose(y, 50.0)


# ═══════════════════════════════════════════════════════════════════════
# Machine validation
# ═══════════════════════════════════════════════════════════════════════


class TestValidateSetupForProfile:
    """Business rules: 3-axis gate + certification gate."""

    def test_flat_always_valid(self) -> None:
        profile = _make_profile()
        for flat in (SetupType.TOP, SetupType.BOTTOM):
            errors = validate_setup_for_profile(flat, profile, axis_count=3)
            assert errors == [], f"{flat} should be valid on 3-axis"

    def test_edge_blocked_on_3axis(self) -> None:
        profile = _make_profile()
        for edge in (
            SetupType.LEFT_EDGE,
            SetupType.RIGHT_EDGE,
            SetupType.FRONT_EDGE,
            SetupType.BACK_EDGE,
        ):
            errors = validate_setup_for_profile(edge, profile, axis_count=3)
            assert len(errors) == 1
            assert "3-axis" in errors[0]
            assert edge.value in errors[0]

    def test_edge_allowed_on_4axis_verified(self) -> None:
        profile = _make_profile(certification=CertificationStatus.VERIFIED)
        errors = validate_setup_for_profile(
            SetupType.LEFT_EDGE, profile, axis_count=4,
        )
        assert errors == []

    def test_edge_blocked_on_4axis_unverified(self) -> None:
        for cert in (CertificationStatus.DRAFT, CertificationStatus.DEPRECATED):
            profile = _make_profile(certification=cert)
            errors = validate_setup_for_profile(
                SetupType.RIGHT_EDGE, profile, axis_count=4,
            )
            assert len(errors) == 1
            assert "VERIFIED" in errors[0]

    def test_edge_allowed_on_5axis_verified(self) -> None:
        profile = _make_profile(certification=CertificationStatus.VERIFIED)
        errors = validate_setup_for_profile(
            SetupType.FRONT_EDGE, profile, axis_count=5,
        )
        assert errors == []

    def test_multiple_errors_for_different_rules(self) -> None:
        """Not possible in current design (single error path), but test
        that the function returns exactly one error for 3-axis edge."""
        profile = _make_profile(certification=CertificationStatus.DRAFT)
        errors = validate_setup_for_profile(
            SetupType.BACK_EDGE, profile, axis_count=3,
        )
        # 3-axis blocks before certification check
        assert len(errors) == 1
        assert "3-axis" in errors[0]


class TestValidateSetupOrRaise:
    """validate_setup_or_raise wraps validation with exception."""

    def test_valid_does_not_raise(self) -> None:
        profile = _make_profile()
        validate_setup_or_raise(SetupType.TOP, profile, axis_count=3)

    def test_invalid_raises_setup_error(self) -> None:
        profile = _make_profile()
        with pytest.raises(SetupError, match="3-axis"):
            validate_setup_or_raise(SetupType.LEFT_EDGE, profile, axis_count=3)

    def test_unverified_raises_setup_error(self) -> None:
        profile = _make_profile(certification=CertificationStatus.DRAFT)
        with pytest.raises(SetupError, match="VERIFIED"):
            validate_setup_or_raise(
                SetupType.RIGHT_EDGE, profile, axis_count=4,
            )


# ═══════════════════════════════════════════════════════════════════════
# transform_operations
# ═══════════════════════════════════════════════════════════════════════


class TestTransformOperations:
    """Batch operation transform via setup."""

    def test_top_preserves_operations(self) -> None:
        ops = [_make_op(x_mm=100, y_mm=200)]
        result = transform_operations(
            ops, SetupType.TOP,
            panel_w=800, panel_h=600, thickness_mm=18,
        )
        assert len(result) == 1
        assert math.isclose(result[0].x_mm, 100.0)
        assert math.isclose(result[0].y_mm, 200.0)

    def test_bottom_mirrors_y(self) -> None:
        ops = [_make_op(x_mm=100, y_mm=200)]
        result = transform_operations(
            ops, SetupType.BOTTOM,
            panel_w=800, panel_h=600, thickness_mm=18,
        )
        assert math.isclose(result[0].x_mm, 100.0)
        assert math.isclose(result[0].y_mm, 400.0)  # 600 - 200

    def test_left_edge_swaps_coords(self) -> None:
        ops = [_make_op(x_mm=100, y_mm=200)]
        result = transform_operations(
            ops, SetupType.LEFT_EDGE,
            panel_w=800, panel_h=600, thickness_mm=18,
        )
        assert math.isclose(result[0].x_mm, 200.0)
        assert math.isclose(result[0].y_mm, 100.0)

    def test_preserves_operation_identity(self) -> None:
        ops = [_make_op(op_id="drill-42", x_mm=50, y_mm=50)]
        result = transform_operations(
            ops, SetupType.BOTTOM,
            panel_w=100, panel_h=100, thickness_mm=18,
        )
        assert result[0].id == "drill-42"
        assert result[0].op_type == OperationType.DRILL

    def test_multiple_operations(self) -> None:
        ops = [
            _make_op(op_id="a", x_mm=0, y_mm=0),
            _make_op(op_id="b", x_mm=400, y_mm=300),
            _make_op(op_id="c", x_mm=800, y_mm=600),
        ]
        result = transform_operations(
            ops, SetupType.BOTTOM,
            panel_w=800, panel_h=600, thickness_mm=18,
        )
        assert math.isclose(result[0].y_mm, 600.0)   # 600 - 0
        assert math.isclose(result[1].y_mm, 300.0)   # 600 - 300
        assert math.isclose(result[2].y_mm, 0.0)      # 600 - 600

    def test_does_not_mutate_original(self) -> None:
        op = _make_op(x_mm=100, y_mm=200)
        original_x, original_y = op.x_mm, op.y_mm
        transform_operations(
            [op], SetupType.BOTTOM,
            panel_w=800, panel_h=600, thickness_mm=18,
        )
        assert math.isclose(op.x_mm, original_x)
        assert math.isclose(op.y_mm, original_y)

    def test_empty_operations(self) -> None:
        result = transform_operations(
            [], SetupType.BOTTOM,
            panel_w=800, panel_h=600, thickness_mm=18,
        )
        assert result == []


# ═══════════════════════════════════════════════════════════════════════
# setup_local_to_canonical (integration with coordinates.py)
# ═══════════════════════════════════════════════════════════════════════


class TestSetupLocalToCanonical:
    """Face-local coords → canonical panel coords with setup awareness."""

    def test_top_front_identity(self) -> None:
        """TOP setup, front face: local coords pass through unchanged."""
        px, py = setup_local_to_canonical(
            Face.FRONT, 100.0, 200.0, "top",
            panel_w=800, panel_h=600, thickness=18,
        )
        assert math.isclose(px, 100.0)
        assert math.isclose(py, 200.0)

    def test_bottom_front_mirror(self) -> None:
        """BOTTOM setup, front face: Y is mirrored."""
        px, py = setup_local_to_canonical(
            Face.FRONT, 100.0, 200.0, "bottom",
            panel_w=800, panel_h=600, thickness=18,
        )
        assert math.isclose(px, 100.0)
        assert math.isclose(py, 400.0)

    def test_top_back_mirror(self) -> None:
        """TOP setup, back face: face_to_panel mirrors X, then flat (identity)."""
        px, py = setup_local_to_canonical(
            Face.BACK, 100.0, 200.0, "top",
            panel_w=800, panel_h=600, thickness=18,
        )
        # back face: x → panel_w - x = 800 - 100 = 700
        assert math.isclose(px, 700.0)
        assert math.isclose(py, 200.0)

    def test_bottom_back_double_mirror(self) -> None:
        """BOTTOM setup, back face: X mirror (face) + Y mirror (setup)."""
        px, py = setup_local_to_canonical(
            Face.BACK, 100.0, 200.0, "bottom",
            panel_w=800, panel_h=600, thickness=18,
        )
        assert math.isclose(px, 700.0)  # back: 800 - 100
        assert math.isclose(py, 400.0)  # bottom: 600 - 200

    def test_invalid_setup_string(self) -> None:
        with pytest.raises(ValueError):
            setup_local_to_canonical(
                Face.FRONT, 0, 0, "diagonal",
                panel_w=100, panel_h=100, thickness=18,
            )


# ═══════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Boundary conditions and degenerate inputs."""

    def test_zero_panel_dimensions(self) -> None:
        """Flat transform with zero-height panel: bottom mirror at y=0."""
        x, y = apply_flat_transform(0.0, 0.0, SetupType.BOTTOM, panel_h=0.0)
        assert math.isclose(y, 0.0)

    def test_very_large_coordinates(self) -> None:
        """No overflow or precision issues with large values."""
        x, y = apply_flat_transform(1e6, 1e6, SetupType.BOTTOM, panel_h=2e6)
        assert math.isclose(y, 1e6)

    def test_negative_coordinates_allowed(self) -> None:
        """Transforms don't reject negative coords (domain validates, not transforms)."""
        x, y = apply_flat_transform(-10.0, -20.0, SetupType.BOTTOM, panel_h=100.0)
        assert math.isclose(x, -10.0)
        assert math.isclose(y, 120.0)

    def test_axis_count_boundary_3_vs_4(self) -> None:
        """axis_count=3 blocks; axis_count=4 allows (with verified profile)."""
        profile = _make_profile(certification=CertificationStatus.VERIFIED)
        assert validate_setup_for_profile(SetupType.LEFT_EDGE, profile, axis_count=3)
        assert not validate_setup_for_profile(SetupType.LEFT_EDGE, profile, axis_count=4)

    def test_default_axis_count_is_3(self) -> None:
        """validate_setup_for_profile defaults to axis_count=3 (conservative)."""
        profile = _make_profile(certification=CertificationStatus.VERIFIED)
        errors = validate_setup_for_profile(SetupType.LEFT_EDGE, profile)
        assert len(errors) == 1  # blocked as 3-axis by default
