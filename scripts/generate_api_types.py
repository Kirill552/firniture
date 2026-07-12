#!/usr/bin/env python3
"""
Generate web/src/lib/api/generated.ts from tests/fixtures/openapi_snapshot.json.

Converts OpenAPI 3.x schemas to TypeScript interfaces and type aliases.
Resolves $ref, converts anyOf unions, and produces valid TypeScript syntax.

Usage:
    python scripts/generate_api_types.py
    python scripts/generate_api_types.py --check  # dry-run, exits 1 if diff
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = ROOT / "tests" / "fixtures" / "openapi_snapshot.json"
OUTPUT_PATH = ROOT / "web" / "src" / "lib" / "api" / "generated.ts"

# ---------------------------------------------------------------------------
# Schema → TypeScript type resolution
# ---------------------------------------------------------------------------


def resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref like '#/components/schemas/Foo' within the spec."""
    parts = ref.lstrip("#/").split("/")
    node = spec
    for p in parts:
        node = node[p]
    return node


def schema_to_ts(spec: dict, schema: dict, depth: int = 0) -> str:
    """Convert an OpenAPI schema node to a TypeScript type string."""

    # $ref
    if "$ref" in schema:
        resolved = resolve_ref(spec, schema["$ref"])
        ref_name = schema["$ref"].split("/")[-1]
        # If it's an enum type alias, use it directly
        if "enum" in resolved and resolved.get("type") == "string":
            return ref_name
        return ref_name

    # anyOf — nullable or union
    if "anyOf" in schema:
        variants = schema["anyOf"]
        # Check if it's a nullable pattern: [T, null]
        non_null = [v for v in variants if v.get("type") != "null"]
        has_null = any(v.get("type") == "null" for v in variants)

        if len(non_null) == 1:
            inner = schema_to_ts(spec, non_null[0], depth)
            if has_null:
                return f"{inner} | null"
            return inner

        # Multiple non-null variants → union
        parts = [schema_to_ts(spec, v, depth) for v in non_null]
        result = " | ".join(parts)
        if has_null:
            result += " | null"
        return result

    # oneOf / anyOf with multiple refs
    if "oneOf" in schema:
        parts = [schema_to_ts(spec, v, depth) for v in schema["oneOf"]]
        return " | ".join(parts)

    # allOf — intersection (rare, but handle)
    if "allOf" in schema:
        parts = [schema_to_ts(spec, v, depth) for v in schema["allOf"]]
        return " & ".join(parts)

    # Enum (string)
    if "enum" in schema and schema.get("type") == "string":
        vals = " | ".join(f"'{v}'" for v in schema["enum"])
        return vals

    # Array
    if schema.get("type") == "array":
        items = schema.get("items", {})
        # prefixItems tuple (DXFJobResponse.sheet_size)
        if "prefixItems" in schema:
            tuple_types = [schema_to_ts(spec, item, depth) for item in schema["prefixItems"]]
            return "[" + ", ".join(tuple_types) + "]"
        inner = schema_to_ts(spec, items, depth + 1)
        if depth > 0:
            return f"({inner})[]"
        return f"{inner}[]"

    # Object with additionalProperties
    if schema.get("type") == "object" and "additionalProperties" in schema:
        val_type = schema.get("additionalProperties", True)
        if val_type is True or val_type == {}:
            return "Record<string, unknown>"
        inner = schema_to_ts(spec, val_type, depth + 1)
        return f"Record<string, {inner}>"

    # Primitive types
    type_map = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }
    t = schema.get("type")
    if t in type_map:
        return type_map[t]

    # Fallback
    return "unknown"


def enum_type_name(name: str) -> str:
    """Check if a schema is a pure enum that should be a type alias."""
    return name


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------


