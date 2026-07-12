"""Тесты для модуля раскроя: layout_parts.

Покрытие:
    - Модели данных (PartRequest, SheetSpec, LayoutConfig, результаты)
    - Пустые входы
    - Одна деталь на один лист
    - Несколько деталей, нет пересечений
    - Kerf — зазор между деталями
    - Margin — поля листа
    - Grain — ограничение ротации
    - Несколько листов
    - Неразмещённые детали
    - Утилизация
    - Граничные случаи (деталь точно по размеру, ротация 90°)
"""
from __future__ import annotations

import pytest

from api.manufacturing.layout import (
    GrainDirection,
    LayoutConfig,
    LayoutResult,
    PartRequest,
    Placement,
    SheetSpec,
    _can_rotate,
    _expand_parts,
    _find_bl_position,
    _fits_on_sheet,
    _Rect,
    layout_parts,
)

# ── Вспомогательные функции ─────────────────────────────────────────


def _simple_config(
    sheet_w: float = 2440,
    sheet_h: float = 1220,
    kerf: float = 3.0,
    margin: float = 10.0,
    grain: GrainDirection = GrainDirection.NONE,
) -> LayoutConfig:
    """Создать конфигурацию с одним листом."""
    return LayoutConfig(
        kerf_mm=kerf,
        margin_mm=margin,
        grain=grain,
        sheet_specs=[SheetSpec(id="sheet_1", width_mm=sheet_w, height_mm=sheet_h)],
    )


def _placements_on_sheet(result: LayoutResult, sheet_id: str) -> list[Placement]:
    """Отфильтровать размещения на конкретном листе."""
    return [p for p in result.placements if p.sheet_id == sheet_id]


# ── Модели данных ───────────────────────────────────────────────────


class TestPartRequest:
    """Валидация PartRequest."""

    def test_valid(self) -> None:
        p = PartRequest(id="p1", width_mm=100, height_mm=50)
        assert p.id == "p1"
        assert p.quantity == 1
        assert p.allow_rotation is True

    def test_custom_quantity(self) -> None:
        p = PartRequest(id="p2", width_mm=100, height_mm=50, quantity=5)
        assert p.quantity == 5

    def test_no_rotation(self) -> None:
        p = PartRequest(id="p3", width_mm=100, height_mm=50, allow_rotation=False)
        assert p.allow_rotation is False

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id"):
            PartRequest(id="", width_mm=100, height_mm=50)

    def test_zero_width_raises(self) -> None:
        with pytest.raises(ValueError):
            PartRequest(id="p", width_mm=0, height_mm=50)

    def test_negative_height_raises(self) -> None:
        with pytest.raises(ValueError):
            PartRequest(id="p", width_mm=100, height_mm=-5)

    def test_zero_quantity_raises(self) -> None:
        with pytest.raises(ValueError):
            PartRequest(id="p", width_mm=100, height_mm=50, quantity=0)


class TestSheetSpec:
    """Валидация SheetSpec."""

    def test_valid(self) -> None:
        s = SheetSpec(id="s1", width_mm=2440, height_mm=1220)
        assert s.width_mm == 2440

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id"):
            SheetSpec(id="", width_mm=2440, height_mm=1220)

    def test_zero_dimension_raises(self) -> None:
        with pytest.raises(ValueError):
            SheetSpec(id="s1", width_mm=0, height_mm=1220)


class TestLayoutConfig:
    """Валидация LayoutConfig."""

    def test_defaults(self) -> None:
        cfg = LayoutConfig()
        assert cfg.kerf_mm == 3.0
        assert cfg.margin_mm == 10.0
        assert cfg.grain == GrainDirection.NONE
        assert cfg.sheet_specs == []

    def test_negative_kerf_raises(self) -> None:
        with pytest.raises(ValueError):
            LayoutConfig(kerf_mm=-1)

    def test_negative_margin_raises(self) -> None:
        with pytest.raises(ValueError):
            LayoutConfig(margin_mm=-5)


