"""Тесты генератора G-code присадки."""

import pytest

from api.drilling_gcode import (
    DrillHole,
    DrillingSide,
    HardwareType,
    PanelDrilling,
    Slot,
    _transliterate,
    generate_panel_gcode,
)


class TestTransliterate:
    """Тесты транслитерации."""

    def test_cyrillic_to_latin(self):
        assert _transliterate("Боковина левая") == "bokovina_levaya"

    def test_mixed_text(self):
        assert _transliterate("Панель 720x560") == "panel_720x560"


class TestGeneratePanelGcode:
    """Тесты генерации G-code."""

    @pytest.fixture
    def sample_panel(self) -> PanelDrilling:
        """Тестовая панель с присадкой."""
        return PanelDrilling(
            panel_id="test-1",
            panel_name="Боковина левая",
            width_mm=720,
            height_mm=560,
            thickness_mm=16,
            holes=[
                DrillHole(x=37, y=70, diameter=5, depth=50,
                          side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                DrillHole(x=37, y=650, diameter=5, depth=50,
                          side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                DrillHole(x=37, y=70, diameter=8, depth=11,
                          side=DrillingSide.FACE, hardware_type=HardwareType.CONFIRMAT),
            ],
            slots=[
                Slot(start_x=10, start_y=10, end_x=10, end_y=710, width=4, depth=10),
            ],
        )

    def test_weihong_profile(self, sample_panel):
        """Тест профиля Weihong."""
        gcode = generate_panel_gcode(sample_panel, "weihong")

        # Проверяем заголовок
        assert "O0001" in gcode
        assert "G21" in gcode  # Метрика
        assert "G90" in gcode  # Абсолютные координаты

        # Проверяем Weihong-специфичную паузу в мс
        assert "G04 P500" in gcode

        # Проверяем циклы сверления
        assert "G81" in gcode
        assert "G80" in gcode  # Отмена цикла

        # Проверяем завершение
        assert "M30" in gcode

    def test_fanuc_profile(self, sample_panel):
        """Тест профиля FANUC."""
        gcode = generate_panel_gcode(sample_panel, "fanuc")

        # FANUC использует секунды для G04
        assert "G04 P0.5" in gcode or "G04 P.5" in gcode

    def test_invalid_profile(self, sample_panel):
        """Тест несуществующего профиля."""
        with pytest.raises(ValueError, match="Неизвестный профиль"):
            generate_panel_gcode(sample_panel, "unknown_profile")

    def test_empty_panel(self):
        """Тест панели без отверстий."""
        panel = PanelDrilling(
            panel_id="empty",
            panel_name="Пустая панель",
            width_mm=600,
            height_mm=400,
            thickness_mm=16,
        )
        gcode = generate_panel_gcode(panel, "weihong")

        # Должен быть валидный G-code даже без операций
        assert "O0001" in gcode
        assert "M30" in gcode

    def test_holes_grouped_by_tool(self, sample_panel):
        """Тест группировки отверстий по инструменту."""
        gcode = generate_panel_gcode(sample_panel, "weihong")

        # Должны быть разные инструменты для D5 и D8
        assert "T01 M06" in gcode
        assert "T02 M06" in gcode

    def test_slot_generation(self, sample_panel):
        """Тест генерации паза."""
        gcode = generate_panel_gcode(sample_panel, "weihong")

        # Паз фрезеруется G01, не сверлится
        assert "PAZ pod zadnyuyu stenku" in gcode
        assert "freza D4" in gcode


class TestAllProfiles:
    """Тесты всех профилей станков."""

    @pytest.fixture
    def minimal_panel(self) -> PanelDrilling:
        return PanelDrilling(
            panel_id="min",
            panel_name="Test",
            width_mm=100,
            height_mm=100,
            thickness_mm=16,
            holes=[
                DrillHole(x=50, y=50, diameter=5, depth=10,
                          side=DrillingSide.FACE, hardware_type=HardwareType.SHELF_PIN),
            ],
        )

    @pytest.mark.parametrize("profile_name", ["weihong", "syntec", "fanuc", "dsp", "homag"])
    def test_all_profiles_generate_valid_gcode(self, minimal_panel, profile_name):
        """Все профили должны генерировать валидный G-code."""
        gcode = generate_panel_gcode(minimal_panel, profile_name)

        # Базовые проверки для любого профиля
        assert "G81" in gcode or "G82" in gcode or "G83" in gcode  # Цикл сверления
        assert len(gcode) > 100  # Не пустой
