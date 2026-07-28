
from datetime import date
from decimal import Decimal

import pytest

from api.supplier_prices import import_price_file, get_current_price


def test_csv_import_accepts_different_headers(tmp_path):
    source = tmp_path / "prices.csv"
    source.write_text(
        "Код;Розница;Ед. изм.;Валюта\nH305B02;1 250,50;шт;RUB\n",
        encoding="utf-8-sig",
    )

    result = import_price_file(source, "Тестовый поставщик", price_date=date(2026, 7, 1))

    assert result.imported == 1
    assert result.rejected == []
    assert result.rows[0].sku == "H305B02"
    assert result.rows[0].price == Decimal("1250.50")


def test_xlsx_import_accepts_sku_and_price_headers(tmp_path):
    from openpyxl import Workbook

    source = tmp_path / "prices.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["SKU", "Опт"])
    sheet.append(["ABC-1", 42.5])
    workbook.save(source)

    result = import_price_file(source, "Поставщик", price_date=date(2026, 7, 1))

    assert result.imported == 1
    assert result.rows[0].price == Decimal("42.50")


@pytest.mark.asyncio
async def test_save_import_adds_each_version():
    from api.models import Supplier

    class Session:
        def __init__(self):
            self.supplier = Supplier(name="Поставщик")
            self.saved = []

        async def scalar(self, query):
            return self.supplier

        def add_all(self, rows):
            self.saved.extend(rows)

        async def commit(self):
            return None

    from api.supplier_prices import PriceImportResult, PriceRow, save_price_import

    session = Session()
    row = PriceRow("ABC-1", Decimal("10"), "RUB", "шт", date(2026, 7, 1), "a.csv")
    await save_price_import(session, "Поставщик", PriceImportResult([row], []))
    await save_price_import(session, "Поставщик", PriceImportResult([row], []))

    assert len(session.saved) == 2


def test_csv_import_rejects_missing_sku(tmp_path):
    source = tmp_path / "prices.csv"
    source.write_text("Артикул;Цена\n;100\n", encoding="utf-8-sig")

    result = import_price_file(source, "Поставщик")

    assert len(result.rejected) == 1
    assert "артикул" in result.rejected[0].reason.lower()


@pytest.mark.asyncio
async def test_current_price_uses_latest_version():
    class Session:
        async def scalar(self, query):
            return Decimal("120.00")

    value = await get_current_price(Session(), "ABC-1", "supplier")

    assert value == Decimal("120.00")
