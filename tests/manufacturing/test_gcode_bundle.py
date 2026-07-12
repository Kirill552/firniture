"""Тесты для G-code артефакт-манифеста (Task 18).

Проверяют:
1. Схему манифеста и обязательные поля
2. Стабильные имена файлов без коллизий
3. Воспроизводимость контрольных сумм (независимо от timestamp)
4. README на русском как запись манифеста
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from api.manufacturing.artifacts import (
    ArtifactEntry,
    ArtifactManifest,
    build_manifest,
    stable_filename,
)

# ── ArtifactEntry schema ─────────────────────────────────────────────


class TestArtifactEntry:
    """Запись манифеста — метаданные одного файла."""

    def test_required_provenance_fields(self) -> None:
        """Provenance обязателен: generator, spec_hash."""
        entry = ArtifactEntry(
            filename="panel_abc12345.gcode",
            content_type="application/x-gcode",
            size_bytes=1024,
            checksum_sha256="a" * 64,
            provenance={
                "generator": "test_renderer",
                "spec_hash": "b" * 64,
            },
        )
        assert entry.provenance["generator"] == "test_renderer"
        assert entry.provenance["spec_hash"] == "b" * 64

    def test_missing_generator_raises(self) -> None:
        """Без generator в provenance — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="c" * 64,
                provenance={"spec_hash": "d" * 64},
            )

    def test_missing_spec_hash_in_provenance_raises(self) -> None:
        """Без spec_hash в provenance — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="e" * 64,
                provenance={"generator": "test_renderer"},
            )

    def test_empty_provenance_raises(self) -> None:
        """Пустой provenance — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="f" * 64,
                provenance={},
            )

    def test_valid_optional_provenance_fields(self) -> None:
        """Provenance может содержать дополнительные поля."""
        entry = ArtifactEntry(
            filename="test.gcode",
            content_type="application/x-gcode",
            size_bytes=100,
            checksum_sha256="a" * 64,
            provenance={
                "generator": "test_renderer",
                "spec_hash": "b" * 64,
                "machine_profile": "router_3axis",
                "tool_library_version": "1.2.0",
            },
        )
        assert entry.provenance["machine_profile"] == "router_3axis"


# ── ArtifactManifest schema ──────────────────────────────────────────


