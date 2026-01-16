"""
Модуль извлечения параметров мебели из изображений.

Процесс:
1. Vision OCR: Изображение → текст
2. GPT: Текст → структурированные параметры (JSON)
3. Валидация и fallback на диалог при низкой уверенности
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time

from shared.yandex_ai import (
    OCRResponse,
    YandexCloudSettings,
    create_openai_client,
    create_vision_client,
)

from .schemas import (
    ExtractedDimensions,
    ExtractedFurnitureParams,
    ExtractedMaterial,
    FurnitureType,
    ImageExtractResponse,
)

log = logging.getLogger(__name__)

# Минимальный порог уверенности для автоматического принятия
MIN_CONFIDENCE_THRESHOLD = 0.6

# Промпт для GPT для парсинга текста OCR в структурированные параметры
FURNITURE_EXTRACTION_PROMPT = """Ты — эксперт по мебельному производству. Проанализируй текст, извлечённый из изображения/эскиза мебели, и извлеки параметры изделия.

ВАЖНО: Извлекай только то, что явно указано в тексте. Не додумывай. Если параметр не указан — оставь null.

## Текст из изображения:
{ocr_text}

## Извлеки параметры в формате JSON:

```json
{{
  "furniture_type": {{
    "category": "навесной_шкаф | напольный_шкаф | тумба | пенал | столешница | фасад | полка | ящик | другое",
    "subcategory": "опционально, более точное описание",
    "description": "краткое описание изделия"
  }},
  "dimensions": {{
    "width_mm": число или null,
    "height_mm": число или null,
    "depth_mm": число или null,
    "thickness_mm": число или null
  }},
  "body_material": {{
    "type": "ЛДСП | МДФ | массив | фанера | ДВП | стекло | металл | другое | null",
    "color": "цвет или null",
    "texture": "текстура или null",
    "brand": "бренд или null"
  }},
  "facade_material": {{
    "type": "тип или null",
    "color": "цвет или null",
    "texture": "текстура или null",
    "brand": "бренд или null"
  }},
  "door_count": число или null,
  "drawer_count": число или null,
  "shelf_count": число или null,
  "has_legs": true | false | null,
  "confidence": число от 0 до 1 (насколько ты уверен в извлечённых данных),
  "needs_clarification": true если данных недостаточно,
  "clarification_questions": ["вопрос1", "вопрос2"] если needs_clarification=true
}}
```

Отвечай ТОЛЬКО валидным JSON без дополнительного текста.
"""

MODULE_COUNT_PROMPT = """Проанализируй изображение и определи:
1. Это эскиз/фото ОДНОГО мебельного модуля или целой кухни/комнаты?
2. Сколько отдельных мебельных модулей видно? (шкаф, тумба, пенал — каждый считается отдельно)

