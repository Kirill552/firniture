"""
Mock ответы для диалога с ИИ-технологом.
Используется для локальной разработки когда нет Yandex Cloud ключей.
"""
import asyncio
import random
import logging
from typing import AsyncGenerator

log = logging.getLogger(__name__)

# Базовые mock ответы ИИ-технолога в зависимости от этапа диалога
MOCK_DIALOGUE_STAGES = {
    "initial": [
        "Здравствуйте! Я изучил параметры вашего заказа. Давайте проверим и уточним все детали для подготовки к производству.",
        "Добрый день! Спасибо за предоставленные данные. Я ИИ-технолог платформы «Мебель-ИИ». Давайте вместе финализируем спецификацию.",
        "Приветствую! Я получил первичные данные по изделию. Сейчас проведу проверку и задам несколько уточняющих вопросов."
    ],

    "dimensions": [
        "Отлично! Теперь уточним размеры. Какие габариты изделия планируются? (укажите ширину × высота × глубина в мм)",
        "Хорошо. Следующий важный момент — точные размеры. Нужны габариты в формате: ширина × высота × глубина (в миллиметрах).",
        "Понял. Теперь про размеры — какие точные габариты должны быть у изделия? Укажите, пожалуйста, в миллиметрах."
    ],

    "materials": [
        "Отлично, размеры записал. Теперь про материалы. Какой материал для корпуса предпочитаете: ЛДСП, МДФ или массив?\n[BUTTONS: \"ЛДСП\", \"МДФ\", \"Массив\"]",
        "Понял по размерам. Теперь важный момент — материал корпуса. Обычно используют ЛДСП 16 мм, МДФ 16 мм или массив. Что выберем?\n[BUTTONS: \"ЛДСП 16мм\", \"МДФ 16мм\", \"Массив\"]",
        "Размеры зафиксировал. Следующий вопрос — какой материал для фасадов: МДФ с плёнкой ПВХ, МДФ с эмалью, или массив?\n[BUTTONS: \"МДФ с ПВХ\", \"МДФ эмаль\", \"Массив\"]"
    ],

    "thickness": [
        "Хорошо, материал выбран. Уточните толщину панелей для корпуса — стандартные варианты: 16 мм или 18 мм?\n[BUTTONS: \"16 мм\", \"18 мм\", \"Другая толщина\"]",
        "Отлично. Теперь по толщине материала — для фасадов обычно используют 16 мм или 18 мм. Какая толщина нужна?\n[BUTTONS: \"16 мм\", \"18 мм\"]",
    ],

    "edge": [
        "Понял. Теперь важный момент — кромкование. Для видимых торцов используем кромку ПВХ 1 мм или 2 мм?\n[BUTTONS: \"ПВХ 1 мм\", \"ПВХ 2 мм\", \"Без кромки\"]",
        "Хорошо. Следующий вопрос по кромке — какая обработка торцов нужна: ПВХ 2 мм (премиум), ПВХ 1 мм (стандарт) или АБС?\n[BUTTONS: \"ПВХ 2 мм\", \"ПВХ 1 мм\", \"АБС\"]"
    ],

    "hardware": [
        "Отлично. Теперь про фурнитуру — нужны ли доводчики на петлях и направляющих? Это добавит +15-20% к стоимости фурнитуры.\n[BUTTONS: \"Да, с доводчиками\", \"Нет, обычные\"]",
        "Понял. По петлям — обычно для корпусной мебели используют петли Blum или Hettich. Какой бренд предпочитаете?\n[BUTTONS: \"Blum\", \"Hettich\", \"Эконом-вариант\"]",
        "Хорошо. Для выдвижных ящиков нужны направляющие. Стандартный вариант — шариковые направляющие полного выдвижения. Подойдут?\n[BUTTONS: \"Да, шариковые\", \"Нужны Tandembox\", \"Без ящиков\"]"
    ],

    "color": [
        "Отлично, фурнитуру зафиксировал. Последний момент — цвет и декор. Какой оттенок ЛДСП/МДФ нужен? (например: белый, дуб, венге)",
        "Хорошо. Теперь про цвет фасадов — у нас есть каталог декоров. Какой оттенок предпочитаете? Можете указать название или описать.",
    ],

    "finalization": [
        "Отлично! Все ключевые параметры согласованы:\n- Габариты зафиксированы\n- Материалы и толщины выбраны\n- Кромка определена\n- Фурнитура подобрана\n- Цвет/декор указан\n\nМожем переходить к формированию полной спецификации и CAM-программ?",
        "Превосходно! Все параметры проверены и согласованы. Спецификация готова к производству. Переходим к следующему этапу — формирование деталировки и программ для станков?",
        "Отлично поработали! Все данные собраны и проверены. Теперь система автоматически сформирует:\n- Полную спецификацию (BOM)\n- Карты раскроя\n- Программы для ЧПУ\n\nПереходим к генерации?"
    ]
}

