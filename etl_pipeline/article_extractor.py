"""
Бесплатный парсер артикулов из PDF каталогов Boyard.

Использует PyMuPDF для извлечения текста и регулярные выражения для поиска артикулов.
Стандартные параметры присадки применяются из config.py.
"""
import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass, asdict, field
from collections import defaultdict

from .config import (
    ARTICLE_PATTERNS,
    CATEGORY_BY_PREFIX,
    HINGE_TYPE_KEYWORDS,
    HINGE_TYPES,
    HINGE_SERIES,
    STANDARD_DRILLING_PARAMS,
    SKIP_PAGES,
    MIN_PAGE_TEXT_LENGTH,
    OUTPUT_DIR,
)


@dataclass
class HardwareItem:
    """Позиция фурнитуры с параметрами присадки."""
    article: str
    name: str
    category: str
    series: str | None = None
    hinge_type: str | None = None  # slide_on, clip_on, mini

    # Параметры присадки (из стандартов)
    cup_diameter: float | None = None
    drilling_depth: float | None = None
    center_distance: float | None = None
    hole_offset: float | None = None
    mounting_hole_diameter: float | None = None

    # Мета
    source_page: int = 0
    source_file: str = ""
    features: list[str] = field(default_factory=list)


def extract_articles_from_text(text: str) -> set[str]:
    """Извлекает артикулы из текста по паттернам."""
    articles = set()

    for pattern in ARTICLE_PATTERNS[:3]:  # Только специфичные паттерны Boyard
        matches = pattern.findall(text)
        for match in matches:
            # Фильтруем слишком короткие и слишком длинные
            if 4 <= len(match) <= 40:
                articles.add(match)

    return articles


def detect_category(article: str) -> str:
    """Определяет категорию по префиксу артикула."""
    for prefix, category in CATEGORY_BY_PREFIX.items():
        if article.upper().startswith(prefix):
            return category
    return "прочее"


def detect_hinge_type(text: str) -> str | None:
    """Определяет тип петли по тексту страницы."""
    text_lower = text.lower()

    for hinge_type, keywords in HINGE_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return hinge_type

    return "clip_on"  # По умолчанию для современных петель


def detect_series(text: str) -> str | None:
    """Определяет серию петли по тексту."""
    text_upper = text.upper()

    # Проверяем в порядке от более специфичного к общему
    if "NEO HIT" in text_upper:
        return "NEO HIT"
    if "NEO" in text_upper:
        return "NEO"
    if "CLASSICO" in text_upper:
        return "CLASSICO"
    if "MODERN" in text_upper:
        return "MODERN"

    return None


def extract_page_context(text: str) -> dict:
    """Извлекает контекст страницы: серию, модель, категорию."""
    context = {
        "series": None,
        "model": None,
        "category": None,
    }

    lines = text.split('\n')
    text_upper = text.upper()

    # Ищем серию
    series_patterns = [
        ("NEO HIT", "NEO HIT"),
        ("CASUAL", "CASUAL"),
        ("PROFI", "PROFI"),
        ("MODERN", "MODERN"),
        ("CLASSICO", "CLASSICO"),
        ("NEO", "NEO"),  # После NEO HIT, чтобы не перехватить
    ]
    for pattern, series_name in series_patterns:
        if pattern in text_upper:
            context["series"] = series_name
            break

    # Ищем модель (H3XX)
    model_match = re.search(r'\b(H3\d{2})\b', text)
    if model_match:
        context["model"] = model_match.group(1)

    # Категория
    if "петл" in text.lower():
        context["category"] = "Мебельная петля"
    elif "направляющ" in text.lower():
        context["category"] = "Направляющая"
    elif "подъёмник" in text.lower() or "подъемник" in text.lower():
        context["category"] = "Подъёмник"

    return context


def build_name(article: str, context: dict) -> str:
    """Собирает название из контекста страницы."""
    parts = []

    # Категория
    if context.get("category"):
        parts.append(context["category"])

    # Серия
    if context.get("series"):
        parts.append(context["series"])

    # Модель из артикула (H316A02 → H316)
    model_match = re.match(r'(H\d{3})', article)
    if model_match:
        parts.append(model_match.group(1))

    # Тип (A/B/C) если есть
    type_match = re.search(r'H\d{3}([ABC])', article)
    if type_match:
        type_map = {"A": "накладная", "B": "полунакладная", "C": "внутренняя"}
        parts.append(type_map.get(type_match.group(1), ""))

    return " ".join(filter(None, parts))


