# Mock данные для диалога с ИИ-технологом

## Описание

Этот модуль предоставляет mock/fallback данные для диалога с ИИ-технологом когда отсутствуют ключи Yandex Cloud (`YC_FOLDER_ID` и `YC_API_KEY`).

Mock режим позволяет:
- ✅ Разрабатывать и тестировать frontend без доступа к YandexGPT
- ✅ Запускать проект локально без настройки Yandex Cloud
- ✅ Тестировать логику диалога без затрат на API
- ✅ Демонстрировать функционал без реальных ключей

## Файлы

- `dialogue_mocks.py` — основной модуль с mock ответами и функциями
- `test_dialogue_mock.py` — скрипт для тестирования mock режима
- `README.md` — эта документация

## Как работает

### Автоматическое переключение режимов

Эндпоинт `POST /api/v1/dialogue/clarify` автоматически определяет наличие YC ключей:

```python
# В routers.py
use_mock_mode = not are_yc_keys_available()

if use_mock_mode:
    # Используем mock ответы
    return generate_mock_dialogue_response(...)
else:
    # Используем реальный YandexGPT
    return yandex_gpt_client.stream_chat_completion(...)
```

### Проверка режима

Чтобы узнать, какой режим используется, смотрите логи сервера:

```bash
# Mock режим
[WARNING] [MOCK MODE] YC keys not found. Using mock dialogue responses for order 123

# Production режим
[INFO] [PRODUCTION MODE] Using YandexGPT for order 123
```

## Использование

### 1. Запуск тестов

Запустите тестовый скрипт для проверки mock функционала:

```bash
# Из корня проекта
cd api
python -m mocks.test_dialogue_mock
```

Тесты проверят:
- ✅ Базовый диалог (вопросы-ответы)
- ✅ Ответы на кнопки (Да/Нет/Не знаю)
- ✅ Function calling (mock инструменты)
- ✅ Наличие/отсутствие YC ключей

### 2. Запуск API в mock режиме

**Шаг 1**: Убедитесь, что YC ключи НЕ заданы в `.env`:

```bash
# .env файл
# YC_FOLDER_ID=  # закомментировано
# YC_API_KEY=    # закомментировано

# Или вообще удалите эти строки
```

**Шаг 2**: Запустите API сервер:

```bash
# Активируйте venv (если ещё не активирован)
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac

# Запустите сервер
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Шаг 3**: Проверьте логи — должно появиться:

```
[WARNING] [MOCK MODE] YC keys not found. Using mock dialogue responses...
```

### 3. Тестирование через API

#### Пример cURL запроса

```bash
curl -X POST "http://localhost:8000/api/v1/dialogue/clarify" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "messages": [
      {"role": "user", "content": "Привет! Нужно сделать кухонный гарнитур"}
    ]
  }'
```

#### Пример Python запроса

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/dialogue/clarify",
    json={
        "order_id": 1,
        "messages": [
            {"role": "user", "content": "Размеры: 3000 × 2400 × 600 мм"}
        ]
    },
    stream=True
)

# Потоковая обработка ответа
for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
    if chunk:
        print(chunk, end="", flush=True)
```