# ── Вспомогательные функции ─────────────────────────────────────────


class TestExpandParts:
    """_expand_parts: разворачивает quantity."""

    def test_single(self) -> None:
        parts = [PartRequest(id="a", width_mm=100, height_mm=50)]
        result = _expand_parts(parts)
        assert len(result) == 1
        assert result[0] == ("a", 100.0, 50.0, True)

    def test_quantity(self) -> None:
        parts = [PartRequest(id="a", width_mm=100, height_mm=50, quantity=3)]
        result = _expand_parts(parts)
        assert len(result) == 3
        assert result[0][0] == "a#1"
        assert result[1][0] == "a#2"
        assert result[2][0] == "a#3"

    def test_multiple_parts(self) -> None:
        parts = [
            PartRequest(id="a", width_mm=100, height_mm=50, quantity=2),
            PartRequest(id="b", width_mm=200, height_mm=100),
        ]
        result = _expand_parts(parts)
        assert len(result) == 3


class TestCanRotate:
    """_can_rotate: генерация ориентаций."""

    def test_square_no_rotation(self) -> None:
        variants = _can_rotate(100, 100, True, GrainDirection.NONE)
        assert len(variants) == 1  # квадрат — ротация бессмысленна

    def test_rect_with_rotation(self) -> None:
        variants = _can_rotate(100, 50, True, GrainDirection.NONE)
        assert len(variants) == 2
        assert variants[0] == (100, 50, False)
        assert variants[1] == (50, 100, True)

    def test_no_rotation_flag(self) -> None:
        variants = _can_rotate(100, 50, False, GrainDirection.NONE)
        assert len(variants) == 1

    def test_grain_vertical_blocks_rotation(self) -> None:
        """Grain VERTICAL — ротация 90° запрещена."""
        variants = _can_rotate(100, 50, True, GrainDirection.VERTICAL)
        assert len(variants) == 1
        assert variants[0] == (100, 50, False)

    def test_grain_horizontal_blocks_rotation(self) -> None:
        """Grain HORIZONTAL — ротация 90° запрещена."""
        variants = _can_rotate(100, 50, True, GrainDirection.HORIZONTAL)
        assert len(variants) == 1
        assert variants[0] == (100, 50, False)


class TestRect:
    """_Rect: внутренняя модель."""

    def test_overlaps(self) -> None:
        r1 = _Rect(0, 0, 10, 10, "a", 0, False, 10, 10)
        r2 = _Rect(5, 5, 10, 10, "b", 1, False, 10, 10)
        assert r1.overlaps(r2)
        assert r2.overlaps(r1)

    def test_no_overlap(self) -> None:
        r1 = _Rect(0, 0, 10, 10, "a", 0, False, 10, 10)
        r2 = _Rect(20, 20, 10, 10, "b", 1, False, 10, 10)
        assert not r1.overlaps(r2)

    def test_touching_no_overlap(self) -> None:
        """Прямоугольники впритык — не пересекаются."""
        r1 = _Rect(0, 0, 10, 10, "a", 0, False, 10, 10)
        r2 = _Rect(10, 0, 10, 10, "b", 1, False, 10, 10)
        assert not r1.overlaps(r2)


