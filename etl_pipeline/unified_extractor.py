"""
Единый парсер для направляющих, подъёмников и опор Boyard.

Категории:
- SB: направляющие СТАРТ (роликовые с металлическими боковинами)
- DB88xx: направляющие B-Slide (скрытого монтажа)
- DB45xx/DB17xx: шариковые направляющие
- DS: роликовые направляющие
- MB: направляющие Metabox-типа
- GL: газлифты и подъёмники
- N: опоры и колёсики
"""
import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from typing import Optional

from .config import OUTPUT_DIR, CATALOGS_DIR


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SlideItem:
    """Направляющая для ящиков."""
    article: str                    # Полный артикул (SB09W.1/300)
    base_code: str                  # Базовый код (SB09)
    name: str                       # Название серии (СТАРТ, B-Slide)
    category: str                   # Подкатегория (шариковая, роликовая, скрытого монтажа)
    slide_type: str                 # Тип (ball_bearing, roller, concealed)

    # Размеры
    length: int | None = None       # Длина (мм)
    drawer_height: int | None = None  # Высота боковины (для MB/SB)

    # Характеристики
    load_capacity: float | None = None  # Нагрузка (кг)
    extension: str | None = None    # Выдвижение (full/partial)
    soft_close: bool = False        # Доводчик
    push_to_open: bool = False      # Открывание нажатием

    # Мета
    color: str | None = None
    pack_quantity: int = 1
    source_page: int = 0
    source_file: str = ""


@dataclass
class LifterItem:
    """Газлифт/подъёмник для фасадов."""
    article: str                    # GL102GR/50/3
    base_code: str                  # GL102
    name: str                       # Название серии
    category: str                   # газлифт, подъёмник

    # Характеристики
    force: int | None = None        # Усилие в Ньютонах
    length: int | None = None       # Длина (мм)
    stroke: int | None = None       # Ход (мм)
    opening_angle: int | None = None  # Угол открывания (градусы)

    # Мета
    color: str | None = None
    pack_quantity: int = 1
    source_page: int = 0
    source_file: str = ""


@dataclass
class SupportItem:
    """Мебельная опора/колёсико."""
    article: str                    # N301CP/CP.1
    base_code: str                  # N301
    name: str                       # Название
    category: str                   # опора, колёсико

    # Размеры
    height: int | None = None       # Высота (мм)
    adjustment_range: int | None = None  # Диапазон регулировки (мм)
    diameter: int | None = None     # Диаметр (для колёс)

    # Характеристики
    load_capacity: float | None = None  # Нагрузка (кг)
    with_brake: bool = False        # С тормозом

    # Мета
    color: str | None = None
    pack_quantity: int = 1
    source_page: int = 0
    source_file: str = ""


# =============================================================================
# ПАТТЕРНЫ АРТИКУЛОВ
# =============================================================================

