"""
Двухэтапный парсер PDF каталогов фурнитуры.

Этап 1: PyMuPDF — извлечение текста, поиск страниц с чертежами присадки (бесплатно)
Этап 2: OpenAI Vision — извлечение данных из чертежей (GPT-4o-mini, дёшево)
"""
import json
import os
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from openai import OpenAI

# Загружаем .env из папки etl_pipeline
load_dotenv(Path(__file__).parent / ".env")

from .config import (
    DRILLING_KEYWORDS,
    OPENAI_MODEL_CHEAP,
    MAX_PDF_PAGES,
    EXTRACTION_SCHEMA,
)


@dataclass
class PageInfo:
    """Информация о странице PDF."""
    page_num: int
    has_drilling_info: bool
    keywords_found: list[str]
    text_preview: str  # первые 500 символов


@dataclass
class DrillingData:
    """Данные присадки из каталога."""
    article: str
    name: str
    category: str
    drilling_diameter: float | None
    drilling_depth: float | None
    cup_diameter: float | None
    mounting_hole_distance: float | None
    edge_distance: float | None
    material_thickness: list[float] | None
    notes: str
    source_page: int
    source_file: str


def analyze_pdf_pages(pdf_path: Path) -> list[PageInfo]:
    """
    Этап 1: Анализ PDF — поиск страниц с информацией о присадке.
    Бесплатно, использует PyMuPDF.
    """
    pages_info = []

    doc = fitz.open(pdf_path)
    print(f"Анализируем {pdf_path.name}: {len(doc)} страниц")

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().lower()

        # Ищем ключевые слова
        found_keywords = [kw for kw in DRILLING_KEYWORDS if kw.lower() in text]
        has_drilling = len(found_keywords) >= 2  # минимум 2 ключевых слова

        pages_info.append(PageInfo(
            page_num=page_num + 1,  # 1-indexed для удобства
            has_drilling_info=has_drilling,
            keywords_found=found_keywords,
            text_preview=text[:500],
        ))

    doc.close()

    drilling_pages = [p for p in pages_info if p.has_drilling_info]
    print(f"Найдено {len(drilling_pages)} страниц с информацией о присадке")

    return pages_info


def split_pdf_by_pages(pdf_path: Path, page_numbers: list[int], output_dir: Path) -> list[Path]:
    """
    Разбивает PDF на отдельные файлы по указанным страницам.
    Возвращает список путей к созданным файлам.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files = []

    doc = fitz.open(pdf_path)

    # Группируем страницы по MAX_PDF_PAGES для API лимита
    for i in range(0, len(page_numbers), MAX_PDF_PAGES):
        batch = page_numbers[i:i + MAX_PDF_PAGES]

        new_doc = fitz.open()
        for page_num in batch:
            new_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)

        output_path = output_dir / f"{pdf_path.stem}_pages_{batch[0]}-{batch[-1]}.pdf"
        new_doc.save(output_path)
        new_doc.close()

        created_files.append(output_path)
        print(f"Создан: {output_path.name} ({len(batch)} страниц)")

    doc.close()
    return created_files


def extract_drilling_data_vision(pdf_path: Path, client: OpenAI) -> list[dict]:
    """
    Этап 2: Извлечение данных присадки через OpenAI Vision.
    Использует GPT-4o-mini для экономии.
    """
    # Загружаем файл в OpenAI
    with open(pdf_path, "rb") as f:
        file = client.files.create(file=f, purpose="user_data")

    prompt = f"""Извлеки данные о присадке (сверлении) мебельной фурнитуры из этого PDF.

Для каждой позиции извлеки:
{json.dumps(EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

Верни JSON массив объектов. Пример:
[
  {{
    "article": "H301A02",
    "name": "Петля накладная с доводчиком",
    "category": "петля",
    "drilling_diameter": 35,
    "drilling_depth": 12,
    "cup_diameter": 35,
    "mounting_hole_distance": 52,
    "edge_distance": 5,
    "material_thickness": [16, 18, 19],
    "notes": "Угол открывания 110°"
  }}
]

Если данных нет — верни пустой массив [].
Только JSON, без markdown обёртки."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL_CHEAP,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "file",
                        "file": {
                            "file_id": file.id,
                        }
                    },
                    {"type": "text", "text": prompt},
                ]
            }],
            max_tokens=4096,
        )
        result_text = response.choices[0].message.content.strip()
        print(f"API ответ (первые 500 символов): {result_text[:500]}")
    except Exception as e:
        print(f"Ошибка API: {e}")
        client.files.delete(file.id)
        return []

    # Удаляем файл после использования
    client.files.delete(file.id)

    # Парсим ответ

    # Убираем возможную markdown обёртку
    if result_text.startswith("```"):
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]

    try:
        return json.loads(result_text)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        print(f"Ответ: {result_text[:500]}")
        return []


def process_catalog(pdf_path: Path, output_dir: Path) -> list[DrillingData]:
    """
    Полный pipeline обработки каталога.
    """
    print(f"\n{'='*60}")
    print(f"Обработка каталога: {pdf_path.name}")
    print(f"{'='*60}\n")

    # Этап 1: Анализ страниц (бесплатно)
    pages_info = analyze_pdf_pages(pdf_path)
    drilling_pages = [p.page_num for p in pages_info if p.has_drilling_info]

    if not drilling_pages:
        print("Не найдено страниц с информацией о присадке!")
        return []

    print(f"\nСтраницы с присадкой: {drilling_pages[:20]}{'...' if len(drilling_pages) > 20 else ''}")

    # Разбиваем PDF на части
    temp_dir = output_dir / "temp"
    split_files = split_pdf_by_pages(pdf_path, drilling_pages, temp_dir)

    # Этап 2: Извлечение через Vision (платно)
    client = OpenAI()
    all_data = []

    for split_file in split_files:
        print(f"\nОтправляем в OpenAI Vision: {split_file.name}")
        data = extract_drilling_data_vision(split_file, client)

        # Добавляем source info
        for item in data:
            item["source_file"] = pdf_path.name

        all_data.extend(data)
        print(f"Извлечено позиций: {len(data)}")

    # Сохраняем результат
    output_file = output_dir / f"{pdf_path.stem}_drilling_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\nРезультат сохранён: {output_file}")
    print(f"Всего извлечено позиций: {len(all_data)}")

    return all_data


if __name__ == "__main__":
    from .config import CATALOGS_DIR, OUTPUT_DIR

    # Пример использования
    pdf_files = list(CATALOGS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"PDF файлы не найдены в {CATALOGS_DIR}")
    else:
        for pdf_file in pdf_files:
            process_catalog(pdf_file, OUTPUT_DIR)
