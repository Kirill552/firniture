from types import SimpleNamespace

from api.purchase_list import calculate_purchase_list


def test_purchase_uses_square_meter_price_and_rounds_sheets_up():
    panels = [SimpleNamespace(width_mm=2000, height_mm=1000, material="ЛДСП", name="Боковина")]
    items, _ = calculate_purchase_list(
        panels,
        settings={"price_board_m2": 450, "sheet_width_mm": 2800, "sheet_height_mm": 2070},
    )
    board = next(item for item in items if item.name == "ЛДСП")
    assert board.quantity == 1
    assert board.unit_price == 450
    assert board.total_price == 450 * 2.8 * 2.07


def test_purchase_uses_facade_square_meter_price():
    panels = [SimpleNamespace(width_mm=1000, height_mm=1000, material=None, name="Фасад двери")]
    items, _ = calculate_purchase_list(
        panels,
        settings={"price_facade_board_m2": 900, "sheet_width_mm": 2800, "sheet_height_mm": 2070},
    )
    facade = next(item for item in items if item.name == "Фасады")
    assert facade.unit_price == 900
    assert facade.total_price == 900 * 2.8 * 2.07
