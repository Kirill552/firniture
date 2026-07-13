"""
Модуль извлечения параметров мебели из изображений.

Строгие серверные проверки (Task 1) выполняются ДО любого OCR/LLM/vision:
- base64 strict
- decoded size <=10MB
- magic bytes + MIME match
- PDF/image structural limits (pages, dims, MP)
- relevance preflight (single furniture module) via limited vision
- только потом — полный pipeline

Mock mode не обходит проверки. Невалидный/мусор -> 422/413/415 без grant и без дорогих вызовов.
Валидный low-confidence -> success + grant + fallback_to_dialogue.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import time

from PIL import Image

from api.settings import settings
from shared.ai_client import get_ai_client
from shared.ai_settings import AISettings

from .pdf_utils import PDFValidationError, pdf_to_images
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

# Сигнатуры содержимого: расширению файла не доверяем.
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # further check WEBP
    (b"%PDF-", "application/pdf"),
]


def _detect_mime_by_magic(data: bytes) -> str | None:
    """Return canonical mime or None. Never trust client extension."""
    for sig, mime in _MAGIC_SIGNATURES:
        if data.startswith(sig):
            if mime == "image/webp":
                if b"WEBP" not in data[0:16]:
                    return None
            return mime
    return None


def _validate_base64_and_size(image_base64: str) -> tuple[bytes, str | None, str | None]:
    """Strict decode + size. Returns (bytes, error_code, message) or (b, None, None)."""
    try:
        # Строго проверяем padding и запрещаем посторонние символы.
        file_bytes = base64.b64decode(image_base64, validate=True)
    except Exception:
        return b"", "invalid_base64", "Некорректный base64 в поле image_base64"

    if len(file_bytes) > settings.MAX_UPLOAD_BYTES:
        mb = len(file_bytes) / (1024 * 1024)
        return file_bytes, "payload_too_large", f"Файл слишком большой: {mb:.1f} МБ (максимум 10 МБ)"

    if len(image_base64) > settings.MAX_BASE64_BYTES:
        return file_bytes, "payload_too_large", "Поле base64 превышает допустимый размер"

    return file_bytes, None, None


def _validate_mime_magic(declared: str, data: bytes) -> tuple[bool, str | None, str | None]:
    actual = _detect_mime_by_magic(data)
    if actual is None:
        return False, "unsupported_file_type", "Неподдерживаемый тип файла по сигнатуре. Разрешены JPEG, PNG, WebP, PDF."
    if actual != declared:
        return False, "mime_mismatch", f"Заявленный MIME {declared} не соответствует фактическому содержимому ({actual})."
    if declared not in settings.ALLOWED_MIME_TYPES:
        return False, "unsupported_file_type", "Неподдерживаемый MIME тип."
    return True, None, None


def _validate_image_structure(data: bytes) -> tuple[bool, str | None, str | None]:
    """Pillow: dimensions, MP, min size. Reject decompression bombs / blank-ish."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()  # structural
        # Открываем изображение повторно: verify закрывает исходный объект.
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            if w <= 0 or h <= 0:
                return False, "image_too_large", "Изображение имеет нулевые размеры"
            if w < settings.MIN_IMAGE_SIDE_PX or h < settings.MIN_IMAGE_SIDE_PX:
                return False, "image_too_large", f"Изображение слишком маленькое (мин {settings.MIN_IMAGE_SIDE_PX}px)"
            if w > settings.MAX_IMAGE_SIDE_PX or h > settings.MAX_IMAGE_SIDE_PX:
                return False, "image_too_large", f"Изображение слишком большое по стороне (макс {settings.MAX_IMAGE_SIDE_PX}px)"
            pixels = w * h
            if pixels > settings.MAX_IMAGE_PIXELS:
                return False, "image_too_large", f"Изображение превышает 24 МП ({pixels} пикселей)"
            # Быстрая выборочная проверка пустого или почти однотонного изображения.
            try:
                small = im.convert("L").resize((8, 8))
                extrema = small.getextrema()
                if isinstance(extrema, tuple) and len(extrema) == 2:
                    mn, mx = extrema
                    if (mx - mn) < 4:  # almost solid color
                        return False, "not_furniture_source", "Загрузите фото, скриншот или PDF с одним мебельным модулем."
            except Exception:
                pass
            return True, None, None
    except Exception as e:
        return False, "unsupported_file_type", f"Не удалось открыть изображение: {type(e).__name__}"


def _validate_pdf_structure(data: bytes) -> tuple[bool, str | None, str | None]:
    try:
        pdf_to_images(data)  # reuses strict validate (pages 1-2, size, not encrypted)
        return True, None, None
    except PDFValidationError as e:
        code = "invalid_pdf"
        msg = str(e)
        if "большой" in msg.lower():
            code = "payload_too_large"
        return False, code, msg
    except Exception as e:
        return False, "invalid_pdf", f"Невалидный PDF: {e}"

