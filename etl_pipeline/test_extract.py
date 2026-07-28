"""Тест извлечения данных присадки из одной страницы."""
import json
import fitz
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()

# Извлекаем одну страницу с петлями (стр. 16 — NEO с амортизацией)
catalog_path = Path(__file__).parent.parent / "furnitura_catalogi" / "boyard" / "Каталог функциональной фурнитуры BOYARD 2024 .pdf"
output_path = Path(__file__).parent / "output" / "test_page_16.pdf"
output_path.parent.mkdir(parents=True, exist_ok=True)

# Извлекаем страницы 2-10 (техническая информация о петлях)
doc = fitz.open(catalog_path)
new_doc = fitz.open()
for page in range(1, 11):  # страницы 2-11 (0-indexed: 1-10)
    new_doc.insert_pdf(doc, from_page=page, to_page=page)
new_doc.save(output_path)
new_doc.close()
doc.close()

print(f"Извлечена страница 16: {output_path}")
print(f"Размер: {output_path.stat().st_size / 1024:.1f} KB")

# Загружаем в OpenAI
with open(output_path, "rb") as f:
    file = client.files.create(file=f, purpose="user_data")

print(f"Файл загружен: {file.id}")

# Запрос на извлечение данных присадки
prompt = """Это страница из каталога мебельной фурнитуры Boyard.

Извлеки ВСЕ данные о присадке (сверлении) для каждой позиции на этой странице.

Для каждой позиции найди:
- article: Артикул (например H301A02)
- name: Название
- cup_diameter: Диаметр чашки петли (обычно 35мм или 26мм)
- drilling_depth: Глубина сверления чашки (мм)
- mounting_hole_distance: Расстояние между крепёжными отверстиями (обычно 52мм)
- edge_distance: Отступ от края фасада (мм)
- material_thickness: Для каких толщин материала подходит

Верни JSON массив. Если на странице нет чертежей присадки — верни [].
"""

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "file", "file": {"file_id": file.id}},
                {"type": "text", "text": prompt},
            ]
        }],
        max_tokens=2000,
    )
    result = response.choices[0].message.content
    print(f"\nОтвет API:\n{result}")
except Exception as e:
    print(f"\nОшибка: {e}")

client.files.delete(file.id)