class TestFitsOnSheet:
    """_fits_on_sheet: проверка размещения."""

    def test_fits(self) -> None:
        assert _fits_on_sheet(100, 50, 0, 0, 1000, 1000, [], 0)

    def test_out_of_bounds(self) -> None:
        assert not _fits_on_sheet(100, 50, 990, 0, 1000, 1000, [], 0)

    def test_overlaps_existing(self) -> None:
        existing = [_Rect(0, 0, 100, 100, "a", 0, False, 100, 100)]
        assert not _fits_on_sheet(100, 100, 50, 50, 1000, 1000, existing, 0)

    def test_no_overlap_adjacent(self) -> None:
        existing = [_Rect(0, 0, 100, 100, "a", 0, False, 100, 100)]
        assert _fits_on_sheet(100, 100, 100, 0, 1000, 1000, existing, 0)

    def test_kerf_prevents_adjacent(self) -> None:
        """С kerf=10 прямоугольники впритык не должны считаться подходящими."""
        existing = [_Rect(0, 0, 100, 100, "a", 0, False, 100, 100)]
        # Прямоугольник впритык по X, но kerf=10 → зазор не соблюдён
        assert not _fits_on_sheet(100, 100, 100, 0, 1000, 1000, existing, 10)

    def test_kerf_fits_with_gap(self) -> None:
        """С kerf=10 прямоугольники с зазором 10 подходят."""
        existing = [_Rect(0, 0, 100, 100, "a", 0, False, 100, 100)]
        assert _fits_on_sheet(100, 100, 110, 0, 1000, 1000, existing, 10)


class TestFindBlPosition:
    """_find_bl_position: Bottom-Left поиск."""

    def test_empty_sheet(self) -> None:
        pos = _find_bl_position(100, 50, 1000, 1000, [], 0)
        assert pos == (0, 0)

    def test_after_one_rect(self) -> None:
        existing = [_Rect(0, 0, 100, 50, "a", 0, False, 100, 50)]
        pos = _find_bl_position(100, 50, 1000, 1000, existing, 0)
        # BL: предпочтение самому нижнему Y → (100, 0) правее первого
        assert pos == (100, 0)

    def test_two_rects_same_row(self) -> None:
        existing = [_Rect(0, 0, 100, 50, "a", 0, False, 100, 50)]
        pos = _find_bl_position(100, 50, 1000, 1000, existing, 0)
        # BL: (100, 0) предпочтительнее (0, 50) — ниже Y
        assert pos == (100, 0)

    def test_fills_row(self) -> None:
        """При ширине листа 200, две детали по 100 — вторая встаёт рядом."""
        existing = [_Rect(0, 0, 100, 50, "a", 0, False, 100, 50)]
        pos = _find_bl_position(100, 50, 200, 1000, existing, 0)
        assert pos == (100, 0)

    def test_too_large(self) -> None:
        """Деталь не влезает — None."""
        pos = _find_bl_position(2000, 50, 1000, 1000, [], 0)
        assert pos is None


# ── Интеграционные тесты layout_parts ───────────────────────────────


