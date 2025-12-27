# Быстрый старт: Mock диалог с ИИ-технологом

## Что это?

Mock режим позволяет разрабатывать и тестировать диалог с ИИ-технологом **без настройки Yandex Cloud**.

## Быстрый запуск (3 шага)

### 1. Проверить что mock работает

```bash
# Из корня проекта
python -m api.mocks.test_dialogue_mock
```

Вы должны увидеть:
```
[OK] YC ключи не найдены — API будет работать в MOCK режиме
```

### 2. Запустить API сервер

```bash
# Активировать venv (если ещё не активирован)
.\venv\Scripts\activate  # Windows
# или
source venv/bin/activate # Linux/Mac

# Запустить сервер
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Протестировать эндпоинт

#### Вариант A: Через curl

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

#### Вариант B: Через Python

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

for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
    if chunk:
        print(chunk, end="", flush=True)
```

#### Вариант C: Через JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/api/v1/dialogue/clarify', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    order_id: 1,
    messages: [
      {role: 'user', content: 'ЛДСП 16мм'}
    ]
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  console.log(decoder.decode(value));
}
```

## Проверка логов

В консоли API сервера должны появиться логи:

```
[WARNING] [MOCK MODE] YC keys not found. Using mock dialogue responses for order 1
[INFO] [MOCK MODE] Mock response saved to DB for order 1
```

## Переключение в production

Чтобы использовать реальный YandexGPT:

1. Добавьте в `.env`:
```bash
YC_FOLDER_ID=your-folder-id
YC_API_KEY=your-api-key
```

2. Перезапустите сервер

3. Логи изменятся на:
```
[INFO] [PRODUCTION MODE] Using YandexGPT for order 1
```

## Проблемы?

### Mock режим не включается

Проверьте, что в `.env` НЕТ ключей или они пустые:
```bash
# Должно быть так:
# YC_FOLDER_ID=
# YC_API_KEY=

# Или вообще удалите эти строки
```

### Нет order_id в БД

Mock режим требует существующий заказ в БД. Создайте его через:
```bash
POST /api/v1/orders
{
  "name": "Тестовый заказ",
  "description": "Для тестирования диалога"
}
```

### Streaming не работает

Убедитесь, что:
- Используете `stream=True` в requests (Python)
- Обрабатываете `response.body.getReader()` (JavaScript)
- Не ждёте полного ответа, а обрабатываете chunks

## Что дальше?

Полная документация: `api/mocks/README.md`

Структура mock ответов: `api/mocks/dialogue_mocks.py`

Изменения в API: `api/mocks/CHANGES_ROUTERS.diff`
