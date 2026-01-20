"""Тесты для централизованных констант."""

from api.constants import (
    DEFAULT_SHEET_WIDTH_MM,
    DEFAULT_SHEET_HEIGHT_MM,
    DEFAULT_THICKNESS_MM,
    DEFAULT_EDGE_THICKNESS_MM,
    DEFAULT_VISIBLE_EDGE_THICKNESS_MM,
    DEFAULT_FACADE_EDGE_THICKNESS_MM,
    DEFAULT_GAP_MM,
    DEFAULT_SHELF_GAP_MM,
    DEFAULT_DRAWER_GAP_MM,
    DEFAULT_BACK_PANEL_INSET_MM,
    DEFAULT_BACK_SLOT_WIDTH_MM,
    DEFAULT_BACK_SLOT_DEPTH_MM,
    DEFAULT_MAX_SHELF_SPAN_MM,
    DEFAULT_TIE_BEAM_HEIGHT_MM,
    DEFAULT_SPINDLE_SPEED,
    DEFAULT_FEED_RATE_CUTTING,
    DEFAULT_FEED_RATE_PLUNGE,
    DEFAULT_FEED_RATE_DRILLING,
    DEFAULT_CUT_DEPTH,
    DEFAULT_SAFE_HEIGHT,
    DEFAULT_TOOL_DIAMETER,
    DEFAULT_STEP_DOWN,
    DEFAULT_DRILL_PECK_DEPTH,
    DEFAULT_DRILL_RETRACT,
    DEFAULT_DRILLING_DEPTH,
    STANDARD_SHEETS,
)


def test_sheet_dimensions_reasonable():
    """Размеры листа должны быть в разумных пределах."""
    assert 2000 <= DEFAULT_SHEET_WIDTH_MM <= 3000, "Ширина листа должна быть 2000-3000мм"
    assert 1500 <= DEFAULT_SHEET_HEIGHT_MM <= 2500, "Высота листа должна быть 1500-2500мм"


def test_thickness_reasonable():
    """Толщина ЛДСП 16 или 18мм."""
    assert DEFAULT_THICKNESS_MM in (16.0, 18.0), "Толщина должна быть 16 или 18мм"


def test_edge_thickness_logical():
    """Толщины кромок должны быть логичными."""
    assert 0.3 <= DEFAULT_EDGE_THICKNESS_MM <= 0.5, "Стандартная кромка 0.3-0.5мм"
    assert 0.8 <= DEFAULT_VISIBLE_EDGE_THICKNESS_MM <= 1.2, "Видимая кромка 0.8-1.2мм"
    assert 1.5 <= DEFAULT_FACADE_EDGE_THICKNESS_MM <= 2.5, "Кромка фасада 1.5-2.5мм"

    # Кромка фасада должна быть толще видимой
    assert DEFAULT_FACADE_EDGE_THICKNESS_MM > DEFAULT_VISIBLE_EDGE_THICKNESS_MM
    # Видимая кромка должна быть толще стандартной
    assert DEFAULT_VISIBLE_EDGE_THICKNESS_MM > DEFAULT_EDGE_THICKNESS_MM


def test_gaps_reasonable():
    """Зазоры должны быть в разумных пределах."""
    assert 3.0 <= DEFAULT_GAP_MM <= 5.0, "Зазор на пропил 3-5мм"
    assert 2.0 <= DEFAULT_SHELF_GAP_MM <= 4.0, "Зазор полки 2-4мм"
    assert 20.0 <= DEFAULT_DRAWER_GAP_MM <= 30.0, "Зазор ящика 20-30мм"
    assert 5.0 <= DEFAULT_BACK_PANEL_INSET_MM <= 15.0, "Отступ задней стенки 5-15мм"


def test_slot_dimensions_reasonable():
    """Размеры пазов должны быть разумными."""
    assert 3.0 <= DEFAULT_BACK_SLOT_WIDTH_MM <= 5.0, "Ширина паза 3-5мм"
    assert 8.0 <= DEFAULT_BACK_SLOT_DEPTH_MM <= 12.0, "Глубина паза 8-12мм"


def test_structural_constraints():
    """Конструктивные ограничения должны быть безопасными."""
    assert 500.0 <= DEFAULT_MAX_SHELF_SPAN_MM <= 700.0, "Макс. ширина полки 500-700мм"
    assert 80.0 <= DEFAULT_TIE_BEAM_HEIGHT_MM <= 120.0, "Высота царги 80-120мм"


def test_spindle_speed_safe():
    """Обороты шпинделя должны быть безопасными для дерева."""
    assert 15000 <= DEFAULT_SPINDLE_SPEED <= 24000, "Безопасный диапазон оборотов 15k-24k"


