"""Contract tests for Task 9 — artifact separation.

Separated artifact kinds:
  1. Cutting-map domain: Panel, SheetLayout, PlacedPanel, layout algorithms
     (zero ezdxf dependency — pure data + packing).
  2. DXF artifact: drawing generation in api.dxf_generator (uses ezdxf).
  3. G-code artifact: GCodeGenerator + IR in api.gcode_generator.
  4. Deprecated bridge: dxf_to_gcode emits DeprecationWarning.

Focused contract tests only — no routes, no models, no DB.
"""
from __future__ import annotations

import ast
import importlib
import sys
import warnings
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Cutting-map is ezdxf-free
# ---------------------------------------------------------------------------


class TestCuttingMapIsolation:
    """api.manufacturing.cutting_map must not import ezdxf."""

    def test_no_ezdxf_in_source(self) -> None:
        """AST scan confirms no ezdxf reference in cutting_map.py."""
        src = Path("api/manufacturing/cutting_map.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        ezdxf_refs: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "ezdxf" in alias.name:
                        ezdxf_refs.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and "ezdxf" in node.module:
                    ezdxf_refs.append(f"from {node.module}")

        assert not ezdxf_refs, (
            f"cutting_map.py must not import ezdxf, found: {ezdxf_refs}"
        )

    def test_module_loads_without_ezdxf(self) -> None:
        """cutting_map can be imported even when ezdxf is absent.

        We simulate ezdxf absence by temporarily removing it from sys.modules,
        then restore the original cutting_map module to preserve identity checks.
        """
        original_cm = sys.modules.get("api.manufacturing.cutting_map")
        ezdxf_modules = {
            k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("ezdxf")
        }
        try:
            if "api.manufacturing.cutting_map" in sys.modules:
                del sys.modules["api.manufacturing.cutting_map"]
            mod = importlib.import_module("api.manufacturing.cutting_map")
            assert hasattr(mod, "Panel")
            assert hasattr(mod, "SheetLayout")
            assert hasattr(mod, "PlacedPanel")
            assert hasattr(mod, "optimize_layout")
        finally:
            # Restore original module object to keep identity checks valid
            if original_cm is not None:
                sys.modules["api.manufacturing.cutting_map"] = original_cm
            else:
                sys.modules.pop("api.manufacturing.cutting_map", None)
            sys.modules.update(ezdxf_modules)


# ---------------------------------------------------------------------------
# 2. Cutting-map data types are usable independently
# ---------------------------------------------------------------------------


class TestCuttingMapTypes:
    """Panel, SheetLayout, PlacedPanel construction without DXF."""

    def test_panel_construction(self) -> None:
        from api.manufacturing.cutting_map import Panel

        p = Panel(id="p1", name=" Shelf", width_mm=600, height_mm=300)
        assert p.width_mm == 600
        assert p.height_mm == 300
        assert p.material == "ЛДСП"

    def test_panel_drilling_points(self) -> None:
        from api.manufacturing.cutting_map import Panel

        holes = [{"x": 50, "y": 37, "diameter": 5, "depth": 12}]
        p = Panel(id="p2", name="Side", width_mm=800, height_mm=400, drilling_points=holes)
        assert len(p.drilling_points) == 1
        assert p.drilling_points[0]["diameter"] == 5

    def test_placed_panel_construction(self) -> None:
        from api.manufacturing.cutting_map import PlacedPanel

        pp = PlacedPanel(name="Top", x=10, y=20, width_mm=600, height_mm=300, rotated=True)
        assert pp.rotated is True
        assert pp.x == 10

    def test_sheet_layout_utilization_alias(self) -> None:
        from api.manufacturing.cutting_map import SheetLayout

        layout = SheetLayout(
            sheet_width=2800,
            sheet_height=2070,
            placed_panels=[],
            unplaced_panels=[],
            utilization_percent=75.5,
        )
        assert layout.utilization == 75.5
        assert layout.utilization == layout.utilization_percent


# ---------------------------------------------------------------------------
# 3. Layout algorithms produce valid SheetLayout
# ---------------------------------------------------------------------------


class TestLayoutAlgorithms:
    """optimize_layout and _simple_layout produce well-formed SheetLayout."""

    def test_simple_layout_all_fit(self) -> None:
        from api.manufacturing.cutting_map import Panel, _simple_layout

        panels = [
            Panel(id="a", name="A", width_mm=200, height_mm=100),
            Panel(id="b", name="B", width_mm=200, height_mm=100),
        ]
        layout = _simple_layout(panels, sheet_width=2800, sheet_height=2070, gap_mm=3)

        assert layout.sheet_width == 2800
        assert len(layout.placed_panels) == 2
        assert len(layout.unplaced_panels) == 0
        assert layout.utilization_percent > 0

    def test_simple_layout_overflow(self) -> None:
        from api.manufacturing.cutting_map import Panel, _simple_layout

        big = Panel(id="big", name="Big", width_mm=3000, height_mm=2100)
        layout = _simple_layout([big], sheet_width=2800, sheet_height=2070, gap_mm=3)

        assert len(layout.placed_panels) == 0
        assert len(layout.unplaced_panels) == 1
        assert layout.utilization_percent == 0.0

    def test_optimize_layout_returns_sheet_layout(self) -> None:
        from api.manufacturing.cutting_map import Panel, SheetLayout, optimize_layout

        panels = [
            Panel(id="a", name="A", width_mm=400, height_mm=300),
            Panel(id="b", name="B", width_mm=400, height_mm=300),
            Panel(id="c", name="C", width_mm=400, height_mm=300),
        ]
        layout = optimize_layout(panels, sheet_width=2800, sheet_height=2070, gap_mm=3)

        assert isinstance(layout, SheetLayout)
        assert layout.sheet_width == 2800
        assert layout.utilization_percent > 0


# ---------------------------------------------------------------------------
# 4. DXF generator re-exports cutting-map types (backward compat)
# ---------------------------------------------------------------------------


class TestDxfGeneratorBackwardCompat:
    """api.dxf_generator re-exports Panel, SheetLayout, PlacedPanel."""

    def test_reexport_panel(self) -> None:
        from api.dxf_generator import Panel
        from api.manufacturing.cutting_map import Panel as CmPanel

        assert Panel is CmPanel

    def test_reexport_sheet_layout(self) -> None:
        from api.dxf_generator import SheetLayout
        from api.manufacturing.cutting_map import SheetLayout as CmSL

        assert SheetLayout is CmSL

    def test_reexport_placed_panel(self) -> None:
        from api.dxf_generator import PlacedPanel
        from api.manufacturing.cutting_map import PlacedPanel as CmPP

        assert PlacedPanel is CmPP

    def test_reexport_optimize_layout(self) -> None:
        from api.dxf_generator import optimize_layout
        from api.manufacturing.cutting_map import optimize_layout as cm_ol

        assert optimize_layout is cm_ol

    def test_reexport_optimize_layout_best(self) -> None:
        from api.dxf_generator import optimize_layout_best
        from api.manufacturing.cutting_map import optimize_layout_best as cm_olb

        assert optimize_layout_best is cm_olb


# ---------------------------------------------------------------------------
# 5. DXF artifact generation (contract — produces bytes)
# ---------------------------------------------------------------------------


class TestDxfArtifactGeneration:
    """generate_panel_dxf produces valid DXF bytes + layout."""

    def test_generate_produces_bytes_and_layout(self) -> None:
        from api.dxf_generator import Panel, SheetLayout, generate_panel_dxf

        panels = [
            Panel(id="p1", name="Shelf", width_mm=600, height_mm=300),
            Panel(id="p2", name="Side", width_mm=800, height_mm=400),
        ]
        data, layout = generate_panel_dxf(panels, sheet_size=(2800, 2070))

        assert isinstance(data, bytes)
        assert len(data) > 0
        assert isinstance(layout, SheetLayout)

    def test_single_panel_dxf(self) -> None:
        from api.dxf_generator import Panel, generate_single_panel_dxf

        panel = Panel(id="s1", name="Top", width_mm=1200, height_mm=600)
        data = generate_single_panel_dxf(panel)

        assert isinstance(data, bytes)
        assert len(data) > 0


# ---------------------------------------------------------------------------
# 6. G-code artifact generation (contract — produces string)
# ---------------------------------------------------------------------------


class TestGCodeArtifactGeneration:
    """GCodeGenerator produces valid G-code programs."""

    def test_generator_produces_string(self) -> None:
        from api.gcode_generator import GCodeGenerator

        gen = GCodeGenerator("weihong")
        result = gen.generate_from_paths(
            paths=[],
            holes=[],
            arcs=[],
            slots=[],
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_machine_profiles_available(self) -> None:
        from api.gcode_generator import MACHINE_PROFILES

        assert "weihong" in MACHINE_PROFILES
        assert "fanuc" in MACHINE_PROFILES


# ---------------------------------------------------------------------------
# 7. Deprecated dxf_to_gcode emits DeprecationWarning
# ---------------------------------------------------------------------------


class TestDxfToGCodeDeprecated:
    """dxf_to_gcode() emits DeprecationWarning (Task 9)."""

    def test_deprecation_warning_emitted(self) -> None:
        """Calling dxf_to_gcode triggers DeprecationWarning."""
        # We can't call it without a real DXF, but we can verify the warning
        # is wired up by checking the function source or by calling with
        # invalid data — the warning fires before parsing.
        from api.gcode_generator import dxf_to_gcode

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                dxf_to_gcode(b"not-a-dxf")
            except Exception:
                # Expected — DXF parsing fails, but warning should fire first
                pass

            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) >= 1, (
                "dxf_to_gcode() must emit DeprecationWarning"
            )
            assert "deprecated" in str(dep_warnings[0].message).lower()

    def test_still_callable(self) -> None:
        """dxf_to_gcode remains callable for backward compatibility."""
        from api.gcode_generator import dxf_to_gcode

        # Verify it's a callable, not removed
        assert callable(dxf_to_gcode)


# ---------------------------------------------------------------------------
# 8. Artifact kinds are mutually exclusive in import graph
# ---------------------------------------------------------------------------


class TestArtifactGraphSeparation:
    """Verify the separation boundary: cutting_map → DXF → G-code."""

    def test_cutting_map_no_dxf_imports(self) -> None:
        """cutting_map.py does not import dxf_generator or gcode_generator."""
        src = Path("api/manufacturing/cutting_map.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)

        forbidden = {"dxf_generator", "gcode_generator", "ezdxf"}
        found = forbidden & set(imported_modules)
        assert not found, (
            f"cutting_map.py must not import: {found}"
        )

    def test_dxf_generator_uses_cutting_map(self) -> None:
        """dxf_generator.py imports from cutting_map, not vice versa."""
        src = Path("api/dxf_generator.py").read_text(encoding="utf-8")
        assert "from api.manufacturing.cutting_map import" in src

    def test_gcode_generator_independent_of_cutting_map(self) -> None:
        """gcode_generator.py does not import cutting_map (independent domain)."""
        src = Path("api/gcode_generator.py").read_text(encoding="utf-8")
        assert "cutting_map" not in src
