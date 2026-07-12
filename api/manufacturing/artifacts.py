"""G-code артефакт-манифест — ядро (Task 18).

Генерирует воспроизводимый манифест артефактов из typed data:
- Стабильные имена файлов (collision-free, SHA-256 от контента)
- Обязательные provenance-поля (generator, spec_hash)
- Детерминированный хеш манифеста (исключая timestamp)

Зависимости: только pydantic, hashlib, json — stdlib + pydantic.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")




# ── Стабильные имена файлов ──────────────────────────────────────────


_PREFIX_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
_EXT_RE = re.compile(r"^[a-zA-Z0-9]{1,16}$")


def _validate_filename_component(value: str, label: str, pattern: re.Pattern[str], max_len: int) -> None:
    """Проверить компонент имени файла (префикс или расширение).

    Допустимы только символы из явного allowlist-паттерна.
    Отклоняются: пустые строки, пробелы по краям, Windows-недопустимые
    символы (``: * ? " < > |``), контрол-символы и все прочие.
    """
    if not value or not value.strip():
        raise ValueError(f"{label} не может быть пустым или состоять только из пробелов")
    if value != value.strip():
        raise ValueError(
            f"{label} не должен содержать пробелы в начале или конце"
        )
    if len(value) > max_len:
        raise ValueError(
            f"{label} слишком длинный ({len(value)} > {max_len})"
        )
    if not pattern.match(value):
        raise ValueError(
            f"{label} содержит недопустимые символы: "
            f"допустимы только латинские буквы, цифры и {pattern.pattern}"
        )


def stable_filename(prefix: str, ext: str, content: bytes) -> str:
    """Стабильное имя файла: ``{prefix}_{sha256_full_hex}.{ext}``

    Одинаковый контент → одинаковое имя.
    Полный SHA-256 (64 hex) исключает коллизии по truncated prefix.

    Префикс: ``[a-zA-Z0-9_-]``, макс. 128 символов.
    Расширение: ``[a-zA-Z0-9]``, макс. 16 символов.

    Raises ValueError если компонент содержит символы вне allowlist,
    пустые строки, пробелы по краям или превышает допустимую длину.
    """
    _validate_filename_component(prefix, "prefix", _PREFIX_RE, 128)
    _validate_filename_component(ext, "ext", _EXT_RE, 16)
    h = hashlib.sha256(content).hexdigest()
    return f"{prefix}_{h}.{ext}"


# ── Запись манифеста ─────────────────────────────────────────────────


class ArtifactEntry(BaseModel):
    """Одна запись в манифесте — метаданные одного сгенерированного файла."""

    filename: str = Field(..., min_length=1, description="Стабильное имя файла")
    content_type: str = Field(..., min_length=1, description="MIME-тип содержимого")
    size_bytes: int = Field(..., ge=0, description="Размер файла в байтах")
    checksum_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 хеш содержимого файла"
    )
    provenance: dict[str, str] = Field(
        ..., min_length=1, description="Метаданные происхождения файла"
    )

    @model_validator(mode="after")
    def _validate_provenance_required_fields(self) -> ArtifactEntry:
        """Provenance обязан содержать generator и spec_hash."""
        missing: list[str] = []
        if "generator" not in self.provenance:
            missing.append("generator")
        if "spec_hash" not in self.provenance:
            missing.append("spec_hash")
        if missing:
            raise ValueError(
                f"provenance должен содержать: {', '.join(missing)}"
            )
        return self

    @model_validator(mode="after")
    def _validate_sha256_fields(self) -> ArtifactEntry:
        """checksum_sha256 и provenance.spec_hash — lowercase hex ровно 64."""
        bad_fields: list[str] = []
        for field_name, value in (
            ("checksum_sha256", self.checksum_sha256),
            ("provenance.spec_hash", self.provenance.get("spec_hash", "")),
        ):
            if not _SHA256_RE.fullmatch(value):
                bad_fields.append(field_name)
        if bad_fields:
            raise ValueError(
                f"SHA-256 должен быть lowercase hex 64 символа: {', '.join(bad_fields)}"
            )
        return self


# ── Манифест ─────────────────────────────────────────────────────────


class ArtifactManifest(BaseModel):
    """Верхний уровень манифеста артефактов.

    generated_at не участвует в детерминированном хеше —
    чтобы повторная генерация с одинаковым контентом
    выдавала идентичный манифест.
    """

    spec_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 спецификации")
    entries: list[ArtifactEntry] = Field(default_factory=list, description="Список файлов")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Время генерации (не влияет на детерминированный хеш)",
    )

    def deterministic_hash(self) -> str:
        """SHA-256 от детерминированного JSON-представления манифеста.

        Исключает generated_at для воспроизводимости.
        """
        data = {
            "spec_hash": self.spec_hash,
            "entries": [
                {
                    "filename": e.filename,
                    "content_type": e.content_type,
                    "size_bytes": e.size_bytes,
                    "checksum_sha256": e.checksum_sha256,
                    "provenance": e.provenance,
                }
                for e in self.entries
            ],
        }
        payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @model_validator(mode="after")
    def _validate_spec_hash_format(self) -> ArtifactManifest:
        """spec_hash — lowercase hex ровно 64 символа."""
        if not _SHA256_RE.fullmatch(self.spec_hash):
            raise ValueError(
                "spec_hash должен быть lowercase hex ровно 64 символа"
            )
        return self

    @model_validator(mode="after")
    def _validate_provenance_spec_hash_match(self) -> ArtifactManifest:
        """spec_hash манифеста совпадает с provenance.spec_hash каждой записи."""
        mismatches: list[int] = []
        for idx, entry in enumerate(self.entries):
            entry_spec = entry.provenance.get("spec_hash", "")
            if entry_spec != self.spec_hash:
                mismatches.append(idx)
        if mismatches:
            raise ValueError(
                f"spec_hash манифеста не совпадает с provenance.spec_hash "
                f"в записях: {mismatches}"
            )
        return self


# ── Генерация манифеста ──────────────────────────────────────────────


def build_manifest(
    spec_hash: str,
    files: list[dict[str, Any]],
) -> ArtifactManifest:
    """Построить манифест из typed data.

    Каждый элемент files — dict:
        content:      bytes         — содержимое файла
        content_type: str           — MIME-тип
        prefix:       str           — префикс имени файла
        ext:          str           — расширение файла (без точки)
        provenance:   dict[str,str] — метаданные происхождения
    """
    entries: list[ArtifactEntry] = []
    for f in files:
        content: bytes = f["content"]
        checksum = hashlib.sha256(content).hexdigest()
        filename = stable_filename(f["prefix"], f["ext"], content)
        entries.append(
            ArtifactEntry(
                filename=filename,
                content_type=f["content_type"],
                size_bytes=len(content),
                checksum_sha256=checksum,
                provenance=f["provenance"],
            )
        )
    return ArtifactManifest(spec_hash=spec_hash, entries=entries)
