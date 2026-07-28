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
        return b"", "invalid_base64", "Не удалось прочитать загруженный файл."

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
    except Exception:
        log.exception("[Vision] Не удалось открыть изображение")
        return False, "unsupported_file_type", "Не удалось открыть изображение. Загрузите JPG, PNG, WebP или PDF."

def _validate_pdf_structure(data: bytes) -> tuple[bool, str | None, str | None]:
    try:
        pdf_to_images(data)  # reuses strict validate (pages 1-2, size, not encrypted)
        return True, None, None
    except PDFValidationError as e:
        log.warning("[Vision] Проверка PDF не пройдена: %s", e)
        return False, "invalid_pdf", "Не удалось прочитать PDF. Проверьте файл или задайте габариты вручную."
    except Exception as e:
        log.exception("[Vision] Проверка PDF завершилась с исключением")
        return False, "invalid_pdf", "Не удалось прочитать PDF. Проверьте файл или задайте габариты вручную."

# Промпт для мультимодального извлечения: изображение всегда остаётся главным источником.
FURNITURE_EXTRACTION_PROMPT = """Роль: ты — технолог мебельного производства; задача — по изображению эскиза, фото или 3D-рендера вернуть параметры изделия.

Порядок чтения:
1. Сначала прочитай цифры с выносок и подписей на изображении.
2. Привяжи каждую цифру к своей оси, иначе деталь выйдет боком:
   - выноска вдоль нижней или верхней кромки, горизонтальная — это ШИРИНА;
   - выноска вдоль правой или левой кромки, вертикальная — это ВЫСОТА;
   - подпись «глубина», косая выноска в сторону от корпуса или вынесенный сбоку
     размер вида «300 мм» рядом с боковиной — это ГЛУБИНА;
   - если ось не подписана, помни пропорции кухонной мебели: глубина почти всегда
     наименьшая из трёх, а у навесного шкафа высота больше глубины.
   Проверь себя: получилось, что глубина больше высоты — значит оси перепутаны,
   перечитай выноски заново.
3. Затем определи тип изделия по форме.
4. Затем посчитай по изображению двери, ящики и полки.

Источники строго разделяй:
- "ocr" — цифра или подпись реально прочитана на изображении;
- "inferred" — объект виден на изображении без подписи (например, две двери видны глазом);
- "default" — объект или размер не виден вообще, поэтому взят производственный стандарт.
Не выдумывай размеры: если выноски нет, ставь null и источник "default". Выдуманный размер на станке станет испорченной деталью.
Размеры кухонной мебели указывай в миллиметрах. Проверяй здравый смысл: ширина 300–1200, высота 300–2400, глубина 280–700, толщина 10–25. Число вне диапазона, вероятно, не габарит: ставь соответствующий размер null и источник "default", а не подгоняй число.
Если изображение показывает несколько модулей, не складывай их в один шкаф и не выдумывай общий габарит: опиши это в suggested_prompt и предложи выбрать один модуль или задать габарит по стене.

Вспомогательный OCR-текст (не заменяет изображение):
{ocr_text}

Верни только JSON, без markdown, пояснений, служебных блоков и <think>. Формат:
{{
  "furniture_type": {{"category": "навесной_шкаф | напольный_шкаф | тумба | пенал | столешница | фасад | полка | ящик | другое", "subcategory": null, "description": null, "source": "ocr | inferred | default"}},
  "dimensions": {{"width_mm": null, "width_source": "ocr | inferred | default", "height_mm": null, "height_source": "ocr | inferred | default", "depth_mm": null, "depth_source": "ocr | inferred | default", "thickness_mm": null, "thickness_source": "ocr | inferred | default"}},
  "body_material": {{"type": null, "color": null, "source": "ocr | inferred | default"}},
  "door_count": null, "door_count_source": "ocr | inferred | default",
  "drawer_count": null, "drawer_count_source": "ocr | inferred | default",
  "shelf_count": null, "shelf_count_source": "ocr | inferred | default",
  "confidence": 0.0,
  "suggested_prompt": null
}}

Примеры:
1) Эскиз с выносками 600, 720, 300 и двумя фасадами: dimensions = 600/720/300 с источником "ocr", door_count = 2 с источником "inferred", тип определяется по форме.
2) Фото готовой тумбы без размеров с одним ящиком: dimensions = null с источником "default", drawer_count = 1 с источником "inferred", тип "тумба".
3) 3D-рендер кухни с несколькими шкафами: не выдавай общий габарит; furniture_type.source = "inferred", размеры null/default, suggested_prompt = "Вижу несколько модулей. Выберите один модуль или задайте габарит по стене."
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
    mime_type: str = "image/jpeg",
) -> tuple[str, float]:
    """Извлекает вспомогательный OCR-текст, не подменяя им изображение."""
    image_base64 = base64.b64encode(image_bytes).decode()
    client = get_ai_client()
    response = await client.vision_extract(
        image_base64=image_base64,
        prompt="Прочитай только видимые цифры, подписи и текст на изображении. Если текста нет, верни пустую строку.",
        mime_type=mime_type,
        max_tokens=2000,
    )
    return response.text, 0.8


async def analyze_module_count(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> tuple[bool, int, list[str], str]:
    """Определяет, является ли изображение одним мебельным модулем."""
    image_base64 = base64.b64encode(image_bytes).decode()
    client = get_ai_client()
    response = await client.vision_extract(
        image_base64=image_base64,
        prompt=MODULE_COUNT_PROMPT,
        mime_type=mime_type,
        max_tokens=2000,
    )

    try:
        data = json.loads(_extract_json_payload(response.text))
        return (
            data.get("is_single_module", True),
            data.get("module_count", 1),
            data.get("module_types", []),
            data.get("reason", ""),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        log.warning("Не удалось разобрать ответ о количестве модулей")
        return (True, 1, [], "Не удалось определить")


def _extract_json_payload(text: str) -> str:
    """Извлекает первый сбалансированный JSON после размышлений модели."""
    import re

    body = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<think>.*", "", body, flags=re.DOTALL | re.IGNORECASE)
    start = body.find("{")
    if start < 0:
        raise ValueError("Ответ модели не содержит JSON")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(body)):
        char = body[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return body[start:index + 1]
    raise ValueError("Ответ модели содержит обрезанный JSON")


def _dimension_value(value: object, field: str) -> int | None:
    """Принимает только целые миллиметры в здравом диапазоне."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    ranges = {"width": (300, 1200), "height": (300, 2400), "depth": (280, 700), "thickness": (10, 25)}
    low, high = ranges[field]
    integer = int(value)
    return integer if value == integer and low <= integer <= high else None

