#!/usr/bin/env python
"""
CLI для ETL pipeline каталогов фурнитуры Boyard.

Использование:
    uv run python -m etl_pipeline.run extract              # Извлечь петли
    uv run python -m etl_pipeline.run handles              # Извлечь ручки/крючки
    uv run python -m etl_pipeline.run slides               # Извлечь направляющие/подъёмники/опоры
    uv run python -m etl_pipeline.run slides --verbose     # С подробным выводом
    uv run python -m etl_pipeline.run stats                # Статистика по извлечённым данным
    uv run python -m etl_pipeline.run list                 # Список каталогов
    uv run python -m etl_pipeline.run params               # Показать параметры присадки
"""
import argparse
import json
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl_pipeline.config import CATALOGS_DIR, OUTPUT_DIR, STANDARD_DRILLING_PARAMS
from etl_pipeline.article_extractor import process_catalog
from etl_pipeline.handle_extractor import process_handles
from etl_pipeline.unified_extractor import process_functional_catalog


def cmd_extract(args):
    """Извлекает артикулы из PDF каталогов (бесплатно через PyMuPDF)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        # Конкретный файл
        pdf_path = CATALOGS_DIR / args.file
        if not pdf_path.exists():
            print(f"Файл не найден: {pdf_path}")
            return 1
        pdf_files = [pdf_path]
    else:
        # Все PDF
        pdf_files = list(CATALOGS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"PDF файлы не найдены в {CATALOGS_DIR}")
        return 1

    print(f"Найдено каталогов: {len(pdf_files)}")
    print(f"Стандартные параметры присадки: {STANDARD_DRILLING_PARAMS}")
    print()

    total_items = 0
    for pdf_file in pdf_files:
        items = process_catalog(pdf_file, OUTPUT_DIR, verbose=args.verbose)
        total_items += len(items)

    print(f"\n{'='*60}")
    print(f"ИТОГО: {total_items} артикулов из {len(pdf_files)} каталогов")
    return 0


def cmd_stats(args):
    """Показывает статистику по извлечённым данным."""
    json_files = list(OUTPUT_DIR.glob("*_hardware.json"))

    if not json_files:
        print("Нет данных. Сначала запустите: uv run python -m etl_pipeline.run extract")
        return 1

    total_items = 0
    by_category = {}
    by_series = {}
    with_drilling = 0

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        total_items += len(data)

        for item in data:
            cat = item.get("category", "прочее")
            by_category[cat] = by_category.get(cat, 0) + 1

            series = item.get("series")
            if series:
                by_series[series] = by_series.get(series, 0) + 1

            if item.get("cup_diameter"):
                with_drilling += 1

    print(f"Статистика RAG базы фурнитуры")
    print(f"{'='*40}")
    print(f"Всего артикулов: {total_items}")
    print(f"С параметрами присадки: {with_drilling}")
    print()
    print("По категориям:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print()
    if by_series:
        print("По сериям:")
        for series, count in sorted(by_series.items(), key=lambda x: -x[1]):
            print(f"  {series}: {count}")

    return 0


def cmd_list(args):
    """Список доступных каталогов."""
    pdf_files = list(CATALOGS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"PDF файлы не найдены в {CATALOGS_DIR}")
        return 1

    print(f"Каталоги в {CATALOGS_DIR}:")
    print(f"{'='*60}")
    for pdf_file in sorted(pdf_files):
        size_mb = pdf_file.stat().st_size / 1024 / 1024
        print(f"  {pdf_file.name} ({size_mb:.1f} MB)")

    return 0


def cmd_handles(args):
    """Извлекает ручки и крючки из каталога лицевой фурнитуры."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        pdf_path = CATALOGS_DIR / args.file
        if not pdf_path.exists():
            print(f"Файл не найден: {pdf_path}")
            return 1
        pdf_files = [pdf_path]
    else:
        # Ищем каталог лицевой фурнитуры
        pdf_files = list(CATALOGS_DIR.glob("*лицев*.pdf"))

    if not pdf_files:
        print(f"Каталог лицевой фурнитуры не найден в {CATALOGS_DIR}")
        return 1

    total_items = 0
    for pdf_file in pdf_files:
        items = process_handles(pdf_file, OUTPUT_DIR, verbose=args.verbose)
        total_items += len(items)

    print(f"\n{'='*60}")
    print(f"ИТОГО: {total_items} ручек/крючков")
    return 0


def cmd_slides(args):
    """Извлекает направляющие, подъёмники и опоры из каталога функциональной фурнитуры."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        pdf_path = CATALOGS_DIR / args.file
        if not pdf_path.exists():
            print(f"Файл не найден: {pdf_path}")
            return 1
        pdf_files = [pdf_path]
    else:
        # Ищем каталог функциональной фурнитуры
        pdf_files = list(CATALOGS_DIR.glob("*функцион*.pdf"))

    if not pdf_files:
        print(f"Каталог функциональной фурнитуры не найден в {CATALOGS_DIR}")
        return 1

    for pdf_file in pdf_files:
        results = process_functional_catalog(pdf_file, OUTPUT_DIR, verbose=args.verbose)

    total = sum(len(v) for v in results.values())
    print(f"\n{'='*60}")
    print(f"ИТОГО: {total} позиций (направляющие + подъёмники + опоры)")
    return 0


def cmd_show_params(args):
    """Показывает стандартные параметры присадки."""
    from etl_pipeline.config import HINGE_TYPES, FACADE_THICKNESS_MAP

    print("Стандартные параметры присадки Boyard")
    print("="*50)
    print("Источник: Каталог 2024, стр. 8-13")
    print()

    for hinge_type, info in HINGE_TYPES.items():
        print(f"\n{info['name']}:")
        print(f"  {info['description']}")
        params = info['params']
        print(f"  d (диаметр чашки): {params['cup_diameter']} мм")
        print(f"  P (глубина сверления): {params['drilling_depth']} мм")
        print(f"  L (межцентровое): {params['center_distance']} мм")
        print(f"  F (смещение): {params['hole_offset']} мм")
        print(f"  Саморезы: {params['mounting_hole_diameter']} мм")

    print("\n\nОтступ K по толщине фасада:")
    for thickness, params in FACADE_THICKNESS_MAP.items():
        print(f"  Фасад {thickness}мм: K={params['edge_distance']}мм, наложение={params['overlay']}мм")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="ETL pipeline для каталогов фурнитуры Boyard (бесплатно!)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Команды")

    # extract (петли)
    p_extract = subparsers.add_parser("extract", help="Извлечь петли из каталогов")
    p_extract.add_argument("--file", "-f", help="Конкретный PDF файл")
    p_extract.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    # handles (ручки)
    p_handles = subparsers.add_parser("handles", help="Извлечь ручки/крючки из каталога")
    p_handles.add_argument("--file", "-f", help="Конкретный PDF файл")
    p_handles.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    # slides (направляющие, подъёмники, опоры)
    p_slides = subparsers.add_parser("slides", help="Извлечь направляющие/подъёмники/опоры")
    p_slides.add_argument("--file", "-f", help="Конкретный PDF файл")
    p_slides.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    # stats
    subparsers.add_parser("stats", help="Статистика по данным")

    # list
    subparsers.add_parser("list", help="Список каталогов")

    # params
    subparsers.add_parser("params", help="Показать параметры присадки")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "extract": cmd_extract,
        "handles": cmd_handles,
        "slides": cmd_slides,
        "stats": cmd_stats,
        "list": cmd_list,
        "params": cmd_show_params,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
