"""Тесты для калькулятора координат присадки."""

from api.drilling_calculator import (
    calculate_drilling_for_facade,
    calculate_drilling_for_side_panel,
    calculate_hinge_drill_points,
    calculate_slide_drill_points,
)


class TestHingeDrillPoints:
    """Тесты присадки петель."""

    def test_2_hinges_creates_6_points(self):
        """2 петли = 2 чашки + 4 крепежа = 6 точек."""
        points = calculate_hinge_drill_points(720, hinge_count=2)
        assert len(points) == 6

    def test_3_hinges_creates_9_points(self):
        """3 петли = 3 чашки + 6 крепежа = 9 точек."""
        points = calculate_hinge_drill_points(1200, hinge_count=3)
        assert len(points) == 9

    def test_cup_diameter_35mm(self):
        """Диаметр чашки 35мм."""
        points = calculate_hinge_drill_points(720, hinge_count=2)
        cups = [p for p in points if p.hardware_type == "hinge_cup"]
        assert all(p.diameter == 35.0 for p in cups)

    def test_mount_diameter_5mm(self):
        """Диаметр крепежа 5мм."""
        points = calculate_hinge_drill_points(720, hinge_count=2)
        mounts = [p for p in points if p.hardware_type == "hinge_mount"]
        assert all(p.diameter == 5.0 for p in mounts)

    def test_x_position_is_edge_offset(self):
        """X чашки = отступ от края (21.5мм)."""
        points = calculate_hinge_drill_points(720, hinge_count=2)
        cups = [p for p in points if p.hardware_type == "hinge_cup"]
        assert all(p.x == 21.5 for p in cups)

    def test_layers_correct(self):
        """Слои DXF корректны."""
        points = calculate_hinge_drill_points(720, hinge_count=2)
        cups = [p for p in points if p.hardware_type == "hinge_cup"]
        mounts = [p for p in points if p.hardware_type == "hinge_mount"]
        assert all(p.layer == "DRILL_V_35" for p in cups)
        assert all(p.layer == "DRILL_V_5" for p in mounts)


class TestSlideDrillPoints:
    """Тесты присадки направляющих."""

    def test_single_drawer_creates_points(self):
        """1 ящик создаёт несколько отверстий."""
        points = calculate_slide_drill_points(
            panel_height_mm=720,
            panel_depth_mm=500,
            drawer_positions_mm=[50],
        )
        assert len(points) >= 4  # Минимум 4 отверстия на направляющую

    def test_hole_diameter_4mm(self):
        """Диаметр отверстий 4мм."""
        points = calculate_slide_drill_points(
            panel_height_mm=720,
            panel_depth_mm=500,
            drawer_positions_mm=[50],
        )
        assert all(p.diameter == 4.0 for p in points)

    def test_hole_spacing_32mm(self):
        """Шаг отверстий 32мм."""
        points = calculate_slide_drill_points(
            panel_height_mm=720,
            panel_depth_mm=500,
            drawer_positions_mm=[50],
        )
        x_coords = sorted([p.x for p in points])
        if len(x_coords) >= 2:
            spacing = x_coords[1] - x_coords[0]
            assert spacing == 32.0

    def test_layer_drill_h_4(self):
        """Слой DRILL_H_4."""
        points = calculate_slide_drill_points(
            panel_height_mm=720,
            panel_depth_mm=500,
            drawer_positions_mm=[50],
        )
        assert all(p.layer == "DRILL_H_4" for p in points)


class TestDrillingForFacade:
    """Тесты расчёта присадки фасада."""

    def test_standard_facade_720(self):
        """Стандартный фасад 400x720."""
        result = calculate_drilling_for_facade(400, 720)
        assert result.panel_name == "Фасад"
        assert result.panel_height_mm == 720
        assert len(result.drill_points) == 6  # 2 петли

    def test_tall_facade_warning(self):
        """Высокий фасад >2200мм даёт предупреждение."""
        result = calculate_drilling_for_facade(400, 2300)
        assert any("2200" in w for w in result.warnings)


class TestDrillingForSidePanel:
    """Тесты расчёта присадки боковины."""

    def test_3_drawers(self):
        """Боковина с 3 ящиками."""
        result = calculate_drilling_for_side_panel(
            height_mm=720,
            depth_mm=500,
            drawer_count=3,
        )
        assert result.panel_name == "Боковина"
        assert len(result.drill_points) > 0
        # 3 ящика * N отверстий
        # hardware_id: side_panel_slide_{drawer}_{hole}
        # Проверяем наличие точек для каждого ящика
        has_drawer_1 = any("_slide_1_" in p.hardware_id for p in result.drill_points)
        has_drawer_2 = any("_slide_2_" in p.hardware_id for p in result.drill_points)
        has_drawer_3 = any("_slide_3_" in p.hardware_id for p in result.drill_points)

        assert has_drawer_1
        assert has_drawer_2
        assert has_drawer_3

    def test_drawer_overflow_warning(self):
        """Ящики не помещаются — предупреждение."""
        result = calculate_drilling_for_side_panel(
            height_mm=300,
            depth_mm=500,
            drawer_count=5,
            drawer_height_mm=150,
        )
        assert any("не помещается" in w for w in result.warnings)
