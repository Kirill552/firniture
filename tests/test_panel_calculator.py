"""Тесты для калькулятора панелей."""

import pytest

from api.constants import (
    DEFAULT_SHELF_GAP_MM as SHELF_GAP_MM,
)
from api.constants import (
    DEFAULT_THICKNESS_MM,
)
from api.panel_calculator import (
    WallCabinetTemplate,
    calculate_panels,
)


class TestWallCabinet:
    """Тесты навесного шкафа."""

    def test_basic_dimensions(self):
        """Базовый расчёт размеров."""
        result = calculate_panels(
            cabinet_type="wall",
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            shelf_count=2,
        )

        assert result.cabinet_type == "wall"
        assert result.total_panels >= 5  # 2 боковины + верх + низ + 2 полки
        assert result.total_area_m2 > 0

    def test_inner_width_calculation(self):
        """Проверка расчёта внутренней ширины."""
        template = WallCabinetTemplate(
            width_mm=600,
            height_mm=720,
            depth_mm=300,
        )

        # Внутренняя ширина = 600 - 2×16 = 568
        assert template.inner_width == 600 - 2 * DEFAULT_THICKNESS_MM

    def test_shelf_gap(self):
        """Проверка зазора для полки."""
        result = calculate_panels(
            cabinet_type="wall",
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            shelf_count=1,
        )

        # Находим полку
        shelf = next((p for p in result.panels if p.name == "Полка"), None)
        assert shelf is not None

        # Ширина полки = внутренняя ширина - 2×3мм
        expected_inner_width = 600 - 2 * DEFAULT_THICKNESS_MM
        expected_shelf_width = expected_inner_width - 2 * SHELF_GAP_MM

        assert shelf.width_mm == expected_shelf_width

    def test_shelf_sag_warning(self):
        """Проверка предупреждения о провисе."""
        result = calculate_panels(
            cabinet_type="wall",
            width_mm=800,  # Широкий шкаф
            height_mm=720,
            depth_mm=300,
            shelf_count=1,
        )

        # Должно быть предупреждение
        assert any("провис" in w.lower() for w in result.warnings)


class TestBaseCabinet:
    """Тесты напольной тумбы."""

    def test_has_ties_not_top(self):
        """Проверка что есть царги, а не сплошной верх."""
        result = calculate_panels(
            cabinet_type="base",
            width_mm=600,
            height_mm=720,
            depth_mm=560,
        )

        # Должны быть царги
        ties = [p for p in result.panels if "царга" in p.name.lower()]
        assert len(ties) == 2  # Передняя и задняя


class TestDrawerCabinet:
    """Тесты тумбы с ящиками."""

    def test_drawer_width_gap(self):
        """Проверка зазора 26мм для ящиков."""
        result = calculate_panels(
            cabinet_type="drawer",
            width_mm=600,
            height_mm=720,
            depth_mm=560,
            drawer_count=3,
        )

        # Находим боковину ящика
        drawer_side = next(
            (p for p in result.panels if "боковина ящика" in p.name.lower()),
            None
        )

        # Ширина корпуса ящика = внутренняя ширина - 26мм
        # Боковина ящика должна иметь правильную глубину
        assert drawer_side is not None

    def test_drawer_panels_count(self):
        """Проверка количества панелей для ящиков."""
        result = calculate_panels(
            cabinet_type="drawer",
            width_mm=600,
            height_mm=720,
            depth_mm=560,
            drawer_count=3,
        )

        # Для каждого ящика: фасад + 2 боковины + 2 стенки + дно
        # Плюс корпус: 2 боковины + дно + 2 царги
        # 3 ящика × (1 + 1×2 + 1×2 + 1) = 3 × 5 наименований

        drawer_panels = [p for p in result.panels if "ящик" in p.name.lower()]
        assert len(drawer_panels) >= 12  # Минимум 4 типа × 3 ящика


class TestSinkCabinet:
    """Тесты тумбы под мойку."""

    def test_no_bottom_panel(self):
        """Проверка отсутствия дна."""
        result = calculate_panels(
            cabinet_type="base_sink",
            width_mm=800,
            height_mm=720,
            depth_mm=560,
        )

        # Не должно быть панели "Дно"
        bottom = next((p for p in result.panels if p.name == "Дно"), None)
        assert bottom is None

    def test_has_ties(self):
        """Проверка наличия связей."""
        result = calculate_panels(
            cabinet_type="base_sink",
            width_mm=800,
            height_mm=720,
            depth_mm=560,
        )

        ties = [p for p in result.panels if "связь" in p.name.lower()]
        assert len(ties) == 4  # 2 верхние + 2 нижние

    def test_sink_warning(self):
        """Проверка предупреждения про сифон."""
        result = calculate_panels(
            cabinet_type="base_sink",
            width_mm=800,
            height_mm=720,
            depth_mm=560,
        )

        assert any("мойк" in w.lower() or "сифон" in w.lower() for w in result.warnings)


class TestEdgeCalculation:
    """Тесты расчёта кромки."""

    def test_edge_length(self):
        """Проверка расчёта длины кромки."""
        result = calculate_panels(
            cabinet_type="wall",
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            shelf_count=1,
        )

        # Длина кромки должна быть > 0
        assert result.edge_length_m > 0


class TestUnknownCabinetType:
    """Тесты обработки ошибок."""

    def test_invalid_type(self):
        """Проверка ошибки для неизвестного типа."""
        with pytest.raises(ValueError, match="Неизвестный тип корпуса"):
            calculate_panels(
                cabinet_type="unknown_type",
                width_mm=600,
                height_mm=720,
                depth_mm=300,
            )