# Реакции на различные фразы пользователя
MOCK_REACTIONS = {
    "да": [
        "Отлично, понял!",
        "Хорошо, зафиксировал.",
        "Принято, двигаемся дальше.",
    ],
    "нет": [
        "Хорошо, уточните, пожалуйста, что нужно изменить.",
        "Понял. Тогда подскажите правильный вариант.",
    ],
    "не знаю": [
        "Понимаю. Давайте я предложу стандартные варианты для вашего типа изделия.",
        "Без проблем. Обычно в таких случаях используют следующие решения...",
    ],
    "спасибо": [
        "Всегда рада помочь! Продолжаем?",
        "Пожалуйста! Двигаемся дальше.",
    ]
}

# Ошибки и edge cases
MOCK_ERROR_RESPONSES = [
    "Извините, не совсем понял ваш ответ. Не могли бы вы уточнить?",
    "Хм, кажется, произошла какая-то путаница. Давайте попробуем ещё раз — ",
]


class MockDialogueState:
    """Отслеживание состояния mock диалога для более естественных ответов."""

    def __init__(self):
        self.current_stage = "initial"
        self.asked_questions = set()
        self.stage_order = ["initial", "dimensions", "materials", "thickness", "edge", "hardware", "color", "finalization"]
        self.stage_index = 0

    def get_next_stage(self) -> str:
        """Переход к следующему этапу диалога."""
        if self.stage_index < len(self.stage_order) - 1:
            self.stage_index += 1
            self.current_stage = self.stage_order[self.stage_index]
        return self.current_stage

    def get_current_response(self) -> str:
        """Получить ответ для текущего этапа."""
        responses = MOCK_DIALOGUE_STAGES.get(self.current_stage, MOCK_DIALOGUE_STAGES["initial"])
        return random.choice(responses)


# Глобальное состояние для разных заказов (в реальности это должно быть в Redis/БД)
_dialogue_states = {}


def get_dialogue_state(order_id: int) -> MockDialogueState:
    """Получить или создать состояние диалога для заказа."""
    if order_id not in _dialogue_states:
        _dialogue_states[order_id] = MockDialogueState()
    return _dialogue_states[order_id]


