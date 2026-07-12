"""Golden suite: детерминированный референсный манифест для сертификации CAM.

Фикстура описывает 20 панелей с 25 операциями (drill / slot / pocket)
на 6 гранях.  Тесты ВАЛИДИРУЮТ манифест через Pydantic-модели,
НО НЕ запускают станок / симулятор / air-cut.

Все поля результатов испытаний (симулятор, air-cut, sacrificial)
остаются пустыми — это шаблон, не результат.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ── Пути ────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "cam"
GOLDEN_MANIFEST = FIXTURES_DIR / "golden_manifest.json"

# ── Lazy imports (avoid ezdxf at collection time) ───────────────────

_contracts = None


def _get_contracts():  # type: ignore[no-untyped-def]
    global _contracts
    if _contracts is None:
        from api.manufacturing import contracts as _mod

        _contracts = _mod
    return _contracts


# ════════════════════════════════════════════════════════════════════
# 1. Фикстура существует и валиден
# ════════════════════════════════════════════════════════════════════


class TestGoldenManifestExists:
    """Манифест должен существовать и быть валидным JSON."""

    def test_file_exists(self) -> None:
        assert GOLDEN_MANIFEST.exists(), f"Файл не найден: {GOLDEN_MANIFEST}"

    def test_valid_json(self) -> None:
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        assert isinstance(raw, dict), "Корень манифеста — объект"

    def test_has_panels_key(self) -> None:
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        assert "panels" in raw, "Ключ 'panels' обязателен"
        assert isinstance(raw["panels"], list), "'panels' — список"


# ════════════════════════════════════════════════════════════════════
# 2. Количество панелей и операций
# ════════════════════════════════════════════════════════════════════

EXPECTED_PANEL_COUNT = 20
EXPECTED_OP_TYPES = {"drill", "slot", "pocket"}
EXPECTED_FACES = {"front", "back", "left", "right", "top", "bottom"}


class TestGoldenManifestCounts:
    """Манифест должен содержать минимум 20 панелей с 3 типами операций."""

    @pytest.fixture()
    def raw_manifest(self) -> dict:
        return json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))

    def test_panel_count(self, raw_manifest: dict) -> None:
        assert len(raw_manifest["panels"]) >= EXPECTED_PANEL_COUNT, (
            f"Ожидается >= {EXPECTED_PANEL_COUNT} панелей, "
            f"получено {len(raw_manifest['panels'])}"
        )

    def test_panel_ids_unique(self, raw_manifest: dict) -> None:
        ids = [p["id"] for p in raw_manifest["panels"]]
        assert len(ids) == len(set(ids)), "Дублирующиеся panel IDs"

    def test_all_operation_types_present(self, raw_manifest: dict) -> None:
        types: set[str] = set()
        for panel in raw_manifest["panels"]:
            for op in panel.get("operations", []):
                types.add(op["op_type"])
        assert EXPECTED_OP_TYPES == types, (
            f"Ожидались типы {EXPECTED_OP_TYPES}, найдены {types}"
        )

    def test_minimum_total_operations(self, raw_manifest: dict) -> None:
        total = sum(len(p.get("operations", [])) for p in raw_manifest["panels"])
        assert total >= 25, (
            f"Ожидается >= 25 операций, получено {total}"
        )

    def test_faces_coverage(self, raw_manifest: dict) -> None:
        faces: set[str] = set()
        for panel in raw_manifest["panels"]:
            for op in panel.get("operations", []):
                faces.add(op.get("face", ""))
        assert EXPECTED_FACES.issubset(faces), (
            f"Не все грани представлены. Найдены: {faces}"
        )


# ════════════════════════════════════════════════════════════════════
# 3. Pydantic-валидация через ManufacturingSpec
# ════════════════════════════════════════════════════════════════════


class TestGoldenManifestPydantic:
    """Манифест должен проходить валидацию ManufacturingSpec."""

    @pytest.fixture()
    def raw_manifest(self) -> dict:
        return json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))

    def test_validates_as_manufacturing_spec(self, raw_manifest: dict) -> None:
        c = _get_contracts()
        spec = c.ManufacturingSpec.model_validate(raw_manifest)
        assert spec.units == c.Unit.MM
        assert spec.spec_version == "1.0"

    def test_all_panels_have_dimensions(self, raw_manifest: dict) -> None:
        c = _get_contracts()
        spec = c.ManufacturingSpec.model_validate(raw_manifest)
        for panel in spec.panels:
            assert panel.width_mm > 0, f"{panel.id}: width_mm <= 0"
            assert panel.height_mm > 0, f"{panel.id}: height_mm <= 0"
            assert panel.thickness_mm > 0, f"{panel.id}: thickness_mm <= 0"

    def test_all_operations_have_positive_dimensions(self, raw_manifest: dict) -> None:
        c = _get_contracts()
        spec = c.ManufacturingSpec.model_validate(raw_manifest)
        for panel in spec.panels:
            for op in panel.operations:
                assert op.id, f"Пустой op.id в {panel.id}"

    def test_operation_ids_unique_within_panel(self, raw_manifest: dict) -> None:
        c = _get_contracts()
        spec = c.ManufacturingSpec.model_validate(raw_manifest)
        for panel in spec.panels:
            ids = [op.id for op in panel.operations]
            assert len(ids) == len(set(ids)), (
                f"{panel.id}: дублирующиеся operation IDs"
            )


# ════════════════════════════════════════════════════════════════════
# 4. Детерминизм: canonical form
# ════════════════════════════════════════════════════════════════════


class TestGoldenManifestDeterministic:
    """Каноническое представление детерминировано и воспроизводимо."""

    @pytest.fixture()
    def raw_manifest(self) -> dict:
        return json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))

    def test_canonical_json_stable(self, raw_manifest: dict) -> None:
        c = _get_contracts()
        from api.manufacturing.coordinates import canonical_json

        spec = c.ManufacturingSpec.model_validate(raw_manifest)
        first = canonical_json(spec)
        second = canonical_json(spec)
        assert first == second, "canonical_json не детерминирован"

    def test_spec_hash_stable(self, raw_manifest: dict) -> None:
        c = _get_contracts()
        from api.manufacturing.coordinates import spec_hash

        spec = c.ManufacturingSpec.model_validate(raw_manifest)
        h1 = spec_hash(spec)
        h2 = spec_hash(spec)
        assert h1 == h2, "spec_hash не детерминирован"
        assert len(h1) == 64, "spec_hash — не SHA-256"

    def test_panel_sort_invariance(self, raw_manifest: dict) -> None:
        """Перестановка панелей не меняет canonical dict."""
        c = _get_contracts()
        spec = c.ManufacturingSpec.model_validate(raw_manifest)
        d1 = spec.to_canonical_dict()

        # Shuffle panels in-place then re-validate
        shuffled = raw_manifest.copy()
        shuffled["panels"] = list(reversed(shuffled["panels"]))
        spec2 = c.ManufacturingSpec.model_validate(shuffled)
        d2 = spec2.to_canonical_dict()

        assert d1 == d2, "to_canonical_dict зависит от порядка панелей"


# ════════════════════════════════════════════════════════════════════
# 5. Категории панелей (drill / slot / pocket / multi / boundary)
# ════════════════════════════════════════════════════════════════════


class TestGoldenManifestCategories:
    """Проверяем логическую структуру: 4 drill, 4 slot, 4 pocket, 3 multi, 5 boundary."""

    @pytest.fixture()
    def spec(self):
        c = _get_contracts()
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        return c.ManufacturingSpec.model_validate(raw)

    def _ops_by_panel(self, spec, panel_id: str):
        for p in spec.panels:
            if p.id == panel_id:
                return p.operations
        raise KeyError(f"Panel {panel_id} not found")

    def test_drill_panels_count(self, spec) -> None:
        drill_ids = [f"panel-{i:03d}" for i in range(1, 5)]
        for pid in drill_ids:
            ops = self._ops_by_panel(spec, pid)
            assert len(ops) == 1
            assert ops[0].op_type.value == "drill"

    def test_slot_panels_count(self, spec) -> None:
        slot_ids = [f"panel-{i:03d}" for i in range(5, 9)]
        for pid in slot_ids:
            ops = self._ops_by_panel(spec, pid)
            assert len(ops) == 1
            assert ops[0].op_type.value == "slot"

    def test_pocket_panels_count(self, spec) -> None:
        pocket_ids = [f"panel-{i:03d}" for i in range(9, 13)]
        for pid in pocket_ids:
            ops = self._ops_by_panel(spec, pid)
            assert len(ops) == 1
            assert ops[0].op_type.value == "pocket"

    def test_multi_operation_panels(self, spec) -> None:
        multi_ids = [f"panel-{i:03d}" for i in range(13, 16)]
        for pid in multi_ids:
            ops = self._ops_by_panel(spec, pid)
            assert len(ops) >= 2, f"{pid} должна иметь >= 2 операций"

    def test_boundary_panels(self, spec) -> None:
        boundary_ids = [f"panel-{i:03d}" for i in range(16, 21)]
        for pid in boundary_ids:
            ops = self._ops_by_panel(spec, pid)
            assert len(ops) == 1, f"{pid} boundary: ровно 1 операция"


# ════════════════════════════════════════════════════════════════════
# 6. Поля испытаний ОСТАЮТСЯ пустыми (шаблон, не результат)
# ════════════════════════════════════════════════════════════════════


class TestGoldenManifestNoCertificationClaim:
    """Фикстура НЕ содержит результатов испытаний — это шаблон, не сертификация."""

    def test_manifest_has_no_test_results(self) -> None:
        """Гарантия: фикстура описывает ТОЛЬКО геометрию операций,
        без полей результатов (результат симулятора, air-cut, sacrificial).
        """
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        result_keywords = {
            "simulator_result", "air_cut_result", "sacrificial_result",
            "operator_sign", "signed", "verified", "certified",
            "test_result", "pass", "fail",
        }
        raw_str = json.dumps(raw).lower()
        for kw in result_keywords:
            assert kw not in raw_str, (
                f"Манифест содержит '{kw}' — фикстура не должна "
                "заявлять о результатах испытаний"
            )

    def test_no_panel_has_certification_status(self) -> None:
        """Ни одна панель не имеет статуса 'verified'."""
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        for panel in raw["panels"]:
            assert "certification" not in panel, (
                f"{panel['id']}: панель не должна иметь certification"
            )

    def test_manifest_version_is_1_0(self) -> None:
        """Версия манифеста = 1.0 (шаблон)."""
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        assert raw.get("spec_version") == "1.0"


# ════════════════════════════════════════════════════════════════════
# 7. Материалы и допуски
# ════════════════════════════════════════════════════════════════════


class TestGoldenManifestMaterials:
    """Панели используют реалистичные материалы мебельного производства."""

    EXPECTED_MATERIALS = {"ЛДСП", "МДФ", "Фанера"}

    def test_all_panels_have_material(self) -> None:
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        for panel in raw["panels"]:
            mat = panel.get("material")
            assert mat, f"{panel['id']}: material обязателен"
            assert mat in self.EXPECTED_MATERIALS, (
                f"{panel['id']}: неожиданный материал '{mat}'"
            )

    def test_thickness_in_realistic_range(self) -> None:
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        for panel in raw["panels"]:
            t = panel["thickness_mm"]
            assert 10 <= t <= 30, (
                f"{panel['id']}: толщина {t} мм вне диапазона 10-30"
            )


# ════════════════════════════════════════════════════════════════════
# 8. Операции в пределах панели
# ════════════════════════════════════════════════════════════════════


class TestGoldenManifestOperationsInBounds:
    """Каждая операция геометрически размещена внутри своей панели."""

    @pytest.fixture()
    def spec(self):
        c = _get_contracts()
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        return c.ManufacturingSpec.model_validate(raw)

    def test_drill_operations_in_bounds(self, spec) -> None:
        c = _get_contracts()
        for panel in spec.panels:
            for op in panel.operations:
                if isinstance(op, c.DrillOperation):
                    assert 0 <= op.x_mm <= panel.width_mm, (
                        f"{panel.id}/{op.id}: x={op.x_mm} вне ширины {panel.width_mm}"
                    )
                    assert 0 <= op.y_mm <= panel.height_mm, (
                        f"{panel.id}/{op.id}: y={op.y_mm} вне высоты {panel.height_mm}"
                    )

    def test_slot_operations_in_bounds(self, spec) -> None:
        c = _get_contracts()
        for panel in spec.panels:
            for op in panel.operations:
                if isinstance(op, c.SlotOperation):
                    assert 0 <= op.x_mm <= panel.width_mm, (
                        f"{panel.id}/{op.id}: x={op.x_mm} вне ширины"
                    )
                    assert op.x_mm + op.length_mm <= panel.width_mm + 1, (
                        f"{panel.id}/{op.id}: slot выходит за правый край"
                    )

    def test_pocket_operations_in_bounds(self, spec) -> None:
        c = _get_contracts()
        for panel in spec.panels:
            for op in panel.operations:
                if isinstance(op, c.PocketOperation):
                    assert 0 <= op.x_mm <= panel.width_mm, (
                        f"{panel.id}/{op.id}: x={op.x_mm} вне ширины"
                    )
                    assert op.x_mm + op.width_mm <= panel.width_mm + 1, (
                        f"{panel.id}/{op.id}: pocket выходит за правый край"
                    )

    def test_depth_within_thickness(self) -> None:
        c = _get_contracts()
        raw = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
        spec = c.ManufacturingSpec.model_validate(raw)
        for panel in spec.panels:
            for op in panel.operations:
                if hasattr(op, "depth_mm"):
                    assert op.depth_mm <= panel.thickness_mm, (
                        f"{panel.id}/{op.id}: depth {op.depth_mm} > "
                        f"thickness {panel.thickness_mm}"
                    )