PATTERNS = {
    # СТАРТ серия: SB09W.1/300, SB28GR.1/450, SB08W.1/270
    "sb_full": re.compile(r'\b(SB\d{2}(?:W|GR|GRPH)\.(?:1|2)/\d{3})\b'),
    "sb_base": re.compile(r'\b(SB\d{2})\b'),

    # B-Slide: DB8881Zn/300, DB8882Zn/550, DB7772Zn/400
    "bslide_full": re.compile(r'\b(DB(?:88|89|77)\d{2}Zn/\d{3})\b'),
    "bslide_base": re.compile(r'\b(DB88\d{2}|DB89\d{2}|DB77\d{2})\b'),

    # Шариковые DB45xx/DB17xx: DB4505Zn/300, DB4518Zn/500, DB1711Zn/250
    "ball_full": re.compile(r'\b(DB(?:45|17)\d{2}Zn/\d{3})\b'),
    "ball_base": re.compile(r'\b(DB45\d{2}|DB17\d{2})\b'),

    # Роликовые DS: DS03W.1/250, DS 03W.1/300
    "ds_full": re.compile(r'\bDS\s*(\d{2})(W|GR)?\.(\d)/(\d{3})\b'),
    "ds_base": re.compile(r'\b(DS\d{2})\b'),

    # Metabox MB: MB08601W/500, MB05401W/450, MB00081W/450
    "mb_full": re.compile(r'\b(MB\d{5}(?:W|GR)/\d{3})\b'),
    "mb_base": re.compile(r'\b(MB\d{5})\b'),

    # Газлифты GL: GL102GR/50/3, GL107W/100/3
    "gl_full": re.compile(r'\b(GL\d{3}(?:W|GR|BL)?/\d{2,3}/\d)\b'),
    "gl_base": re.compile(r'\b(GL\d{3})\b'),

    # Опоры N: N301CP/CP.1, N310BL.2
    "n_full": re.compile(r'\b(N\d{3}[A-Z]{2,4}(?:/[A-Z]{2,4})?\.?\d?)\b'),
    "n_base": re.compile(r'\b(N\d{3})\b'),

    # Длина из артикула: /300, /450, /550
    "length": re.compile(r'/(\d{3})(?:\s|$|\))'),

    # Усилие газлифта: /50/, /80/, /100/
    "force": re.compile(r'/(\d{2,3})/'),

    # Размеры в тексте: 300 мм, 450мм
    "dimension_mm": re.compile(r'(\d{3})\s*мм'),

    # Нагрузка: 30 кг, 45кг
    "load_kg": re.compile(r'(\d{1,3})\s*кг'),
}

# Цвета
COLOR_CODES = {
    "W": "белый",
    "GR": "серый",
    "GRPH": "графит",
    "BL": "чёрный",
    "CP": "хром",
    "Zn": "цинк",
    "NI": "никель",
}

# Серии направляющих
SLIDE_SERIES = {
    "SB": {"name": "СТАРТ", "type": "roller", "category": "роликовая с боковиной"},
    "DB88": {"name": "B-Slide", "type": "concealed", "category": "скрытого монтажа"},
    "DB89": {"name": "B-Slide PRO", "type": "concealed", "category": "скрытого монтажа"},
    "DB77": {"name": "B-Slide SLIM", "type": "concealed", "category": "скрытого монтажа"},
    "DB45": {"name": "шариковая", "type": "ball_bearing", "category": "шариковая"},
    "DB17": {"name": "телескопическая", "type": "ball_bearing", "category": "шариковая"},
    "DS": {"name": "роликовая", "type": "roller", "category": "роликовая"},
    "MB": {"name": "Metabox", "type": "metabox", "category": "роликовая с боковиной"},
}

# Модели газлифтов
LIFTER_MODELS = {
    "GL102": {"name": "VERSO", "angle": 80},
    "GL103": {"name": "VERSO PUSH", "angle": 80},
    "GL104": {"name": "RECTO", "angle": 90},
    "GL105": {"name": "RECTO PUSH", "angle": 90},
    "GL106": {"name": "VERSO-II", "angle": 100},
    "GL107": {"name": "VERSO-II PUSH", "angle": 100},
    "GL110": {"name": "GAS SPRING", "angle": None},
}


# =============================================================================
# ФУНКЦИИ ИЗВЛЕЧЕНИЯ
# =============================================================================

def extract_color(article: str) -> str | None:
    """Извлекает цвет из артикула."""
    for code, name in COLOR_CODES.items():
        if code in article.upper():
            return name
    return None


def extract_length(article: str) -> int | None:
    """Извлекает длину из артикула."""
    match = PATTERNS["length"].search(article)
    if match:
        return int(match.group(1))
    return None


def extract_force(article: str) -> int | None:
    """Извлекает усилие газлифта из артикула."""
    match = PATTERNS["force"].search(article)
    if match:
        return int(match.group(1))
    return None


def detect_slide_series(article: str) -> dict | None:
    """Определяет серию направляющей по артикулу."""
    for prefix, info in SLIDE_SERIES.items():
        if article.upper().startswith(prefix):
            return info
    return None


