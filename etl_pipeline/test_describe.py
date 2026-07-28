"""Тест — что видит модель на странице."""
import fitz
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()

catalog_path = Path(__file__).parent.parent / "furnitura_catalogi" / "boyard" / "Каталог функциональной фурнитуры BOYARD 2024 .pdf"
output_path = Path(__file__).parent / "output" / "test_page.pdf"
output_path.parent.mkdir(parents=True, exist_ok=True)

# Попробуем страницу 7 (должна быть техническая информация)
doc = fitz.open(catalog_path)
new_doc = fitz.open()
new_doc.insert_pdf(doc, from_page=6, to_page=6)  # страница 7
new_doc.save(output_path)
new_doc.close()
doc.close()

print(f"Страница 7: {output_path.stat().st_size / 1024:.1f} KB")

with open(output_path, "rb") as f:
    file = client.files.create(file=f, purpose="user_data")

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "file", "file": {"file_id": file.id}},
                {"type": "text", "text": "Опиши подробно что ты видишь на этой странице. Есть ли тут чертежи, схемы сверления, размеры отверстий?"},
            ]
        }],
        max_tokens=1000,
    )
    print(f"\nСтраница 7:\n{response.choices[0].message.content}")
except Exception as e:
    print(f"Ошибка: {e}")

client.files.delete(file.id)
