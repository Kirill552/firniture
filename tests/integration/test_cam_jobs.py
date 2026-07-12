"""Integration tests for CAM job worker — Task 9 ManufacturingSpec path.

Verifies:
1. Worker imports spec_to_gcode_paths (NOT extract_all_from_dxf in production).
2. Worker does NOT call extract_all_from_dxf in production.
3. When typed-path imports are unavailable, worker raises Russian migration error.
4. GCODE generation via ManufacturingSpec produces valid output.
5. Worker fail-closed when ManufacturingSpec not in context.
6. cut_depth from context/profile is propagated to all contour paths.

No routes, no DB, no Redis — focused on the generation logic only.
"""

from __future__ import annotations

import ast
import warnings
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Worker source code never calls dxf_to_gcode
# ---------------------------------------------------------------------------


class TestWorkerNoLegacyDxfPaths:
    """Worker source must not use extract_all_from_dxf or dxf_to_gcode in production."""

    def test_no_dxf_to_gcode_import(self) -> None:
        """api/worker.py does not import dxf_to_gcode."""
        src = Path("api/worker.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "gcode_generator" in node.module
            ):
                imported_names = {alias.name for alias in node.names}
                assert "dxf_to_gcode" not in imported_names, (
                    "worker.py still imports dxf_to_gcode — Task 9 regression"
                )

    def test_no_extract_all_from_dxf_import(self) -> None:
        """api/worker.py does not import extract_all_from_dxf."""
        src = Path("api/worker.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "gcode_generator" in node.module
            ):
                imported_names = {alias.name for alias in node.names}
                assert "extract_all_from_dxf" not in imported_names, (
                    "worker.py still imports extract_all_from_dxf — Task 9 regression"
                )

    def test_no_extract_all_from_dxf_call(self) -> None:
        """api/worker.py source does not call extract_all_from_dxf()."""
        src = Path("api/worker.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                assert name != "extract_all_from_dxf", (
                    "worker.py still calls extract_all_from_dxf() — Task 9 regression"
                )

    def test_worker_imports_spec_to_gcode_paths(self) -> None:
        """api/worker.py imports spec_to_gcode_paths and GCodeGenerator."""
        src = Path("api/worker.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        imported_symbols: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "gcode_generator" in node.module
            ):
                imported_symbols.update(alias.name for alias in node.names)

        assert "spec_to_gcode_paths" in imported_symbols, (
            "worker.py must import spec_to_gcode_paths for ManufacturingSpec path"
        )
        assert "GCodeGenerator" in imported_symbols, (
            "worker.py must import GCodeGenerator for typed path"
        )

    def test_no_dxf_to_gcode_call(self) -> None:
        """api/worker.py source does not contain a dxf_to_gcode(...) call."""
        src = Path("api/worker.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                assert name != "dxf_to_gcode", (
                    "worker.py still calls dxf_to_gcode() — Task 9 regression"
                )


# ---------------------------------------------------------------------------
# 2. spec_to_gcode_paths produces valid G-code (unit-level contract)
# ---------------------------------------------------------------------------