class TestLayoutEmpty:
    """Пустые входы."""

    def test_no_parts(self) -> None:
        cfg = _simple_config()
        result = layout_parts(cfg, [])
        assert result.placements == []
        assert result.unplaced == []
        assert result.total_parts == 0

    def test_no_sheets(self) -> None:
        cfg = LayoutConfig()
        parts = [PartRequest(id="p", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert len(result.unplaced) == 1
        assert result.unplaced[0].reason == "нет листов в конфигурации"

    def test_empty_both(self) -> None:
        result = layout_parts(LayoutConfig(), [])
        assert result.placements == []


class TestLayoutSinglePart:
    """Одна деталь на один лист."""

    def test_one_part_fits(self) -> None:
        cfg = _simple_config()
        parts = [PartRequest(id="p1", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1
        assert result.total_parts == 1
        assert len(result.placements) == 1
        assert len(result.unplaced) == 0
        p = result.placements[0]
        assert p.part_id == "p1"
        assert p.rotated is False
        assert p.sheet_id == "sheet_1"
        # Размещение с учётом margin
        assert p.x_mm == 10.0
        assert p.y_mm == 10.0

    def test_one_part_too_large(self) -> None:
        cfg = _simple_config(sheet_w=100, sheet_h=100)
        parts = [PartRequest(id="p1", width_mm=200, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 0
        assert len(result.unplaced) == 1


class TestLayoutMultipleParts:
    """Несколько деталей — проверка отсутствия пересечений."""

    def test_two_parts_no_overlap(self) -> None:
        cfg = _simple_config(sheet_w=500, sheet_h=500, kerf=0, margin=0)
        parts = [
            PartRequest(id="a", width_mm=100, height_mm=100),
            PartRequest(id="b", width_mm=100, height_mm=100),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 2

        # Проверяем что прямоугольники не пересекаются
        rects = [
            _Rect(
                p.x_mm, p.y_mm, p.width_mm, p.height_mm,
                p.part_id, 0, p.rotated, p.original_width_mm, p.original_height_mm,
            )
            for p in result.placements
        ]
        assert not rects[0].overlaps(rects[1])
        assert not rects[1].overlaps(rects[0])

    def test_many_parts_no_overlaps(self) -> None:
        """50 одинаковых деталей на большом листе — ни одного пересечения."""
        cfg = _simple_config(sheet_w=2440, sheet_h=1220, kerf=3, margin=10)
        parts = [
            PartRequest(id="p", width_mm=100, height_mm=50, quantity=50),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 50

        # Проверяем все пары на пересечение
        rects = [
            _Rect(
                p.x_mm, p.y_mm, p.width_mm, p.height_mm,
                p.part_id, 0, p.rotated, p.original_width_mm, p.original_height_mm,
            )
            for p in result.placements
        ]
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not rects[i].overlaps(rects[j]), (
                    f"Пересечение: {rects[i].part_id} и {rects[j].part_id}"
                )


class TestLayoutKerf:
    """Kerf — зазор между деталями."""

    def test_kerf_gap_enforced(self) -> None:
        """Две детали впритык с kerf=5 — вторая должна сдвинуться."""
        cfg = _simple_config(sheet_w=300, sheet_h=100, kerf=5, margin=0)
        parts = [
            PartRequest(id="a", width_mm=100, height_mm=100),
            PartRequest(id="b", width_mm=100, height_mm=100),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 2

        # Вторая деталь должна быть как минимум на 5 мм правее первой
        a = result.placements[0]
        b = result.placements[1]
        gap = min(
            abs(b.x_mm - (a.x_mm + a.width_mm)),
            abs(a.x_mm - (b.x_mm + b.width_mm)),
        )
        assert gap >= 5.0, f"Зазор {gap} < kerf 5.0"

    def test_zero_kerf_adjacent(self) -> None:
        """С kerf=0 детали могут встать впритык."""
        cfg = _simple_config(sheet_w=200, sheet_h=100, kerf=0, margin=0)
        parts = [
            PartRequest(id="a", width_mm=100, height_mm=100),
            PartRequest(id="b", width_mm=100, height_mm=100),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 2


class TestLayoutMargin:
    """Margin — поля листа."""

    def test_margin_shifts_placement(self) -> None:
        cfg = _simple_config(sheet_w=1000, sheet_h=1000, margin=50, kerf=0)
        parts = [PartRequest(id="p", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        p = result.placements[0]
        assert p.x_mm == 50.0
        assert p.y_mm == 50.0

    def test_margin_reduces_usable_area(self) -> None:
        """Деталь 90x40 не влезет в лист 100x100 с margin=10."""
        cfg = _simple_config(sheet_w=100, sheet_h=100, margin=10, kerf=0)
        # Usable area = 80x80
        parts = [PartRequest(id="p", width_mm=90, height_mm=40)]
        result = layout_parts(cfg, parts)
        assert len(result.unplaced) == 1


class TestLayoutGrain:
    """Grain direction — ограничение ротации."""

    def test_grain_none_allows_rotation(self) -> None:
        cfg = _simple_config(
            sheet_w=200, sheet_h=500, kerf=0, margin=0,
            grain=GrainDirection.NONE,
        )
        # Деталь 100x50, лист 200x500
        # С ротацией: 50x100 → тоже влезет
        parts = [PartRequest(id="p", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1

    def test_grain_does_not_break_placement(self) -> None:
        """Grain не должен ломать размещение — деталь всё равно размещается."""
        cfg = _simple_config(
            sheet_w=500, sheet_h=500, kerf=0, margin=0,
            grain=GrainDirection.VERTICAL,
        )
        parts = [PartRequest(id="p", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1
    def test_grain_vertical_no_rotated_placement(self) -> None:
        """Placement-уровень: VERTICAL grain — деталь 100x50 не ротируется."""
        cfg = _simple_config(
            sheet_w=200, sheet_h=200, kerf=0, margin=0,
            grain=GrainDirection.VERTICAL,
        )
        parts = [PartRequest(id="p", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1
        placement = result.placements[0]
        assert placement.rotated is False
        assert placement.width_mm == 100
        assert placement.height_mm == 50

    def test_grain_horizontal_no_rotated_placement(self) -> None:
        """Placement-уровень: HORIZONTAL grain — деталь 100x50 не ротируется."""
        cfg = _simple_config(
            sheet_w=200, sheet_h=200, kerf=0, margin=0,
            grain=GrainDirection.HORIZONTAL,
        )
        parts = [PartRequest(id="p", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1
        placement = result.placements[0]
        assert placement.rotated is False
        assert placement.width_mm == 100
        assert placement.height_mm == 50


class TestLayoutMultipleSheets:
    """Несколько листов."""

    def test_overflow_to_second_sheet(self) -> None:
        """Детали не влезают на один лист — используются оба."""
        cfg = LayoutConfig(
            kerf_mm=0,
            margin_mm=0,
            sheet_specs=[
                SheetSpec(id="s1", width_mm=200, height_mm=100),
                SheetSpec(id="s2", width_mm=200, height_mm=100),
            ],
        )
        parts = [
            PartRequest(id="a", width_mm=200, height_mm=100),
            PartRequest(id="b", width_mm=200, height_mm=100),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 2

        sheets_used = {p.sheet_id for p in result.placements}
        assert len(sheets_used) == 2

    def test_all_on_one_sheet(self) -> None:
        """Мелкие детали помещаются на один лист — второй не используется."""
        cfg = LayoutConfig(
            kerf_mm=0,
            margin_mm=0,
            sheet_specs=[
                SheetSpec(id="s1", width_mm=1000, height_mm=1000),
                SheetSpec(id="s2", width_mm=1000, height_mm=1000),
            ],
        )
        parts = [
            PartRequest(id="a", width_mm=50, height_mm=50),
            PartRequest(id="b", width_mm=50, height_mm=50),
        ]
        result = layout_parts(cfg, parts)
        assert all(p.sheet_id == "s1" for p in result.placements)

    def test_two_sheets_utilization(self) -> None:
        """Проверяем утилизацию обоих листов."""
        cfg = LayoutConfig(
            kerf_mm=0,
            margin_mm=0,
            sheet_specs=[
                SheetSpec(id="s1", width_mm=100, height_mm=100),
                SheetSpec(id="s2", width_mm=100, height_mm=100),
            ],
        )
        parts = [
            PartRequest(id="a", width_mm=100, height_mm=100),
            PartRequest(id="b", width_mm=100, height_mm=100),
        ]
        result = layout_parts(cfg, parts)
        assert len(result.sheet_utilizations) == 2
        # Каждый лист: 100*100 / (100*100) = 1.0
        for su in result.sheet_utilizations:
            assert su.utilization == pytest.approx(1.0)


class TestLayoutUnplaced:
    """Неразмещённые детали."""

    def test_unplaced_reason(self) -> None:
        cfg = _simple_config(sheet_w=100, sheet_h=100, margin=0, kerf=0)
        parts = [PartRequest(id="p", width_mm=200, height_mm=50)]
        result = layout_parts(cfg, parts)
        assert len(result.unplaced) == 1
        assert result.unplaced[0].part_id == "p"
        assert "не помещается" in result.unplaced[0].reason

    def test_mixed_placed_and_unplaced(self) -> None:
        """Одна деталь влезает, другая — нет."""
        cfg = _simple_config(sheet_w=100, sheet_h=100, margin=0, kerf=0)
        parts = [
            PartRequest(id="small", width_mm=50, height_mm=50),
            PartRequest(id="big", width_mm=200, height_mm=50),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1
        assert len(result.unplaced) == 1
        assert result.unplaced[0].part_id == "big"

    def test_no_sheets_all_unplaced(self) -> None:
        cfg = LayoutConfig()
        parts = [PartRequest(id="p", width_mm=100, height_mm=50, quantity=3)]
        result = layout_parts(cfg, parts)
        assert result.total_parts == 3
        assert result.placed_parts == 0
        assert len(result.unplaced) == 1
        assert result.unplaced[0].quantity_remaining == 3


class TestLayoutUtilization:
    """Утилизация."""

    def test_full_utilization(self) -> None:
        cfg = _simple_config(sheet_w=100, sheet_h=100, margin=0, kerf=0)
        parts = [PartRequest(id="p", width_mm=100, height_mm=100)]
        result = layout_parts(cfg, parts)
        su = result.sheet_utilizations[0]
        assert su.utilization == pytest.approx(1.0)
        assert su.placed_count == 1

    def test_half_utilization(self) -> None:
        cfg = _simple_config(sheet_w=200, sheet_h=100, margin=0, kerf=0)
        parts = [PartRequest(id="p", width_mm=100, height_mm=100)]
        result = layout_parts(cfg, parts)
        su = result.sheet_utilizations[0]
        assert su.utilization == pytest.approx(0.5)

    def test_zero_utilization_empty_sheet(self) -> None:
        cfg = _simple_config()
        result = layout_parts(cfg, [])
        su = result.sheet_utilizations[0]
        assert su.utilization == 0.0
        assert su.placed_count == 0

    def test_total_parts_count(self) -> None:
        cfg = _simple_config()
        parts = [
            PartRequest(id="a", width_mm=50, height_mm=50, quantity=3),
            PartRequest(id="b", width_mm=50, height_mm=50, quantity=2),
        ]
        result = layout_parts(cfg, parts)
        assert result.total_parts == 5
        assert result.placed_parts == 5


class TestLayoutRotation:
    """Ротация деталей."""

    def test_rotation_when_beneficial(self) -> None:
        """Деталь 200x50 на лист 50x500 — не влезает без ротации, влезает с."""
        cfg = _simple_config(sheet_w=50, sheet_h=500, margin=0, kerf=0)
        parts = [PartRequest(id="p", width_mm=200, height_mm=50, allow_rotation=True)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1
        assert result.placements[0].rotated is True
        # После ротации: w=50, h=200 → влезает в 50x500
        assert result.placements[0].width_mm == 50.0
        assert result.placements[0].height_mm == 200.0

    def test_no_rotation_when_disabled(self) -> None:
        cfg = _simple_config(sheet_w=50, sheet_h=500, margin=0, kerf=0)
        parts = [PartRequest(id="p", width_mm=200, height_mm=50, allow_rotation=False)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 0
        assert len(result.unplaced) == 1

    def test_square_no_rotation_effect(self) -> None:
        cfg = _simple_config(sheet_w=500, sheet_h=500, margin=0, kerf=0)
        parts = [PartRequest(id="p", width_mm=100, height_mm=100)]
        result = layout_parts(cfg, parts)
        assert result.placements[0].rotated is False


class TestLayoutDeterminism:
    """Детерминированность: одинаковый вход → одинаковый выход."""

    def test_same_input_same_output(self) -> None:
        cfg = _simple_config(sheet_w=500, sheet_h=500, kerf=3, margin=10)
        parts = [
            PartRequest(id="a", width_mm=80, height_mm=40, quantity=5),
            PartRequest(id="b", width_mm=120, height_mm=60, quantity=3),
        ]
        r1 = layout_parts(cfg, parts)
        r2 = layout_parts(cfg, parts)

        assert len(r1.placements) == len(r2.placements)
        for p1, p2 in zip(r1.placements, r2.placements, strict=True):
            assert p1.part_id == p2.part_id
            assert p1.x_mm == p2.x_mm
            assert p1.y_mm == p2.y_mm
            assert p1.width_mm == p2.width_mm
            assert p1.height_mm == p2.height_mm
            assert p1.rotated == p2.rotated
            assert p1.sheet_id == p2.sheet_id

    def test_input_order_does_not_matter(self) -> None:
        """Детали в разном порядке → тот же результат (сортировка по размеру)."""
        cfg = _simple_config(sheet_w=500, sheet_h=500, kerf=0, margin=0)
        parts_a = [
            PartRequest(id="a", width_mm=80, height_mm=40),
            PartRequest(id="b", width_mm=120, height_mm=60),
        ]
        parts_b = [
            PartRequest(id="b", width_mm=120, height_mm=60),
            PartRequest(id="a", width_mm=80, height_mm=40),
        ]
        r1 = layout_parts(cfg, parts_a)
        r2 = layout_parts(cfg, parts_b)

        # Сортировка по высоте/ширине → b(120x60) идёт первым в обоих случаях
        assert len(r1.placements) == len(r2.placements)
        for p1, p2 in zip(r1.placements, r2.placements, strict=True):
            assert p1.part_id == p2.part_id
            assert p1.x_mm == p2.x_mm
            assert p1.y_mm == p2.y_mm


class TestLayoutEdgeCases:
    """Граничные случаи."""

    def test_exact_fit(self) -> None:
        """Деталь точно по размеру usable area."""
        cfg = _simple_config(sheet_w=120, sheet_h=120, margin=10, kerf=0)
        # Usable: 100x100
        parts = [PartRequest(id="p", width_mm=100, height_mm=100)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1

    def test_many_small_parts(self) -> None:
        """100 мелких деталей — ни одного пересечения."""
        cfg = _simple_config(sheet_w=1000, sheet_h=1000, kerf=2, margin=5)
        parts = [PartRequest(id="p", width_mm=20, height_mm=20, quantity=100)]
        result = layout_parts(cfg, parts)
        assert result.placed_parts > 0  # Большинство должны поместиться

        rects = [
            _Rect(
                p.x_mm, p.y_mm, p.width_mm, p.height_mm,
                p.part_id, 0, p.rotated, p.original_width_mm, p.original_height_mm,
            )
            for p in result.placements
        ]
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not rects[i].overlaps(rects[j])

    def test_all_parts_out_of_bounds(self) -> None:
        """Все детали больше листа."""
        cfg = _simple_config(sheet_w=100, sheet_h=100, margin=0, kerf=0)
        parts = [
            PartRequest(id="a", width_mm=200, height_mm=50),
            PartRequest(id="b", width_mm=50, height_mm=200),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 0
        assert len(result.unplaced) == 2

    def test_result_models_valid(self) -> None:
        """LayoutResult — валидная Pydantic модель."""
        cfg = _simple_config()
        parts = [PartRequest(id="p", width_mm=100, height_mm=50)]
        result = layout_parts(cfg, parts)
        # Проверяем что результат сериализуется
        data = result.model_dump()
        assert "placements" in data
        assert "unplaced" in data
        assert "sheet_utilizations" in data

    def test_kerf_larger_than_part(self) -> None:
        """Kerf больше размера детали — вторая не влезет."""
        # Две 100x100 детали с kerf=100 на 200x200:
        # Первая (0,0) → expanded (-50,-50)-(150,150).
        # Вторая нигде не помещается без пересечения.
        cfg = _simple_config(sheet_w=200, sheet_h=200, kerf=100, margin=0)
        parts = [
            PartRequest(id="a", width_mm=100, height_mm=100),
            PartRequest(id="b", width_mm=100, height_mm=100),
        ]
        result = layout_parts(cfg, parts)
        assert result.placed_parts == 1
        assert len(result.unplaced) == 1
