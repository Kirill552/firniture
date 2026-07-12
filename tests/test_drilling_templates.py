"""Тесты для шаблонов присадки."""

from api.drilling_templates import (
    SLIDE_TEMPLATES,
    get_hinge_template,
    get_slide_template,
    list_hinge_templates,
    list_slide_templates,
)


class TestHingeTemplates:
    """Тесты шаблонов петель."""

    def test_overlay_template_exists(self):
        """Накладная петля должна быть в шаблонах."""
        template = get_hinge_template("hinge_35mm_overlay")
        assert template is not None
        assert template.cup_diameter_mm == 35.0
        assert template.edge_offset_mm == 21.5

    def test_half_overlay_has_offset(self):
        """Полунакладная должна иметь смещение на корпусе."""
        overlay = get_hinge_template("hinge_35mm_overlay")
        half = get_hinge_template("hinge_35mm_half_overlay")
        assert half.body_offset_mm > overlay.body_offset_mm

    def test_inset_has_max_offset(self):
        """Вкладная должна иметь максимальное смещение."""
        overlay = get_hinge_template("hinge_35mm_overlay")
        inset = get_hinge_template("hinge_35mm_inset")
        assert inset.body_offset_mm > overlay.body_offset_mm + 10

    def test_mounting_holes_symmetrical(self):
        """Крепёжные отверстия должны быть симметричны."""
        template = get_hinge_template("hinge_35mm_overlay")
        holes = template.mounting_holes
        assert len(holes) == 2
        assert holes[0].dy_mm == -holes[1].dy_mm

    def test_list_hinge_templates(self):
        """Список шаблонов должен содержать все петли."""
        templates = list_hinge_templates()
        assert len(templates) == 3
        ids = [t["id"] for t in templates]
        assert "hinge_35mm_overlay" in ids


class TestSlideTemplates:
    """Тесты шаблонов направляющих."""

    def test_h45_template_exists(self):
        """H45 направляющие должны быть в шаблонах."""
        template = get_slide_template("slide_ball_h45")
        assert template is not None
        assert template.profile_height_mm == 45.0
        assert template.load_capacity_kg == 45.0

    def test_h35_lower_capacity(self):
        """H35 должны иметь меньшую нагрузку чем H45."""
        h35 = get_slide_template("slide_ball_h35")
        h45 = get_slide_template("slide_ball_h45")
        assert h35.load_capacity_kg < h45.load_capacity_kg

    def test_roller_lowest_capacity(self):
        """Роликовые должны иметь минимальную нагрузку."""
        roller = get_slide_template("slide_roller")
        h35 = get_slide_template("slide_ball_h35")
        assert roller.load_capacity_kg < h35.load_capacity_kg

    def test_hole_spacing_32mm(self):
        """Шаг отверстий должен быть 32мм (система 32)."""
        for template in SLIDE_TEMPLATES.values():
            assert template.hole_spacing_mm == 32.0

    def test_list_slide_templates(self):
        """Список шаблонов должен содержать все направляющие."""
        templates = list_slide_templates()
        assert len(templates) == 3
        types = [t["type"] for t in templates]
        assert "ball_h45" in types
        assert "roller" in types
