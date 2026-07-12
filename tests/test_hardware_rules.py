"""Тесты для правил расчёта фурнитуры."""
import pytest

from api.hardware_rules import (
    calculate_hinge_count,
    calculate_hinge_positions,
    calculate_hinges,
    calculate_slide_length,
    calculate_slides,
    estimate_door_weight,
)


class TestHingeCount:
    """Тесты расчёта количества петель."""

    def test_small_door_2_hinges(self):
        """Маленькая дверь: 2 петли."""
        assert calculate_hinge_count(500) == 2
        assert calculate_hinge_count(700) == 2

    def test_medium_door_3_hinges(self):
        """Средняя дверь: 3 петли."""
        assert calculate_hinge_count(1000) == 3
        assert calculate_hinge_count(1200) == 3

    def test_tall_door_4_hinges(self):
        """Высокая дверь: 4 петли."""
        assert calculate_hinge_count(1400) == 4
        assert calculate_hinge_count(1600) == 4

    def test_very_tall_door_5_hinges(self):
        """Очень высокая дверь: 4-5 петель."""
        assert calculate_hinge_count(1800) == 4
        assert calculate_hinge_count(2200) == 5

    def test_weight_increases_count(self):
        """Тяжёлая дверь требует больше петель."""
        # По высоте 700мм = 2 петли
        # Но вес 15кг требует 3 петли
        assert calculate_hinge_count(700, door_weight_kg=15) == 3

    def test_weight_vs_height_max(self):
        """Берётся максимум из расчёта по высоте и весу."""
        # Высота 1400мм = 4 петли
        # Вес 10кг = 2 петли
        # Результат = 4
        assert calculate_hinge_count(1400, door_weight_kg=10) == 4


class TestHingePositions:
    """Тесты расчёта позиций петель."""

    def test_2_hinges_at_margins(self):
        """2 петли на отступах от краёв."""
        positions = calculate_hinge_positions(720, 2)
        assert positions == [100.0, 620.0]

    def test_3_hinges_evenly_spaced(self):
        """3 петли равномерно распределены."""
        positions = calculate_hinge_positions(720, 3)
        assert len(positions) == 3
        assert positions[0] == 100.0
        assert positions[2] == 620.0
        # Средняя должна быть посередине
        assert positions[1] == pytest.approx(360.0, rel=0.01)

    def test_custom_margins(self):
        """Кастомные отступы."""
        positions = calculate_hinge_positions(
            720, 2, top_margin_mm=80, bottom_margin_mm=80
        )
        assert positions == [80.0, 640.0]

    def test_min_2_hinges(self):
        """Минимум 2 петли."""
        with pytest.raises(ValueError):
            calculate_hinge_positions(720, 1)


class TestSlideLength:
    """Тесты расчёта длины направляющих."""

    def test_standard_depth_500(self):
        """Глубина 500мм -> направляющие 450мм."""
        assert calculate_slide_length(500) == 450

    def test_standard_depth_560(self):
        """Глубина 560мм -> направляющие 500мм."""
        assert calculate_slide_length(560) == 500

    def test_round_down_to_50(self):
        """Округление вниз до 50мм."""
        assert calculate_slide_length(530) == 450  # 530-50=480 -> 450

    def test_min_length_250(self):
        """Минимальная длина 250мм."""
        assert calculate_slide_length(200) == 250
        assert calculate_slide_length(280) == 250


class TestFullCalculations:
    """Интеграционные тесты полных расчётов."""

    def test_calculate_hinges_full(self):
        """Полный расчёт петель."""
        result = calculate_hinges(1200)
        assert result.count == 3
        assert len(result.positions_mm) == 3

    def test_calculate_slides_full(self):
        """Полный расчёт направляющих."""
        result = calculate_slides(560, drawer_count=3)
        assert result.length_mm == 500
        assert result.pairs_count == 3

    def test_estimate_door_weight_ldsp(self):
        """Расчёт веса двери ЛДСП."""
        # 400x720x16 мм ЛДСП
        weight = estimate_door_weight(400, 720, 16, "ЛДСП")
        # ~3.13 кг
        assert 2.5 < weight < 4.0

    def test_estimate_door_weight_mdf(self):
        """МДФ тяжелее ЛДСП."""
        ldsp = estimate_door_weight(400, 720, 16, "ЛДСП")
        mdf = estimate_door_weight(400, 720, 16, "МДФ")
        assert mdf > ldsp
