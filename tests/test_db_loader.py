from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from api.database import SessionLocal
from api.models import HardwareItem
from etl_pipeline.db_loader import load_items


@pytest.fixture
async def clean_loader_items():
    skus = ["TEST-ETL-001", "TEST-ETL-002", "LOADER-MERGE-1"]
    async with SessionLocal() as session:
        await session.execute(delete(HardwareItem).where(HardwareItem.sku.in_(skus)))
        await session.commit()
    yield
    async with SessionLocal() as session:
        await session.execute(delete(HardwareItem).where(HardwareItem.sku.in_(skus)))
        await session.commit()


@pytest.mark.asyncio
async def test_loader_is_idempotent_and_persists_review_flag(clean_loader_items):
    items = [
        {
            "sku": "TEST-ETL-001",
            "name": "Первая петля",
            "type": "петля",
            "brand": "TEST",
            "params": {},
            "page": 4,
            "needs_review": True,
        },
        {
            "sku": "TEST-ETL-002",
            "name": "Вторая петля",
            "type": "петля",
            "brand": "TEST",
            "params": {"cup_diameter_mm": 35},
            "page": 5,
            "needs_review": False,
        },
    ]

    first = await load_items(items, dry_run=False, embedder=None)
    second = await load_items(items, dry_run=False, embedder=None)

    assert (first.added, first.updated) == (2, 0)
    assert (second.added, second.updated) == (0, 0)

    # Имя каталога не переписываем: экстрактор подсовывал обрывки вёрстки и на проде
    # затёр «Мебельная петля PROFI H301» строкой «и полный артикул тоже: H31».
    items[0]["name"] = "Обрывок вёрстки"
    items[0]["needs_review"] = False
    changed = await load_items(items, dry_run=False, embedder=None)
    assert (changed.added, changed.updated) == (0, 1)

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(HardwareItem).where(HardwareItem.sku == "TEST-ETL-001")
            )
        ).scalar_one()
        assert row.name == "Первая петля"
        assert row.params["needs_review"] is False
        assert row.params["page"] == 4


@pytest.mark.asyncio
async def test_loader_dry_run_does_not_write(clean_loader_items):
    items = [{"sku": "TEST-ETL-001", "name": "Сухой", "type": "петля", "brand": "TEST"}]
    report = await load_items(items, dry_run=True, embedder=None)
    assert (report.added, report.updated, report.written) == (1, 0, False)

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(HardwareItem).where(HardwareItem.sku == "TEST-ETL-001")
            )
        ).scalar_one_or_none()
        assert row is None


@pytest.mark.asyncio
async def test_existing_card_details_survive_reload(clean_loader_items):
    """Прошлые парсеры записали серию и межосевое расстояние — их нельзя терять.

    В боевой базе 1305 позиций с полями series, center_distance, hole_offset.
    Наш конвейер таких полей не даёт: если он перезапишет карточку целиком,
    присадка потеряет реальные размеры и мебельщик получит испорченную деталь.
    """
    async with SessionLocal() as session:
        session.add(
            HardwareItem(
                sku="LOADER-MERGE-1",
                brand="BOYARD",
                type="петля",
                name="Мебельная петля PROFI H301",
                params={
                    "series": "PROFI",
                    "cup_diameter": 35,
                    "center_distance": 48,
                    "hole_offset": 6,
                },
            )
        )
        await session.commit()

    await load_items(
        [
            {
                "sku": "LOADER-MERGE-1",
                "brand": "BOYARD",
                "type": "петля",
                "name": "",
                "params": {"opening_angle_deg": 105},
                "needs_review": True,
                "page": 44,
            }
        ],
        embedder=None,
    )

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(HardwareItem).where(HardwareItem.sku == "LOADER-MERGE-1")
            )
        ).scalar_one()
        assert row.params["series"] == "PROFI"
        assert row.params["center_distance"] == 48
        assert row.params["hole_offset"] == 6
        assert row.params["cup_diameter"] == 35
        assert row.params["opening_angle_deg"] == 105
        assert row.params["needs_review"] is True
        assert row.name == "Мебельная петля PROFI H301"
