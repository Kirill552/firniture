#!/usr/bin/env python3
"""Проверяет манифест релиза и разрешённые ссылки образов Compose."""

from __future__ import annotations

from collections import Counter
import json
import re
import sys
from typing import Any

SERVICES = ("api", "web", "worker")
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


def fail(message: str) -> None:
    print(f"release manifest: {message}", file=sys.stderr)
    raise SystemExit(1)


def reject_constant(value: str) -> None:
    raise ValueError(f"недопустимая константа JSON {value!r}")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"дублирующееся поле JSON {key!r}")
        result[key] = value
    return result


def field_from_mapping(mapping: object, names: tuple[str, ...]) -> object:
    if not isinstance(mapping, dict):
        return None
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def service_entry(manifest: dict[str, Any], service: str) -> object:
    for collection_name in ("images", "services"):
        entry = field_from_mapping(manifest.get(collection_name), (service,))
        if entry is not None:
            return entry
    return field_from_mapping(
        manifest,
        (f"{service}_image", f"{service}_image_ref", f"{service}_reference"),
    )


def approved_digest(manifest: dict[str, Any], service: str, entry: object) -> object:
    digest = field_from_mapping(entry, ("approved_digest", "image_digest", "digest"))
    if digest is not None:
        return digest
    for collection_name in ("digests", "image_digests", "approved_digests"):
        digest = field_from_mapping(manifest.get(collection_name), (service,))
        if digest is not None:
            return digest
    return field_from_mapping(
        manifest,
        (f"{service}_approved_digest", f"{service}_image_digest", f"{service}_digest"),
    )


def image_reference(entry: object) -> object:
    if isinstance(entry, str):
        return entry
    return field_from_mapping(entry, ("image", "reference", "ref"))


def valid_digest(value: object) -> bool:
    return isinstance(value, str) and DIGEST_PATTERN.fullmatch(value) is not None


def has_exact_sha_tag(reference: str, expected_sha: str) -> bool:
    image_without_digest = reference.split("@", 1)[0]
    return ":" in image_without_digest and image_without_digest.rsplit(":", 1)[1] == expected_sha


def _base_image(reference: str) -> str:
    """Return repository/name without :tag or @digest for cross-representation comparison."""
    if not reference:
        return ""
    s = reference.split("@", 1)[0]
    if ":" in s:
        s = s.rsplit(":", 1)[0]
    return s.lower()



def load_manifest(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as manifest_file:
            manifest = json.load(
                manifest_file,
                object_pairs_hook=reject_duplicate_keys,
                parse_constant=reject_constant,
            )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        fail(f"некорректный JSON: {error}")
    if not isinstance(manifest, dict):
        fail("корневой элемент должен быть JSON-объектом")
    return manifest


def validate(manifest_path: str, expected_sha: str, compose_images: list[str]) -> None:
    manifest = load_manifest(manifest_path)
    if manifest.get("release_sha") != expected_sha:
        fail(f"поле release_sha не совпадает с запрошенным SHA: {expected_sha}")

    references: list[str] = []
    approved_digests: set[str] = set()
    for service in SERVICES:
        entry = service_entry(manifest, service)
        reference = image_reference(entry)
        if not isinstance(reference, str) or not reference:
            fail(f"отсутствует image reference для сервиса {service}")
        digest = approved_digest(manifest, service, entry)
        if digest is not None and not valid_digest(digest):
            fail(f"некорректный approved digest для сервиса {service}")
        reference_digest = reference.rsplit("@", 1)[1] if "@" in reference else None
        tag_matches = has_exact_sha_tag(reference, expected_sha)
        digest_matches = reference_digest is not None and digest == reference_digest
        if reference_digest is not None and not digest_matches:
            fail(f"image reference сервиса {service} не связана с approved digest")
        if not tag_matches and not digest_matches:
            fail(f"image reference сервиса {service} не соответствует release SHA или approved digest")
        references.append(reference)
        if digest is not None:
            approved_digests.add(digest)

    if compose_images:
        resolved_release_refs: list[str] = []
        for r in compose_images:
            if has_exact_sha_tag(r, expected_sha):
                resolved_release_refs.append(r)
                continue
            rd = r.rsplit("@", 1)[1] if "@" in r else None
            if rd and valid_digest(rd) and rd in approved_digests:
                resolved_release_refs.append(r)
        if Counter(_base_image(r) for r in resolved_release_refs) != Counter(_base_image(r) for r in references):
            fail("разрешённые Compose image references не совпадают с сервисами манифеста")


def main() -> None:
    if len(sys.argv) != 3:
        print("использование: release_manifest.py MANIFEST RELEASE_SHA", file=sys.stderr)
        raise SystemExit(2)
    compose_images = [line.strip() for line in sys.stdin if line.strip()]
    validate(sys.argv[1], sys.argv[2], compose_images)


if __name__ == "__main__":
    main()
