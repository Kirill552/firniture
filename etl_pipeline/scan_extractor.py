"""Извлечение параметров присадки со страниц PDF без текстового слоя."""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import fitz

from shared.ai_client import AIClient, get_ai_client
from shared.ai_settings import AISettings

SCAN_PROMPT = """Ты разбираешь скан каталога мебельной фурнитуры. Верни ТОЛЬКО JSON:
{"positions":[{"sku":"...","name":"...","type":"петля|направляющая|другое",
"brand":"...","params":{"cup_diameter_mm":null,"opening_angle_deg":null,
"mount_type":null,"hinge_type":null,"drill_offset_mm":null,"drill_depth_mm":null,
"slide_type":null,"length_mm":null},"page":1,"needs_review":false}]}

Извлекай только цифры и подписи, которые ЧЁТКО видны на изображении. НИЧЕГО НЕ
ДОГАДЫВАЙСЯ: нечитаемое поле оставь null и поставь needs_review=true. Не переноси
размеры с другой позиции. Поля Contract: cup_diameter_mm (только 26 или 35),
opening_angle_deg, mount_type (накладная|полунакладная|вкладная|угловая-45),
hinge_type, drill_offset_mm, drill_depth_mm, slide_type, length_mm. Если артикул
не читается, sku="" и needs_review=true. page будет заменён кодом на номер страницы.
"""

PARAM_KEYS = (
    "cup_diameter_mm", "opening_angle_deg", "mount_type", "hinge_type",
    "drill_offset_mm", "drill_depth_mm", "slide_type", "length_mm",
)


# Каталоги называют один и тот же тип наложения по-разному: «внутренняя» у AKS —
# это вкладная петля. Расчёт присадки различает только эти четыре типа.
MOUNT_SYNONYMS = {
    "накладная": "накладная",
    "полунакладная": "полунакладная",
    "вкладная": "вкладная",
    "внутренняя": "вкладная",
    "внутреняя": "вкладная",
    "угловая-45": "угловая-45",
    "угловая 45": "угловая-45",
}


def _normalize_mount(value: Any) -> str | None:
    """Приводит название наложения к типу, который понимает расчёт присадки."""
    if not isinstance(value, str):
        return None
    return MOUNT_SYNONYMS.get(value.strip().lower())


def _empty_position(page: int, brand: str, error: str) -> dict[str, Any]:
    return {"sku": "", "name": "", "type": "не определён", "brand": brand,
            "params": {key: None for key in PARAM_KEYS}, "page": page,
            "needs_review": True, "validation_errors": [error]}


def validate_position(position: dict[str, Any]) -> dict[str, Any]:
    """Удаляет сомнительные размеры и сохраняет причину для ручной проверки."""
    params = position.setdefault("params", {})
    errors = list(position.get("validation_errors", []))
    for key in PARAM_KEYS:
        params.setdefault(key, None)
    if params.get("mount_type") is not None:
        normalized = _normalize_mount(params["mount_type"])
        if normalized is None and "mount_type" not in errors:
            errors.append("mount_type")
        params["mount_type"] = normalized
    checks = {
        "cup_diameter_mm": lambda value: value in (26, 35),
        "opening_angle_deg": lambda value: isinstance(value, (int, float)) and 90 <= value <= 180,
        "drill_depth_mm": lambda value: isinstance(value, (int, float)) and 0 < value < 16,
        "drill_offset_mm": lambda value: isinstance(value, (int, float)) and 3 <= value <= 30,
    }
    for key, check in checks.items():
        value = params.get(key)
        if value is not None and not check(value):
            params[key] = None
            if key not in errors:
                errors.append(key)
    position["validation_errors"] = errors
    position["needs_review"] = bool(position.get("needs_review")) or bool(errors)
    return position


def _json_payload(text: str) -> str:
    """Достаёт JSON из ответа reasoning-модели: та пишет размышления до объекта."""
    body = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<think>.*", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body.strip(), flags=re.IGNORECASE)
    start = body.find("{")
    if start == -1:
        return body
    depth = 0
    for index in range(start, len(body)):
        if body[index] == "{":
            depth += 1
        elif body[index] == "}":
            depth -= 1
            if depth == 0:
                return body[start : index + 1]
    return body[start:]


def parse_vision_response(text: str, page: int, brand: str) -> list[dict[str, Any]]:
    """Разбирает JSON Vision и применяет детерминированные проверки."""
    cleaned = _json_payload(text)
    try:
        payload = json.loads(cleaned)
        raw_positions = payload.get("positions", [])
        if not isinstance(raw_positions, list):
            raise ValueError("positions_not_list")
    except (json.JSONDecodeError, AttributeError, ValueError):
        return [_empty_position(page, brand, "invalid_json")]
    result = []
    for raw in raw_positions:
        if not isinstance(raw, dict):
            result.append(_empty_position(page, brand, "invalid_position"))
            continue
        raw_params = raw.get("params")
        if not isinstance(raw_params, dict):
            raw_params = {}
        position = {"sku": str(raw.get("sku", "")), "name": str(raw.get("name", "")),
                    "type": str(raw.get("type", "не определён")), "brand": str(raw.get("brand", brand)),
                    "params": dict(raw_params), "page": page,
                    "needs_review": bool(raw.get("needs_review", False))}
        if not position["sku"]:
            position["needs_review"] = True
            position.setdefault("validation_errors", []).append("sku_unreadable")
        result.append(validate_position(position))
    return result or [_empty_position(page, brand, "no_positions")]


# Шлюз провайдера отклоняет крупные вложения невнятной ошибкой про image_url,
# поэтому картинка ужимается до предела, проверенного живым запросом.
MAX_IMAGE_BASE64 = 600_000


def render_page(pdf_path: str | Path, page_number: int, dpi: int = 150) -> bytes:
    """Рендерит страницу в JPEG в памяти; временных файлов в корне нет."""
    with fitz.open(pdf_path) as document:
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
        return pixmap.tobytes("jpeg", jpg_quality=85)


def render_page_within_limit(
    pdf_path: str | Path,
    page_number: int,
    dpi: int = 150,
    max_base64: int = MAX_IMAGE_BASE64,
) -> str:
    """Готовит base64 страницы, понижая dpi пока вложение не влезет в предел шлюза."""
    current = dpi
    while True:
        encoded = base64.b64encode(render_page(pdf_path, page_number, current)).decode("ascii")
        if len(encoded) <= max_base64 or current <= 70:
            return encoded
        current = max(70, int(current * 0.8))


async def extract_scanned_pdf(
    pdf_path: str | Path,
    brand: str,
    pages: list[int] | None = None,
    dpi: int = 150,
    client: AIClient | None = None,
    max_tokens: int = 6000,
) -> list[dict[str, Any]]:
    """Распознаёт выбранные страницы скана через общий Vision-клиент."""
    if not AISettings().ai_api_key:
        raise RuntimeError("AI API key is not configured; real scan extraction was not run")
    with fitz.open(pdf_path) as document:
        selected = pages or list(range(1, len(document) + 1))
    ai_client = client or get_ai_client()
    results: list[dict[str, Any]] = []
    for page_number in selected:
        encoded = render_page_within_limit(pdf_path, page_number, dpi)
        response = await ai_client.vision_extract(
            encoded,
            f"{SCAN_PROMPT}\nНомер страницы: {page_number}",
            max_tokens=max_tokens,
        )
        results.extend(parse_vision_response(response.text, page_number, brand))
    return results
