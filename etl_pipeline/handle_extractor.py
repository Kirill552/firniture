"""
Парсер каталога ручек и крючков Boyard.

Извлекает:
- Артикулы (RS/RC/K серии)
- Названия серий (DOLCE, STARK, HYGGE...)
- Размеры (N, L, H, D)
- Межцентровое расстояние (для присадки)
- Вес
- Цвета
"""
import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass, asdict, field
from collections import defaultdict

from .config import OUTPUT_DIR


@dataclass
class HandleItem:
    """Позиция ручки/крючка."""
    article: str                    # RS530AC.1/128
    base_code: str                  # RS530
    name: str                       # DOLCE
    category: str                   # ручка-скоба, ручка-кнопка, крючок

    # Размеры (мм)
    center_distance: int | None = None   # N — межцентровое (главное для присадки!)
    length: int | None = None            # L — общая длина
    height: int | None = None            # H — высота
    depth: int | None = None             # D — глубина/выступ

    # Присадка
    hole_diameter: int = 5               # Диаметр отверстия под винт (стандарт M4)
    hole_count: int = 1                  # 1 для кнопки, 2 для скобы

    # Мета
    weight: int | None = None            # Вес в граммах
    color: str | None = None             # Цвет
    source_page: int = 0
    source_file: str = ""


# Паттерны для парсинга
HANDLE_PATTERNS = {
    # Полный артикул: RS530AC.1/128
    "full_article": re.compile(r'\b(R[SC]\d{3}[A-Z]{1,4}\.\d/\d{2,3})\b'),

    # Артикул кнопки: RC530AC.1
    "knob_article": re.compile(r'\b(RC\d{3}[A-Z]{1,4}\.\d)\b'),

    # Базовый код: RS530, RC530
    "base_code": re.compile(r'\b(R[SC]\d{3})\b'),

    # Крючок: K100, K204.05
    "hook_code": re.compile(r'\b(K\d{3}(?:\.\d{2})?)\b'),

    # Размеры N L H D в таблице
    "dimensions_header": re.compile(r'N\s+L\s+H\s+D'),
    "dimensions_values": re.compile(r'(\d{2,3})\s+(\d{2,3})\s+(\d{2,3})\s+(\d{2,3})'),

    # Размеры L H D (для кнопок)
    "dimensions_lhd": re.compile(r'L\s+H\s+D'),
    "dimensions_lhd_values": re.compile(r'^(\d{2,3})\s+(\d{2,3})\s+(\d{2,3})$', re.MULTILINE),

    # Вес
    "weight": re.compile(r'(\d{2,3})\s*(?:г|g)?\s*$', re.MULTILINE),

    # Название серии (заглавные латинские буквы)
    "series_name": re.compile(r'^([A-Z]{3,15})$', re.MULTILINE),
}

# Цвета Boyard
COLOR_CODES = {
    "AC": "Старинная медь",
    "AP": "Старинное олово",
    "MAB": "Матовая старинная латунь",
    "BAF": "Чёрное старинное железо",
    "BAZ": "Чернёный старинный цинк",
    "RCHMP": "Розовое шампанское",
    "CP": "Хром",
    "SN": "Матовый никель",
    "BN": "Чёрный никель",
    "AB": "Старинная бронза",
    "PB": "Полированная латунь",
}


def extract_color_from_article(article: str) -> str | None:
    """Извлекает цвет из артикула."""
    for code, name in COLOR_CODES.items():
        if code in article.upper():
            return name
    return None


def extract_center_distance_from_article(article: str) -> int | None:
    """Извлекает межцентровое из артикула (например RS530AC.1/128 → 128)."""
    match = re.search(r'/(\d{2,3})$', article)
    if match:
        return int(match.group(1))
    return None


def detect_category(article: str) -> str:
    """Определяет категорию по артикулу."""
    if article.startswith("RS"):
        return "ручка-скоба"
    elif article.startswith("RC"):
        return "ручка-кнопка"
    elif article.startswith("K"):
        return "крючок"
    elif article.startswith("RT"):
        return "торцевая ручка"
    elif article.startswith("RP"):
        return "профильная ручка"
    return "прочее"


