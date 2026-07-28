"""Тест OpenAI API с PDF."""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Загружаем .env
load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()

# Тестируем на оглавлении (маленький файл)
pdf_path = Path(__file__).parent.parent / "furnitura_catalogi" / "boyard" / "оглавление функц.pdf"

print(f"Тестируем: {pdf_path.name}")
print(f"Размер: {pdf_path.stat().st_size / 1024:.1f} KB")

# Загружаем файл
with open(pdf_path, "rb") as f:
    file = client.files.create(file=f, purpose="user_data")

print(f"Файл загружен: {file.id}")

# Простой запрос
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "file",
                    "file": {"file_id": file.id}
                },
                {
                    "type": "text",
                    "text": "Что это за документ? Перечисли основные разделы."
                },
            ]
        }],
        max_tokens=1000,
    )
    print(f"\nОтвет API:\n{response.choices[0].message.content}")
except Exception as e:
    print(f"\nОшибка: {e}")

# Удаляем файл
client.files.delete(file.id)
print("\nФайл удалён")
