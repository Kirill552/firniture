"""Загрузка результатов каталогового ETL в hardware_items."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import SessionLocal
from api.models import HardwareItem
from shared.embeddings import concat_hardware_item_text, embed_text, get_embed_version

Embedder = Callable[[str], Awaitable[list[float]]]


@dataclass(slots=True)
class LoadReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    embeddings_created: int = 0
    embeddings_failed: int = 0
    written: bool = False


def _params(item: dict[str, Any]) -> dict[str, Any]:
    params = dict(item.get("params") or {})
    params["needs_review"] = bool(item.get("needs_review", False))
    if item.get("page") is not None:
        params["page"] = item["page"]
    return params


def _merge_params(existing: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    """Дополняет карточку, но не обесценивает её.

    В базе уже лежат разборы прошлых парсеров: серия, межосевое расстояние, отступ
    отверстия. Наш конвейер таких полей не даёт, поэтому существующее значение
    всегда важнее пришедшего: затереть проверенный размер пустотой — потерять присадку.
    """
    merged = dict(existing or {})
    for key, value in incoming.items():
        if value is None:
            continue
        if key in ("needs_review", "page"):
            merged[key] = value
            continue
        if merged.get(key) is None:
            merged[key] = value
    return merged


def _changed(row: HardwareItem, item: dict[str, Any], params: dict[str, Any]) -> bool:
    return any(
        (
            row.brand != item.get("brand"),
            row.type != item.get("type", "прочее"),
            row.name != _resolved_name(row, item),
            row.params != params,
        )
    )


def _resolved_name(row: HardwareItem, item: dict[str, Any]) -> str | None:
    """Имя позиции не улучшаем догадками из вёрстки.

    Экстрактор берёт ближайшую строку страницы, и это бывает обрывок вроде
    «и полный артикул тоже: H31». Уже сохранённое название каталога всегда
    точнее, поэтому заполняем только пустое поле.
    """
    if row.name:
        return row.name
    candidate = (item.get("name") or "").strip()
    return candidate or None


def _apply(row: HardwareItem, item: dict[str, Any], params: dict[str, Any]) -> None:
    row.brand = item.get("brand")
    row.type = item.get("type", "прочее")
    row.name = _resolved_name(row, item)
    row.params = params


async def _find(session: AsyncSession, item: dict[str, Any]) -> HardwareItem | None:
    query = select(HardwareItem).where(
        and_(HardwareItem.sku == item["sku"], HardwareItem.brand == item.get("brand"))
    )
    return (await session.execute(query)).scalar_one_or_none()


def _merge_duplicates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Схлопывает повторы бренда с артикулом внутри одного прогона.

    Vision видит одну и ту же петлю на развороте дважды, а таблица допускает
    артикул один раз. Непустые параметры из повторов дополняют первую запись.
    """
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    for item in items:
        sku = str(item.get("sku", "")).strip()
        if not sku:
            continue
        item["sku"] = sku
        key = (str(item.get("brand") or ""), sku)
        if key not in merged:
            merged[key] = item
            order.append(key)
            continue
        target_params = merged[key].setdefault("params", {}) or {}
        for name, value in (item.get("params") or {}).items():
            if target_params.get(name) is None and value is not None:
                target_params[name] = value
        merged[key]["params"] = target_params
    return [merged[key] for key in order]


async def load_items(
    items: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    embedder: Embedder | None = embed_text,
    session: AsyncSession | None = None,
) -> LoadReport:
    """Загрузить позиции; при dry_run только посчитать изменения."""
    report = LoadReport(written=not dry_run)
    own_session = session is None
    active_session = session or SessionLocal()
    try:
        for item in _merge_duplicates(items):
            sku = item["sku"]
            incoming = _params(item)
            row = await _find(active_session, item)
            params = _params(item) if row is None else _merge_params(row.params, incoming)
            if row is None:
                report.added += 1
                if dry_run:
                    continue
                row = HardwareItem(sku=sku)
                _apply(row, item, params)
                active_session.add(row)
                await active_session.flush()
                changed = True
            elif _changed(row, item, params):
                report.updated += 1
                if dry_run:
                    continue
                _apply(row, item, params)
                row.embedding = None
                row.embedding_version = None
                changed = True
            else:
                report.unchanged += 1
                continue
            if embedder is not None and not dry_run and changed:
                try:
                    row.embedding = await embedder(concat_hardware_item_text(row))
                    row.embedding_version = get_embed_version()
                    report.embeddings_created += 1
                except Exception:
                    row.embedding = None
                    row.embedding_version = None
                    report.embeddings_failed += 1
        if not dry_run:
            await active_session.commit()
    except Exception:
        if not dry_run:
            await active_session.rollback()
        raise
    finally:
        if own_session:
            await active_session.close()
    return report


async def load_file(path: Path, *, dry_run: bool = False) -> LoadReport:
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("Ожидался JSON-массив позиций")
    return await load_items(items, dry_run=dry_run)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Загрузка каталога в hardware_items")
    parser.add_argument("path", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="только показать изменения")
    args = parser.parse_args()
    report = asyncio.run(load_file(args.path, dry_run=args.dry_run))
    mode = "сухой прогон" if args.dry_run else "запись"
    print(
        f"{mode}: добавится {report.added}, обновится {report.updated}, "
        f"без изменений {report.unchanged}; embeddings: "
        f"создано {report.embeddings_created}, ошибок {report.embeddings_failed}"
    )


if __name__ == "__main__":
    _main()