class TestSpecToGcodePaths:
    """spec_to_gcode_paths → GCodeGenerator.generate_from_paths pipeline."""

    def test_spec_to_gcode_paths_generates_gcode(self) -> None:
        """spec_to_gcode_paths converts ManufacturingSpec to valid G-code."""
        from api.gcode_generator import (
            GCodeGenerator,
            MachineProfile,
            spec_to_gcode_paths,
        )
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec

        spec = ManufacturingSpec(
            spec_version="1.0",
            panels=[
                PanelSpec(id="p1", width_mm=600, height_mm=400, thickness_mm=16),
            ],
        )

        result = spec_to_gcode_paths(spec, cut_depth=18.0)

        profile = MachineProfile(name="test", machine_type="test")
        generator = GCodeGenerator(profile)
        gcode = generator.generate_from_paths(
            paths=result.paths,
            holes=result.holes,
            arcs=result.arcs,
            slots=result.slots,
        )

        assert isinstance(gcode, str)
        assert len(gcode) > 0
        assert "G00" in gcode or "G01" in gcode
        # Contour must produce cutting moves
        assert "G01" in gcode, "spec_to_gcode_paths must produce linear cutting moves"

    def test_spec_to_gcode_paths_with_drill_operations(self) -> None:
        """spec_to_gcode_paths extracts DrillOperations as DrillPoints."""
        from api.gcode_generator import (
            GCodeGenerator,
            MachineProfile,
            spec_to_gcode_paths,
        )
        from api.manufacturing.contracts import (
            DrillOperation,
            Face,
            ManufacturingSpec,
            PanelSpec,
        )

        spec = ManufacturingSpec(
            spec_version="1.0",
            panels=[
                PanelSpec(
                    id="p1",
                    width_mm=600,
                    height_mm=400,
                    thickness_mm=16,
                    operations=[
                        DrillOperation(
                            id="d1",
                            face=Face.FRONT,
                            x_mm=50.0,
                            y_mm=25.0,
                            diameter_mm=8.0,
                            depth_mm=12.0,
                        ),
                    ],
                ),
            ],
        )

        result = spec_to_gcode_paths(spec, cut_depth=18.0)
        assert len(result.holes) == 1
        assert result.holes[0].diameter == 8.0
        assert result.holes[0].depth == 12.0

        profile = MachineProfile(name="test", machine_type="test")
        generator = GCodeGenerator(profile)
        gcode = generator.generate_from_paths(
            paths=result.paths,
            holes=result.holes,
            arcs=result.arcs,
            slots=result.slots,
        )

        # Must include drilling cycle
        assert "G81" in gcode or "G82" in gcode or "G83" in gcode, (
            "spec_to_gcode_paths must produce drilling cycles for DrillOperations"
        )

    def test_cut_depth_propagated_to_all_contour_paths(self) -> None:
        """Custom cut_depth is applied to every contour path, not ignored."""
        from api.gcode_generator import (
            GCodeGenerator,
            MachineProfile,
            spec_to_gcode_paths,
        )
        from api.manufacturing.contracts import ManufacturingSpec, PanelSpec

        CUSTOM_DEPTH = 12.5

        spec = ManufacturingSpec(
            spec_version="1.0",
            panels=[
                PanelSpec(id="p1", width_mm=600, height_mm=400, thickness_mm=16),
                PanelSpec(id="p2", width_mm=300, height_mm=200, thickness_mm=16),
            ],
        )

        result = spec_to_gcode_paths(spec, cut_depth=CUSTOM_DEPTH)

        # Every contour path must carry the requested depth
        for path in result.paths:
            assert path.depth == CUSTOM_DEPTH, (
                f"Path depth {path.depth} != requested cut_depth {CUSTOM_DEPTH}"
            )

        # Verify G-code reflects the custom depth in the comment
        profile = MachineProfile(name="test", machine_type="test")
        generator = GCodeGenerator(profile)
        gcode = generator.generate_from_paths(
            paths=result.paths,
            holes=result.holes,
            arcs=result.arcs,
            slots=result.slots,
        )

        assert f"depth={CUSTOM_DEPTH}mm" in gcode, (
            f"G-code must contain comment with requested depth {CUSTOM_DEPTH}mm"
        )


# ---------------------------------------------------------------------------
# 3. Worker fail-closed when imports unavailable
# ---------------------------------------------------------------------------


class TestWorkerFailClosed:
    """Worker raises Russian error when G-code generator is unavailable."""

    @pytest.mark.asyncio
    async def test_unavailable_raises_runtime_error(self) -> None:
        """When GCODE_GENERATOR_AVAILABLE is False, process_job raises."""
        from api.worker import process_job

        payload = {
            "job_id": "test-fail-closed",
            "job_kind": "GCODE",
            "context": {
                "manufacturing_spec": {"spec_version": "1.0", "panels": []},
            },
        }

        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        with patch("api.worker.GCODE_GENERATOR_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Генератор G-code недоступен"):
                await process_job(session, payload)

    @pytest.mark.asyncio
    async def test_missing_manufacturing_spec_raises_value_error(self) -> None:
        """Worker raises ValueError when manufacturing_spec not in context."""
        from api.worker import process_job

        payload = {
            "job_id": "test-no-spec",
            "job_kind": "GCODE",
            "context": {
                # No manufacturing_spec key
            },
        }

        session = AsyncMock()

        with pytest.raises(ValueError, match="ManufacturingSpec не передан"):
            await process_job(session, payload)

    @pytest.mark.asyncio
    async def test_invalid_manufacturing_spec_raises_value_error(self) -> None:
        """Worker raises ValueError when ManufacturingSpec is invalid."""
        from api.worker import process_job

        payload = {
            "job_id": "test-invalid-spec",
            "job_kind": "GCODE",
            "context": {
                "manufacturing_spec": {
                    "spec_version": "",  # Empty version — invalid
                    "panels": [],
                },
            },
        }

        session = AsyncMock()

        with pytest.raises(ValueError, match="Невалидный ManufacturingSpec"):
            await process_job(session, payload)


# ---------------------------------------------------------------------------
# 4. Regression: dxf_to_gcode still exists but is unused by worker
# ---------------------------------------------------------------------------


class TestDeprecatedFunctionStillExists:
    """dxf_to_gcode remains importable for backward compat, but worker doesn't use it."""

    def test_dxf_to_gcode_importable(self) -> None:
        """dxf_to_gcode is still a callable in gcode_generator."""
        from api.gcode_generator import dxf_to_gcode

        assert callable(dxf_to_gcode)

    def test_dxf_to_gcode_emits_warning(self) -> None:
        """Calling dxf_to_gcode triggers DeprecationWarning."""
        from api.gcode_generator import dxf_to_gcode

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                dxf_to_gcode(b"not-a-dxf")
            except Exception:
                pass

            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) >= 1, "dxf_to_gcode() must emit DeprecationWarning"


# ---------------------------------------------------------------------------
# 5. Task 9 direct-spec: fail-closed on missing profile / provenance
# ---------------------------------------------------------------------------


