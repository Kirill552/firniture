"""
Тестовый скрипт для проверки mock диалога.
Запуск: python -m api.mocks.test_dialogue_mock
"""
import asyncio
import sys
import os
from pathlib import Path

# Устанавливаем UTF-8 для Windows консоли
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.mocks.dialogue_mocks import (
    generate_mock_dialogue_response,
    mock_function_call_response,
    are_yc_keys_available
)


async def test_basic_dialogue():
    """Тест базового диалога."""
    print("=" * 80)
    print("ТЕСТ 1: Базовый диалог с ИИ-технологом")
    print("=" * 80)

    order_id = 999  # Тестовый заказ

    # Симулируем первое сообщение пользователя
    print("\n[ПОЛЬЗОВАТЕЛЬ] Привет, нужно сделать кухонный гарнитур")
    print("\n[ИИ-ТЕХНОЛОГ] ", end="", flush=True)

    full_response = ""
    async for chunk in generate_mock_dialogue_response(
        order_id=order_id,
        user_message="Привет, нужно сделать кухонный гарнитур",
        is_first_message=True
    ):
        print(chunk, end="", flush=True)
        full_response += chunk

    print("\n" + "-" * 80)

    # Следующий ответ пользователя
    print("\n[ПОЛЬЗОВАТЕЛЬ] Размеры: 3000 × 2400 × 600 мм")
    print("\n[ИИ-ТЕХНОЛОГ] ", end="", flush=True)

    async for chunk in generate_mock_dialogue_response(
        order_id=order_id,
        user_message="Размеры: 3000 × 2400 × 600 мм",
        is_first_message=False
    ):
        print(chunk, end="", flush=True)

    print("\n" + "-" * 80)

    # Ещё один ответ
    print("\n[ПОЛЬЗОВАТЕЛЬ] ЛДСП 16мм")
    print("\n[ИИ-ТЕХНОЛОГ] ", end="", flush=True)

    async for chunk in generate_mock_dialogue_response(
        order_id=order_id,
        user_message="ЛДСП 16мм",
        is_first_message=False
    ):
        print(chunk, end="", flush=True)

    print("\n\n[OK] Тест базового диалога пройден!\n")


async def test_button_responses():
    """Тест ответов на нажатия кнопок."""
    print("=" * 80)
    print("ТЕСТ 2: Ответы на кнопки")
    print("=" * 80)

    order_id = 888

    responses = ["Да", "Нет", "Не знаю", "Спасибо"]

    for response in responses:
        print(f"\n[ПОЛЬЗОВАТЕЛЬ] {response}")
        print("[ИИ-ТЕХНОЛОГ] ", end="", flush=True)

        async for chunk in generate_mock_dialogue_response(
            order_id=order_id,
            user_message=response,
            is_first_message=False
        ):
            print(chunk, end="", flush=True)

        print()
        await asyncio.sleep(0.5)

    print("\n[OK] Тест ответов на кнопки пройден!\n")


async def test_function_calling():
    """Тест mock function calling."""
    print("=" * 80)
    print("ТЕСТ 3: Function Calling (mock инструменты)")
    print("=" * 80)

    # Тест get_available_materials
    print("\n[CALL] get_available_materials(panel_type='корпус')")
    result = await mock_function_call_response("get_available_materials", panel_type="корпус")
    print(f"[OK] Результат: {result}\n")

    # Тест get_material_properties
    print("\n[CALL] get_material_properties(material_name='ЛДСП Egger')")
    result = await mock_function_call_response("get_material_properties", material_name="ЛДСП Egger")
    print(f"[OK] Результат: {result}\n")

    # Тест check_hardware_compatibility
    print("\n[CALL] check_hardware_compatibility(panel_thickness=18, hardware_sku='BLUM-123')")
    result = await mock_function_call_response(
        "check_hardware_compatibility",
        panel_thickness=18,
        hardware_sku="BLUM-123"
    )
    print(f"[OK] Результат: {result}\n")

    # Тест find_hardware
    print("\n[CALL] find_hardware(query='петля накладная blum')")
    result = await mock_function_call_response("find_hardware", query="петля накладная blum")
    print(f"[OK] Результат: {result}\n")

    print("[OK] Тест function calling пройден!\n")


async def test_yc_keys_check():
    """Тест проверки наличия YC ключей."""
    print("=" * 80)
    print("ТЕСТ 4: Проверка YC ключей")
    print("=" * 80)

    keys_available = are_yc_keys_available()
    print(f"\nYC ключи доступны: {keys_available}")

    if keys_available:
        print("[!] YC ключи найдены — API будет работать в PRODUCTION режиме")
        print("[i] Для тестирования mock режима удалите/закомментируйте YC_FOLDER_ID и YC_API_KEY из .env")
    else:
        print("[OK] YC ключи не найдены — API будет работать в MOCK режиме")

    print()


async def main():
    """Запуск всех тестов."""
    print("\n" + ">>> ЗАПУСК ТЕСТОВ MOCK ДИАЛОГА <<<".center(80) + "\n")

    await test_yc_keys_check()
    await test_basic_dialogue()
    await test_button_responses()
    await test_function_calling()

    print("=" * 80)
    print(">> ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! <<".center(80))
    print("=" * 80)
    print("\n[!] Теперь можно запустить API сервер и проверить эндпоинт:")
    print("   POST /api/v1/dialogue/clarify")
    print("   с телом:")
    print("   {")
    print('     "order_id": 1,')
    print('     "messages": [{"role": "user", "content": "Привет!"}]')
    print("   }\n")


if __name__ == "__main__":
    asyncio.run(main())
