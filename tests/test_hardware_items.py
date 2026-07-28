from __future__ import annotations

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from api.ai_tools import handle_check_hardware_compatibility, handle_get_hardware_details
from api.database import SessionLocal
from api.models import HardwareItem


SKU = "TEST-DUPLICATE-SKU"


@pytest.fixture
async def clean_hardware_items():
    async with SessionLocal() as session:
        await session.execute(delete(HardwareItem).where(HardwareItem.sku == SKU))
        await session.commit()
    yield
    async with SessionLocal() as session:
        await session.execute(delete(HardwareItem).where(HardwareItem.sku == SKU))
        await session.commit()


def make_item(brand: str) -> HardwareItem:
    return HardwareItem(sku=SKU, brand=brand, type="hinge", name=f"{brand} item")


@pytest.mark.asyncio
async def test_same_sku_is_allowed_for_different_brands(clean_hardware_items):
    async with SessionLocal() as session:
        session.add_all([make_item("AKS"), make_item("AKS PLUS")])
        await session.commit()


@pytest.mark.asyncio
async def test_same_sku_is_rejected_inside_one_brand(clean_hardware_items):
    async with SessionLocal() as session:
        session.add_all([make_item("AKS"), make_item("AKS")])
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_ai_hardware_details_picks_deterministic_item_for_duplicate_sku(clean_hardware_items):
    async with SessionLocal() as session:
        session.add_all([make_item("AKS PLUS"), make_item("AKS")])
        await session.commit()

    result = await handle_get_hardware_details(SKU)

    assert result["success"] is True
    assert result["item"]["brand"] == "AKS"


@pytest.mark.asyncio
async def test_ai_compatibility_picks_deterministic_item_for_duplicate_sku(clean_hardware_items):
    async with SessionLocal() as session:
        first = make_item("AKS PLUS")
        first.thickness_min_mm = 20
        second = make_item("AKS")
        second.thickness_min_mm = 10
        session.add_all([first, second])
        await session.commit()

    result = await handle_check_hardware_compatibility(SKU, "ЛДСП", 15)

    assert result["success"] is True
    assert result["thickness_compatible"] is True