def apply_drilling_params(item: HardwareItem) -> HardwareItem:
    """Применяет стандартные параметры присадки к позиции."""
    if item.category != "петля":
        return item

    # Определяем тип петли и берём соответствующие параметры
    hinge_type = item.hinge_type or "clip_on"
    params = HINGE_TYPES.get(hinge_type, HINGE_TYPES["clip_on"])["params"]

    item.cup_diameter = params["cup_diameter"]
    item.drilling_depth = params["drilling_depth"]
    item.center_distance = params["center_distance"]
    item.hole_offset = params["hole_offset"]
    item.mounting_hole_diameter = params["mounting_hole_diameter"]

    # Добавляем features из серии
    if item.series and item.series in HINGE_SERIES:
        item.features = HINGE_SERIES[item.series].get("features", [])

    return item


def process_pdf(pdf_path: Path, verbose: bool = False) -> list[HardwareItem]:
    """
    Обрабатывает PDF каталог и извлекает все артикулы с параметрами.

    Бесплатно! Использует только PyMuPDF.
    """
    items = []
    seen_articles = set()  # Для дедупликации

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"Обработка: {pdf_path.name} ({total_pages} страниц)")

    for page_num in range(total_pages):
        # Пропускаем служебные страницы
        if (page_num + 1) in SKIP_PAGES:
            continue

        page = doc[page_num]
        text = page.get_text()

        # Пропускаем пустые страницы
        if len(text) < MIN_PAGE_TEXT_LENGTH:
            continue

        # Извлекаем артикулы
        articles = extract_articles_from_text(text)

        if not articles:
            continue

        # Определяем контекст страницы
        hinge_type = detect_hinge_type(text)
        series = detect_series(text)
        page_context = extract_page_context(text)

        if verbose:
            print(f"  Стр. {page_num + 1}: {len(articles)} артикулов, серия={series}, тип={hinge_type}")

        # Создаём записи для каждого артикула
        for article in articles:
            # Дедупликация
            if article in seen_articles:
                continue
            seen_articles.add(article)

            category = detect_category(article)
            name = build_name(article, page_context)

            item = HardwareItem(
                article=article,
                name=name,
                category=category,
                series=series or page_context.get("series"),
                hinge_type=hinge_type if category == "петля" else None,
                source_page=page_num + 1,
                source_file=pdf_path.name,
            )

            # Применяем стандартные параметры присадки
            item = apply_drilling_params(item)

            items.append(item)

    doc.close()

    # Статистика
    by_category = defaultdict(int)
    for item in items:
        by_category[item.category] += 1

    print(f"\nИзвлечено {len(items)} уникальных артикулов:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    return items


def save_results(items: list[HardwareItem], output_path: Path) -> None:
    """Сохраняет результаты в JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(item) for item in items]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nСохранено: {output_path}")


def process_catalog(pdf_path: Path, output_dir: Path = OUTPUT_DIR, verbose: bool = False) -> list[HardwareItem]:
    """
    Полный pipeline обработки каталога.

    Возвращает список HardwareItem с параметрами присадки.
    """
    print(f"\n{'='*60}")
    print(f"ETL: {pdf_path.name}")
    print(f"{'='*60}")

    items = process_pdf(pdf_path, verbose=verbose)

    if items:
        output_path = output_dir / f"{pdf_path.stem}_hardware.json"
        save_results(items, output_path)
    else:
        print("Артикулы не найдены!")

    return items


# Для тестирования
if __name__ == "__main__":
    from .config import CATALOGS_DIR

    pdf_files = list(CATALOGS_DIR.glob("*.pdf"))

    if pdf_files:
        # Тестируем на первом каталоге
        process_catalog(pdf_files[0], verbose=True)
    else:
        print(f"PDF не найдены в {CATALOGS_DIR}")