def parse_slides_page(text: str, page_num: int, source_file: str) -> list[SlideItem]:
    """Парсит страницу с направляющими."""
    items = []
    seen = set()

    # Ищем все артикулы направляющих
    for pattern_name in ["sb_full", "bslide_full", "ball_full", "ds_full", "mb_full"]:
        for match in PATTERNS[pattern_name].finditer(text):
            article = match.group(1)
            if article in seen:
                continue
            seen.add(article)

            # Определяем серию
            series_info = detect_slide_series(article)
            if not series_info:
                continue

            # Извлекаем базовый код
            base_code = article.split(".")[0].split("/")[0][:4]
            if base_code.startswith("MB"):
                base_code = article[:5]  # MB086

            # Извлекаем параметры
            length = extract_length(article)
            color = extract_color(article)

            # Нагрузка из текста (ищем рядом с артикулом)
            load_match = PATTERNS["load_kg"].search(text)
            load = int(load_match.group(1)) if load_match else None

            # Доводчик
            soft_close = any(kw in text.lower() for kw in ["soft", "доводчик", "амортизат"])
            push_open = any(kw in text.lower() for kw in ["push", "нажатием", "открыв"])

            item = SlideItem(
                article=article,
                base_code=base_code,
                name=series_info["name"],
                category=series_info["category"],
                slide_type=series_info["type"],
                length=length,
                color=color,
                load_capacity=load,
                soft_close=soft_close,
                push_to_open=push_open,
                source_page=page_num,
                source_file=source_file,
            )
            items.append(item)

    return items


def parse_lifters_page(text: str, page_num: int, source_file: str) -> list[LifterItem]:
    """Парсит страницу с газлифтами/подъёмниками."""
    items = []
    seen = set()

    for match in PATTERNS["gl_full"].finditer(text):
        article = match.group(1)
        if article in seen:
            continue
        seen.add(article)

        # Базовый код
        base_match = PATTERNS["gl_base"].search(article)
        base_code = base_match.group(1) if base_match else article[:5]

        # Модель
        model_info = LIFTER_MODELS.get(base_code, {"name": "газлифт", "angle": None})

        # Параметры
        force = extract_force(article)
        color = extract_color(article)

        item = LifterItem(
            article=article,
            base_code=base_code,
            name=model_info["name"],
            category="подъёмник" if "VERSO" in model_info["name"] or "RECTO" in model_info["name"] else "газлифт",
            force=force,
            opening_angle=model_info["angle"],
            color=color,
            source_page=page_num,
            source_file=source_file,
        )
        items.append(item)

    return items


def parse_supports_page(text: str, page_num: int, source_file: str) -> list[SupportItem]:
    """Парсит страницу с опорами."""
    items = []
    seen = set()

    for match in PATTERNS["n_full"].finditer(text):
        article = match.group(1)
        if article in seen:
            continue
        seen.add(article)

        # Базовый код
        base_match = PATTERNS["n_base"].search(article)
        base_code = base_match.group(1) if base_match else article[:4]

        # Категория по номеру
        num = int(base_code[1:])
        if 100 <= num < 200:
            category = "колёсико"
        elif 300 <= num < 400:
            category = "регулируемая опора"
        else:
            category = "опора"

        # Цвет
        color = extract_color(article)

        item = SupportItem(
            article=article,
            base_code=base_code,
            name=category,
            category=category,
            color=color,
            source_page=page_num,
            source_file=source_file,
        )
        items.append(item)

    return items


# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