Отвечай JSON:
```json
{
  "is_single_module": true/false,
  "module_count": число,
  "module_types": ["тип1", "тип2", ...],
  "reason": "краткое объяснение"
}
```
"""


async def extract_text_from_image(
    image_bytes: bytes,
    settings: YandexCloudSettings,
    language_codes: list[str] = None,
) -> tuple[str, float]:
    """
    Извлекает текст из изображения через Yandex Vision OCR.

    Returns:
        Tuple[str, float]: (извлечённый текст, средняя уверенность)
    """
    if language_codes is None:
        language_codes = ["ru", "en"]

    async with create_vision_client(settings) as client:
        response: OCRResponse = await client.extract_text_from_image(
            image_bytes=image_bytes,
            language_codes=language_codes,
        )

    return response.text, response.confidence


async def analyze_module_count(
    image_bytes: bytes,
    settings: YandexCloudSettings,
) -> tuple[bool, int, list[str], str]:
    """
    Анализирует изображение и определяет количество модулей.

    Returns:
        (is_single_module, module_count, module_types, reason)
    """
    import base64

    image_base64 = base64.b64encode(image_bytes).decode()

    async with create_openai_client(settings) as client:
        response = await client.chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": MODULE_COUNT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=500,
        )

    try:
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(json_lines)

        data = json.loads(text)
        return (
            data.get("is_single_module", True),
            data.get("module_count", 1),
            data.get("module_types", []),
            data.get("reason", "")
        )
    except json.JSONDecodeError:
        log.warning("Failed to parse module count response, assuming single module")
        return (True, 1, [], "Не удалось определить")


async def parse_ocr_text_to_params(
    ocr_text: str,
    settings: YandexCloudSettings,
) -> ExtractedFurnitureParams:
    """
    Парсит текст OCR в структурированные параметры через GPT.
    """
    if not ocr_text or len(ocr_text.strip()) < 5:
        return ExtractedFurnitureParams(
            confidence=0.0,
            needs_clarification=True,
            clarification_questions=["Текст на изображении не распознан. Опишите изделие текстом."],
            raw_text=ocr_text,
        )

    prompt = FURNITURE_EXTRACTION_PROMPT.format(ocr_text=ocr_text)

    async with create_openai_client(settings) as client:
        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": "Ты — парсер структурированных данных. Отвечай только JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Низкая температура для детерминизма
            max_tokens=1500,
        )

    # Парсим JSON из ответа
    try:
        # Ищем JSON в ответе (может быть обёрнут в ```json ... ```)
        text = response.text.strip()
        if text.startswith("```"):
            # Убираем markdown code block
            lines = text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```json") or line.startswith("```"):
                    in_json = not in_json
                    continue
                if in_json:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        data = json.loads(text)

        # Конструируем объект
        furniture_type = None
        if data.get("furniture_type"):
            ft = data["furniture_type"]
            furniture_type = FurnitureType(
                category=ft.get("category", "другое"),
                subcategory=ft.get("subcategory"),
                description=ft.get("description"),
            )

        dimensions = None
        if data.get("dimensions"):
            d = data["dimensions"]
            dimensions = ExtractedDimensions(
                width_mm=d.get("width_mm"),
                height_mm=d.get("height_mm"),
                depth_mm=d.get("depth_mm"),
                thickness_mm=d.get("thickness_mm"),
            )

        body_material = None
        if data.get("body_material"):
            m = data["body_material"]
            body_material = ExtractedMaterial(
                type=m.get("type"),
                color=m.get("color"),
                texture=m.get("texture"),
                brand=m.get("brand"),
            )

        facade_material = None
        if data.get("facade_material"):
            m = data["facade_material"]
            facade_material = ExtractedMaterial(
                type=m.get("type"),
                color=m.get("color"),
                texture=m.get("texture"),
                brand=m.get("brand"),
            )

        return ExtractedFurnitureParams(
            furniture_type=furniture_type,
            dimensions=dimensions,
            body_material=body_material,
            facade_material=facade_material,
            door_count=data.get("door_count"),
            drawer_count=data.get("drawer_count"),
            shelf_count=data.get("shelf_count"),
            has_legs=data.get("has_legs"),
            raw_text=ocr_text,
            confidence=data.get("confidence", 0.5),
            needs_clarification=data.get("needs_clarification", False),
            clarification_questions=data.get("clarification_questions") or [],
        )

    except json.JSONDecodeError as e:
        log.error(f"Failed to parse GPT response as JSON: {e}")
        return ExtractedFurnitureParams(
            confidence=0.0,
            needs_clarification=True,
            clarification_questions=["Не удалось распознать параметры. Опишите изделие подробнее."],
            raw_text=ocr_text,
        )


async def extract_furniture_params_from_image(
    image_base64: str,
    settings: YandexCloudSettings | None = None,
    language_hint: str = "ru",
) -> ImageExtractResponse:
    """
    Главная функция: извлекает параметры мебели из изображения.

    Args:
        image_base64: Изображение в base64
        settings: Настройки Yandex Cloud (если None — загружаются из env)
        language_hint: Язык для OCR ("ru", "en", "auto")

    Returns:
        ImageExtractResponse с параметрами или ошибкой
    """
    start_time = time.time()

    # Загружаем настройки если не переданы
    if settings is None:
        folder_id = os.getenv("YC_FOLDER_ID", "")
        api_key = os.getenv("YC_API_KEY", "")

        if not folder_id or not api_key:
            return ImageExtractResponse(
                success=False,
                error="YC_FOLDER_ID и YC_API_KEY не настроены",
                fallback_to_dialogue=True,
                dialogue_prompt="Опишите мебельное изделие, которое нужно изготовить.",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        settings = YandexCloudSettings(
            yc_folder_id=folder_id,
            yc_api_key=api_key,
        )

    try:
        # Декодируем base64
        image_bytes = base64.b64decode(image_base64)

        # Шаг 0: Проверка количества модулей
        log.info("[Vision] Checking module count...")
        is_single, module_count, module_types, reason = await analyze_module_count(
            image_bytes=image_bytes,
            settings=settings,
        )

        if not is_single or module_count > 1:
            types_str = ", ".join(module_types) if module_types else "различные модули"
            return ImageExtractResponse(
                success=False,
                error=f"Обнаружено {module_count} модулей ({types_str}). Загрузите фото одного модуля.",
                error_type="multiple_modules",
                module_count=module_count,
                fallback_to_dialogue=False,
                dialogue_prompt=None,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Определяем языки для OCR
        language_codes = ["ru", "en"] if language_hint == "auto" else [language_hint, "en"]

        # Шаг 1: OCR
        log.info("[Vision] Starting OCR extraction...")
        ocr_text, ocr_confidence = await extract_text_from_image(
            image_bytes=image_bytes,
            settings=settings,
            language_codes=language_codes,
        )
        log.info(f"[Vision] OCR complete. Text length: {len(ocr_text)}, confidence: {ocr_confidence:.2f}")

        # Шаг 2: Парсинг через GPT
        log.info("[Vision] Parsing OCR text with GPT...")
        params = await parse_ocr_text_to_params(
            ocr_text=ocr_text,
            settings=settings,
        )
        log.info(f"[Vision] Parsing complete. Confidence: {params.confidence:.2f}")

        # Шаг 3: Определяем нужен ли fallback на диалог
        needs_fallback = (
            params.confidence < MIN_CONFIDENCE_THRESHOLD
            or params.needs_clarification
            or (params.dimensions is None and params.furniture_type is None)
        )

        dialogue_prompt = None
        if needs_fallback:
            # Формируем начальный промпт для диалога
            if params.raw_text:
                dialogue_prompt = f"Я вижу на изображении: {params.raw_text[:200]}... Уточните, что именно нужно изготовить?"
            else:
                dialogue_prompt = "Не удалось распознать параметры с изображения. Опишите изделие, которое нужно изготовить."

            if params.clarification_questions:
                dialogue_prompt += f"\n\nВопросы: {', '.join(params.clarification_questions)}"

        processing_time_ms = int((time.time() - start_time) * 1000)

        return ImageExtractResponse(
            success=True,
            parameters=params,
            ocr_confidence=ocr_confidence,
            fallback_to_dialogue=needs_fallback,
            dialogue_prompt=dialogue_prompt,
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        log.error(f"[Vision] Extraction failed: {e}")
        return ImageExtractResponse(
            success=False,
            error=str(e),
            fallback_to_dialogue=True,
            dialogue_prompt="Произошла ошибка при обработке изображения. Опишите изделие текстом.",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


# Mock функция для тестирования без реальных API
async def extract_furniture_params_mock(
    image_base64: str,
) -> ImageExtractResponse:
    """Mock функция для локального тестирования без Yandex Cloud."""
    import asyncio

    # Имитируем задержку обработки
    await asyncio.sleep(0.5)

    mock_params = ExtractedFurnitureParams(
        furniture_type=FurnitureType(
            category="навесной_шкаф",
            subcategory="кухонный",
            description="Навесной шкаф для кухни с одной дверцей",
        ),
        dimensions=ExtractedDimensions(
            width_mm=600,
            height_mm=720,
            depth_mm=300,
            thickness_mm=16,
        ),
        body_material=ExtractedMaterial(
            type="ЛДСП",
            color="белый",
        ),
        facade_material=ExtractedMaterial(
            type="МДФ",
            color="матовый белый",
        ),
        door_count=1,
        shelf_count=2,
        has_legs=False,
        raw_text="[MOCK] Навесной шкаф 600x720x300 ЛДСП белый МДФ фасад",
        confidence=0.85,
        needs_clarification=False,
    )

    return ImageExtractResponse(
        success=True,
        parameters=mock_params,
        ocr_confidence=0.9,
        fallback_to_dialogue=False,
        processing_time_ms=500,
    )