def test_feed_rates_safe():
    """Подачи не должны быть опасно высокими."""
    assert DEFAULT_FEED_RATE_CUTTING <= 1500, "Подача резки ≤ 1500 мм/мин"
    assert DEFAULT_FEED_RATE_PLUNGE <= 600, "Подача врезания ≤ 600 мм/мин"
    assert DEFAULT_FEED_RATE_DRILLING <= 500, "Подача сверления ≤ 500 мм/мин"

    # Врезание должно быть медленнее резки
    assert DEFAULT_FEED_RATE_PLUNGE < DEFAULT_FEED_RATE_CUTTING, "Врезание медленнее резки"
    # Сверление должно быть медленнее резки
    assert DEFAULT_FEED_RATE_DRILLING < DEFAULT_FEED_RATE_CUTTING, "Сверление медленнее резки"


def test_cut_depth_matches_material():
    """Глубина резки >= толщины материала."""
    assert DEFAULT_CUT_DEPTH >= DEFAULT_THICKNESS_MM, "Глубина резки должна быть ≥ толщины материала"
    assert DEFAULT_CUT_DEPTH <= DEFAULT_THICKNESS_MM + 5.0, "Глубина резки не должна быть избыточной"


def test_safe_height_reasonable():
    """Безопасная высота должна быть разумной."""
    assert 3.0 <= DEFAULT_SAFE_HEIGHT <= 10.0, "Безопасная высота 3-10мм"


def test_tool_diameter_standard():
    """Диаметр инструмента должен быть стандартным."""
    standard_diameters = [3.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    assert DEFAULT_TOOL_DIAMETER in standard_diameters, f"Диаметр должен быть стандартным: {standard_diameters}"


def test_step_down_safe():
    """Глубина прохода не должна превышать диаметр инструмента."""
    assert DEFAULT_STEP_DOWN <= DEFAULT_TOOL_DIAMETER, "Глубина прохода ≤ диаметра инструмента"
    assert DEFAULT_STEP_DOWN >= 2.0, "Глубина прохода ≥ 2мм"


def test_drilling_parameters_logical():
    """Параметры сверления должны быть логичными."""
    assert 3.0 <= DEFAULT_DRILL_PECK_DEPTH <= 8.0, "Глубина клевания 3-8мм"
    assert 1.0 <= DEFAULT_DRILL_RETRACT <= 3.0, "Отвод при сверлении 1-3мм"
    assert 10.0 <= DEFAULT_DRILLING_DEPTH <= 15.0, "Глубина сверления 10-15мм"

    # Глубина сверления должна быть меньше толщины материала
    assert DEFAULT_DRILLING_DEPTH < DEFAULT_THICKNESS_MM, "Глубина сверления < толщины материала (сквозные отверстия)"


def test_standard_sheets_not_empty():
    """Должны быть предопределённые размеры листов."""
    assert len(STANDARD_SHEETS) >= 4, "Должно быть минимум 4 стандартных размера"
    assert "ЛДСП_2800x2070" in STANDARD_SHEETS, "Должен быть размер ЛДСП_2800x2070"
    assert "ЛДСП_2750x1830" in STANDARD_SHEETS, "Должен быть размер ЛДСП_2750x1830"


def test_standard_sheets_format():
    """Стандартные листы должны иметь правильный формат."""
    for name, (width, height) in STANDARD_SHEETS.items():
        assert isinstance(name, str), f"Название должно быть строкой: {name}"
        assert isinstance(width, (int, float)), f"Ширина должна быть числом: {width}"
        assert isinstance(height, (int, float)), f"Высота должна быть числом: {height}"
        assert width > 0, f"Ширина должна быть > 0: {width}"
        assert height > 0, f"Высота должна быть > 0: {height}"
        assert 2000 <= width <= 3000, f"Ширина листа должна быть 2000-3000мм: {width}"
        assert 1500 <= height <= 2500, f"Высота листа должна быть 1500-2500мм: {height}"


def test_constants_types():
    """Все константы должны иметь правильные типы."""
    # Размеры — целые числа
    assert isinstance(DEFAULT_SHEET_WIDTH_MM, int)
    assert isinstance(DEFAULT_SHEET_HEIGHT_MM, int)

    # Толщины — float
    assert isinstance(DEFAULT_THICKNESS_MM, float)
    assert isinstance(DEFAULT_EDGE_THICKNESS_MM, float)

    # G-code параметры
    assert isinstance(DEFAULT_SPINDLE_SPEED, int), "Обороты шпинделя — целое число"
    assert isinstance(DEFAULT_FEED_RATE_CUTTING, int), "Подача — целое число"
    assert isinstance(DEFAULT_CUT_DEPTH, float), "Глубина резки — float"

    # Словарь стандартных листов
    assert isinstance(STANDARD_SHEETS, dict)