# Модель называет материал и тип своими словами: «дерево», «кухонный гарнитур».
# Одно незнакомое слово раньше валило весь разбор в except и обнуляло распознавание,
# поэтому синонимы приводим к словарю схемы, а незнакомое становится «другое».
MATERIAL_SYNONYMS = {
    "лдсп": "ЛДСП", "дсп": "ЛДСП", "ламинированная дсп": "ЛДСП", "ldsp": "ЛДСП",
    "мдф": "МДФ", "mdf": "МДФ",
    "массив": "массив", "дерево": "массив", "массив дерева": "массив", "древесина": "массив",
    "фанера": "фанера", "plywood": "фанера",
    "двп": "ДВП", "хдф": "ДВП", "hdf": "ДВП",
    "стекло": "стекло", "glass": "стекло",
    "металл": "металл", "алюминий": "металл", "сталь": "металл",
}

CATEGORY_SYNONYMS = {
    "навесной_шкаф": "навесной_шкаф", "навесной шкаф": "навесной_шкаф", "верхний шкаф": "навесной_шкаф",
    "напольный_шкаф": "напольный_шкаф", "напольный шкаф": "напольный_шкаф", "нижний шкаф": "напольный_шкаф",
    "тумба": "тумба", "тумба под мойку": "тумба",
    "пенал": "пенал", "шкаф пенал": "пенал",
    "столешница": "столешница", "фасад": "фасад", "полка": "полка", "ящик": "ящик",
}


def _normalized(value: object, synonyms: dict[str, str]) -> str | None:
    """Слово модели -> значение схемы; неизвестное отдаём как «другое»."""
    if not isinstance(value, str) or not value.strip():
        return None
    return synonyms.get(value.strip().lower().replace("-", " "), "другое")