async def generate_mock_dialogue_response(
    order_id: int,
    user_message: str,
    is_first_message: bool = False
) -> AsyncGenerator[str, None]:
    """
    Генерирует mock ответ ИИ-технолога с потоковой отдачей (streaming).

    Args:
        order_id: ID заказа
        user_message: Последнее сообщение пользователя
        is_first_message: Это первое сообщение в диалоге?

    Yields:
        Части ответа (chunks) для имитации streaming
    """
    log.info(f"[MOCK MODE] Generating dialogue response for order {order_id}")

    state = get_dialogue_state(order_id)

    # Определяем, какой ответ генерировать
    if is_first_message:
        response_text = state.get_current_response()
    else:
        # Проверяем на ключевые фразы в сообщении пользователя
        message_lower = user_message.lower().strip()

        # Простая реакция на базовые ответы
        if any(word in message_lower for word in ["да", "ок", "хорошо", "согласен", "подходит"]):
            # Переходим к следующему этапу
            state.get_next_stage()
            response_text = random.choice(MOCK_REACTIONS["да"]) + " " + state.get_current_response()
        elif any(word in message_lower for word in ["нет", "не подходит", "другой"]):
            response_text = random.choice(MOCK_REACTIONS["нет"])
        elif any(word in message_lower for word in ["не знаю", "незнаю", "не уверен"]):
            response_text = random.choice(MOCK_REACTIONS["не знаю"]) + " " + state.get_current_response()
        elif any(word in message_lower for word in ["спасибо", "благодарю"]):
            response_text = random.choice(MOCK_REACTIONS["спасибо"])
        else:
            # Для любого другого ответа — двигаемся дальше
            state.get_next_stage()
            response_text = state.get_current_response()

    # Имитация streaming: отдаём текст по словам с небольшой задержкой
    words = response_text.split()
    for i, word in enumerate(words):
        # Добавляем пробел перед словом (кроме первого)
        chunk = word if i == 0 else f" {word}"
        yield chunk

        # Небольшая задержка для реалистичности (10-50мс)
        await asyncio.sleep(random.uniform(0.01, 0.05))

    log.info(f"[MOCK MODE] Response generated for order {order_id}: {len(words)} words")


async def mock_function_call_response(function_name: str, **kwargs) -> dict:
    """
    Mock ответы для function calling инструментов.

    Args:
        function_name: Имя вызываемой функции
        **kwargs: Параметры функции

    Returns:
        Mock результат выполнения функции
    """
    log.info(f"[MOCK MODE] Function call: {function_name} with params {kwargs}")

    if function_name == "get_available_materials":
        panel_type = kwargs.get("panel_type", "корпус")
        return {
            "корпус": ["ЛДСП Egger", "ЛДСП Kronospan", "МДФ влагостойкая", "Массив сосны"],
            "фасад": ["МДФ с плёнкой ПВХ", "МДФ эмаль", "Массив дуба", "ЛДСП с покрытием"],
            "столешница": ["ЛДСП 38мм", "Искусственный камень", "Натуральный камень", "Массив"]
        }.get(panel_type, ["ЛДСП", "МДФ", "Массив"])

    elif function_name == "get_material_properties":
        material_name = kwargs.get("material_name", "")
        # Упрощённый mock
        return {
            "название": material_name,
            "доступные_толщины_мм": [16, 18, 22, 25],
            "цвета": ["белый", "дуб натуральный", "венге", "графит"],
            "текстура": "матовая/глянцевая"
        }

    elif function_name == "check_hardware_compatibility":
        # Всегда возвращаем совместимость в mock режиме
        return {
            "compatible": True,
            "comment": "Фурнитура совместима с указанной толщиной панели."
        }

    elif function_name == "find_hardware":
        query = kwargs.get("query", "")
        # Mock результаты поиска фурнитуры
        return [
            {
                "sku": "BLUM-71B3550",
                "название": "Blum CLIP top BLUMOTION петля накладная",
                "цена": 450.00,
                "описание": "Петля с доводчиком для накладных дверей"
            },
            {
                "sku": "HETT-HD-3D",
                "название": "Hettich Sensys петля накладная 3D",
                "цена": 380.00,
                "описание": "Петля с 3D регулировкой"
            },
            {
                "sku": "GTV-ECON",
                "название": "GTV петля накладная эконом",
                "цена": 120.00,
                "описание": "Экономичный вариант петли"
            }
        ]

    else:
        return {"error": f"Unknown function: {function_name}"}


# Вспомогательная функция для проверки наличия YC ключей
def are_yc_keys_available() -> bool:
    """Проверяет, доступны ли Yandex Cloud API ключи."""
    import os
    yc_folder_id = os.getenv("YC_FOLDER_ID", "").strip()
    yc_api_key = os.getenv("YC_API_KEY", "").strip()
    return bool(yc_folder_id and yc_api_key)