class TestArtifactManifest:
    """Верхний уровень манифеста."""

    def test_manifest_has_spec_hash_and_files(self) -> None:
        """Манифест содержит spec_hash и список entries."""
        manifest = ArtifactManifest(
            spec_hash="a" * 64,
            entries=[],
        )
        assert manifest.spec_hash == "a" * 64
        assert manifest.entries == []

    def test_manifest_entries_list(self) -> None:
        """Манифест хранит список ArtifactEntry."""
        entry = ArtifactEntry(
            filename="test.gcode",
            content_type="application/x-gcode",
            size_bytes=100,
            checksum_sha256="a" * 64,
            provenance={"generator": "r", "spec_hash": "c" * 64},
        )
        manifest = ArtifactManifest(spec_hash="c" * 64, entries=[entry])
        assert len(manifest.entries) == 1
        assert manifest.entries[0].filename == "test.gcode"

    def test_manifest_excludes_generated_at_from_checksum(self) -> None:
        """generated_at не влияет на детерминированный хеш манифеста."""
        m1 = ArtifactManifest(
            spec_hash="a" * 64,
            entries=[],
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        m2 = ArtifactManifest(
            spec_hash="a" * 64,
            entries=[],
            generated_at=datetime(2025, 6, 15, tzinfo=UTC),
        )
        # детерминированный хеш манифеста одинаков
        assert m1.deterministic_hash() == m2.deterministic_hash()


# ── Stable filename generation ───────────────────────────────────────


class TestStableFilename:
    """Стабильные имена файлов: одинаковый контент → одинаковое имя."""

    def test_same_content_same_name(self) -> None:
        """Одинаковый контент → одинаковое имя файла."""
        content = b"G21 G90\nM3 S1000\nG1 X10 Y10\n"
        name1 = stable_filename("panel", "gcode", content)
        name2 = stable_filename("panel", "gcode", content)
        assert name1 == name2

    def test_different_content_different_name(self) -> None:
        """Разный контент → разное имя файла."""
        content1 = b"G21 G90\nM3 S1000\n"
        content2 = b"G21 G90\nM3 S2000\n"
        name1 = stable_filename("panel", "gcode", content1)
        name2 = stable_filename("panel", "gcode", content2)
        assert name1 != name2

    def test_filename_format(self) -> None:
        """Формат: {prefix}_{sha256_full_hex}.{ext}"""
        content = b"hello world"
        name = stable_filename("readme", "md", content)
        h = hashlib.sha256(content).hexdigest()
        assert name == f"readme_{h}.md"
        assert len(h) == 64, "digest must be full 64 hex chars"

    def test_collision_avoidance_with_similar_content(self) -> None:
        """Даже похожий контент даёт разные имена."""
        contents = [
            b"G21\nG90\nG1 X10 Y10 Z-2 F1000\n",
            b"G21\nG90\nG1 X10 Y10 Z-3 F1000\n",
            b"G21\nG90\nG1 X10 Y11 Z-2 F1000\n",
            b"G21\nG90\nG1 X11 Y10 Z-2 F1000\n",
        ]
        names = {stable_filename("panel", "gcode", c) for c in contents}
        assert len(names) == 4, f"Ожидалось 4 уникальных имени, получено {len(names)}"

    def test_empty_content(self) -> None:
        """Пустой контент всё ещё генерирует стабильное имя."""
        name = stable_filename("empty", "txt", b"")
        assert name.startswith("empty_")
        assert name.endswith(".txt")

    def test_no_collision_when_digest_prefixes_match(self) -> None:
        """Regression: два контента с одинаковыми первыми 8 hex SHA-256
        дают РАЗНЫЕ имена файлов (полный digest в имени).
        """
        # Два фейковых digest, совпадающих в первых 8 hex, различающихся далее
        fake_a = "abcdef01" + "a" * 56  # 64 hex total
        fake_b = "abcdef01" + "b" * 56
        assert fake_a[:8] == fake_b[:8], "предусловие: prefix-ы совпадают"
        assert fake_a != fake_b, "предусловие: digest-ы различаются"

        def _mock_sha256(data: bytes) -> object:
            """Возвращает мок, у которого hexdigest() зависит от data."""
            digest = fake_a if data == b"payload-A" else fake_b

            class _Hash:
                def hexdigest(self) -> str:
                    return digest

            return _Hash()

        with patch("api.manufacturing.artifacts.hashlib.sha256", side_effect=_mock_sha256):
            name_a = stable_filename("part", "gcode", b"payload-A")
            name_b = stable_filename("part", "gcode", b"payload-B")

        assert name_a != name_b, (
            "Файлы с одинаковым 8-char prefix должны различаться по полному digest"
        )
        assert name_a == f"part_{fake_a}.gcode"
        assert name_b == f"part_{fake_b}.gcode"

class TestStableFilenamePathSafety:
    """Regression: stable_filename использует explicit allowlist для компонентов имени.

    Task 18 — path-traversal / invalid-object-key hardening.
    Префикс: ``[a-zA-Z0-9_-]``, макс. 128 символов.
    Расширение: ``[a-zA-Z0-9]``, макс. 16 символов.
    """

    CONTENT = b"G21 G90\n"

    # ── Префикс: отклонение ──────────────────────────────────────

    def test_traversal_dotdot(self) -> None:
        """'../x' в префиксе → ValueError (traversal sequence)."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("../x", "gcode", self.CONTENT)

    def test_traversal_dotdot_prefix(self) -> None:
        """'../../x' в префиксе → ValueError (traversal sequence)."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("../../x", "gcode", self.CONTENT)

    def test_slash_in_prefix(self) -> None:
        """Прямой слеш в префиксе → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("nc/evil", "gcode", self.CONTENT)

    def test_backslash_in_prefix(self) -> None:
        """Обратный слеш в префиксе → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("nc\\evil", "gcode", self.CONTENT)

    def test_control_char_in_prefix(self) -> None:
        """Контрол-символ (\\x00) в префиксе → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("p\x00anel", "gcode", self.CONTENT)

    def test_control_char_bel_in_prefix(self) -> None:
        """Контрол-символ (\\x07 BEL) в префиксе → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("p\x07anel", "gcode", self.CONTENT)

    def test_empty_prefix(self) -> None:
        """Пустой префикс → ValueError."""
        with pytest.raises(ValueError, match="пустым|пробелов"):
            stable_filename("", "gcode", self.CONTENT)

    def test_whitespace_prefix(self) -> None:
        """Префикс из пробелов → ValueError."""
        with pytest.raises(ValueError, match="пустым|пробелов"):
            stable_filename("   ", "gcode", self.CONTENT)

    def test_leading_whitespace_prefix(self) -> None:
        """Пробел в начале префикса → ValueError."""
        with pytest.raises(ValueError, match="пробелы в начале"):
            stable_filename(" panel", "gcode", self.CONTENT)

    def test_trailing_whitespace_prefix(self) -> None:
        """Пробел в конце префикса → ValueError."""
        with pytest.raises(ValueError, match="пробелы в начале"):
            stable_filename("panel ", "gcode", self.CONTENT)

    def test_dot_in_prefix_rejected(self) -> None:
        """Точка в префиксе → ValueError (не в allowlist)."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("v1.0-part", "gcode", self.CONTENT)

    def test_windows_colon_in_prefix(self) -> None:
        """Двоеточие Windows → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("C:evil", "gcode", self.CONTENT)

    def test_windows_star_in_prefix(self) -> None:
        """Звёздочка Windows → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("file*name", "gcode", self.CONTENT)

    def test_windows_question_in_prefix(self) -> None:
        """Вопросительный знак Windows → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("file?name", "gcode", self.CONTENT)

    def test_windows_quote_in_prefix(self) -> None:
        """Кавычка Windows → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename('file"name', "gcode", self.CONTENT)

    def test_windows_angle_bracket_in_prefix(self) -> None:
        """Угловые скобки Windows → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("file<name", "gcode", self.CONTENT)
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("file>name", "gcode", self.CONTENT)

    def test_windows_pipe_in_prefix(self) -> None:
        """Вертикальная черта Windows → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("file|name", "gcode", self.CONTENT)

    def test_prefix_too_long(self) -> None:
        """Префикс длиннее 128 символов → ValueError."""
        with pytest.raises(ValueError, match="слишком длинный"):
            stable_filename("a" * 129, "gcode", self.CONTENT)

    def test_unicode_in_prefix(self) -> None:
        """Юникод в префиксе → ValueError (не ASCII allowlist)."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("панель", "gcode", self.CONTENT)

    # ── Расширение: отклонение ───────────────────────────────────

    def test_slash_in_extension(self) -> None:
        """Прямой слеш в расширении → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("panel", "gcode/evil", self.CONTENT)

    def test_backslash_in_extension(self) -> None:
        """Обратный слеш в расширении → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("panel", "gcode\\evil", self.CONTENT)

    def test_dotdot_in_extension(self) -> None:
        """'..' в расширении → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("panel", "..", self.CONTENT)

    def test_control_char_in_extension(self) -> None:
        """Контрол-символ в расширении → ValueError."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("panel", "g\x01code", self.CONTENT)

    def test_empty_extension(self) -> None:
        """Пустое расширение → ValueError."""
        with pytest.raises(ValueError, match="пустым|пробелов"):
            stable_filename("panel", "", self.CONTENT)

    def test_underscore_in_ext_rejected(self) -> None:
        """Подчёркивание в расширении → ValueError (не в ext allowlist)."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("panel", "g_code", self.CONTENT)

    def test_hyphen_in_ext_rejected(self) -> None:
        """Дефис в расширении → ValueError (не в ext allowlist)."""
        with pytest.raises(ValueError, match="недопустимые символы"):
            stable_filename("panel", "g-code", self.CONTENT)

    def test_ext_too_long(self) -> None:
        """Расширение длиннее 16 символов → ValueError."""
        with pytest.raises(ValueError, match="слишком длинный"):
            stable_filename("panel", "a" * 17, self.CONTENT)

    def test_leading_whitespace_extension(self) -> None:
        """Пробел в начале расширения → ValueError."""
        with pytest.raises(ValueError, match="пробелы в начале"):
            stable_filename("panel", " gcode", self.CONTENT)

    # ── Допустимые входные данные ────────────────────────────────

    def test_valid_deterministic(self) -> None:
        """Нормальный prefix/ext по-прежнему дают детерминированное имя."""
        name1 = stable_filename("panel", "gcode", self.CONTENT)
        name2 = stable_filename("panel", "gcode", self.CONTENT)
        assert name1 == name2
        h = hashlib.sha256(self.CONTENT).hexdigest()
        assert name1 == f"panel_{h}.gcode"

    def test_no_separator_leaks_into_output(self) -> None:
        """Результат никогда не содержит / или \\ из входных данных."""
        for prefix in ("ok", "under_score", "dashed-name"):
            for ext in ("gcode", "txt"):
                name = stable_filename(prefix, ext, self.CONTENT)
                assert "/" not in name, f"slash leaked into {name!r}"
                assert "\\" not in name, f"backslash leaked into {name!r}"

    def test_prefix_max_length_accepted(self) -> None:
        """Префикс ровно 128 символов — допустим."""
        name = stable_filename("a" * 128, "gcode", self.CONTENT)
        assert name.startswith("a" * 128 + "_")

    def test_ext_max_length_accepted(self) -> None:
        """Расширение ровно 16 символов — допустимо."""
        name = stable_filename("panel", "a" * 16, self.CONTENT)
        assert name.endswith("." + "a" * 16)

# ── build_manifest ───────────────────────────────────────────────────


class TestBuildManifest:
    """Генерация манифеста из typed data."""

    def test_build_manifest_with_gcode_entry(self) -> None:
        """Манифест из одного G-code файла."""
        gcode_content = b"G21\nG90\nM3 S1000\nG1 X10 Y10 F1000\nM5\n"
        manifest = build_manifest(
            spec_hash="abc123" + "0" * 58,
            files=[
                {
                    "content": gcode_content,
                    "content_type": "application/x-gcode",
                    "prefix": "panel_front",
                    "ext": "gcode",
                    "provenance": {
                        "generator": "test_renderer",
                        "spec_hash": "abc123" + "0" * 58,
                    },
                },
            ],
        )
        assert isinstance(manifest, ArtifactManifest)
        assert len(manifest.entries) == 1
        entry = manifest.entries[0]
        assert entry.content_type == "application/x-gcode"
        assert entry.size_bytes == len(gcode_content)
        expected_hash = hashlib.sha256(gcode_content).hexdigest()
        assert entry.checksum_sha256 == expected_hash

    def test_build_manifest_readme_in_russian(self) -> None:
        """README на русском как запись манифеста."""
        readme_text = "# G-code для панели «Фронт»\n\nЭтот файл сгенерирован системой mebel-ai.\n"
        readme_bytes = readme_text.encode("utf-8")
        manifest = build_manifest(
            spec_hash="fff" + "0" * 61,
            files=[
                {
                    "content": readme_bytes,
                    "content_type": "text/markdown; charset=utf-8",
                    "prefix": "readme",
                    "ext": "md",
                    "provenance": {
                        "generator": "readme_generator",
                        "spec_hash": "fff" + "0" * 61,
                    },
                },
            ],
        )
        entry = manifest.entries[0]
        assert entry.filename.startswith("readme_")
        assert entry.filename.endswith(".md")
        assert entry.size_bytes == len(readme_bytes)

    def test_build_manifest_reproducible_checksums(self) -> None:
        """Дважды построенный манифест с одинаковым контентом → одинаковые checksums."""
        content = b"G21\nG90\n"
        files_spec = [
            {
                "content": content,
                "content_type": "application/x-gcode",
                "prefix": "panel_test",
                "ext": "gcode",
                "provenance": {
                    "generator": "test",
                    "spec_hash": "a" * 64,
                },
            },
        ]
        m1 = build_manifest(spec_hash="a" * 64, files=files_spec)
        m2 = build_manifest(spec_hash="a" * 64, files=files_spec)
        assert m1.entries[0].checksum_sha256 == m2.entries[0].checksum_sha256
        assert m1.entries[0].filename == m2.entries[0].filename
        assert m1.deterministic_hash() == m2.deterministic_hash()

    def test_build_manifest_multiple_files(self) -> None:
        """Манифест из нескольких файлов — каждый с уникальным именем."""
        files_spec = [
            {
                "content": b"G21\n",
                "content_type": "application/x-gcode",
                "prefix": "panel_front",
                "ext": "gcode",
                "provenance": {"generator": "r", "spec_hash": "a" * 64},
            },
            {
                "content": b"G21\nG90\n",
                "content_type": "application/x-gcode",
                "prefix": "panel_back",
                "ext": "gcode",
                "provenance": {"generator": "r", "spec_hash": "a" * 64},
            },
            {
                "content": "# Описание\n\nСодержимое README.\n".encode(),
                "content_type": "text/markdown; charset=utf-8",
                "prefix": "readme",
                "ext": "md",
                "provenance": {"generator": "readme_gen", "spec_hash": "a" * 64},
            },
        ]
        manifest = build_manifest(spec_hash="a" * 64, files=files_spec)
        assert len(manifest.entries) == 3
        names = [e.filename for e in manifest.entries]
        assert len(set(names)) == 3, f"Имена файлов должны быть уникальными: {names}"

    def test_build_manifest_deterministic_hash_ignores_timestamp(self) -> None:
        """Хеш манифеста детерминирован и не зависит от времени."""
        content = b"test"
        files_spec = [
            {
                "content": content,
                "content_type": "text/plain",
                "prefix": "f",
                "ext": "txt",
                "provenance": {"generator": "g", "spec_hash": "a" * 64},
            },
        ]
        m1 = build_manifest(spec_hash="a" * 64, files=files_spec)
        m2 = build_manifest(spec_hash="a" * 64, files=files_spec)
        # Same content, same spec → same deterministic hash
        assert m1.deterministic_hash() == m2.deterministic_hash()

    def test_build_manifest_empty_files(self) -> None:
        """Манифест без файлов — валидно."""
        manifest = build_manifest(spec_hash="a" * 64, files=[])
        assert manifest.entries == []
        assert isinstance(manifest.deterministic_hash(), str)

# ── SHA-256 field validation ─────────────────────────────────────────


class TestSHA256FieldValidation:
    """SHA-256 поля должны быть lowercase hex ровно 64 символа."""

    def test_entry_rejects_uppercase_checksum(self) -> None:
        """Uppercase hex в checksum_sha256 — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="A" * 64,
                provenance={"generator": "g", "spec_hash": "b" * 64},
            )

    def test_entry_rejects_mixed_case_checksum(self) -> None:
        """Mixed case hex в checksum_sha256 — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="aB" * 32,
                provenance={"generator": "g", "spec_hash": "b" * 64},
            )

    def test_entry_rejects_too_short_checksum(self) -> None:
        """Слишком короткий checksum — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="a" * 63,
                provenance={"generator": "g", "spec_hash": "b" * 64},
            )

    def test_entry_rejects_too_long_checksum(self) -> None:
        """Слишком длинный checksum — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="a" * 65,
                provenance={"generator": "g", "spec_hash": "b" * 64},
            )

    def test_entry_rejects_non_hex_checksum(self) -> None:
        """Не hex символы в checksum — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="g" * 64,
                provenance={"generator": "g", "spec_hash": "b" * 64},
            )

    def test_entry_rejects_uppercase_provenance_spec_hash(self) -> None:
        """Uppercase hex в provenance.spec_hash — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="a" * 64,
                provenance={"generator": "g", "spec_hash": "B" * 64},
            )

    def test_entry_rejects_short_provenance_spec_hash(self) -> None:
        """Короткий provenance.spec_hash — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="a" * 64,
                provenance={"generator": "g", "spec_hash": "a" * 10},
            )

    def test_entry_rejects_non_hex_provenance_spec_hash(self) -> None:
        """Не hex символы в provenance.spec_hash — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactEntry(
                filename="test.gcode",
                content_type="application/x-gcode",
                size_bytes=100,
                checksum_sha256="a" * 64,
                provenance={"generator": "g", "spec_hash": "z" * 64},
            )

    def test_manifest_rejects_uppercase_spec_hash(self) -> None:
        """Uppercase hex в manifest spec_hash — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactManifest(spec_hash="A" * 64, entries=[])

    def test_manifest_rejects_non_hex_spec_hash(self) -> None:
        """Не hex символы в manifest spec_hash — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactManifest(spec_hash="g" * 64, entries=[])

    def test_manifest_rejects_short_spec_hash(self) -> None:
        """Короткий manifest spec_hash — ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactManifest(spec_hash="a" * 32, entries=[])