#### Пример JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/api/v1/dialogue/clarify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    order_id: 1,
    messages: [
      { role: 'user', content: 'ЛДСП 16мм' }
    ]
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  console.log(chunk); // Выводим chunks по мере получения
}
```

## Этапы диалога (mock)

Mock диалог имитирует следующие этапы:

1. **Initial** — приветствие и начало диалога
2. **Dimensions** — уточнение размеров (ШхВхГ в мм)
3. **Materials** — выбор материала (ЛДСП/МДФ/Массив)
4. **Thickness** — толщина панелей (16/18 мм)
5. **Edge** — кромкование (ПВХ 1мм/2мм)
6. **Hardware** — фурнитура (петли, направляющие, доводчики)
7. **Color** — цвет и декор
8. **Finalization** — финализация и переход к следующему шагу

Каждый этап содержит несколько вариантов ответов (выбирается случайно для разнообразия).

## Интерактивные кнопки

Mock ответы поддерживают формат кнопок из спецификации:

```
[BUTTONS: "Вариант 1", "Вариант 2", "Вариант 3"]
```

Frontend должен парсить этот формат и рендерить кликабельные кнопки.

## Mock Function Calling

Доступные mock инструменты (см. `mock_function_call_response`):

### 1. `get_available_materials`

Получить список доступных материалов для типа панели.

**Параметры:**
- `panel_type: str` — тип панели ("корпус", "фасад", "столешница")

**Возвращает:**
```python
["ЛДСП Egger", "ЛДСП Kronospan", "МДФ влагостойкая", ...]
```

### 2. `get_material_properties`

Получить свойства конкретного материала.

**Параметры:**
- `material_name: str` — название материала

**Возвращает:**
```python
{
    "название": "ЛДСП Egger",
    "доступные_толщины_мм": [16, 18, 22, 25],
    "цвета": ["белый", "дуб натуральный", "венге", "графит"],
    "текстура": "матовая/глянцевая"
}
```

### 3. `check_hardware_compatibility`

Проверить совместимость фурнитуры с толщиной панели.

**Параметры:**
- `panel_thickness: int` — толщина панели в мм
- `hardware_sku: str` — артикул фурнитуры

**Возвращает:**
```python
{
    "compatible": true,
    "comment": "Фурнитура совместима с указанной толщиной панели."
}
```

### 4. `find_hardware`

Найти фурнитуру по текстовому запросу.

**Параметры:**
- `query: str` — поисковый запрос

**Возвращает:**
```python
[
    {
        "sku": "BLUM-71B3550",
        "название": "Blum CLIP top BLUMOTION петля накладная",
        "цена": 450.00,
        "описание": "Петля с доводчиком для накладных дверей"
    },
    ...
]
```

## Переключение в production режим

Чтобы переключиться с mock режима на реальный YandexGPT:

1. Добавьте в `.env` файл:
```bash
YC_FOLDER_ID=your-folder-id
YC_API_KEY=your-api-key
```

2. Перезапустите API сервер

3. Проверьте логи — должно появиться:
```
[INFO] [PRODUCTION MODE] Using YandexGPT for order 123
```

## Настройка mock ответов

Чтобы изменить или добавить новые mock ответы, отредактируйте `dialogue_mocks.py`:

### Добавить новый этап диалога

```python
MOCK_DIALOGUE_STAGES = {
    # ... существующие этапы ...

    "new_stage": [
        "Первый вариант ответа для нового этапа",
        "Второй вариант ответа",
        "Третий вариант с кнопками\n[BUTTONS: \"Вариант А\", \"Вариант Б\"]"
    ]
}
```

### Добавить новую реакцию

```python
MOCK_REACTIONS = {
    # ... существующие реакции ...

    "новая_фраза": [
        "Реакция на новую фразу пользователя",
        "Альтернативная реакция"
    ]
}
```

### Добавить новый mock инструмент

```python
async def mock_function_call_response(function_name: str, **kwargs) -> dict:
    # ... существующие инструменты ...

    elif function_name == "new_tool":
        param = kwargs.get("param")
        return {
            "result": f"Mock данные для {param}"
        }
```

## Troubleshooting

### Проблема: Mock режим не включается

**Решение:** Проверьте, что YC ключи действительно не заданы:

```python
import os
print("YC_FOLDER_ID:", os.getenv("YC_FOLDER_ID", "НЕ ЗАДАН"))
print("YC_API_KEY:", os.getenv("YC_API_KEY", "НЕ ЗАДАН"))
```

### Проблема: Ответы всегда одинаковые

**Решение:** Это нормально — каждый этап диалога выбирает случайный ответ из списка. Для большего разнообразия добавьте больше вариантов в `MOCK_DIALOGUE_STAGES`.

### Проблема: Streaming не работает

**Решение:** Убедитесь, что:
1. Используете `StreamingResponse` в FastAPI
2. Client поддерживает streaming (например, `stream=True` в requests)
3. Chunks обрабатываются по мере получения, а не после завершения

## Лицензия

Часть проекта "Мебель-ИИ". Все права защищены.
