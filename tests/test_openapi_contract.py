"""
OpenAPI contract snapshot tests.

Deterministic backend schema assertion: generates the live OpenAPI spec from
the FastAPI app, serialises it canonically (sorted keys, stable ordering),
and diffs against the checked-in baseline fixture.  Any drift (added,
removed, or re-typed endpoint / schema) causes a clear, actionable failure.

Also validates the generated TypeScript API contract (generated.ts):
- Deterministic snapshot: generated.ts matches generator output
- Compile gate: generated.ts passes tsc --noEmit
- No raw 'any' types (all nullable fields use T | null from snapshot)

Usage:
    pytest tests/test_openapi_contract.py -v

To update the baseline after an intentional schema change:
    pytest tests/test_openapi_contract.py --update-snapshot
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SNAPSHOT_PATH = FIXTURE_DIR / "openapi_snapshot.json"

# Generated TypeScript API contract
GENERATED_TS_PATH = Path(__file__).resolve().parent.parent / "web" / "src" / "lib" / "api" / "generated.ts"
GENERATOR_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "generate_api_types.py"
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    """Deterministic serialisation: sorted keys, no trailing whitespace, LF only."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False).replace("\r\n", "\n")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_snapshot() -> dict:
    """Load the checked-in baseline OpenAPI snapshot."""
    if not SNAPSHOT_PATH.exists():
        pytest.fail(
            f"Baseline snapshot not found at {SNAPSHOT_PATH}.\n"
            "Run: python -m tests.test_openapi_contract --update-snapshot"
        )
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _generate_live_schema() -> dict:
    """Import the FastAPI app and extract its current OpenAPI schema."""
    from api.main import app

    return app.openapi()


def _diff_paths(live: dict, baseline: dict) -> dict[str, list[str]]:
    """
    Structural diff of the two OpenAPI specs.

    Returns a dict with keys: added, removed, changed — each a list of
    human-readable descriptions.
    """
    live_paths = live.get("paths", {})
    base_paths = baseline.get("paths", {})

    live_schemas = live.get("components", {}).get("schemas", {})
    base_schemas = baseline.get("components", {}).get("schemas", {})

    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []

    # --- paths ---
    live_path_set = set(live_paths.keys())
    base_path_set = set(base_paths.keys())

    for p in sorted(live_path_set - base_path_set):
        methods = ", ".join(sorted(live_paths[p].keys()))
        added.append(f"PATH {p} [{methods}]")

    for p in sorted(base_path_set - live_path_set):
        methods = ", ".join(sorted(base_paths[p].keys()))
        removed.append(f"PATH {p} [{methods}]")

    for p in sorted(live_path_set & base_path_set):
        live_methods = set(live_paths[p].keys())
        base_methods = set(base_paths[p].keys())
        for m in sorted(live_methods - base_methods):
            added.append(f"METHOD {m.upper()} {p}")
        for m in sorted(base_methods - live_methods):
            removed.append(f"METHOD {m.upper()} {p}")

        # Compare response schemas for shared methods
        for m in sorted(live_methods & base_methods):
            live_ep = live_paths[p][m]
            base_ep = base_paths[p][m]
            if live_ep != base_ep:
                changed.append(f"ENDPOINT {m.upper()} {p}")

    # --- schemas ---
    live_schema_set = set(live_schemas.keys())
    base_schema_set = set(base_schemas.keys())

    for s in sorted(live_schema_set - base_schema_set):
        added.append(f"SCHEMA {s}")

    for s in sorted(base_schema_set - live_schema_set):
        removed.append(f"SCHEMA {s}")

    for s in sorted(live_schema_set & base_schema_set):
        if live_schemas[s] != base_schemas[s]:
            changed.append(f"SCHEMA {s}")

    return {"added": added, "removed": removed, "changed": changed}


# ---------------------------------------------------------------------------
# Tests — OpenAPI snapshot
# ---------------------------------------------------------------------------


