"""Failing tests for coordinate transforms and canonical serialization.

TDD RED phase — все тесты падают до реализации.
"""
from __future__ import annotations

import hashlib
import json
import math

# ---------------------------------------------------------------------------
# Coordinate transforms
# ---------------------------------------------------------------------------

class TestFaceLocalToPanel:
    """Convert face-local (x, y) to canonical panel-level coordinates."""

    def test_front_face_unchanged(self):
        """FRONT face: local coords == panel coords."""
        from api.manufacturing.contracts import Face
        from api.manufacturing.coordinates import face_to_panel
        x, y = face_to_panel(Face.FRONT, 50.0, 100.0, panel_w=600, panel_h=720, thickness=16)
        assert math.isclose(x, 50.0)
        assert math.isclose(y, 100.0)

    def test_back_face_mirror_x(self):
        """BACK face: x mirrored across panel width."""
        from api.manufacturing.contracts import Face
        from api.manufacturing.coordinates import face_to_panel
        x, y = face_to_panel(Face.BACK, 50.0, 100.0, panel_w=600, panel_h=720, thickness=16)
        assert math.isclose(x, 550.0)  # 600 - 50
        assert math.isclose(y, 100.0)

    def test_left_face_swap_and_use_thickness(self):
        """LEFT face: local x → panel y offset, local y becomes panel x at x=0."""
        from api.manufacturing.contracts import Face
        from api.manufacturing.coordinates import face_to_panel
        x, y = face_to_panel(Face.LEFT, 5.0, 100.0, panel_w=600, panel_h=720, thickness=16)
        # LEFT face: x is depth into panel (ignored), y maps to panel y
        assert math.isclose(x, 0.0)
        assert math.isclose(y, 100.0)

    def test_right_face_at_width(self):
        """RIGHT face: y maps to panel y, at x = panel_w."""
        from api.manufacturing.contracts import Face
        from api.manufacturing.coordinates import face_to_panel
        x, y = face_to_panel(Face.RIGHT, 5.0, 100.0, panel_w=600, panel_h=720, thickness=16)
        assert math.isclose(x, 600.0)
        assert math.isclose(y, 100.0)

    def test_top_face_at_height(self):
        """TOP face: x maps to panel x, y at panel_h."""
        from api.manufacturing.contracts import Face
        from api.manufacturing.coordinates import face_to_panel
        x, y = face_to_panel(Face.TOP, 50.0, 3.0, panel_w=600, panel_h=720, thickness=16)
        assert math.isclose(x, 50.0)
        assert math.isclose(y, 720.0)

    def test_bottom_face_at_zero(self):
        """BOTTOM face: x maps to panel x, y at 0."""
        from api.manufacturing.contracts import Face
        from api.manufacturing.coordinates import face_to_panel
        x, y = face_to_panel(Face.BOTTOM, 50.0, 3.0, panel_w=600, panel_h=720, thickness=16)
        assert math.isclose(x, 50.0)
        assert math.isclose(y, 0.0)


class TestPanelToGcode:
    """Convert canonical panel coords to G-code XY."""

    def test_simple_offset(self):
        from api.manufacturing.coordinates import panel_to_gcode
        x, y = panel_to_gcode(50.0, 100.0, offset_x=0, offset_y=0)
        assert math.isclose(x, 50.0)
        assert math.isclose(y, 100.0)

    def test_with_offsets(self):
        from api.manufacturing.coordinates import panel_to_gcode
        x, y = panel_to_gcode(50.0, 100.0, offset_x=200.0, offset_y=300.0)
        assert math.isclose(x, 250.0)
        assert math.isclose(y, 400.0)


class TestGcodeToPanel:
    """Convert G-code XY back to canonical panel coords."""

    def test_inverse_of_panel_to_gcode(self):
        from api.manufacturing.coordinates import gcode_to_panel, panel_to_gcode
        orig_x, orig_y = 150.0, 220.0
        ox, oy = 200.0, 300.0
        gx, gy = panel_to_gcode(orig_x, orig_y, offset_x=ox, offset_y=oy)
        px, py = gcode_to_panel(gx, gy, offset_x=ox, offset_y=oy)
        assert math.isclose(px, orig_x)
        assert math.isclose(py, orig_y)


class TestMirrorOperation:
    """Mirror operation across a face."""

    def test_mirror_x(self):
        from api.manufacturing.contracts import DrillOperation, Face
        from api.manufacturing.coordinates import mirror_operation_x
        op = DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=5)
        mirrored = mirror_operation_x(op, panel_w=600)
        assert math.isclose(mirrored.x_mm, 550.0)
        assert math.isclose(mirrored.y_mm, 100.0)
        assert mirrored.id == "d1"

    def test_mirror_y(self):
        from api.manufacturing.contracts import DrillOperation, Face
        from api.manufacturing.coordinates import mirror_operation_y
        op = DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=5)
        mirrored = mirror_operation_y(op, panel_h=720)
        assert math.isclose(mirrored.x_mm, 50.0)
        assert math.isclose(mirrored.y_mm, 620.0)