def parse_handle_page(text: str, page_num: int, source_file: str) -> list[HandleItem]:
    """Парсит одну страницу каталога ручек."""
    items = []

    # Ищем название серии (DOLCE, RIGATA, IRIS...)
    series_name = None
    name_matches = HANDLE_PATTERNS["series_name"].findall(text)
    for name in name_matches:
        # Фильтруем служебные слова
        if name not in ["MODERN", "TRADITION", "TYPE", "ARTICLE", "WEIGHT", "COLOR"]:
            if len(name) >= 3:
                series_name = name
                break

    # Ищем базовые коды (RS530, RC530)
    base_codes = set(HANDLE_PATTERNS["base_code"].findall(text))
    hook_codes = set(HANDLE_PATTERNS["hook_code"].findall(text))
    all_codes = base_codes | hook_codes

    if not all_codes:
        return items

    # Ищем размеры N L H D
    dimensions = {}
    dim_match = HANDLE_PATTERNS["dimensions_values"].search(text)
    if dim_match:
        dimensions = {
            "N": int(dim_match.group(1)),
            "L": int(dim_match.group(2)),
            "H": int(dim_match.group(3)),
            "D": int(dim_match.group(4)),
        }

    # Ищем полные артикулы
    full_articles = HANDLE_PATTERNS["full_article"].findall(text)
    knob_articles = HANDLE_PATTERNS["knob_article"].findall(text)
    all_articles = set(full_articles + knob_articles)

    # Если нет полных артикулов, создаём записи из базовых кодов
    if not all_articles:
        for code in all_codes:
            category = detect_category(code)
            item = HandleItem(
                article=code,
                base_code=code,
                name=series_name or "",
                category=category,
                center_distance=dimensions.get("N"),
                length=dimensions.get("L"),
                height=dimensions.get("H"),
                depth=dimensions.get("D"),
                hole_count=2 if category == "ручка-скоба" else 1,
                source_page=page_num,
                source_file=source_file,
            )
            items.append(item)
    else:
        # Создаём записи из полных артикулов
        for article in all_articles:
            # Находим базовый код
            base_match = re.match(r'(R[SC]\d{3}|K\d{3})', article)
            base_code = base_match.group(1) if base_match else article[:5]

            category = detect_category(article)
            color = extract_color_from_article(article)
            center_dist = extract_center_distance_from_article(article)

            item = HandleItem(
                article=article,
                base_code=base_code,
                name=series_name or "",
                category=category,
                center_distance=center_dist or dimensions.get("N"),
                length=dimensions.get("L"),
                height=dimensions.get("H"),
                depth=dimensions.get("D"),
                hole_count=2 if category == "ручка-скоба" else 1,
                color=color,
                source_page=page_num,
                source_file=source_file,
            )
            items.append(item)

    return items


def process_handle_catalog(pdf_path: Path, verbose: bool = False) -> list[HandleItem]:
    """
    Обрабатывает каталог ручек Boyard.
    """
    items = []
    seen_articles = set()

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"Обработка: {pdf_path.name} ({total_pages} страниц)")

    # Пропускаем первые страницы (оглавление)
    start_page = 22 if total_pages > 50 else 0  # Ручки начинаются со стр. 22

    for page_num in range(start_page, total_pages):
        page = doc[page_num]
        text = page.get_text()

        # Пропускаем пустые и служебные страницы
        if len(text) < 100:
            continue

        # Парсим страницу
        page_items = parse_handle_page(text, page_num + 1, pdf_path.name)

        for item in page_items:
            # Дедупликация
            if item.article in seen_articles:
                continue
            seen_articles.add(item.article)
            items.append(item)

        if verbose and page_items:
            print(f"  Стр. {page_num + 1}: {len(page_items)} позиций")

    doc.close()

    # Статистика
    by_category = defaultdict(int)
    for item in items:
        by_category[item.category] += 1

    print(f"\nИзвлечено {len(items)} уникальных позиций:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    return items


def save_handle_results(items: list[HandleItem], output_path: Path) -> None:
    """Сохраняет результаты в JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(item) for item in items]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nСохранено: {output_path}")


def process_handles(pdf_path: Path, output_dir: Path = OUTPUT_DIR, verbose: bool = False) -> list[HandleItem]:
    """
    Полный pipeline обработки каталога ручек.
    """
    print(f"\n{'='*60}")
    print(f"ETL Ручки: {pdf_path.name}")
    print(f"{'='*60}")

    items = process_handle_catalog(pdf_path, verbose=verbose)

    if items:
        output_path = output_dir / f"{pdf_path.stem}_handles.json"
        save_handle_results(items, output_path)
    else:
        print("Позиции не найдены!")

    return items


if __name__ == "__main__":
    from .config import CATALOGS_DIR

    # Ищем каталог лицевой фурнитуры
    pdf_files = list(CATALOGS_DIR.glob("*лицев*.pdf"))

    if pdf_files:
        process_handles(pdf_files[0], verbose=True)
    else:
        print(f"Каталог лицевой фурнитуры не найден в {CATALOGS_DIR}")
