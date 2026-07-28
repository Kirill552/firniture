"""Расчёт закупки в единицах поставщика."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Iterable

from .schemas import SETTINGS_DEFAULTS


@dataclass(frozen=True)
class PurchaseItem:
    name: str
    quantity: float
    unit: str
    unit_price: float
    category: str
    area_per_unit_m2: float = 1.0

    @property
    def total_price(self) -> float:
        return round(self.quantity * self.unit_price * self.area_per_unit_m2, 2)


def _settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    values = dict(SETTINGS_DEFAULTS)
    values.update(settings or {})
    return values


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _panel_area(panels: Iterable[Any]) -> float:
    """Площадь деталей в м². Панель приходит и словарём, и ORM-объектом."""
    total = 0.0
    for panel in panels:
        width = float(_get_value(panel, "width_mm", 0) or 0)
        height = float(_get_value(panel, "height_mm", 0) or 0)
        quantity = int(_get_value(panel, "quantity", 1) or 1)
        total += width * height * quantity / 1_000_000
    return total


def _sheet_count(panels: list[Any], params: dict[str, Any], settings: dict[str, Any]) -> int:
    layout = params.get("layout") or params.get("cutting_layout") or {}
    for key in ("sheets_count", "sheet_count", "sheets"):
        value = layout.get(key) if isinstance(layout, dict) else None
        if value is not None:
            return max(0, int(ceil(float(value))))
    width = float(settings.get("sheet_width_mm", 2800))
    height = float(settings.get("sheet_height_mm", 2070))
    sheet_area = width * height / 1_000_000
    waste = float(settings.get("purchase_waste_percent", 10.0)) / 100
    return int(ceil(_panel_area(panels) * (1 + waste) / sheet_area)) if panels else 0


def _edge_length(edge_bands: Iterable[dict[str, Any]], visible: bool) -> float:
    total = 0.0
    for band in edge_bands:
        kind = str(band.get("type", "")).lower()
        thickness = float(band.get("thickness_mm", 2 if "2" in kind else 0.4))
        is_visible = thickness >= 1.0 or "вид" in kind or "visible" in kind
        if is_visible == visible:
            total += float(band.get("length_m", 0))
    return total


def calculate_purchase_list(
    panels: list[Any],
    params: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> tuple[list[PurchaseItem], bool]:
    """Вернуть позиции закупки и признак использования дефолтных цен."""
    params = params or {}
    values = _settings(settings)
    items: list[PurchaseItem] = []
    prices_are_defaults = not bool(settings and any(k in settings for k in (
        "price_board_m2", "price_facade_board_m2", "price_hdf_m2",
        "price_edge_visible_m", "price_edge_hidden_m", "price_cut_m",
        "price_edging_m", "price_drilling_hole",
    )))
    panels_list = list(panels)

    # Что за деталь, решает её имя: фасад остаётся фасадом, каким бы декором
    # он ни был. Материал говорит только о декоре — «Дуб сонома» это цвет,
    # а не признак корпусной детали.
    ldsp: list[Any] = []
    facade: list[Any] = []
    hdf: list[Any] = []
    for panel in panels_list:
        name = str(_get_value(panel, "name", "") or "").lower()
        material = str(_get_value(panel, "material", "") or "").lower()
        decor = str(_get_value(panel, "decor", "") or "").lower()
        surface = f"{material} {decor}"

        if "хдф" in surface or "двп" in surface:
            hdf.append(panel)
        elif name.startswith("фасад") or any(
            token in surface for token in ("фасад", "мдф", "эмаль", "пластик")
        ):
            facade.append(panel)
        else:
            ldsp.append(panel)

    sheet_area_m2 = (
        float(values.get("sheet_width_mm", 2800))
        * float(values.get("sheet_height_mm", 2070))
        / 1_000_000
    )

    if ldsp:
        items.append(PurchaseItem(
            "ЛДСП", _sheet_count(ldsp, params, values), "лист",
            float(values["price_board_m2"]), "materials", sheet_area_m2,
        ))
    if facade:
        items.append(PurchaseItem(
            "Фасады", _sheet_count(facade, params, values), "лист",
            float(values["price_facade_board_m2"]), "materials", sheet_area_m2,
        ))
    if hdf:
        items.append(PurchaseItem(
            "ХДФ/ДВП", int(ceil(_panel_area(hdf) * 1.1 / sheet_area_m2)), "лист",
            float(values["price_hdf_m2"]), "materials", sheet_area_m2,
        ))
    edge_bands = params.get("edge_bands", [])
    for visible, name, key in ((True, "Кромка видимая 2 мм", "price_edge_visible_m"), (False, "Кромка скрытая 0,4 мм", "price_edge_hidden_m")):
        length = _edge_length(edge_bands, visible) * 1.1
        if length > 0:
            items.append(PurchaseItem(name, round(length, 2), "м", float(values.get(key, 45 if visible else 15)), "materials"))
    for key, category, fallback in (("hardware", "hardware", 0), ("fasteners", "fasteners", 1)):
        for item in params.get(key, []):
            quantity = float(item.get("quantity", item.get("qty", 0)))
            if quantity > 0:
                items.append(PurchaseItem(item.get("name", "Фурнитура" if key == "hardware" else "Крепёж"), quantity, "шт", float(item.get("unit_price", fallback)), category))
    cut_length = sum(
        (float(_get_value(p, "width_mm", 0)) + float(_get_value(p, "height_mm", 0)))
        * 2
        * int(_get_value(p, "quantity", 1) or 1)
        / 1000
        for p in panels_list
    )
    if cut_length:
        items.append(PurchaseItem("Распил", round(cut_length, 2), "м", float(values.get("price_cut_m", 30)), "services"))
    edge_length = sum(float(b.get("length_m", 0)) for b in edge_bands)
    if edge_length:
        items.append(PurchaseItem("Кромление", round(edge_length * 1.1, 2), "м", float(values.get("price_edging_m", 40)), "services"))

    # Ряды системы 32 в оплату не идут: это перфорация под перестановку полки,
    # её сверлят одним проходом, а не поштучно. Считаем то, за что берут деньги:
    # конфирматы, чашки петель и крепления направляющих.
    paid_kinds = {"confirmat", "dowel", "hinge_cup", "hinge_mount", "slide"}
    drill_count = 0
    for panel in panels_list:
        points = _get_value(panel, "drilling_points", []) or []
        quantity = int(_get_value(panel, "quantity", 1) or 1)
        drill_count += quantity * sum(
            1
            for point in points
            if (point.get("hardware_type") if isinstance(point, dict) else None) in paid_kinds
        )
    if drill_count:
        items.append(PurchaseItem("Присадка", drill_count, "отв.", float(values.get("price_drilling_hole", 10)), "services"))
    return items, prices_are_defaults


def summarize_purchase(
    items: Iterable[PurchaseItem], settings: dict[str, Any] | None = None
) -> dict[str, float]:
    """Итоги закупки: материалы, фурнитура с крепежом, услуги цеха.

    Плюс цена для клиента: мастер умножает затраты на свой коэффициент —
    «затратил семнадцать тысяч, продал за сорок». Множитель берётся из настроек.
    """
    result = {"materials": 0.0, "hardware": 0.0, "services": 0.0}
    for item in items:
        bucket = "hardware" if item.category == "fasteners" else item.category
        result[bucket] = result.get(bucket, 0.0) + item.total_price
    result["total"] = sum(result.values())

    values = _settings(settings)
    multiplier = float(values.get("markup_multiplier") or 0)
    if multiplier > 1:
        result["markup_multiplier"] = multiplier
        result["client_price"] = result["total"] * multiplier

    return {key: round(value, 2) for key, value in result.items()}