class TestDirectSpecFailClosed:
    """Worker must fail-closed when authoritative context is missing."""

    @pytest.mark.asyncio
    async def test_missing_machine_profile_raises(self) -> None:
        """GCODE job without machine_profile in context → fail-closed."""
        from api.worker import process_job

        payload = {
            "job_id": "test-no-profile",
            "job_kind": "GCODE",
            "context": {
                "manufacturing_spec": {"spec_version": "1.0", "panels": []},
                # machine_profile intentionally omitted
            },
        }

        session = AsyncMock()

        with pytest.raises(ValueError, match="machine_profile не передан"):
            await process_job(session, payload)

    @pytest.mark.asyncio
    async def test_unknown_machine_profile_raises(self) -> None:
        """GCODE job with unrecognized profile name → fail-closed."""
        from api.worker import process_job

        payload = {
            "job_id": "test-unknown-profile",
            "job_kind": "GCODE",
            "context": {
                "manufacturing_spec": {"spec_version": "1.0", "panels": []},
                "machine_profile": "nonexistent_brand",
            },
        }

        session = AsyncMock()

        with pytest.raises(ValueError, match="Неизвестный machine_profile"):
            await process_job(session, payload)

    @pytest.mark.asyncio
    async def test_cut_depth_from_context_is_used(self) -> None:
        """cut_depth from context is propagated to spec_to_gcode_paths, not ignored."""
        from api.worker import process_job

        payload = {
            "job_id": "test-cut-depth",
            "job_kind": "GCODE",
            "context": {
                "manufacturing_spec": {"spec_version": "1.0", "panels": []},
                "machine_profile": "weihong",
                "cut_depth": 15.5,
            },
        }

        session = AsyncMock()
        storage_patch = patch("api.worker.ObjectStorage")

        with storage_patch as mock_storage_cls:
            mock_storage = mock_storage_cls.return_value
            mock_storage.ensure_bucket = MagicMock()
            mock_storage.put_object = MagicMock()

            with patch("api.worker.spec_to_gcode_paths") as mock_spec:
                from api.gcode_generator import DXFExtractResult

                mock_spec.return_value = DXFExtractResult(paths=[], holes=[], arcs=[], slots=[])

                with patch("api.worker.GCodeGenerator") as mock_gen_cls:
                    mock_gen = mock_gen_cls.return_value
                    mock_gen.generate_from_paths.return_value = "(G-code stub)"

                    await process_job(session, payload)

            # Verify spec_to_gcode_paths received the explicit cut_depth
            mock_spec.assert_called_once()
            call_kwargs = mock_spec.call_args
            assert call_kwargs[1].get("cut_depth") == 15.5 or call_kwargs[0][1] == 15.5, (
                f"spec_to_gcode_paths called with {call_kwargs}, expected cut_depth=15.5"
            )

    @pytest.mark.asyncio
    async def test_machine_profile_from_context_not_defaulted(self) -> None:
        """Worker uses the explicit machine_profile from context, not a silent default."""
        from api.worker import process_job

        payload = {
            "job_id": "test-profile-provenance",
            "job_kind": "GCODE",
            "context": {
                "manufacturing_spec": {"spec_version": "1.0", "panels": []},
                "machine_profile": "fanuc",
            },
        }

        session = AsyncMock()
        storage_patch = patch("api.worker.ObjectStorage")

        with storage_patch as mock_storage_cls:
            mock_storage = mock_storage_cls.return_value
            mock_storage.ensure_bucket = MagicMock()
            mock_storage.put_object = MagicMock()

            with patch("api.worker.spec_to_gcode_paths") as mock_spec:
                from api.gcode_generator import DXFExtractResult

                mock_spec.return_value = DXFExtractResult(paths=[], holes=[], arcs=[], slots=[])

                with patch("api.worker.GCodeGenerator") as mock_gen_cls:
                    mock_gen = mock_gen_cls.return_value
                    mock_gen.generate_from_paths.return_value = "(G-code stub)"

                    await process_job(session, payload)

            # GCodeGenerator must have been called with fanuc profile (not weihong default)
            mock_gen_cls.assert_called_once()
            created_profile = mock_gen_cls.call_args[0][0]
            assert created_profile.machine_type.value == "fanuc", (
                f"Expected machine_type.value 'fanuc', got '{created_profile.machine_type.value}'"
            )

    def test_worker_source_has_no_extract_all_from_dxf(self) -> None:
        """Worker source code contains zero extract_all_from_dxf references (behavioral regression)."""
        import ast

        source = Path(__file__).resolve().parent.parent.parent / "api" / "worker.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "extract_all_from_dxf":
                pytest.fail(
                    "worker.py references extract_all_from_dxf — "
                    "deprecated DXF path must not exist in production GCODE branch"
                )
            if isinstance(node, ast.Attribute) and node.attr == "extract_all_from_dxf":
                pytest.fail(
                    "worker.py references extract_all_from_dxf — "
                    "deprecated DXF path must not exist in production GCODE branch"
                )