class TestRotateOperation:
    """Rotate operation 90° clockwise around panel center."""

    def test_rotate_90_cw(self):
        from api.manufacturing.contracts import DrillOperation, Face
        from api.manufacturing.coordinates import rotate_operation_cw
        op = DrillOperation(id="d1", face=Face.FRONT, x_mm=0, y_mm=0, diameter_mm=5, depth_mm=5)
        rotated = rotate_operation_cw(op, panel_w=100, panel_h=200)
        # (0,0) rotated 90° CW (CNC y-down) around (50,100) → (150, 50)
        assert math.isclose(rotated.x_mm, 150.0)
        assert math.isclose(rotated.y_mm, 50.0)
# ---------------------------------------------------------------------------
# Canonical serialization / SHA-256
# ---------------------------------------------------------------------------

class TestCanonicalSerialization:
    """Deterministic JSON serialization for hashing."""

    def test_deterministic_output(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        from api.manufacturing.coordinates import canonical_json
        spec = ManufacturingSpec(
            panels=[PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16)],
        )
        a = canonical_json(spec)
        b = canonical_json(spec)
        assert a == b
        assert isinstance(a, str)

    def test_sorted_keys(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        from api.manufacturing.coordinates import canonical_json
        spec = ManufacturingSpec(
            panels=[PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16)],
        )
        s = canonical_json(spec)
        # Keys should be sorted — check a couple
        idx_id = s.find('"id"')
        idx_w = s.find('"width_mm"')
        if idx_id >= 0 and idx_w >= 0:
            assert idx_id < idx_w  # 'id' sorts before 'width_mm'

    def test_no_whitespace(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        from api.manufacturing.coordinates import canonical_json
        spec = ManufacturingSpec(
            panels=[PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16)],
        )
        s = canonical_json(spec)
        assert "\n" not in s
        assert "  " not in s

    def test_different_spec_different_json(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        from api.manufacturing.coordinates import canonical_json
        spec_a = ManufacturingSpec(panels=[PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16)])
        spec_b = ManufacturingSpec(panels=[PanelSpec(id="p2", width_mm=600, height_mm=720, thickness_mm=16)])
        assert canonical_json(spec_a) != canonical_json(spec_b)


class TestSha256:
    """SHA-256 hash of canonical serialization."""

    def test_returns_hex_string(self):
        from api.manufacturing.contracts import ManufacturingSpec
        from api.manufacturing.coordinates import spec_hash
        h = spec_hash(ManufacturingSpec(panels=[]))
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        from api.manufacturing.contracts import ManufacturingSpec
        from api.manufacturing.coordinates import spec_hash
        spec = ManufacturingSpec(panels=[])
        assert spec_hash(spec) == spec_hash(spec)

    def test_matches_manual_hash(self):
        from api.manufacturing.contracts import ManufacturingSpec
        from api.manufacturing.coordinates import canonical_json, spec_hash
        spec = ManufacturingSpec(panels=[])
        expected = hashlib.sha256(canonical_json(spec).encode("utf-8")).hexdigest()
        assert spec_hash(spec) == expected

    def test_different_spec_different_hash(self):
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
        from api.manufacturing.coordinates import spec_hash
        spec_a = ManufacturingSpec(panels=[PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=16)])
        spec_b = ManufacturingSpec(panels=[PanelSpec(id="p1", width_mm=600, height_mm=720, thickness_mm=18)])
        assert spec_hash(spec_a) != spec_hash(spec_b)


class TestRoundtripSpec:
    """Serialize → deserialize roundtrip preserves data."""

    def test_json_roundtrip(self):
        from api.manufacturing.contracts import (
            DrillOperation,
            Face,
            ManufacturingSpec,
            PanelSpec,
            SlotOperation,
        )
        from api.manufacturing.coordinates import canonical_json
        spec = ManufacturingSpec(
            panels=[
                PanelSpec(
                    id="p1", width_mm=600, height_mm=720, thickness_mm=16, material="ЛДСП",
                    operations=[
                        DrillOperation(id="d1", face=Face.FRONT, x_mm=50, y_mm=100, diameter_mm=5, depth_mm=12),
                        SlotOperation(id="s1", face=Face.BACK, x_mm=20, y_mm=0, length_mm=200, width_mm=4, depth_mm=10),
                    ],
                ),
            ],
        )
        s = canonical_json(spec)
        data = json.loads(s)
        assert data["panels"][0]["id"] == "p1"
        assert len(data["panels"][0]["operations"]) == 2