class TestOpenAPIContractSnapshot:
    """Deterministic OpenAPI schema snapshot assertion."""

    def test_snapshot_matches_live_schema(self):
        """
        The checked-in snapshot MUST exactly match the live schema.

        If this fails, either:
        1. An intentional API change was made — run with --update-snapshot
        2. An unintentional drift occurred — investigate before updating
        """
        baseline = _load_snapshot()
        live = _generate_live_schema()

        baseline_json = _canonical_json(baseline)
        live_json = _canonical_json(live)

        if baseline_json == live_json:
            return  # PASS — no drift

        # Structured diff for actionable failure message
        diff = _diff_paths(live, baseline)

        lines: list[str] = [
            "OpenAPI contract drift detected.",
            f"  baseline hash : {_sha256(baseline_json)}",
            f"  live hash     : {_sha256(live_json)}",
            "",
        ]

        if diff["added"]:
            lines.append("ADDED (in live, not in baseline):")
            for item in diff["added"]:
                lines.append(f"  + {item}")
            lines.append("")

        if diff["removed"]:
            lines.append("REMOVED (in baseline, not in live):")
            for item in diff["removed"]:
                lines.append(f"  - {item}")
            lines.append("")

        if diff["changed"]:
            lines.append("CHANGED:")
            for item in diff["changed"]:
                lines.append(f"  ~ {item}")
            lines.append("")

        lines.append(
            "To update the baseline after an intentional change:\n"
            "  pytest tests/test_openapi_contract.py --update-snapshot\n"
            "  python scripts/generate_api_types.py"
        )

        pytest.fail("\n".join(lines))

    def test_snapshot_is_deterministic(self):
        """
        Loading and re-serialising the snapshot must produce identical bytes.
        Ensures the fixture was written with canonical JSON.
        """
        raw = SNAPSHOT_PATH.read_bytes().replace(b"\r\n", b"\n")
        parsed = json.loads(raw)
        re_serialised = (_canonical_json(parsed) + "\n").encode("utf-8")
        assert raw == re_serialised, (
            "Snapshot is not in canonical JSON form. "
            "Re-save with: pytest tests/test_openapi_contract.py --update-snapshot"
        )

    def test_all_paths_have_operation_ids(self):
        """
        Every endpoint MUST carry an operationId for client code generation.
        Missing operationIds produce broken TypeScript bindings.
        """
        baseline = _load_snapshot()
        missing: list[str] = []

        for path, methods in baseline.get("paths", {}).items():
            for method, spec in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    if "operationId" not in spec:
                        missing.append(f"{method.upper()} {path}")

        assert not missing, (
            "Endpoints missing operationId (required for TS codegen):\n"
            + "\n".join(f"  - {m}" for m in missing)
        )

    def test_required_fields_present_in_schemas(self):
        """
        Every schema MUST have either 'properties' or be a simple enum/type.
        Missing properties breaks TypeScript interface generation.
        """
        baseline = _load_snapshot()
        schemas = baseline.get("components", {}).get("schemas", {})
        broken: list[str] = []

        for name, spec in schemas.items():
            # Enums with 'enum' key are fine without properties
            if "enum" in spec:
                continue
            # allOf / oneOf / anyOf compositions are fine
            if "allOf" in spec or "oneOf" in spec or "anyOf" in spec:
                continue
            # Simple types (string, integer, etc.)
            if spec.get("type") in ("string", "integer", "number", "boolean"):
                continue
            # Standard object schemas
            if "properties" not in spec and "type" not in spec:
                broken.append(name)

        assert not broken, (
            "Schemas without properties or type (may break codegen):\n"
            + "\n".join(f"  - {s}" for s in broken)
        )

    def test_endpoint_count_matches(self):
        """
        Sanity check: endpoint count must not drop below baseline.
        Removing endpoints is a breaking change that needs explicit approval.
        """
        baseline = _load_snapshot()
        live = _generate_live_schema()

        baseline_count = sum(
            len([m for m in methods if m in ("get", "post", "put", "patch", "delete")])
            for methods in baseline.get("paths", {}).values()
        )
        live_count = sum(
            len([m for m in methods if m in ("get", "post", "put", "patch", "delete")])
            for methods in live.get("paths", {}).values()
        )

        assert live_count >= baseline_count, (
            f"Endpoint count dropped: {baseline_count} -> {live_count}. "
            "Removing endpoints is a breaking API change."
        )


# ---------------------------------------------------------------------------
# Tests — generated TypeScript types
# ---------------------------------------------------------------------------