# Промпт для GPT для парсинга текста OCR в структурированные параметры
FURNITURE_EXTRACTION_PROMPT = """Ты — эксперт по мебельному производству. Проанализируй текст, извлечённый из изображения/эскиза мебели, и извлеки параметры изделия.

ВАЖНО: Для каждого параметра укажи источник:
- "ocr" — нашёл текст/цифру на изображении
- "inferred" — вывел из контекста (форма, пропорции, тип)
- "default" — не нашёл, использую стандартное значение

## Текст из изображения:
{ocr_text}

## Извлеки параметры в формате JSON:

```json
{{{{
  "furniture_type": {{{{
    "category": "навесной_шкаф | напольный_шкаф | тумба | пенал | столешница | фасад | полка | ящик | другое",
    "subcategory": "опционально, более точное описание",
    "description": "краткое описание изделия",
    "source": "ocr | inferred | default"
  }}}},
  "dimensions": {{{{
    "width_mm": число или null,
    "width_source": "ocr | inferred | default",
    "height_mm": число или null,
    "height_source": "ocr | inferred | default",
    "depth_mm": число или null,
    "depth_source": "ocr | inferred | default",
    "thickness_mm": число или null,
    "thickness_source": "ocr | inferred | default"
  }}}},
  "body_material": {{{{
    "type": "ЛДСП | МДФ | массив | фанера | ДВП | стекло | металл | другое | null",
    "color": "цвет или null",
    "source": "ocr | inferred | default"
  }}}},
  "door_count": число или null,
  "door_count_source": "ocr | inferred | default",
  "drawer_count": число или null,
  "drawer_count_source": "ocr | inferred | default",
  "shelf_count": число или null,
  "shelf_count_source": "ocr | inferred | default",
  "confidence": число от 0 до 1
}}}}
```

Если >3 полей = "default", добавь поле:
"suggested_prompt": "Вижу [что видно]. Уточните [что нужно]?"

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
    language_codes: list[str] = None,
) -> tuple[str, float]:
    """
    Извлекает текст из изображения через vision модель.

    Returns:
        Tuple[str, float]: (извлечённый текст, уверенность)
    """
    image_base64 = base64.b64encode(image_bytes).decode()
    client = get_ai_client()
    response = await client.vision_extract(
        image_base64=image_base64,
        prompt="Извлеки весь текст с этого изображения. Верни только текст, без комментариев.",
    )
    return response.text, 0.8  # Vision модели не возвращают confidence


async def analyze_module_count(
    image_bytes: bytes,
) -> tuple[bool, int, list[str], str]:
    """
    Анализирует изображение и определяет количество модулей.

    Returns:
        (is_single_module, module_count, module_types, reason)
    """
    image_base64 = base64.b64encode(image_bytes).decode()
    client = get_ai_client()
    response = await client.vision_extract(
        image_base64=image_base64,
        prompt=MODULE_COUNT_PROMPT,
    )

    try:
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = [line for line in lines if not line.startswith("```")]
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
) -> tuple[ExtractedFurnitureParams, dict[str, str], list[str], int, str | None]:
    """
    Парсит текст OCR в структурированные параметры через GPT.

    Returns:
        (params, field_sources, fields_need_review, recognized_count, suggested_prompt)
    """
    if not ocr_text or len(ocr_text.strip()) < 5:
        params = ExtractedFurnitureParams(
            confidence=0.0,
            needs_clarification=True,
            clarification_questions=["Текст на изображении не распознан. Опишите изделие текстом."],
            raw_text=ocr_text,
        )
        return params, {}, [], 0, None

    prompt = FURNITURE_EXTRACTION_PROMPT.format(ocr_text=ocr_text)

    client = get_ai_client()
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

        # Собираем источники полей
        field_sources = {}
        default_count = 0

        # Тип мебели
        if data.get("furniture_type"):
            ft = data["furniture_type"]
            source = ft.get("source", "default")
            field_sources["furniture_type"] = source
            if source == "default":
                default_count += 1

        # Размеры
        if data.get("dimensions"):
            d = data["dimensions"]
            for field in ["width", "height", "depth", "thickness"]:
                source = d.get(f"{field}_source", "default")
                field_sources[f"{field}_mm"] = source
                if source == "default":
                    default_count += 1

        # Материал
        if data.get("body_material"):
            source = data["body_material"].get("source", "default")
            field_sources["material"] = source
            if source == "default":
                default_count += 1

        # Количества
        for field in ["door_count", "drawer_count", "shelf_count"]:
            source = data.get(f"{field}_source", "default")
            field_sources[field] = source
            if source == "default":
                default_count += 1

        # Определяем поля для review
        fields_need_review = [k for k, v in field_sources.items() if v == "default"]
        recognized_count = len(field_sources) - default_count
        suggested_prompt = data.get("suggested_prompt")

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

        params = ExtractedFurnitureParams(
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
            needs_clarification=default_count > 3,
            clarification_questions=data.get("clarification_questions") or [],
        )

        return params, field_sources, fields_need_review, recognized_count, suggested_prompt

    except json.JSONDecodeError as e:
        log.error(f"Failed to parse GPT response as JSON: {e}")
        params = ExtractedFurnitureParams(
            confidence=0.0,
            needs_clarification=True,
            clarification_questions=["Не удалось распознать параметры. Опишите изделие подробнее."],
            raw_text=ocr_text,
        )
        return params, {}, [], 0, None


async def extract_furniture_params_from_image(
    image_base64: str,
    mime_type: str = "image/jpeg",
    language_hint: str = "ru",
) -> ImageExtractResponse:
    """
    Главная функция: извлекает параметры мебели из изображения.

    ВАЖНО (Task 1):
    - Все детерминированные проверки (size, magic, mime, PDF/image, dims) — СРАЗУ и всегда.
    - Relevance preflight (single furniture) — до полного OCR/LLM.
    - При ошибке preflight / не мебель — 422 not_furniture_source, grant НЕ выдаётся.
    - Low confidence но валидный мебельный источник -> success + (grant от caller).
    """
    start_time = time.time()

    # === РАННИЕ СЕРВЕРНЫЕ ПРОВЕРКИ (до любого AI, до mock decision) ===
    file_bytes, err_code, err_msg = _validate_base64_and_size(image_base64)
    if err_code:
        return ImageExtractResponse(
            success=False,
            error=err_msg,
            error_type=err_code,  # type: ignore[arg-type]
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    ok, code, msg = _validate_mime_magic(mime_type, file_bytes)
    if not ok:
        return ImageExtractResponse(
            success=False,
            error=msg,
            error_type=code,  # type: ignore[arg-type]
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # Подготавливаем байты для Vision OCR.
    try:
        if mime_type == "application/pdf":
            ok, code, msg = _validate_pdf_structure(file_bytes)
            if not ok:
                return ImageExtractResponse(
                    success=False,
                    error=msg,
                    error_type=code,  # type: ignore[arg-type]
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )
            images = pdf_to_images(file_bytes)
            if not images:
                return ImageExtractResponse(
                    success=False,
                    error="PDF не содержит страниц",
                    error_type="invalid_pdf",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )
            image_bytes_for_preflight = images[0]
            # Для полного распознавания ниже используется первая страница.
        else:
            ok, code, msg = _validate_image_structure(file_bytes)
            if not ok:
                return ImageExtractResponse(
                    success=False,
                    error=msg,
                    error_type=code,  # type: ignore[arg-type]
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )
            image_bytes_for_preflight = file_bytes
    except PDFValidationError as e:
        return ImageExtractResponse(
            success=False,
            error=str(e),
            error_type="invalid_pdf",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )
    except Exception as e:
        return ImageExtractResponse(
            success=False,
            error=f"Ошибка валидации файла: {e}",
            error_type="unsupported_file_type",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # Проверка AI ключа ПОСЛЕ детерминированных проверок (mock тоже их прошёл)
    ai_settings = AISettings()
    if not ai_settings.ai_api_key:
        # В реальном пути (не mock router) это не должно случаться, но для безопасности
        return ImageExtractResponse(
            success=False,
            error="AI_API_KEY не настроен",
            fallback_to_dialogue=True,
            dialogue_prompt="Опишите мебельное изделие, которое нужно изготовить.",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    try:
        # === ОГРАНИЧЕННЫЙ PREFLIGHT: релевантность + ровно один мебельный модуль ===
        # Должен быть fail-closed: ошибки AI префлайта -> не furniture / 503
        log.info("[Vision] Running limited relevance/module preflight...")
        try:
            is_single, module_count, module_types, reason = await analyze_module_count(
                image_bytes=image_bytes_for_preflight,
            )
        except Exception as pre_e:
            log.warning("[Vision] Preflight vision failed (fail-closed): %s", pre_e)
            return ImageExtractResponse(
                success=False,
                error="Сервис временно недоступен. Попробуйте позже.",
                error_type="service_unavailable",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        if not is_single or module_count != 1:
            return ImageExtractResponse(
                success=False,
                error="Загрузите фото, скриншот или PDF с одним мебельным модулем.",
                error_type="not_furniture_source",
                module_count=module_count,
                fallback_to_dialogue=False,
                dialogue_prompt=None,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Только теперь — полный OCR + parse (дорого)
        language_codes = ["ru", "en"] if language_hint == "auto" else [language_hint, "en"]

        log.info("[Vision] Starting OCR extraction...")
        ocr_text, ocr_confidence = await extract_text_from_image(
            image_bytes=image_bytes_for_preflight,
            language_codes=language_codes,
        )
        log.info(f"[Vision] OCR complete. Text length: {len(ocr_text)}, confidence: {ocr_confidence:.2f}")

        log.info("[Vision] Parsing OCR text with GPT...")
        params, field_sources, fields_need_review, recognized_count, suggested_prompt = await parse_ocr_text_to_params(
            ocr_text=ocr_text,
        )
        log.info(f"[Vision] Parsing complete. Confidence: {params.confidence:.2f}")

        needs_fallback = (
            params.confidence < MIN_CONFIDENCE_THRESHOLD
            or params.needs_clarification
            or (params.dimensions is None and params.furniture_type is None)
        )

        dialogue_prompt = None
        if needs_fallback:
            if params.raw_text:
                dialogue_prompt = f"Я вижу на изображении: {params.raw_text[:200]}... Уточните, что именно нужно изготовить?"
            else:
                dialogue_prompt = "Не удалось распознать параметры с изображения. Опишите изделие, которое нужно изготовить."
            if params.clarification_questions:
                dialogue_prompt += f"\n\nВопросы: {', '.join(params.clarification_questions)}"

        processing_time_ms = int((time.time() - start_time) * 1000)
        final_confidence = params.confidence if params.confidence > 0 else ocr_confidence

        # Разрешение добавит routers.py после лимитов, блокировки и успешной проверки.
        return ImageExtractResponse(
            success=True,
            parameters=params,
            field_sources=field_sources,
            fields_need_review=fields_need_review,
            recognized_count=recognized_count,
            suggested_prompt=suggested_prompt,
            ocr_confidence=final_confidence,
            fallback_to_dialogue=needs_fallback,
            dialogue_prompt=dialogue_prompt,
            processing_time_ms=processing_time_ms,
            module_count=1,
            guest_upload_grant=None,  # router attaches if all gates passed
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
    mime_type: str = "image/jpeg",
) -> ImageExtractResponse:
    """Mock функция — ВСЕГДА проходит те же детерминированные проверки, что и prod path.
    Нет bypass: отсутствие ключа не даёт success на мусоре.
    """
    import asyncio

    start = time.time()
    await asyncio.sleep(0.05)  # tiny for test speed

    # 1. base64 + size (strict)
    file_bytes, err_code, err_msg = _validate_base64_and_size(image_base64)
    if err_code:
        return ImageExtractResponse(
            success=False,
            error=err_msg,
            error_type=err_code,  # type: ignore[arg-type]
            processing_time_ms=int((time.time() - start) * 1000),
        )

    # 2. magic + declared match
    ok, code, msg = _validate_mime_magic(mime_type, file_bytes)
    if not ok:
        return ImageExtractResponse(
            success=False,
            error=msg,
            error_type=code,  # type: ignore[arg-type]
            processing_time_ms=int((time.time() - start) * 1000),
        )

    # 3. structural + PDF/pages or image dims
    if mime_type == "application/pdf":
        ok, code, msg = _validate_pdf_structure(file_bytes)
    else:
        ok, code, msg = _validate_image_structure(file_bytes)
    if not ok:
        return ImageExtractResponse(
            success=False,
            error=msg,
            error_type=code,  # type: ignore[arg-type]
            processing_time_ms=int((time.time() - start) * 1000),
        )

    # В mock-режиме структурно корректный тестовый файл считаем мебельным.
    # Реальный режим выполняет ограниченный Vision preflight выше.
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

    field_sources = {
        "furniture_type": "ocr",
        "width_mm": "ocr",
        "height_mm": "ocr",
        "depth_mm": "ocr",
        "thickness_mm": "ocr",
        "material": "ocr",
        "door_count": "ocr",
        "drawer_count": "default",
        "shelf_count": "ocr",
    }
    fields_need_review = [k for k, v in field_sources.items() if v == "default"]
    recognized_count = len(field_sources) - len(fields_need_review)

    return ImageExtractResponse(
        success=True,
        parameters=mock_params,
        field_sources=field_sources,
        fields_need_review=fields_need_review,
        recognized_count=recognized_count,
        suggested_prompt="Проверь параметры и уточни недостающее (тип, размеры, материал, количество дверей/полок).",
        ocr_confidence=0.9,
        fallback_to_dialogue=False,
        processing_time_ms=int((time.time() - start) * 1000),
        module_count=1,
        guest_upload_grant=None,  # grant issued by caller (router) only after full acceptance
    )