def generate(spec: dict) -> str:
    """Generate TypeScript source from an OpenAPI spec dict."""
    schemas = spec.get("components", {}).get("schemas", {})
    paths = spec.get("paths", {})

    lines: list[str] = []

    # Header
    lines.append("/**")
    lines.append(" * Auto-generated API contract from OpenAPI snapshot.")
    lines.append(" * Source: tests/fixtures/openapi_snapshot.json")
    lines.append(" * DO NOT EDIT MANUALLY — regenerate with:")
    lines.append(" *   python scripts/generate_api_types.py")
    lines.append(" *")
    lines.append(" * Drift detected? Update snapshot:")
    lines.append(" *   MOCK_MODE=true pytest tests/test_openapi_contract.py --update-snapshot")
    lines.append(" */")
    lines.append("")

    # --- Enums (type aliases) ---
    enum_schemas = {}
    object_schemas = {}
    for name, schema in schemas.items():
        if "enum" in schema and schema.get("type") == "string":
            enum_schemas[name] = schema
        else:
            object_schemas[name] = schema

    if enum_schemas:
        lines.append("// Enums")
        lines.append("")
        for name in sorted(enum_schemas):
            vals = " | ".join(f"'{v}'" for v in enum_schemas[name]["enum"])
            lines.append(f"export type {name} = {vals}")
            lines.append("")

    # --- Schema interfaces ---
    lines.append("// Schema interfaces")
    lines.append("")

    for name in sorted(object_schemas):
        schema = object_schemas[name]

        # Skip composition types that are just $ref wrappers
        if "$ref" in schema and len(schema) <= 2:
            continue

        # Interface or type?
        has_properties = "properties" in schema
        has_allOf = "allOf" in schema
        has_oneOf = "oneOf" in schema
        has_anyOf = "anyOf" in schema

        desc = schema.get("description", "")
        if desc:
            lines.append(f"/** {name} — {desc} */")
        else:
            lines.append(f"/** {name} */")

        if has_properties:
            # Object interface
            required_fields = set(schema.get("required", []))
            lines.append(f"export interface {name} {{")

            for prop_name, prop_schema in schema["properties"].items():
                # JSDoc for property
                prop_desc = prop_schema.get("description", "")
                if prop_desc:
                    lines.append(f"  /** {prop_desc} */")

                # Resolve the type
                ts_type = schema_to_ts(spec, prop_schema)

                # Check for default — makes field optional if default exists
                has_default = "default" in prop_schema
                optional = "?" if prop_name not in required_fields or has_default else ""

                # Escape property names that are not valid JS identifiers
                safe_name = prop_name if re.match(r"^[a-zA-Z_$][a-zA-Z0-9_$]*$", prop_name) else f'"{prop_name}"'

                lines.append(f"  {safe_name}{optional}: {ts_type}")

            lines.append("}")
            lines.append("")

        elif has_allOf:
            # Intersection type
            parts = [schema_to_ts(spec, v) for v in schema["allOf"]]
            lines.append(f"export type {name} = {' & '.join(parts)}")
            lines.append("")

        elif has_oneOf or has_anyOf:
            # Union type
            variants = schema.get("oneOf") or schema.get("anyOf", [])
            parts = [schema_to_ts(spec, v) for v in variants]
            lines.append(f"export type {name} = {' | '.join(parts)}")
            lines.append("")

        elif schema.get("type") in ("string", "integer", "number", "boolean"):
            # Simple type alias
            ts_type = schema_to_ts(spec, schema)
            lines.append(f"export type {name} = {ts_type}")
            lines.append("")

    # --- API endpoint contracts ---
    lines.append("// API endpoint contracts")
    lines.append("")

    for path_key in sorted(paths.keys()):
        methods = paths[path_key]
        for method in ("get", "post", "put", "patch", "delete"):
            if method not in methods:
                continue
            endpoint = methods[method]
            op_id = endpoint.get("operationId", "")
            summary = endpoint.get("summary", path_key)

            if not op_id:
                continue

            lines.append(f"/** {method.upper()} {path_key} - {summary} */")
            lines.append(f"export interface {op_id} {{")

            # Path parameters
            for param in endpoint.get("parameters", []):
                if param.get("in") == "path":
                    param_type = schema_to_ts(spec, param.get("schema", {}))
                    lines.append(f"  {param['name']}: {param_type}")

            # Request body
            request_body = endpoint.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                body_schema = json_content.get("schema", {})
                if body_schema:
                    body_type = schema_to_ts(spec, body_schema)
                    lines.append(f"  body: {body_type}")

            # Response
            responses = endpoint.get("responses", {})
            resp_200 = responses.get("200") or responses.get("201", {})
            resp_content = resp_200.get("content", {})
            resp_json = resp_content.get("application/json", {})
            resp_schema = resp_json.get("schema", {})

            if resp_schema:
                resp_type = schema_to_ts(spec, resp_schema)
            else:
                # No response schema — mark as void
                resp_type = "void"

            lines.append(f"  response: {resp_type}")
            lines.append("}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate TypeScript types from OpenAPI snapshot")
    parser.add_argument("--check", action="store_true", help="Dry-run: exit 1 if output would differ")
    args = parser.parse_args()

    if not SNAPSHOT_PATH.exists():
        print(f"ERROR: Snapshot not found at {SNAPSHOT_PATH}", file=sys.stderr)
        return 1

    spec = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    output = generate(spec)

    if args.check:
        if OUTPUT_PATH.exists():
            existing = OUTPUT_PATH.read_text(encoding="utf-8")
            if existing == output:
                print("OK: generated.ts matches snapshot")
                return 0
            else:
                print("DIFF: generated.ts differs from snapshot output", file=sys.stderr)
                return 1
        else:
            print("MISSING: generated.ts does not exist", file=sys.stderr)
            return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
