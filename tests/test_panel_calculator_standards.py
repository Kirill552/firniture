"""Проверки стандартов цеха в калькуляторе панелей."""

from api.panel_calculator import calculate_panels
from api.routers import _calculate_fasteners


def test_dowel_fastener_purchase_item_uses_contract_price():
    fasteners = _calculate_fasteners([], drawer_count=0, shelf_count=0, standards={"fastener_type": "dowel"})
    assert fasteners[0]["name"] == "Шкант 8×35"
    assert fasteners[0]["unit_price"] == 1.5


def _panel(result, name):
    return next(panel for panel in result.panels if panel.name == name)


def test_on_bottom_is_default_and_inset_is_alternative():
    on_bottom = calculate_panels("base", 600, 720, 520, shelf_count=0)
    inset = calculate_panels(
        "base", 600, 720, 520, shelf_count=0,
        standards={"bottom_mount": "inset"},
    )
    assert _panel(on_bottom, "Дно").width_mm == 600
    assert _panel(inset, "Дно").width_mm == 568
    assert _panel(on_bottom, "Боковина левая").height_mm == 704
    assert _panel(inset, "Боковина левая").height_mm == 720


def test_facade_gap_comes_from_factory_standards():
    result = calculate_panels(
        "base", 600, 720, 520,
        standards={"facade_gap_mm": 8.0},
    )
    facade = _panel(result, "Фасад")
    assert facade.width_mm == 592
    assert facade.height_mm == 712


def test_dowel_standard_replaces_confirmats():
    result = calculate_panels(
        "base", 600, 720, 520,
        standards={"fastener_type": "dowel"},
    )
    holes = [hole for panel in result.panels for hole in panel.drilling_points]
    fasteners = [hole for hole in holes if hole["hardware_type"] in {"dowel", "confirmat"}]
    assert fasteners
    assert all(hole["hardware_type"] == "dowel" for hole in fasteners)
    assert all(hole["diameter"] == 8.0 and hole["depth"] == 24.0 for hole in fasteners)


def test_hinge_mounts_are_omitted_by_default():
    result = calculate_panels("base", 600, 720, 520)
    side = _panel(result, "Боковина левая")
    assert not any(hole["hardware_type"] == "hinge_mount" for hole in side.drilling_points)


def test_hinge_mounts_match_facade_cup_heights_for_euro_screw():
    result = calculate_panels(
        "base", 600, 720, 520,
        standards={"hardware_mount": "euro_screw"},
    )
    facade = _panel(result, "Фасад")
    side = _panel(result, "Боковина левая")
    cup_y = [hole["y"] for hole in facade.drilling_points if hole["hardware_type"] == "hinge_cup"]
    mount_y = [hole["y"] for hole in side.drilling_points if hole["hardware_type"] == "hinge_mount"]
    assert sorted(mount_y) == sorted(y for y in cup_y for _ in range(2))


def test_confirmat_count_is_unchanged_by_hardware_mount():
    default = calculate_panels("base", 600, 720, 520)
    euro = calculate_panels(
        "base", 600, 720, 520,
        standards={"hardware_mount": "euro_screw"},
    )
    for result in (default, euro):
        holes = [
            hole for panel in result.panels
            for hole in panel.drilling_points
            if hole["hardware_type"] == "confirmat" and hole["side"] == "face"
        ]
        assert len(holes) == 12

def test_confirmat_count_for_wall_cabinet_is_eight_in_both_modes():
    for standards in (None, {"hardware_mount": "euro_screw"}):
        result = calculate_panels("wall", 600, 720, 300, standards=standards)
        holes = [
            hole for panel in result.panels
            for hole in panel.drilling_points
            if hole["hardware_type"] == "confirmat" and hole["side"] == "face"
        ]
        assert len(holes) == 8
 
def test_facades_can_be_excluded_without_changing_dimensions():
    result = calculate_panels("base", 600, 720, 520, include_facades=False)
    assert not any(panel.name.startswith("Фасад") for panel in result.panels)
    assert any("Фасады в раскрой не включены" in warning for warning in result.warnings)


def test_facade_color_is_visible_and_dimensions_stay_standard():
    result = calculate_panels("base", 600, 720, 520, facade_color="Дуб сонома")
    facade = _panel(result, "Фасад")
    assert facade.width_mm == 596
    assert facade.height_mm == 716
    assert "Дуб сонома" in facade.notes
