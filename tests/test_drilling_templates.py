"""Тесты для шаблонов присадки."""

from api.drilling_templates import (
    HINGE_TEMPLATES,
    SLIDE_TEMPLATES,
    get_hinge_template,
    get_slide_template,
    get_template_for_position,
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
        assert len(templates) >= 5
        ids = [t["id"] for t in templates]
        assert "hinge_35mm_overlay" in ids
    def test_all_hinges_have_safe_cup_geometry(self):
        """Все чашки используют известный диаметр и не пробивают плиту."""
        assert len(HINGE_TEMPLATES) >= 5
        for template in HINGE_TEMPLATES.values():
            assert template.cup_diameter_mm in (26.0, 35.0)
            assert 0 < template.cup_depth_mm < 16.0

    def test_position_template_selection_uses_type_and_diameter(self):
        """Выбор петли не подменяет неизвестный тип накладной."""
        assert get_template_for_position(
            "петля полунакладная", {"cup_diameter_mm": 35}
        ).hinge_type == "half_overlay"
        assert get_template_for_position(
            "петля mini", {"cup_diameter_mm": 26}
        ).hinge_type == "mini"
        assert get_template_for_position(
            "петля вкладная", {"cup_diameter_mm": 35}
        ).hinge_type == "inset"
        assert get_template_for_position("петля", {"cup_diameter_mm": 35}) is None
        assert get_template_for_position("неизвестная фурнитура", {}) is None
        assert get_template_for_position("шариковая H35", {}).slide_type == "ball_h35"
        assert (
            get_template_for_position("скрытая направляющая", {}).slide_type
            == "concealed_full"
        )


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

    def test_list_slide_templates(self):
        """Список шаблонов должен содержать все направляющие."""
        templates = list_slide_templates()
        assert len(templates) >= 4
        types = [t["type"] for t in templates]
        assert "ball_h45" in types
        assert "roller" in types

    def test_slide_templates_have_distinct_front_offsets(self):
        """Сетка отверстий каждого типа привязана к своему переднему отступу."""
        offsets = {
            template.front_edge_offset_mm for template in SLIDE_TEMPLATES.values()
        }
        assert len(offsets) == len(SLIDE_TEMPLATES)


class TestLegacyCatalogCards:
    """Карточки прошлых парсеров: 1305 позиций в базе с другими именами полей."""

    def test_legacy_cup_diameter_key_is_understood(self):
        """Старый ETL писал cup_diameter без единиц — позиция не должна терять шаблон."""
        template = get_template_for_position(
            "петля", {"cup_diameter": 35, "mount_type": "накладная"}
        )
        assert template is not None
        assert template.cup_diameter_mm == 35

    def test_mount_type_from_card_selects_inset(self):
        """Тип в базе всегда «петля», наложение лежит в карточке — берём оттуда."""
        template = get_template_for_position(
            "петля", {"cup_diameter": 35, "mount_type": "вкладная"}
        )
        assert template is not None
        assert template.hinge_type == "inset"

    def test_card_without_diameter_gives_no_template(self):
        """Без подтверждённой чашки шаблон не выдаём: наугад сверлить нельзя."""
        assert get_template_for_position("петля", {"series": "PROFI"}) is None

    def test_slide_kind_from_card(self):
        """Вид направляющей приходит полем карточки, а не типом позиции."""
        template = get_template_for_position("направляющая", {"slide_type": "роликовые"})
        assert template is not None
        assert template.name == SLIDE_TEMPLATES["slide_roller"].name