# ── Cross-validation: manifest spec_hash vs provenance ───────────────


class TestProvenanceSpecHashMismatch:
    """spec_hash манифеста должен совпадать с provenance.spec_hash каждой записи."""

    def test_mismatch_single_entry_rejects(self) -> None:
        """Единственная запись с несовпадающим provenance.spec_hash — ValidationError."""
        entry = ArtifactEntry(
            filename="test.gcode",
            content_type="application/x-gcode",
            size_bytes=100,
            checksum_sha256="a" * 64,
            provenance={"generator": "g", "spec_hash": "a" * 64},
        )
        with pytest.raises(ValidationError):
            ArtifactManifest(spec_hash="b" * 64, entries=[entry])

    def test_mismatch_among_multiple_entries_rejects(self) -> None:
        """Одна из нескольких записей с несовпадающим provenance.spec_hash — отвергается."""
        entry_ok = ArtifactEntry(
            filename="ok.gcode",
            content_type="application/x-gcode",
            size_bytes=10,
            checksum_sha256="a" * 64,
            provenance={"generator": "g", "spec_hash": "a" * 64},
        )
        entry_bad = ArtifactEntry(
            filename="bad.gcode",
            content_type="application/x-gcode",
            size_bytes=20,
            checksum_sha256="b" * 64,
            provenance={"generator": "g", "spec_hash": "c" * 64},
        )
        with pytest.raises(ValidationError):
            ArtifactManifest(spec_hash="a" * 64, entries=[entry_ok, entry_bad])

    def test_all_entries_match_accepts(self) -> None:
        """Все записи с совпадающим provenance.spec_hash — валидно."""
        sh = "a" * 64
        entries = [
            ArtifactEntry(
                filename=f"f{i}.gcode",
                content_type="application/x-gcode",
                size_bytes=10,
                checksum_sha256="d" * 64,
                provenance={"generator": "g", "spec_hash": sh},
            )
            for i in range(3)
        ]
        manifest = ArtifactManifest(spec_hash=sh, entries=entries)
        assert len(manifest.entries) == 3
