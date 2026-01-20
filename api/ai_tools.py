"""
AI-инструменты (Function Calling) для ИИ-технолога.

Модуль предоставляет набор инструментов для работы с фурнитурой:
- find_hardware: поиск фурнитуры по описанию (векторный поиск)
- check_hardware_compatibility: проверка совместимости с материалом
- get_hardware_details: детальная информация о позиции по SKU
- calculate_hardware_qty: расчёт количества фурнитуры

Интеграция с YandexGPT через OpenAI-совместимый API.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from api.constants import DEFAULT_THICKNESS_MM
from api.database import SessionLocal
from api.models import HardwareItem
from shared.embeddings import embed_text

log = logging.getLogger(__name__)


# ============================================================================
# Определения инструментов (JSON Schema для OpenAI Function Calling)
# ============================================================================

HARDWARE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculate_panels",
            "description": (
                "Рассчитывает панели для корпусной мебели по габаритам. "
                "Возвращает список панелей с размерами, кромкой и предупреждениями. "
                "ВСЕГДА вызывай этот инструмент когда пользователь указывает размеры шкафа или тумбы."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cabinet_type": {
                        "type": "string",
                        "enum": ["wall", "base", "base_sink", "drawer", "tall"],
                        "description": (
                            "Тип корпуса: "
                            "wall — навесной шкаф, "
                            "base — напольная тумба, "
                            "base_sink — тумба под мойку, "
                            "drawer — тумба с ящиками, "
                            "tall — пенал"
                        )
                    },
                    "width_mm": {"type": "integer", "description": "Ширина корпуса в мм"},
                    "height_mm": {"type": "integer", "description": "Высота корпуса в мм"},
                    "depth_mm": {"type": "integer", "description": "Глубина корпуса в мм"},
                    "material": {"type": "string", "default": "ЛДСП 16мм", "description": "Материал корпуса"},
                    "shelf_count": {"type": "integer", "default": 1, "description": "Количество полок"},
                    "door_count": {"type": "integer", "default": 1, "description": "Количество дверей"},
                    "drawer_count": {"type": "integer", "default": 0, "description": "Количество ящиков"}
                },
                "required": ["cabinet_type", "width_mm", "height_mm", "depth_mm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_hardware",
            "description": (
                "Поиск фурнитуры в каталоге по текстовому описанию. "
                "Использует семантический (векторный) поиск для нахождения наиболее подходящих позиций. "
                "Вызывай этот инструмент когда пользователь спрашивает о фурнитуре или нужно подобрать комплектующие."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Текстовый запрос для поиска. Например: 'петля накладная с доводчиком', "
                            "'направляющие полного выдвижения 500мм', 'подъёмник для верхних шкафов'"
                        )
                    },
                    "hardware_type": {
                        "type": "string",
                        "enum": ["hinge", "slide", "handle", "lift", "leg", "connector", "other"],
                        "description": "Тип фурнитуры для фильтрации результатов (опционально)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Максимальное количество результатов (по умолчанию 5)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_hardware_compatibility",
            "description": (
                "Проверка совместимости фурнитуры с материалом и толщиной. "
                "Вызывай этот инструмент когда нужно убедиться, что выбранная фурнитура подходит "
                "для конкретного материала (ЛДСП, МДФ и т.д.) и толщины панели."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Артикул (SKU) фурнитуры для проверки"
                    },
                    "material": {
                        "type": "string",
                        "description": "Материал панели: ЛДСП, МДФ, ДСП, массив и т.д."
                    },
                    "thickness_mm": {
                        "type": "number",
                        "description": "Толщина панели в миллиметрах"
                    }
                },
                "required": ["sku", "material", "thickness_mm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hardware_details",
            "description": (
                "Получение детальной информации о позиции фурнитуры по артикулу (SKU). "
                "Вызывай этот инструмент когда нужно узнать полные характеристики конкретной позиции."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Артикул (SKU) фурнитуры"
                    }
                },
                "required": ["sku"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_hardware_qty",
            "description": (
                "Расчёт необходимого количества фурнитуры для изделия. "
                "Вызывай этот инструмент когда нужно рассчитать сколько петель, направляющих и т.д. "
                "потребуется для шкафа или другого изделия."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hardware_type": {
                        "type": "string",
                        "enum": ["hinge", "slide", "handle", "lift", "leg"],
                        "description": "Тип фурнитуры для расчёта"
                    },
                    "door_count": {
                        "type": "integer",
                        "description": "Количество дверей (для петель и ручек)"
                    },
                    "door_height_mm": {
                        "type": "number",
                        "description": "Высота двери в мм (влияет на количество петель)"
                    },
                    "drawer_count": {
                        "type": "integer",
                        "description": "Количество ящиков (для направляющих)"
                    },
                    "cabinet_width_mm": {
                        "type": "number",
                        "description": "Ширина шкафа в мм (для расчёта опор)"
                    }
                },
                "required": ["hardware_type"]
            }
        }
    }
]


# ============================================================================
# Обработчики инструментов
# ============================================================================

async def handle_calculate_panels(
    cabinet_type: str,
    width_mm: int,
    height_mm: int,
    depth_mm: int,
    material: str = "ЛДСП 16мм",
    shelf_count: int = 1,
    door_count: int = 1,
    drawer_count: int = 0,
) -> dict[str, Any]:
    """Рассчитать панели для корпусной мебели."""
    from api.panel_calculator import calculate_panels

    log.info(f"[AI Tool] calculate_panels: {cabinet_type} {width_mm}×{height_mm}×{depth_mm}")

    try:
        thickness_mm = 18.0 if "18" in material else DEFAULT_THICKNESS_MM

        result = calculate_panels(
            cabinet_type=cabinet_type,
            width_mm=width_mm,
            height_mm=height_mm,
            depth_mm=depth_mm,
            thickness_mm=thickness_mm,
            shelf_count=shelf_count,
            door_count=door_count,
            drawer_count=drawer_count,
        )

        panels_data = [p.to_dict() for p in result.panels]

        return {
            "success": True,
            "cabinet_type": result.cabinet_type,
            "dimensions": {
                "width_mm": result.width_mm,
                "height_mm": result.height_mm,
                "depth_mm": result.depth_mm,
            },
            "panels": panels_data,
            "summary": {
                "total_panels": result.total_panels,
                "total_area_m2": round(result.total_area_m2, 2),
                "edge_length_m": round(result.edge_length_m, 1),
            },
            "warnings": result.warnings,
        }

    except ValueError as e:
        log.error(f"[AI Tool] calculate_panels error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        log.error(f"[AI Tool] calculate_panels unexpected error: {e}")
        return {"success": False, "error": f"Ошибка расчёта: {e}"}


async def handle_find_hardware(
    query: str,
    hardware_type: str | None = None,
    limit: int = 5
) -> dict[str, Any]:
    """
    Поиск фурнитуры по текстовому запросу с использованием векторного поиска.

    Args:
        query: Текстовый запрос для поиска
        hardware_type: Фильтр по типу фурнитуры
        limit: Максимальное количество результатов

    Returns:
        Словарь с результатами поиска
    """
    log.info(f"[AI Tool] find_hardware: query='{query}', type={hardware_type}, limit={limit}")

    try:
        # Получаем embedding для запроса
        query_embedding = await embed_text(query)

        async with SessionLocal() as db:
            # Строим запрос с k-NN поиском
            stmt = (
                select(HardwareItem)
                .where(HardwareItem.embedding.isnot(None))
                .where(HardwareItem.is_active == True)
                .order_by(HardwareItem.embedding.l2_distance(query_embedding))
                .limit(limit * 2)  # Берём больше для фильтрации
            )

            # Фильтр по типу если указан
            if hardware_type:
                stmt = stmt.where(HardwareItem.type == hardware_type)

            result = await db.execute(stmt)
            items = result.scalars().all()

        # Форматируем результаты
        results = []
        for item in items[:limit]:
            results.append({
                "sku": item.sku,
                "name": item.name,
                "brand": item.brand,
                "type": item.type,
                "category": item.category,
                "description": item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description,
                "price_rub": item.price_rub,
                "params": item.params,
                "compat": item.compat,
                "thickness_range": f"{item.thickness_min_mm or '?'}-{item.thickness_max_mm or '?'} мм"
            })

        return {
            "success": True,
            "count": len(results),
            "items": results,
            "query": query
        }

    except Exception as e:
        log.error(f"[AI Tool] find_hardware error: {e}")
        return {
            "success": False,
            "error": str(e),
            "items": []
        }


async def handle_check_hardware_compatibility(
    sku: str,
    material: str,
    thickness_mm: float
) -> dict[str, Any]:
    """
    Проверка совместимости фурнитуры с материалом и толщиной.

    Args:
        sku: Артикул фурнитуры
        material: Материал панели (ЛДСП, МДФ и т.д.)
        thickness_mm: Толщина панели в мм

    Returns:
        Словарь с результатом проверки совместимости
    """
    log.info(f"[AI Tool] check_hardware_compatibility: sku={sku}, material={material}, thickness={thickness_mm}мм")

    try:
        async with SessionLocal() as db:
            result = await db.execute(
                select(HardwareItem).where(HardwareItem.sku == sku)
            )
            item = result.scalar_one_or_none()

        if not item:
            return {
                "success": False,
                "compatible": False,
                "error": f"Позиция с артикулом {sku} не найдена",
                "sku": sku
            }

        # Проверка толщины
        thickness_ok = True
        thickness_message = "Толщина подходит"

        if item.thickness_min_mm and thickness_mm < item.thickness_min_mm:
            thickness_ok = False
            thickness_message = f"Толщина {thickness_mm}мм меньше минимальной {item.thickness_min_mm}мм"
        elif item.thickness_max_mm and thickness_mm > item.thickness_max_mm:
            thickness_ok = False
            thickness_message = f"Толщина {thickness_mm}мм больше максимальной {item.thickness_max_mm}мм"

        # Проверка материала через compat теги
        material_lower = material.lower()
        material_ok = False
        material_message = "Материал не указан в совместимости"

        # Маппинг материалов на теги совместимости
        material_tags = {
            "лдсп": ["ldsp", "лдсп", "dsp"],
            "мдф": ["mdf", "мдф"],
            "дсп": ["dsp", "дсп", "ldsp"],
            "массив": ["solid", "массив", "wood"],
            "фанера": ["plywood", "фанера"],
        }

        compat_lower = [c.lower() for c in (item.compat or [])]

        for mat_key, tags in material_tags.items():
            if mat_key in material_lower:
                for tag in tags:
                    if any(tag in c for c in compat_lower):
                        material_ok = True
                        material_message = f"Материал {material} совместим"
                        break
                break

        # Если compat пустой, считаем совместимым
        if not item.compat:
            material_ok = True
            material_message = "Ограничений по материалу нет"

        compatible = thickness_ok and material_ok

        return {
            "success": True,
            "compatible": compatible,
            "sku": sku,
            "name": item.name,
            "thickness_compatible": thickness_ok,
            "thickness_message": thickness_message,
            "material_compatible": material_ok,
            "material_message": material_message,
            "recommendation": (
                "Фурнитура подходит для использования" if compatible
                else "Рекомендуется выбрать другую фурнитуру"
            )
        }

    except Exception as e:
        log.error(f"[AI Tool] check_hardware_compatibility error: {e}")
        return {
            "success": False,
            "compatible": False,
            "error": str(e),
            "sku": sku
        }


async def handle_get_hardware_details(sku: str) -> dict[str, Any]:
    """
    Получение детальной информации о позиции фурнитуры.

    Args:
        sku: Артикул фурнитуры

    Returns:
        Словарь с полной информацией о позиции
    """
    log.info(f"[AI Tool] get_hardware_details: sku={sku}")

    try:
        async with SessionLocal() as db:
            result = await db.execute(
                select(HardwareItem).where(HardwareItem.sku == sku)
            )
            item = result.scalar_one_or_none()

        if not item:
            return {
                "success": False,
                "error": f"Позиция с артикулом {sku} не найдена",
                "sku": sku
            }

        return {
            "success": True,
            "item": {
                "sku": item.sku,
                "name": item.name,
                "brand": item.brand,
                "type": item.type,
                "category": item.category,
                "description": item.description,
                "params": item.params,
                "compat": item.compat,
                "material_type": item.material_type,
                "thickness_min_mm": item.thickness_min_mm,
                "thickness_max_mm": item.thickness_max_mm,
                "price_rub": item.price_rub,
                "url": item.url,
                "is_active": item.is_active
            }
        }

    except Exception as e:
        log.error(f"[AI Tool] get_hardware_details error: {e}")
        return {
            "success": False,
            "error": str(e),
            "sku": sku
        }


async def handle_calculate_hardware_qty(
    hardware_type: str,
    door_count: int | None = None,
    door_height_mm: float | None = None,
    drawer_count: int | None = None,
    cabinet_width_mm: float | None = None
) -> dict[str, Any]:
    """
    Расчёт количества фурнитуры для изделия.

    Правила расчёта:
    - Петли: 2 шт на дверь до 800мм, 3 шт до 1600мм, 4 шт свыше
    - Направляющие: 1 пара на ящик
    - Ручки: 1 шт на дверь или ящик
    - Подъёмники: 1 комплект на 1-2 двери
    - Опоры: 4 шт на шкаф до 800мм, 6 шт свыше

    Args:
        hardware_type: Тип фурнитуры
        door_count: Количество дверей
        door_height_mm: Высота двери
        drawer_count: Количество ящиков
        cabinet_width_mm: Ширина шкафа

    Returns:
        Словарь с расчётом количества
    """
    log.info(f"[AI Tool] calculate_hardware_qty: type={hardware_type}, doors={door_count}, drawers={drawer_count}")

    result = {
        "success": True,
        "hardware_type": hardware_type,
        "quantity": 0,
        "unit": "шт",
        "calculation_notes": []
    }

    try:
        if hardware_type == "hinge":
            if not door_count:
                return {
                    "success": False,
                    "error": "Для расчёта петель укажите количество дверей (door_count)"
                }

            height = door_height_mm or 700  # По умолчанию 700мм

            if height <= 800:
                hinges_per_door = 2
            elif height <= 1600:
                hinges_per_door = 3
            else:
                hinges_per_door = 4

            result["quantity"] = door_count * hinges_per_door
            result["calculation_notes"] = [
                f"Дверей: {door_count}",
                f"Высота двери: {height}мм",
                f"Петель на дверь: {hinges_per_door}",
                f"Итого петель: {result['quantity']}"
            ]

        elif hardware_type == "slide":
            if not drawer_count:
                return {
                    "success": False,
                    "error": "Для расчёта направляющих укажите количество ящиков (drawer_count)"
                }

            result["quantity"] = drawer_count  # Пара направляющих = 1 комплект
            result["unit"] = "пар"
            result["calculation_notes"] = [
                f"Ящиков: {drawer_count}",
                f"Направляющих (пар): {result['quantity']}"
            ]

        elif hardware_type == "handle":
            total = (door_count or 0) + (drawer_count or 0)
            if total == 0:
                return {
                    "success": False,
                    "error": "Для расчёта ручек укажите количество дверей или ящиков"
                }

            result["quantity"] = total
            result["calculation_notes"] = [
                f"Дверей: {door_count or 0}",
                f"Ящиков: {drawer_count or 0}",
                f"Итого ручек: {result['quantity']}"
            ]

        elif hardware_type == "lift":
            if not door_count:
                return {
                    "success": False,
                    "error": "Для расчёта подъёмников укажите количество дверей (door_count)"
                }

            # 1 подъёмник на 1-2 двери (для верхних шкафов)
            result["quantity"] = (door_count + 1) // 2
            result["unit"] = "комплект"
            result["calculation_notes"] = [
                f"Дверей (откидных): {door_count}",
                f"Подъёмников: {result['quantity']} (1 комплект на 1-2 двери)"
            ]

        elif hardware_type == "leg":
            width = cabinet_width_mm or 600

            if width <= 800:
                result["quantity"] = 4
            else:
                result["quantity"] = 6

            result["calculation_notes"] = [
                f"Ширина шкафа: {width}мм",
                f"Опор: {result['quantity']} (4 до 800мм, 6 свыше)"
            ]

        else:
            return {
                "success": False,
                "error": f"Неизвестный тип фурнитуры: {hardware_type}"
            }

        return result

    except Exception as e:
        log.error(f"[AI Tool] calculate_hardware_qty error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Диспетчер вызовов инструментов
# ============================================================================

TOOL_HANDLERS = {
    "calculate_panels": handle_calculate_panels,
    "find_hardware": handle_find_hardware,
    "check_hardware_compatibility": handle_check_hardware_compatibility,
    "get_hardware_details": handle_get_hardware_details,
    "calculate_hardware_qty": handle_calculate_hardware_qty,
}


async def execute_tool_call(
    tool_name: str,
    arguments: dict[str, Any]
) -> dict[str, Any]:
    """
    Выполнение вызова инструмента.

    Args:
        tool_name: Имя инструмента
        arguments: Аргументы вызова

    Returns:
        Результат выполнения инструмента
    """
    handler = TOOL_HANDLERS.get(tool_name)

    if not handler:
        log.error(f"[AI Tool] Unknown tool: {tool_name}")
        return {
            "success": False,
            "error": f"Неизвестный инструмент: {tool_name}"
        }

    log.info(f"[TOOL_CALL] Executing {tool_name} with args: {arguments}")

    try:
        result = await handler(**arguments)
        # Логируем результат (сокращённо)
        result_preview = str(result)[:300]
        log.info(f"[TOOL_RESULT] {tool_name} success={result.get('success', True)}, preview: {result_preview}")
        return result
    except TypeError as e:
        log.error(f"[AI Tool] {tool_name} argument error: {e}")
        return {
            "success": False,
            "error": f"Ошибка аргументов: {e}"
        }
    except Exception as e:
        log.error(f"[AI Tool] {tool_name} execution error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_tools_schema() -> list[dict[str, Any]]:
    """Получить схему всех инструментов для передачи в YandexGPT."""
    return HARDWARE_TOOLS