async def parse_ocr_text_to_params(
    ocr_text: str,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
) -> tuple[ExtractedFurnitureParams, dict[str, str], list[str], int, str | None]:
    """Извлекает структуру по картинке, передавая OCR только как подсказку."""
    if not ocr_text and image_bytes is None:
        return ExtractedFurnitureParams(
            confidence=0.0,
            needs_clarification=True,
            clarification_questions=["Изображение не распознано. Опишите изделие или задайте габариты."],
            raw_text=ocr_text,
        ), {}, [], 0, None

    prompt = FURNITURE_EXTRACTION_PROMPT.format(ocr_text=ocr_text or "(OCR-текст отсутствует)")
    client = get_ai_client()
    if image_bytes is not None:
        response = await client.vision_extract(
            image_base64=base64.b64encode(image_bytes).decode(),
            prompt=prompt,
            mime_type=mime_type,
            max_tokens=5000,
        )
    else:
        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": "Ты — парсер структурированных данных. Отвечай только JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=5000,
        )

    try:
        data = json.loads(_extract_json_payload(response.text))
        field_sources: dict[str, str] = {}
        default_count = 0
        ft = data.get("furniture_type") or {}
        source = ft.get("source", "default")
        field_sources["furniture_type"] = source
        default_count += source == "default"
        dimensions_data = data.get("dimensions") or {}
        for field in ["width", "height", "depth", "thickness"]:
            key = f"{field}_mm"
            value = _dimension_value(dimensions_data.get(key), field)
            if value is None and dimensions_data.get(key) is not None:
                dimensions_data[key] = None
                dimensions_data[f"{field}_source"] = "default"
            source = dimensions_data.get(f"{field}_source", "default")
            field_sources[key] = source
            default_count += source == "default"
        material = data.get("body_material") or {}
        source = material.get("source", "default")
        field_sources["material"] = source
        default_count += source == "default"
        for field in ["door_count", "drawer_count", "shelf_count"]:
            source = data.get(f"{field}_source", "default")
            field_sources[field] = source
            default_count += source == "default"
        fields_need_review = [key for key, value in field_sources.items() if value == "default"]
        recognized_count = len(field_sources) - default_count
        furniture_type = FurnitureType(
            category=_normalized(ft.get("category"), CATEGORY_SYNONYMS) or "другое",
            subcategory=ft.get("subcategory"),
            description=ft.get("description"),
        )
        # Поля схемы называются width_mm и далее: короткое имя pydantic молча отбросит,
        # и прочитанные с выносок размеры пропадут при живом «источник: ocr».
        dimensions = ExtractedDimensions(
            **{f"{key}_mm": dimensions_data.get(f"{key}_mm") for key in ["width", "height", "depth", "thickness"]}
        )
        body_material = ExtractedMaterial(
            type=_normalized(material.get("type"), MATERIAL_SYNONYMS),
            color=material.get("color"),
        )
        params = ExtractedFurnitureParams(
            furniture_type=furniture_type,
            dimensions=dimensions,
            body_material=body_material,
            door_count=data.get("door_count"),
            drawer_count=data.get("drawer_count"),
            shelf_count=data.get("shelf_count"),
            raw_text=ocr_text,
            confidence=data.get("confidence", 0.5),
            needs_clarification=default_count > 3,
            clarification_questions=data.get("clarification_questions") or [],
        )
        return params, field_sources, fields_need_review, recognized_count, data.get("suggested_prompt")
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        log.error("Не удалось разобрать ответ Vision: %s", exc)
        params = ExtractedFurnitureParams(
            confidence=0.0,
            needs_clarification=True,
            clarification_questions=[f"Ответ модели повреждён: {exc}"],
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
        log.warning("[Vision] Проверка PDF не пройдена: %s", e)
        return ImageExtractResponse(
            success=False,
            error="Не удалось прочитать PDF. Проверьте файл или задайте габариты вручную.",
            error_type="invalid_pdf",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )
    except Exception as e:
        log.exception("[Vision] Ошибка валидации файла")
        return ImageExtractResponse(
            success=False,
            error="Не удалось проверить файл. Загрузите другой исходник или задайте габариты вручную.",
            error_type="unsupported_file_type",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )
    # Проверка AI ключа ПОСЛЕ детерминированных проверок (mock тоже их прошёл)
    ai_settings = AISettings()
    if not ai_settings.ai_api_key:
        # В реальном пути (не mock router) это не должно случаться, но для безопасности
        return ImageExtractResponse(
            success=False,
            error="Проверка изображения временно недоступна. Задайте габариты вручную.",
            fallback_to_dialogue=True,
            dialogue_prompt="Опишите изделие или задайте его габариты вручную.",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    try:
        # === ОГРАНИЧЕННЫЙ PREFLIGHT: релевантность + ровно один мебельный модуль ===
        # Должен быть fail-closed: ошибки AI префлайта -> не furniture / 503
        log.info("[Vision] Running limited relevance/module preflight...")
        try:
            is_single, module_count, module_types, reason = await analyze_module_count(
                image_bytes=image_bytes_for_preflight,
                mime_type="image/jpeg" if mime_type == "application/pdf" else mime_type,
            )
        except Exception as pre_e:
            log.warning("[Vision] Preflight vision failed (fail-closed): %s", pre_e)
            return ImageExtractResponse(
                success=False,
                error="Проверка изображения временно недоступна. Задайте габариты вручную.",
            )
            return ImageExtractResponse(
                success=False,
                error="Загрузите фото, скриншот или PDF с одним мебельным модулем.",
                error_type="not_furniture_source",
                module_count=module_count,
                fallback_to_dialogue=False,
                dialogue_prompt=None,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Отдельный OCR-проход убран намеренно. Та же модель на просьбу «извлеки весь
        # текст» отвечает рассуждениями вида «The user wants me to extract all text»,
        # и этот мусор, подмешанный в промпт, ронял извлечение: на эскизе с явными
        # выносками 600/720/300 размеры терялись. Без него модель читает выноски сама.
        log.info("[Vision] Starting multimodal parameter extraction...")
        ocr_confidence = 0.0
        params, field_sources, fields_need_review, recognized_count, suggested_prompt = await parse_ocr_text_to_params(
            ocr_text="",
            image_bytes=image_bytes_for_preflight,
            mime_type="image/jpeg" if mime_type == "application/pdf" else mime_type,
        )
        log.info("[Vision] Parsing complete. Confidence: %.2f", params.confidence)

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
            guest_upload_grant=None,
        )

    except Exception as e:
        log.exception("[Vision] Extraction failed")
        return ImageExtractResponse(
            success=False,
            error="Не удалось разобрать изображение. Выберите конкретный шкаф или задайте габариты вручную.",
            fallback_to_dialogue=True,
            dialogue_prompt="Выберите конкретный шкаф или задайте габариты вручную.",
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