def process_functional_catalog(
    pdf_path: Path,
    output_dir: Path = OUTPUT_DIR,
    verbose: bool = False,
    page_ranges: dict[str, tuple[int, int]] | None = None
) -> dict[str, list]:
    """
    Обрабатывает каталог функциональной фурнитуры Boyard.

    Args:
        pdf_path: Путь к PDF каталогу
        output_dir: Папка для сохранения результатов
        verbose: Подробный вывод
        page_ranges: Диапазоны страниц по категориям
            {
                "slides_start": (106, 170),
                "slides_bslide": (174, 195),
                "slides_ball": (200, 230),
                "slides_roller": (212, 270),
                "lifters": (272, 285),
                "supports": (286, 300),
            }
    """
    # Диапазоны страниц по умолчанию (из оглавления каталога 2024)
    if page_ranges is None:
        page_ranges = {
            "slides_start": (106, 170),     # СТАРТ, SB серия
            "slides_bslide": (174, 195),    # B-Slide, DB88/89/77
            "slides_ball": (196, 210),      # Шариковые DB45/DB17
            "slides_roller": (212, 270),    # Роликовые DS, MB
            "lifters": (272, 285),          # Газлифты GL
            "supports": (286, 310),         # Опоры N
        }

    results = {
        "slides": [],
        "lifters": [],
        "supports": [],
    }
    seen_articles = {
        "slides": set(),
        "lifters": set(),
        "supports": set(),
    }

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"\n{'='*60}")
    print(f"ETL: Каталог функциональной фурнитуры")
    print(f"Файл: {pdf_path.name} ({total_pages} страниц)")
    print(f"{'='*60}")

    # Обрабатываем направляющие
    print("\n[1/3] Направляющие...")
    for range_name in ["slides_start", "slides_bslide", "slides_ball", "slides_roller"]:
        if range_name not in page_ranges:
            continue
        start, end = page_ranges[range_name]
        end = min(end, total_pages)

        for page_num in range(start - 1, end):  # PDF индексация с 0
            page = doc[page_num]
            text = page.get_text()

            if len(text) < 50:
                continue

            items = parse_slides_page(text, page_num + 1, pdf_path.name)

            for item in items:
                if item.article not in seen_articles["slides"]:
                    seen_articles["slides"].add(item.article)
                    results["slides"].append(item)

            if verbose and items:
                print(f"  Стр. {page_num + 1}: {len(items)} направляющих")

    print(f"  Найдено: {len(results['slides'])} направляющих")

    # Обрабатываем подъёмники
    print("\n[2/3] Подъёмники и газлифты...")
    if "lifters" in page_ranges:
        start, end = page_ranges["lifters"]
        end = min(end, total_pages)

        for page_num in range(start - 1, end):
            page = doc[page_num]
            text = page.get_text()

            if len(text) < 50:
                continue

            items = parse_lifters_page(text, page_num + 1, pdf_path.name)

            for item in items:
                if item.article not in seen_articles["lifters"]:
                    seen_articles["lifters"].add(item.article)
                    results["lifters"].append(item)

            if verbose and items:
                print(f"  Стр. {page_num + 1}: {len(items)} подъёмников")

    print(f"  Найдено: {len(results['lifters'])} подъёмников")

    # Обрабатываем опоры
    print("\n[3/3] Опоры и колёсики...")
    if "supports" in page_ranges:
        start, end = page_ranges["supports"]
        end = min(end, total_pages)

        for page_num in range(start - 1, end):
            page = doc[page_num]
            text = page.get_text()

            if len(text) < 50:
                continue

            items = parse_supports_page(text, page_num + 1, pdf_path.name)

            for item in items:
                if item.article not in seen_articles["supports"]:
                    seen_articles["supports"].add(item.article)
                    results["supports"].append(item)

            if verbose and items:
                print(f"  Стр. {page_num + 1}: {len(items)} опор")

    print(f"  Найдено: {len(results['supports'])} опор")

    doc.close()

    # Сохраняем результаты
    output_dir.mkdir(parents=True, exist_ok=True)

    for category, items in results.items():
        if not items:
            continue

        output_path = output_dir / f"{pdf_path.stem}_{category}.json"
        data = [asdict(item) for item in items]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\nСохранено: {output_path.name} ({len(items)} позиций)")

    # Статистика
    print(f"\n{'='*60}")
    print("ИТОГО:")
    print(f"  Направляющие: {len(results['slides'])}")
    print(f"  Подъёмники:   {len(results['lifters'])}")
    print(f"  Опоры:        {len(results['supports'])}")
    print(f"  ВСЕГО:        {sum(len(v) for v in results.values())}")

    return results


if __name__ == "__main__":
    # Тест на каталоге функциональной фурнитуры
    pdf_files = list(CATALOGS_DIR.glob("*функцион*.pdf"))

    if pdf_files:
        process_functional_catalog(pdf_files[0], verbose=True)
    else:
        print(f"Каталог функциональной фурнитуры не найден в {CATALOGS_DIR}")