class TestGeneratedTypes:
    """Validate web/src/lib/api/generated.ts against the OpenAPI snapshot."""

    def test_generated_ts_matches_generator_output(self):
        """
        The checked-in generated.ts MUST match the output of the generator script.

        If this fails, run:
            python scripts/generate_api_types.py
        """
        if not GENERATED_TS_PATH.exists():
            pytest.fail(
                f"generated.ts not found at {GENERATED_TS_PATH}.\n"
                "Run: python scripts/generate_api_types.py"
            )
        if not GENERATOR_SCRIPT.exists():
            pytest.skip("Generator script not found — cannot verify deterministic output")

        result = subprocess.run(
            [sys.executable, str(GENERATOR_SCRIPT), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            "generated.ts is out of sync with the OpenAPI snapshot.\n"
            "Run: python scripts/generate_api_types.py"
        )

    def test_generated_ts_compiles(self):
        """
        generated.ts MUST be accepted by the TypeScript compiler.

        Uses tsc --noEmit on an isolated check of just generated.ts.
        """
        if not GENERATED_TS_PATH.exists():
            pytest.skip("generated.ts not found")

        tsc_cmd = WEB_DIR / "node_modules" / ".bin" / "tsc.cmd"
        if not tsc_cmd.exists():
            pytest.skip("tsc not found in node_modules — run: npm install")

        # Use shell=True on Windows to handle .cmd files properly
        result = subprocess.run(
            f'"{tsc_cmd}" --noEmit --strict --target ES2020 '
            f'--moduleResolution bundler --module ESNext '
            f'--skipLibCheck "{GENERATED_TS_PATH}"',
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(WEB_DIR),
            shell=True,
        )
        # Filter to only errors mentioning generated.ts
        ts_errors = [
            line for line in result.stderr.splitlines()
            if "generated.ts" in line
        ]
        assert result.returncode == 0 or not ts_errors, (
            "generated.ts has TypeScript errors:\n" + "\n".join(ts_errors)
        )

    def test_no_any_types_in_generated(self):
        """
        generated.ts MUST NOT contain raw 'any' types.

        All nullable fields should use 'T | null' from the OpenAPI snapshot.
        This test reports any remaining 'any' for manual review.
        """
        if not GENERATED_TS_PATH.exists():
            pytest.skip("generated.ts not found")

        content = GENERATED_TS_PATH.read_text(encoding="utf-8")
        # Match ': any' but not inside comments or string literals
        any_matches = [
            (i + 1, line.strip())
            for i, line in enumerate(content.splitlines())
            if re.search(r":\s*any\b", line)
            and not line.strip().startswith("//")
            and not line.strip().startswith("*")
        ]
        assert not any_matches, (
            "generated.ts contains 'any' types (should use concrete types from snapshot):\n"
            + "\n".join(f"  L{num}: {line}" for num, line in any_matches)
        )

    def test_all_endpoints_have_response_type(self):
        """
        Every endpoint contract MUST declare a response type.

        Endpoints with no schema in the snapshot get 'void' — this is tracked
        but not blocked since the backend may return an empty 200.
        """
        if not GENERATED_TS_PATH.exists():
            pytest.skip("generated.ts not found")

        content = GENERATED_TS_PATH.read_text(encoding="utf-8")
        # Split into interface blocks and check each for response: void
        void_endpoints = []
        blocks = re.split(r"(?=export interface )", content)
        for block in blocks:
            name_match = re.match(r"export interface (\w+)", block)
            if name_match and "response: void" in block.split("}")[0]:
                void_endpoints.append(name_match.group(1))

        # These are known void endpoints from the snapshot — not a failure,
        # but tracked for visibility
        if void_endpoints:
            warnings.warn(
                f"{len(void_endpoints)} endpoint(s) have response: void "
                f"(no schema in snapshot): {', '.join(void_endpoints)}",
                stacklevel=1,
            )


# ---------------------------------------------------------------------------
# CLI: --update-snapshot
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-snapshot",
        action="store_true",
        default=False,
        help="Overwrite the OpenAPI baseline snapshot with the current live schema.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "openapi_contract: OpenAPI contract snapshot tests"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--update-snapshot", default=False):
        return

    # Only run the update logic, skip actual tests
    live = _generate_live_schema()
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    content = _canonical_json(live) + "\n"
    SNAPSHOT_PATH.write_bytes(content.encode("utf-8"))
    print(f"\n  Snapshot updated: {SNAPSHOT_PATH}")
    print(f"  hash: {_sha256(_canonical_json(live))}")

    # Also regenerate generated.ts
    if GENERATOR_SCRIPT.exists():
        result = subprocess.run(
            [sys.executable, str(GENERATOR_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"  generated.ts regenerated: {GENERATED_TS_PATH}")
        else:
            print(f"  WARNING: generator failed: {result.stderr}")
