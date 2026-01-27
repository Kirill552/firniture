# Settings endpoints added 2026-01-16
import json
import logging
import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.ai_tools import execute_tool_call, get_tools_schema
from api.mocks.dialogue_mocks import are_yc_keys_available, generate_mock_dialogue_response
from api.vision_extraction import (
    extract_furniture_params_from_image,
    extract_furniture_params_mock,
)
from shared.storage import ObjectStorage
from shared.yandex_ai import (
    GPTResponseWithTools,
    YandexCloudSettings,
    create_openai_client,
)

from . import crud, models
from .auth import get_current_user, get_current_user_optional
from .database import get_db
from .dxf_generator import Panel as DXFPanel
from .dxf_generator import PlacedPanel, optimize_layout_best
from .models import (
    Artifact,
    CAMJob,
    Factory,
    JobStatusEnum,
    Panel,
    ProductConfig,
    User,
)
from .queues import DRILLING_QUEUE, DXF_QUEUE, GCODE_QUEUE, enqueue
from .schemas import (
    SETTINGS_DEFAULTS,
    CalculatedPanel,
    CalculatePanelsRequest,
    CalculatePanelsResponse,
    CAMJobListItem,
    CAMJobsListResponse,
    CostBreakdownItem,
    CostEstimateResponse,
    DialogueTurnRequest,
    Export1CRequest,
    Export1CResponse,
    FactorySettingsResponse,
    FactorySettingsUpdate,
    FactorySettingsUpdateResponse,
    FinalizeOrderResponse,
    GenerateBOMRequest,
    GenerateBOMResponse,
    HardwareRecommendation,
    ImageExtractRequest,
    ImageExtractResponse,
    LayoutPreviewRequest,
    LayoutPreviewResponse,
    OrderCreate,
    OrderWithProductsResponse,
    PDFCuttingMapRequest,
    PlacedPanelInfo,
    ProductConfigResponse,
)
from .schemas import Order as OrderSchema

log = logging.getLogger(__name__)

# ============================================================================
# Системный промпт ИИ-технолога
# ============================================================================

TECHNOLOGIST_SYSTEM_PROMPT = """Ты — «Технолог-GPT», опытный технолог мебельной фабрики, специализирующийся на кухонной мебели (шкафы, тумбы, столешницы, фасады).

## Твоя задача
Помочь клиенту создать полную спецификацию (BOM) мебельного изделия. Ты АКТИВНО используешь инструменты для расчётов — не "болтаешь", а ДЕЛАЕШЬ.

## Доступные инструменты

### calculate_panels — ГЛАВНЫЙ ИНСТРУМЕНТ
Рассчитывает панели корпуса по габаритам. ВСЕГДА вызывай его когда клиент указывает размеры.

Типы корпусов:
- wall — навесной шкаф
- base — напольная тумба
- base_sink — тумба под мойку (без дна)
- drawer — тумба с ящиками
- tall — пенал

### find_hardware — подбор фурнитуры
Поиск в каталоге Boyard: петли, направляющие, ручки, подъёмники, опоры.

### calculate_hardware_qty — расчёт количества
Сколько петель на дверь, направляющих на ящик и т.д.

### get_hardware_details — информация по артикулу

## Алгоритм работы

1. **Клиент дал размеры** → СРАЗУ вызывай `calculate_panels`
2. **Панели рассчитаны** → вызывай `find_hardware` для фурнитуры
3. **Фурнитура подобрана** → вызывай `calculate_hardware_qty`
4. **Всё готово** → выведи сводку и маркеры [COMPLETE]

## Правила

1. **НЕ спрашивай лишнего** — если клиент указал размеры, сразу считай
2. **Используй дефолты** — полка 1шт, дверь 1шт, если не уточнено
3. **Один вопрос за раз** — если нужно уточнить, спрашивай ОДНО
4. **Кнопки ответов** — предлагай варианты: [BUTTONS: "Вариант 1", "Вариант 2"]
5. **Не показывай JSON** — никаких [TOOL_CALL], function_call и т.д.

## Пример идеального диалога

Клиент: "Напольный шкаф 600×720×560, белый ЛДСП, 2 двери"

Ты:
1. Вызываешь calculate_panels(cabinet_type="base", width=600, height=720, depth=560, door_count=2)
2. Вызываешь find_hardware для петель
3. Вызываешь calculate_hardware_qty(hardware_type="hinge", door_count=2)
4. Выводишь результат:

"Рассчитал напольный шкаф 600×720×560:

**Панели (5 шт, 1.2 м²):**
• Боковина левая — 550×720 мм
• Боковина правая — 550×720 мм
• Дно — 568×550 мм
• Царга передняя — 568×100 мм
• Царга задняя — 568×100 мм

**Фурнитура:**
• Петля Boyard H404A21 накладная — 4 шт
• Конфирмат 5×40 — 12 шт

Всё верно? Могу изменить или сгенерировать DXF."

## Завершение диалога

ВАЖНО: Когда клиент говорит "да", "верно", "генерируй", "генерируй DXF", "всё ок", "подтверждаю" — это ПОДТВЕРЖДЕНИЕ.
Ты НЕ генерируешь DXF сам — ты выдаёшь маркеры завершения, и система сама направит пользователя к генерации.

При подтверждении ОБЯЗАТЕЛЬНО включи в SPEC_JSON:
- `panels` — массив всех панелей из calculate_panels (name, width_mm, height_mm)
- `hardware` — массив фурнитуры (sku, name, qty)

При подтверждении выводи:

[COMPLETE]

[SPEC_JSON]
{
  "furniture_type": "напольная тумба",
  "dimensions": {
    "width_mm": 600,
    "height_mm": 720,
    "depth_mm": 560
  },
  "body_material": {
    "type": "ЛДСП",
    "thickness_mm": 16,
    "color": "белый"
  },
  "door_count": 2,
  "shelf_count": 1,
  "panels": [
    {"name": "Боковина левая", "width_mm": 550, "height_mm": 720},
    {"name": "Боковина правая", "width_mm": 550, "height_mm": 720},
    {"name": "Дно", "width_mm": 568, "height_mm": 550},
    {"name": "Царга передняя", "width_mm": 568, "height_mm": 100},
    {"name": "Царга задняя", "width_mm": 568, "height_mm": 100}
  ],
  "hardware": [
    {"sku": "H404A21", "name": "Петля накладная", "qty": 4}
  ]
}
[/SPEC_JSON]

## Стиль
- Краткие ответы (2-4 предложения)
- Технические термины с пояснениями
- Дружелюбно, но профессионально
"""

router = APIRouter(prefix="/api/v1")
dialogue_router = APIRouter(prefix="/api/v1/dialogue", tags=["Dialogue"])


@router.post("/orders", response_model=OrderSchema)
async def create_order(
    order: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать новый заказ.

    Требует авторизации. Заказ привязывается к фабрике пользователя.
    """
    factory_id = current_user.factory_id
    created_by_id = current_user.id

    return await crud.create_order(
        db=db,
        order=order,
        factory_id=factory_id,
        created_by_id=created_by_id
    )


@router.post("/orders/anonymous", response_model=OrderSchema)
async def create_anonymous_order(
    order: OrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать анонимный заказ (freemium флоу).

    Не требует авторизации. Заказ не привязан к фабрике.
    """
    return await crud.create_order(
        db=db,
        order=order,
        factory_id=None,
        created_by_id=None
    )


@router.get("/orders", response_model=list[OrderSchema])
async def list_orders(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Получить список заказов текущей фабрики.

    Если пользователь не авторизован — возвращает пустой список.
    """
    if not current_user:
        return []

    return await crud.get_orders_by_factory(
        db=db,
        factory_id=current_user.factory_id,
        limit=limit,
        offset=offset
    )


@router.get("/orders/{order_id}", response_model=OrderWithProductsResponse)
async def get_order_with_products_endpoint(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Получить заказ с продуктами для отображения на BOM странице."""
    order = await crud.get_order_with_products(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderWithProductsResponse(
        id=str(order.id),
        customer_ref=order.customer_ref,
        notes=order.notes,
        created_at=order.created_at,
        products=[
            ProductConfigResponse(
                id=str(p.id),
                name=p.name,
                width_mm=p.width_mm,
                height_mm=p.height_mm,
                depth_mm=p.depth_mm,
                material=p.material,
                thickness_mm=p.thickness_mm,
                params=p.params or {},
                notes=p.notes,
            )
            for p in order.products
        ],
    )


def _calculate_fasteners(panels_count: int, door_count: int, drawer_count: int, shelf_count: int) -> list[dict]:
    """Расчёт крепежа на основе количества панелей и элементов."""
    fasteners = []

    # Конфирматы для сборки корпуса (2 на соединение, ~4 соединения на панель)
    confirmats_count = panels_count * 4
    if confirmats_count > 0:
        fasteners.append({
            "id": str(uuid.uuid4()),
            "name": "Конфирмат",
            "size": "7×50",
            "quantity": confirmats_count,
            "purpose": "сборка корпуса",
            "unit_price": 2.0,
        })
        # Заглушки под конфирматы
        fasteners.append({
            "id": str(uuid.uuid4()),
            "name": "Заглушка",
            "size": "15мм",
            "quantity": confirmats_count,
            "purpose": "закрытие конфирматов",
            "unit_price": 1.0,
        })

    # Полкодержатели (4 на полку)
    if shelf_count > 0:
        fasteners.append({
            "id": str(uuid.uuid4()),
            "name": "Полкодержатель",
            "size": "5мм",
            "quantity": shelf_count * 4,
            "purpose": "крепление полок",
            "unit_price": 3.0,
        })

    return fasteners


def _calculate_edge_bands(panels: list, material_color: str = "белый") -> list[dict]:
    """Расчёт кромки на основе панелей."""
    # Считаем периметр всех панелей
    total_visible_edges_mm = 0  # Видимые торцы (ПВХ 2мм)
    total_hidden_edges_mm = 0   # Скрытые торцы (меламин 0.4мм)

    for panel in panels:
        width = panel.get("width_mm", 0) or 0
        height = panel.get("height_mm", 0) or 0
        name_lower = panel.get("name", "").lower()

        # Видимые торцы — передние кромки боковин и фасадов
        if "боковина" in name_lower or "фасад" in name_lower:
            total_visible_edges_mm += height  # Передняя кромка
            total_hidden_edges_mm += height + width * 2  # Остальные
        else:
            # Для остальных панелей — все скрытые
            total_hidden_edges_mm += (width + height) * 2

    edge_bands = []

    if total_visible_edges_mm > 0:
        edge_bands.append({
            "id": str(uuid.uuid4()),
            "type": "ПВХ 2мм",
            "color": material_color,
            "length_m": round(total_visible_edges_mm / 1000, 2),
            "purpose": "видимые торцы",
            "unit_price": 25.0,  # за погонный метр
        })

    if total_hidden_edges_mm > 0:
        edge_bands.append({
            "id": str(uuid.uuid4()),
            "type": "Меламин 0.4мм",
            "color": material_color,
            "length_m": round(total_hidden_edges_mm / 1000, 2),
            "purpose": "скрытые торцы",
            "unit_price": 8.0,
        })

    return edge_bands


@router.post("/orders/{order_id}/finalize", response_model=FinalizeOrderResponse)
async def finalize_order_endpoint(
    order_id: UUID,
    spec: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Финализация заказа после диалога с ИИ-технологом.

    Принимает JSON спецификацию от AI в гибком формате и сохраняет в ProductConfig.
    Автоматически рассчитывает крепёж и кромку.
    """
    import re

    # Проверяем существование заказа
    order = await crud.get_order_with_history(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Извлекаем размеры из разных форматов
    if "dimensions" in spec:
        dims = spec["dimensions"]
        width_mm = dims.get("width_mm") or dims.get("width", 0)
        height_mm = dims.get("height_mm") or dims.get("height", 0)
        depth_mm = dims.get("depth_mm") or dims.get("depth", 0)
    else:
        width_mm = spec.get("width_mm") or spec.get("width", 0)
        height_mm = spec.get("height_mm") or spec.get("height", 0)
        depth_mm = spec.get("depth_mm") or spec.get("depth", 0)

    # Извлекаем материал
    material = None
    thickness_mm = None
    material_color = "белый"
    if "body_material" in spec:
        mat = spec["body_material"]
        material = mat.get("type")
        thickness_mm = mat.get("thickness_mm")
        material_color = mat.get("color", "белый")
    else:
        material = spec.get("material")
        thickness_mm = spec.get("thickness_mm") or spec.get("thickness")

    # Название изделия
    name = spec.get("furniture_type") or spec.get("type") or spec.get("name") or "Изделие"

    # Извлекаем количества
    door_count = spec.get("door_count") or spec.get("doors", 0)
    drawer_count = spec.get("drawer_count") or spec.get("drawers", 0)
    shelf_count = spec.get("shelf_count") or spec.get("shelves", 0)

    # Парсим панели из spec или рассчитываем автоматически
    panels_data = spec.get("panels", [])
    parsed_panels = []

    if panels_data:
        # Панели пришли от AI — добавляем кромку по названию
        for panel_data in panels_data:
            panel_name = panel_data.get("name", "Панель")
            size_str = panel_data.get("size", "")

            panel_width = panel_data.get("width_mm", 0)
            panel_height = panel_data.get("height_mm", 0)
            if size_str and not (panel_width and panel_height):
                match = re.search(r"(\d+)[×x](\d+)", size_str)
                if match:
                    panel_width = float(match.group(1))
                    panel_height = float(match.group(2))

            # Определяем кромку по названию панели
            name_lower = panel_name.lower()
            edge_front = False
            edge_back = False

            if "бокови" in name_lower:  # Боковина левая/правая
                edge_front = True
            elif "верх" in name_lower or "низ" in name_lower or "дно" in name_lower:
                edge_front = True
            elif "фасад" in name_lower or "дверь" in name_lower or "дверц" in name_lower:
                edge_front = True
                edge_back = True  # Фасады кромятся с двух сторон
            elif "полк" in name_lower:
                edge_front = True
            # Задняя панель — без кромки (остаётся False/False)

            parsed_panels.append({
                "name": panel_name,
                "width_mm": panel_width,
                "height_mm": panel_height,
                "edge_front": panel_data.get("edge_front", edge_front),
                "edge_back": panel_data.get("edge_back", edge_back),
            })
    else:
        # Панели НЕ пришли — рассчитываем сами по габаритам
        from api.panel_calculator import calculate_panels

        # Определяем тип корпуса по названию
        furniture_lower = name.lower()
        if "навесн" in furniture_lower or "настенн" in furniture_lower:
            cabinet_type = "wall"
        elif "мойк" in furniture_lower:
            cabinet_type = "base_sink"
        elif "ящик" in furniture_lower:
            cabinet_type = "drawer"
        elif "пенал" in furniture_lower or "колонн" in furniture_lower:
            cabinet_type = "tall"
        else:
            cabinet_type = "base"  # По умолчанию напольная тумба

        try:
            calc_result = calculate_panels(
                cabinet_type=cabinet_type,
                width_mm=int(width_mm) if width_mm else 600,
                height_mm=int(height_mm) if height_mm else 720,
                depth_mm=int(depth_mm) if depth_mm else 560,
                thickness_mm=int(thickness_mm) if thickness_mm else 16,
                door_count=door_count,
                shelf_count=shelf_count,
                drawer_count=drawer_count,
            )

            for p in calc_result.panels:
                parsed_panels.append({
                    "name": p.name,
                    "width_mm": p.width_mm,
                    "height_mm": p.height_mm,
                    "edge_front": p.edge_front,
                    "edge_back": p.edge_back,
                })
        except Exception as e:
            log.warning(f"Failed to calculate panels: {e}")

    # Рассчитываем крепёж
    fasteners = _calculate_fasteners(
        panels_count=len(parsed_panels),
        door_count=door_count,
        drawer_count=drawer_count,
        shelf_count=shelf_count,
    )

    # Рассчитываем кромку
    edge_bands = _calculate_edge_bands(parsed_panels, material_color)

    # Рассчитываем площадь панелей
    total_area_m2 = sum(
        (p["width_mm"] * p["height_mm"]) / 1_000_000
        for p in parsed_panels
    )
    sheet_area_m2 = 5.796  # Стандартный лист 2800×2070

    # Собираем полные params
    full_params = {
        **spec,
        "fasteners": fasteners,
        "edge_bands": edge_bands,
        "summary": {
            "total_area_m2": round(total_area_m2, 3),
            "sheet_area_m2": sheet_area_m2,
            "utilization_percent": round((total_area_m2 / sheet_area_m2) * 100, 1) if total_area_m2 > 0 else 0,
            "panels_count": len(parsed_panels),
            "hardware_count": len(spec.get("hardware", [])),
            "fasteners_count": sum(f["quantity"] for f in fasteners),
        },
    }

    # Создаём ProductConfig
    product_config = ProductConfig(
        order_id=order_id,
        name=name,
        width_mm=float(width_mm) if width_mm else 0,
        height_mm=float(height_mm) if height_mm else 0,
        depth_mm=float(depth_mm) if depth_mm else 0,
        material=material,
        thickness_mm=float(thickness_mm) if thickness_mm else None,
        params=full_params,
    )
    db.add(product_config)
    await db.flush()  # Получаем сгенерированный product_config.id

    # Сохраняем панели в таблицу
    for panel_data in parsed_panels:
        panel = Panel(
            product_id=product_config.id,
            name=panel_data["name"],
            width_mm=panel_data["width_mm"],
            height_mm=panel_data["height_mm"],
            thickness_mm=thickness_mm or 16.0,
            material=material,
            edge_front=panel_data.get("edge_front", False),
            edge_back=panel_data.get("edge_back", False),
            drilling_points=panel_data.get("drilling_points"),
        )
        db.add(panel)

    # Обновляем статус заказа
    order.status = "ready"
    await db.commit()

    return FinalizeOrderResponse(
        success=True,
        order_id=str(order_id),
        product_config_id=str(product_config.id),
        message="Заказ финализирован. Можно переходить к генерации DXF/G-code.",
    )


# ============================================================================
# BOM — полная спецификация заказа
# ============================================================================


@router.get("/orders/{order_id}/bom")
async def get_order_bom(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить полную спецификацию (BOM) заказа.

    Включает:
    - Основные параметры (габариты, материал)
    - Панели с размерами
    - Фурнитуру
    - Крепёж (конфирматы, заглушки)
    - Кромку
    - Сводку (площадь, % использования листа)
    """
    order = await crud.get_order_with_products(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.products:
        raise HTTPException(status_code=404, detail="No product config found for this order")

    # Берём первый ProductConfig (обычно один на заказ)
    product = order.products[0]

    # Получаем панели из БД
    from sqlalchemy import select
    panels_result = await db.execute(
        select(Panel).where(Panel.product_id == product.id)
    )
    panels = panels_result.scalars().all()

    # Формируем ответ
    params = product.params or {}

    return {
        "order_id": str(order_id),
        "product_config_id": str(product.id),
        "furniture_type": product.name,
        "dimensions": {
            "width_mm": product.width_mm,
            "height_mm": product.height_mm,
            "depth_mm": product.depth_mm,
        },
        "body_material": {
            "type": product.material,
            "thickness_mm": product.thickness_mm,
            "color": params.get("body_material", {}).get("color", "белый") if isinstance(params.get("body_material"), dict) else "белый",
        },
        "panels": [
            {
                "id": str(p.id),
                "name": p.name,
                "width_mm": p.width_mm,
                "height_mm": p.height_mm,
                "thickness_mm": p.thickness_mm,
                "material": p.material,
                "edge_front": p.edge_front,
                "edge_back": p.edge_back,
            }
            for p in panels
        ],
        "hardware": params.get("hardware", []),
        "fasteners": params.get("fasteners", []),
        "edge_bands": params.get("edge_bands", []),
        "summary": params.get("summary", {}),
        "door_count": params.get("door_count") or params.get("doors", 0),
        "drawer_count": params.get("drawer_count") or params.get("drawers", 0),
        "shelf_count": params.get("shelf_count") or params.get("shelves", 0),
    }


@router.patch("/orders/{order_id}/bom")
async def update_order_bom(
    order_id: UUID,
    updates: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить спецификацию (BOM) заказа.

    Позволяет редактировать:
    - dimensions: габариты изделия
    - panels: массив панелей (id + обновления)
    - hardware: массив фурнитуры
    - fasteners: массив крепежа
    - edge_bands: массив кромки
    """
    order = await crud.get_order_with_products(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.products:
        raise HTTPException(status_code=404, detail="No product config found")

    product = order.products[0]

    # Обновляем габариты
    if "dimensions" in updates:
        dims = updates["dimensions"]
        if "width_mm" in dims:
            product.width_mm = float(dims["width_mm"])
        if "height_mm" in dims:
            product.height_mm = float(dims["height_mm"])
        if "depth_mm" in dims:
            product.depth_mm = float(dims["depth_mm"])

    # Обновляем название
    if "furniture_type" in updates:
        product.name = updates["furniture_type"]

    # Обновляем материал
    if "body_material" in updates:
        mat = updates["body_material"]
        if "type" in mat:
            product.material = mat["type"]
        if "thickness_mm" in mat:
            product.thickness_mm = float(mat["thickness_mm"])

    # Обновляем панели
    if "panels" in updates:
        from sqlalchemy import select
        for panel_update in updates["panels"]:
            panel_id = panel_update.get("id")
            if panel_id:
                result = await db.execute(
                    select(Panel).where(Panel.id == UUID(panel_id))
                )
                panel = result.scalars().first()
                if panel:
                    if "name" in panel_update:
                        panel.name = panel_update["name"]
                    if "width_mm" in panel_update:
                        panel.width_mm = float(panel_update["width_mm"])
                    if "height_mm" in panel_update:
                        panel.height_mm = float(panel_update["height_mm"])

    # Обновляем params (hardware, fasteners, edge_bands)
    params = product.params or {}
    for key in ["hardware", "fasteners", "edge_bands", "door_count", "drawer_count", "shelf_count"]:
        if key in updates:
            params[key] = updates[key]

    # Пересчитываем сводку если изменились панели
    if "panels" in updates:
        from sqlalchemy import select
        panels_result = await db.execute(
            select(Panel).where(Panel.product_id == product.id)
        )
        panels = panels_result.scalars().all()
        total_area = sum((p.width_mm * p.height_mm) / 1_000_000 for p in panels)
        sheet_area = 5.796
        params["summary"] = {
            "total_area_m2": round(total_area, 3),
            "sheet_area_m2": sheet_area,
            "utilization_percent": round((total_area / sheet_area) * 100, 1) if total_area > 0 else 0,
            "panels_count": len(panels),
            "hardware_count": len(params.get("hardware", [])),
            "fasteners_count": sum(f.get("quantity", 0) for f in params.get("fasteners", [])),
        }

    product.params = params
    await db.commit()

    return {"success": True, "message": "BOM обновлён"}


@router.post("/orders/{order_id}/bom/add-panel")
async def add_panel_to_bom(
    order_id: UUID,
    panel_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Добавить панель в BOM."""
    order = await crud.get_order_with_products(db, order_id)
    if not order or not order.products:
        raise HTTPException(status_code=404, detail="Order not found")

    product = order.products[0]

    panel = Panel(
        product_id=product.id,
        name=panel_data.get("name", "Новая панель"),
        width_mm=float(panel_data.get("width_mm", 0)),
        height_mm=float(panel_data.get("height_mm", 0)),
        thickness_mm=float(panel_data.get("thickness_mm", product.thickness_mm or 16)),
        material=panel_data.get("material", product.material),
        drilling_points=panel_data.get("drilling_points"),
    )
    db.add(panel)
    await db.commit()

    return {"success": True, "panel_id": str(panel.id)}


@router.delete("/orders/{order_id}/bom/panel/{panel_id}")
async def delete_panel_from_bom(
    order_id: UUID,
    panel_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Удалить панель из BOM."""
    from sqlalchemy import select

    # Проверяем что панель принадлежит заказу
    order = await crud.get_order_with_products(db, order_id)
    if not order or not order.products:
        raise HTTPException(status_code=404, detail="Order not found")

    product = order.products[0]

    result = await db.execute(
        select(Panel).where(Panel.id == panel_id, Panel.product_id == product.id)
    )
    panel = result.scalars().first()
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")

    await db.delete(panel)
    await db.commit()

    return {"success": True}


@router.post("/orders/{order_id}/bom/recalculate")
async def recalculate_bom(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Пересчитать BOM на основе текущих габаритов и параметров.

    Вызывает калькуляторы:
    - calculate_panels — панели по габаритам и типу корпуса
    - _calculate_fasteners — крепёж
    - _calculate_edge_bands — кромка

    Сохраняет результат в БД и возвращает обновлённый BOM.
    """
    from sqlalchemy import delete as sql_delete

    from api.panel_calculator import calculate_panels

    order = await crud.get_order_with_products(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.products:
        raise HTTPException(status_code=404, detail="No product config found")

    product = order.products[0]
    params = product.params or {}

    # Определяем тип корпуса из названия
    furniture_name = (product.name or "").lower()
    cabinet_type = "wall"  # По умолчанию навесной

    if "напольн" in furniture_name or "тумб" in furniture_name or "нижн" in furniture_name:
        if "мойк" in furniture_name:
            cabinet_type = "base_sink"
        elif "ящик" in furniture_name:
            cabinet_type = "drawer"
        else:
            cabinet_type = "base"
    elif "пенал" in furniture_name or "высок" in furniture_name or "колонн" in furniture_name:
        cabinet_type = "tall"
    elif "ящик" in furniture_name:
        cabinet_type = "drawer"

    # Параметры для калькулятора
    width_mm = int(product.width_mm or 600)
    height_mm = int(product.height_mm or 720)
    depth_mm = int(product.depth_mm or 300)
    thickness_mm = float(product.thickness_mm or 16)
    shelf_count = params.get("shelf_count", 1)
    door_count = params.get("door_count", 1)
    drawer_count = params.get("drawer_count", 0)

    # Вызываем калькулятор панелей
    calc_result = calculate_panels(
        cabinet_type=cabinet_type,
        width_mm=width_mm,
        height_mm=height_mm,
        depth_mm=depth_mm,
        thickness_mm=thickness_mm,
        shelf_count=shelf_count,
        door_count=door_count,
        drawer_count=drawer_count,
    )

    # Удаляем старые панели
    await db.execute(
        sql_delete(Panel).where(Panel.product_id == product.id)
    )

    # Создаём новые панели
    new_panels = []
    for panel_spec in calc_result.panels:
        panel = Panel(
            product_id=product.id,
            name=panel_spec.name,
            width_mm=panel_spec.width_mm,
            height_mm=panel_spec.height_mm,
            thickness_mm=panel_spec.thickness_mm,
            material=product.material,
            edge_front=panel_spec.edge_front,
            edge_back=panel_spec.edge_back,
            drilling_points=panel_spec.drilling_points,
        )
        db.add(panel)
        new_panels.append(panel)

    await db.flush()  # Получаем ID для новых панелей

    # Рассчитываем крепёж
    fasteners = _calculate_fasteners(
        panels_count=calc_result.total_panels,
        door_count=door_count,
        drawer_count=drawer_count,
        shelf_count=shelf_count,
    )

    # Рассчитываем кромку
    material_color = params.get("body_material", {}).get("color", "белый") if isinstance(params.get("body_material"), dict) else "белый"
    parsed_panels = [p.to_dict() for p in calc_result.panels]
    edge_bands = _calculate_edge_bands(parsed_panels, material_color)

    # Обновляем params
    params["fasteners"] = fasteners
    params["edge_bands"] = edge_bands
    params["cabinet_type"] = cabinet_type
    params["summary"] = {
        "total_panels": calc_result.total_panels,
        "total_area_m2": round(calc_result.total_area_m2, 2),
        "edge_length_m": round(calc_result.edge_length_m, 2),
        "fasteners_count": sum(f["quantity"] for f in fasteners),
        "warnings": calc_result.warnings,
    }

    product.params = params
    await db.commit()

    # Возвращаем обновлённый BOM
    return {
        "order_id": str(order_id),
        "product_config_id": str(product.id),
        "furniture_type": product.name,
        "cabinet_type": cabinet_type,
        "dimensions": {
            "width_mm": product.width_mm,
            "height_mm": product.height_mm,
            "depth_mm": product.depth_mm,
        },
        "body_material": {
            "type": product.material,
            "thickness_mm": product.thickness_mm,
            "color": material_color,
        },
        "panels": [
            {
                "id": str(p.id),
                "name": p.name,
                "width_mm": p.width_mm,
                "height_mm": p.height_mm,
                "thickness_mm": p.thickness_mm,
                "material": p.material,
                "edge_front": p.edge_front,
                "edge_back": p.edge_back,
            }
            for p in new_panels
        ],
        "hardware": params.get("hardware", []),
        "fasteners": fasteners,
        "edge_bands": edge_bands,
        "summary": params["summary"],
        "door_count": door_count,
        "drawer_count": drawer_count,
        "shelf_count": shelf_count,
    }


# ============================================================================
# Dashboard Stats
# ============================================================================


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Получить статистику заказов для dashboard.

    Возвращает количество заказов по статусам:
    - draft: Черновик
    - ready: Готов к производству
    - completed: Выполнен
    - total: Всего заказов
    """
    factory_id = current_user.factory_id if current_user else None
    stats = await crud.get_dashboard_stats(db, factory_id)
    return stats


# ============================================================================
# Settings — настройки фабрики
# ============================================================================

@router.get("/settings", response_model=FactorySettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить настройки фабрики.

    Возвращает merged настройки (сохранённые + дефолты) и список полей,
    где использованы дефолтные значения.

    Требует авторизации.
    """
    # Получаем фабрику пользователя
    result = await db.execute(
        select(Factory).where(Factory.id == current_user.factory_id)
    )
    factory = result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    # Получаем owner email
    owner_result = await db.execute(
        select(User).where(
            User.factory_id == factory.id,
            User.is_owner == True  # noqa: E712
        )
    )
    owner = owner_result.scalar_one_or_none()
    owner_email = owner.email if owner else current_user.email

    # Merge настроек с дефолтами
    saved_settings = factory.settings or {}
    merged_settings = {}
    defaults_used = []

    for key, default_value in SETTINGS_DEFAULTS.items():
        if key in saved_settings and saved_settings[key] is not None:
            merged_settings[key] = saved_settings[key]
        else:
            merged_settings[key] = default_value
            defaults_used.append(key)

    # Добавляем decor (нет дефолта)
    merged_settings["decor"] = saved_settings.get("decor")

    return FactorySettingsResponse(
        factory_name=factory.name,
        owner_email=owner_email,
        settings=merged_settings,
        defaults_used=defaults_used,
    )


@router.patch("/settings", response_model=FactorySettingsUpdateResponse)
async def update_settings(
    req: FactorySettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить настройки фабрики (частично).

    Передайте только те поля, которые хотите изменить.
    Чтобы сбросить поле к дефолту, передайте `null`.

    Требует авторизации (только owner может менять factory_name).
    """
    # Получаем фабрику
    result = await db.execute(
        select(Factory).where(Factory.id == current_user.factory_id)
    )
    factory = result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    updated_fields = []

    # Обновление названия фабрики (только owner)
    if req.factory_name is not None:
        if not current_user.is_owner:
            raise HTTPException(
                status_code=403,
                detail="Only owner can change factory name"
            )
        factory.name = req.factory_name
        updated_fields.append("factory_name")

    # Обновление настроек (JSON field)
    current_settings = dict(factory.settings or {})

    # Все поля настроек (кроме factory_name)
    settings_fields = [
        "machine_profile", "sheet_width_mm", "sheet_height_mm",
        "thickness_mm", "edge_thickness_mm", "decor", "gap_mm",
        "spindle_speed", "feed_rate_cutting", "feed_rate_plunge",
        "cut_depth", "safe_height", "tool_diameter"
    ]

    req_dict = req.model_dump(exclude_unset=True)

    for field in settings_fields:
        if field in req_dict:
            value = req_dict[field]
            if value is None:
                # null = сброс к дефолту (удаляем из settings)
                current_settings.pop(field, None)
            else:
                current_settings[field] = value
            updated_fields.append(field)

    factory.settings = current_settings
    await db.commit()

    return FactorySettingsUpdateResponse(
        success=True,
        updated_fields=updated_fields,
    )


# ============================================================================
# Panel Calculator — расчёт панелей
# ============================================================================

@router.post("/panels/calculate", response_model=CalculatePanelsResponse)
async def calculate_panels_endpoint(
    req: CalculatePanelsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> CalculatePanelsResponse:
    """
    Рассчитать панели для корпусной мебели.

    Типы: wall, base, base_sink, drawer, tall
    Параметры берутся из: запрос > настройки фабрики > дефолты.
    """
    from api.panel_calculator import calculate_panels

    # Получаем настройки фабрики если авторизован
    factory_settings = {}
    if current_user:
        factory = await db.get(Factory, current_user.factory_id)
        if factory:
            factory_settings = factory.settings or {}

    # Merge параметров: запрос > настройки > дефолты
    thickness = (
        req.thickness_mm
        or factory_settings.get("thickness_mm")
        or SETTINGS_DEFAULTS["thickness_mm"]
    )
    edge_thickness = (
        req.edge_thickness_mm
        or factory_settings.get("edge_thickness_mm")
        or SETTINGS_DEFAULTS["edge_thickness_mm"]
    )

    try:
        result = calculate_panels(
            cabinet_type=req.cabinet_type.value,
            width_mm=req.width_mm,
            height_mm=req.height_mm,
            depth_mm=req.depth_mm,
            thickness_mm=thickness,
            edge_thickness_mm=edge_thickness,
            shelf_count=req.shelf_count,
            door_count=req.door_count,
            drawer_count=req.drawer_count,
        )

        panels = [
            CalculatedPanel(
                name=p.name,
                width_mm=p.width_mm,
                height_mm=p.height_mm,
                thickness_mm=p.thickness_mm,
                quantity=p.quantity,
                edge_front=p.edge_front,
                edge_back=p.edge_back,
                edge_top=p.edge_top,
                edge_bottom=p.edge_bottom,
                edge_thickness_mm=p.edge_thickness_mm,
                has_slot_for_back=p.has_slot_for_back,
                notes=p.notes,
            )
            for p in result.panels
        ]

        return CalculatePanelsResponse(
            success=True,
            cabinet_type=result.cabinet_type,
            dimensions={
                "width": result.width_mm,
                "height": result.height_mm,
                "depth": result.depth_mm,
            },
            panels=panels,
            total_panels=result.total_panels,
            total_area_m2=round(result.total_area_m2, 2),
            edge_length_m=round(result.edge_length_m, 1),
            warnings=result.warnings,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# BOM Generator — генерация полного BOM (панели + фурнитура)
# ============================================================================

@router.post("/bom/generate", response_model=GenerateBOMResponse)
async def generate_bom_endpoint(
    req: GenerateBOMRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> GenerateBOMResponse:
    """
    Сгенерировать полный BOM (панели + фурнитура) для изделия.

    Объединяет:
    1. Расчёт панелей через калькулятор
    2. Подбор фурнитуры через RAG
    3. Расчёт количества фурнитуры

    Это endpoint для прямого вызова, без диалога с AI.
    """
    from api.ai_tools import (
        handle_calculate_hardware_qty,
        handle_find_hardware,
    )
    from api.panel_calculator import calculate_panels

    # Получаем настройки фабрики
    factory_settings = {}
    if current_user:
        factory = await db.get(Factory, current_user.factory_id)
        if factory:
            factory_settings = factory.settings or {}

    thickness = factory_settings.get("thickness_mm", SETTINGS_DEFAULTS["thickness_mm"])

    # 1. Расчёт панелей
    try:
        panel_result = calculate_panels(
            cabinet_type=req.cabinet_type.value,
            width_mm=req.width_mm,
            height_mm=req.height_mm,
            depth_mm=req.depth_mm,
            thickness_mm=thickness,
            shelf_count=req.shelf_count,
            door_count=req.door_count,
            drawer_count=req.drawer_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Подбор фурнитуры
    hardware_list: list[HardwareRecommendation] = []

    # Петли (если есть двери)
    if req.door_count > 0:
        hinges = await handle_find_hardware(
            query="петля накладная с доводчиком",
            hardware_type="hinge",
            limit=1,
        )

        qty_result = await handle_calculate_hardware_qty(
            hardware_type="hinge",
            door_count=req.door_count,
            door_height_mm=float(req.height_mm),
        )

        if hinges.get("success") and hinges.get("items"):
            item = hinges["items"][0]
            hardware_list.append(HardwareRecommendation(
                type="hinge",
                sku=item.get("sku"),
                name=item.get("name", "Петля накладная"),
                quantity=qty_result.get("quantity", req.door_count * 2),
                unit="шт",
                source="rag",
            ))
        else:
            hardware_list.append(HardwareRecommendation(
                type="hinge",
                sku=None,
                name="Петля накладная с доводчиком",
                quantity=qty_result.get("quantity", req.door_count * 2),
                unit="шт",
                source="calculated",
            ))

    # Направляющие (если есть ящики)
    if req.drawer_count > 0:
        slides = await handle_find_hardware(
            query="направляющие полного выдвижения",
            hardware_type="slide",
            limit=1,
        )

        qty_result = await handle_calculate_hardware_qty(
            hardware_type="slide",
            drawer_count=req.drawer_count,
        )

        if slides.get("success") and slides.get("items"):
            item = slides["items"][0]
            hardware_list.append(HardwareRecommendation(
                type="slide",
                sku=item.get("sku"),
                name=item.get("name", "Направляющие"),
                quantity=qty_result.get("quantity", req.drawer_count),
                unit="пар",
                source="rag",
            ))
        else:
            hardware_list.append(HardwareRecommendation(
                type="slide",
                sku=None,
                name="Направляющие полного выдвижения",
                quantity=req.drawer_count,
                unit="пар",
                source="calculated",
            ))

    # Конфирматы (всегда)
    fixed_panels = sum(1 for p in panel_result.panels if "полка" not in p.name.lower())
    confirmat_qty = fixed_panels * 4

    hardware_list.append(HardwareRecommendation(
        type="connector",
        sku=None,
        name="Конфирмат 5×40",
        quantity=confirmat_qty,
        unit="шт",
        source="calculated",
    ))

    # Полкодержатели (если есть полки)
    if req.shelf_count > 0:
        hardware_list.append(HardwareRecommendation(
            type="other",
            sku=None,
            name="Полкодержатель 5мм",
            quantity=req.shelf_count * 4,
            unit="шт",
            source="calculated",
        ))

    # Формируем ответ
    panels = [
        CalculatedPanel(
            name=p.name,
            width_mm=p.width_mm,
            height_mm=p.height_mm,
            thickness_mm=p.thickness_mm,
            quantity=p.quantity,
            edge_front=p.edge_front,
            edge_back=p.edge_back,
            edge_top=p.edge_top,
            edge_bottom=p.edge_bottom,
            edge_thickness_mm=p.edge_thickness_mm,
            has_slot_for_back=p.has_slot_for_back,
            notes=p.notes,
        )
        for p in panel_result.panels
    ]

    return GenerateBOMResponse(
        success=True,
        order_id=req.order_id,
        cabinet_type=panel_result.cabinet_type,
        dimensions={
            "width": panel_result.width_mm,
            "height": panel_result.height_mm,
            "depth": panel_result.depth_mm,
        },
        panels=panels,
        hardware=hardware_list,
        total_panels=panel_result.total_panels,
        total_area_m2=round(panel_result.total_area_m2, 2),
        edge_length_m=round(panel_result.edge_length_m, 1),
        total_hardware_items=sum(h.quantity for h in hardware_list),
        warnings=panel_result.warnings,
    )


# ============================================================================
# Hardware Search — RAG поиск фурнитуры
# ============================================================================

from .schemas import HardwareSearchItem, HardwareSearchResponse
from .vector_search import search_hardware_by_text


@router.get("/hardware/search", response_model=HardwareSearchResponse)
async def search_hardware(
    q: str,
    limit: int = 10,
) -> HardwareSearchResponse:
    """
    Поиск фурнитуры по текстовому запросу (RAG).

    Использует векторный поиск через FRIDA embeddings + pgvector.
    Возвращает релевантные позиции из каталога Boyard (1305 позиций).

    ## Примеры запросов:
    - `q=петля 110 градусов` — петли с углом открывания 110°
    - `q=направляющие 450` — направляющие длиной 450мм
    - `q=подъёмник авентос` — подъёмные механизмы Aventos
    - `q=ручка скоба` — ручки-скобы
    """
    results = await search_hardware_by_text(query_text=q, k=limit)

    items = []
    for i, hw in enumerate(results):
        # Рассчитываем score как убывающую релевантность
        score = 1.0 - (i * 0.05) if i < 20 else 0.1
        items.append(HardwareSearchItem(
            sku=hw.sku,
            name=hw.name,
            description=hw.description,
            brand=hw.brand,
            type=hw.type,
            category=hw.category,
            price_rub=hw.price_rub,
            params=hw.params or {},
            score=round(score, 2),
        ))

    return HardwareSearchResponse(
        items=items,
        total=len(items),
        query=q,
    )


# ============================================================================
# Integrations — 1C Export
# ============================================================================

@router.post("/integrations/1c/export", response_model=Export1CResponse)
async def export_1c(req: Export1CRequest, db: AsyncSession = Depends(get_db)) -> Export1CResponse:
    """
    Экспорт заказа в формате для 1С.

    Поддерживаемые форматы:
    - excel: Excel файл (.xlsx) с листами Заказ, Изделия, Панели, Фурнитура
    - csv: Набор CSV файлов в ZIP архиве

    Возвращает presigned URL для скачивания (действует 15 минут).
    """
    import io
    import zipfile

    from api.export_1c import generate_1c_filename, generate_order_csv, generate_order_excel

    # Получаем заказ с продуктами
    order = await crud.get_order_with_products(db, req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Получаем BOM items если есть
    bom_result = await db.execute(
        select(models.BOMItem).where(models.BOMItem.order_id == req.order_id)
    )
    bom_items = list(bom_result.scalars().all())

    storage = ObjectStorage()
    storage.ensure_bucket()

    if req.format == "excel":
        # Генерируем Excel
        excel_bytes = generate_order_excel(order, order.products, bom_items)
        filename = generate_1c_filename(order, "xlsx")
        storage_key = f"exports/1c/{filename}"

        storage.put_object(
            key=storage_key,
            data=excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:  # csv
        # Генерируем CSV файлы и пакуем в ZIP
        csv_files = generate_order_csv(order, order.products, bom_items)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in csv_files.items():
                zf.writestr(name, content)

        zip_buffer.seek(0)
        filename = generate_1c_filename(order, "zip")
        storage_key = f"exports/1c/{filename}"

        storage.put_object(
            key=storage_key,
            data=zip_buffer.getvalue(),
            content_type="application/zip"
        )

    # Генерируем presigned URL
    download_url = storage.presign_get(storage_key, ttl_seconds=900)

    log.info(f"[1C Export] Order {req.order_id} exported as {req.format}: {filename}")

    return Export1CResponse(
        success=True,
        format=req.format,
        filename=filename,
        download_url=download_url,
        expires_in_seconds=900
    )


# ============================================================================
# Vision OCR - извлечение параметров из изображений
# ============================================================================

@router.post("/spec/extract-from-image", response_model=ImageExtractResponse)
async def extract_from_image(req: ImageExtractRequest) -> ImageExtractResponse:
    """
    Извлечение параметров мебели из фото или эскиза.

    Процесс:
    1. Vision OCR: распознавание текста с изображения
    2. GPT: парсинг текста в структурированные параметры
    3. При низкой уверенности — рекомендация перейти в диалог

    ## Пример запроса:
    ```json
    {
        "image_base64": "base64_encoded_image...",
        "image_mime_type": "image/jpeg",
        "language_hint": "ru"
    }
    ```

    ## Пример ответа:
    ```json
    {
        "success": true,
        "parameters": {
            "furniture_type": {"category": "навесной_шкаф", ...},
            "dimensions": {"width_mm": 600, "height_mm": 720, ...},
            "body_material": {"type": "ЛДСП", "color": "белый"},
            ...
        },
        "fallback_to_dialogue": false,
        "ocr_confidence": 0.85,
        "processing_time_ms": 1500
    }
    ```

    При `fallback_to_dialogue: true` рекомендуется перенаправить пользователя
    в диалог с ИИ-технологом для уточнения параметров.
    """
    # Проверяем наличие Yandex Cloud ключей
    use_mock = not are_yc_keys_available()

    if use_mock:
        log.warning("[Vision OCR] Mock mode: YC keys not found")
        return await extract_furniture_params_mock(req.image_base64, req.image_mime_type)

    log.info(f"[Vision OCR] Processing image, mime: {req.image_mime_type}, lang: {req.language_hint}")

    result = await extract_furniture_params_from_image(
        image_base64=req.image_base64,
        mime_type=req.image_mime_type,
        language_hint=req.language_hint,
    )

    log.info(f"[Vision OCR] Result: success={result.success}, confidence={result.ocr_confidence:.2f}, fallback={result.fallback_to_dialogue}")

    return result


# ============================================================================
# CAM - генерация DXF и G-code (P1)
# ============================================================================

from .gcode_generator import get_available_profiles
from .schemas import (
    ArtifactDownload,
    CAMJobStatus,
    DrillingGcodeRequest,
    DrillingGcodeResponse,
    DXFJobRequest,
    DXFJobResponse,
    GCodeJobRequest,
    GCodeJobResponse,
    MachineProfileInfo,
    MachineProfilesList,
)


@router.post("/cam/dxf", response_model=DXFJobResponse)
async def create_dxf_job(
    req: DXFJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DXFJobResponse:
    """
    Создаёт задачу генерации DXF файла для раскроя панелей.

    Параметры берутся из: запрос > настройки фабрики > дефолты.

    ## Пример запроса:
    ```json
    {
        "panels": [
            {"name": "Боковина левая", "width_mm": 720, "height_mm": 560, "edge_left": true},
            {"name": "Боковина правая", "width_mm": 720, "height_mm": 560, "edge_right": true},
            {"name": "Дно", "width_mm": 568, "height_mm": 560, "edge_top": true}
        ],
        "optimize_layout": true
    }
    ```

    Задача ставится в очередь и обрабатывается worker'ом.
    Проверяйте статус через GET /cam/jobs/{job_id}.
    """
    # Получаем настройки фабрики
    factory = await db.get(Factory, current_user.factory_id)
    factory_settings = factory.settings if factory else {}

    # Merge: запрос > настройки фабрики > дефолты
    sheet_width = (
        req.sheet_width_mm
        or factory_settings.get("sheet_width_mm")
        or SETTINGS_DEFAULTS["sheet_width_mm"]
    )
    sheet_height = (
        req.sheet_height_mm
        or factory_settings.get("sheet_height_mm")
        or SETTINGS_DEFAULTS["sheet_height_mm"]
    )
    gap_mm = (
        req.gap_mm
        if req.gap_mm is not None
        else factory_settings.get("gap_mm", SETTINGS_DEFAULTS["gap_mm"])
    )

    # Создаём CAM задачу в БД
    job_id = uuid.uuid4()
    context = {
        "panels": [p.model_dump() for p in req.panels],
        "sheet_width": sheet_width,
        "sheet_height": sheet_height,
        "optimize": req.optimize_layout,
        "gap_mm": gap_mm,
    }

    stmt = insert(CAMJob).values(
        id=job_id,
        order_id=req.order_id,
        job_kind="DXF",
        status=JobStatusEnum.Created,
        context=context,
        idempotency_key=req.idempotency_key,
    )
    await db.execute(stmt)
    await db.commit()

    # Отправляем в очередь
    await enqueue(DXF_QUEUE, {
        "job_id": str(job_id),
        "job_kind": "DXF",
        "context": context,
        "idempotency_key": req.idempotency_key,
    })

    log.info(f"[CAM] Created DXF job {job_id} with {len(req.panels)} panels")

    return DXFJobResponse(
        job_id=job_id,
        status="created",
        panels_count=len(req.panels),
        sheet_size=(sheet_width, sheet_height),
    )


@router.get("/cam/jobs", response_model=CAMJobsListResponse)
async def list_cam_jobs(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> CAMJobsListResponse:
    """
    Получить список CAM задач.

    Параметры:
    - limit: максимальное количество (по умолчанию 50)
    - offset: смещение для пагинации
    - status: фильтр по статусу (Created, Processing, Completed, Failed)
    """
    query = select(CAMJob).order_by(CAMJob.created_at.desc())

    if status:
        query = query.where(CAMJob.status == status)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Общее количество
    count_query = select(CAMJob)
    if status:
        count_query = count_query.where(CAMJob.status == status)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return CAMJobsListResponse(
        jobs=[
            CAMJobListItem(
                job_id=job.id,
                job_kind=job.job_kind,
                status=job.status,
                order_id=job.order_id,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job in jobs
        ],
        total=total,
    )


@router.get("/cam/jobs/{job_id}", response_model=CAMJobStatus)
async def get_cam_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CAMJobStatus:
    """
    Получить статус CAM задачи.

    Статусы:
    - Created: задача создана, ожидает обработки
    - Processing: задача выполняется
    - Completed: задача завершена, доступен артефакт
    - Failed: ошибка выполнения

    При статусе Completed используйте /cam/jobs/{job_id}/download для скачивания.
    """
    job = await db.get(CAMJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="CAM job not found")

    # Извлекаем информацию о раскладке из контекста (если есть)
    layout_info = job.context.get("layout_result", {}) if job.context else {}

    return CAMJobStatus(
        job_id=job.id,
        job_kind=job.job_kind,
        status=job.status,
        artifact_id=job.artifact_id,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        utilization_percent=layout_info.get("utilization_percent"),
        panels_placed=layout_info.get("panels_placed"),
        panels_unplaced=layout_info.get("panels_unplaced"),
    )


@router.get("/cam/jobs/{job_id}/download", response_model=ArtifactDownload)
async def download_cam_artifact(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ArtifactDownload:
    """
    Получить ссылку для скачивания результата CAM задачи.

    Возвращает presigned URL, действительный 15 минут.
    """
    job = await db.get(CAMJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="CAM job not found")

    if job.status != JobStatusEnum.Completed:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status.value}"
        )

    if not job.artifact_id:
        raise HTTPException(status_code=404, detail="No artifact for this job")

    artifact = await db.get(Artifact, job.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Генерируем presigned URL
    storage = ObjectStorage()
    url = storage.presign_get(artifact.storage_key, ttl_seconds=900)

    # Определяем имя файла
    ext = "dxf" if job.job_kind == "DXF" else "gcode" if job.job_kind == "GCODE" else "zip"
    filename = f"order_{job.order_id}_{job.job_kind.lower()}.{ext}" if job.order_id else f"job_{job_id}.{ext}"

    return ArtifactDownload(
        artifact_id=artifact.id,
        type=job.job_kind,
        filename=filename,
        download_url=url,
        size_bytes=artifact.size_bytes or 0,
        expires_in_seconds=900,
    )


@router.get("/cam/jobs/{job_id}/file")
async def stream_cam_file(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Скачать файл CAM задачи напрямую через API (без presigned URL).

    Этот endpoint стримит файл из S3 через сервер, что обходит
    проблемы с файерволом и подписями presigned URL.
    """
    from fastapi.responses import StreamingResponse

    job = await db.get(CAMJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="CAM job not found")

    if job.status != JobStatusEnum.Completed:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status}"
        )

    if not job.artifact_id:
        raise HTTPException(status_code=404, detail="No artifact for this job")

    artifact = await db.get(Artifact, job.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Скачиваем файл из S3
    storage = ObjectStorage()
    file_data = storage.get_object(artifact.storage_key)

    # Определяем имя файла и content-type
    ext = "dxf" if job.job_kind == "DXF" else "gcode" if job.job_kind == "GCODE" else "zip"
    filename = f"order_{job.order_id}_{job.job_kind.lower()}.{ext}" if job.order_id else f"job_{job_id}.{ext}"

    content_type = {
        "DXF": "application/dxf",
        "GCODE": "text/plain",
        "ZIP": "application/zip",
    }.get(job.job_kind, "application/octet-stream")

    return StreamingResponse(
        iter([file_data]),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_data)),
        }
    )


# ============================================================================
# G-code генерация (P2)
# ============================================================================

@router.get("/cam/machine-profiles", response_model=MachineProfilesList)
async def list_machine_profiles() -> MachineProfilesList:
    """
    Получить список доступных профилей станков ЧПУ.

    Профили включают настройки для популярных систем управления:
    - **weihong** — Weihong NCStudio — ~30-35% рынка России, популярен для малого/среднего бизнеса
    - **syntec** — Syntec — ~20-25% рынка России, FANUC-совместимый
    - **fanuc** — Fanuc (ISO 6983, ГОСТ 20999-83) — ~15-20% рынка, промышленный стандарт
    - **dsp** — DSP — ~8-12% рынка, бюджетный сегмент
    - **homag** — Homag — ~2-3% рынка, премиум мебельное оборудование
    """
    profiles = get_available_profiles()
    return MachineProfilesList(
        profiles=[MachineProfileInfo(**p) for p in profiles]
    )


@router.post("/cam/gcode", response_model=GCodeJobResponse)
async def create_gcode_job(
    req: GCodeJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GCodeJobResponse:
    """
    Создаёт задачу генерации G-code из DXF артефакта.

    Параметры берутся из: запрос > настройки фабрики > дефолты профиля станка.

    ## Процесс:
    1. Получает DXF файл по artifact_id
    2. Применяет профиль станка и пользовательские параметры
    3. Конвертирует геометрию DXF в G-code
    4. Сохраняет результат как новый артефакт

    ## Пример запроса:
    ```json
    {
        "dxf_artifact_id": "550e8400-e29b-41d4-a716-446655440000",
        "machine_profile": "weihong",
        "cut_depth": 18.0
    }
    ```

    Задача ставится в очередь. Проверяйте статус через GET /cam/jobs/{job_id}.
    """
    # Проверяем что DXF артефакт существует
    dxf_artifact = await db.get(Artifact, req.dxf_artifact_id)
    if not dxf_artifact:
        raise HTTPException(status_code=404, detail=f"DXF artifact {req.dxf_artifact_id} not found")

    if dxf_artifact.type != "DXF":
        raise HTTPException(status_code=400, detail=f"Artifact is not DXF type: {dxf_artifact.type}")

    # Получаем настройки фабрики
    factory = await db.get(Factory, current_user.factory_id)
    factory_settings = factory.settings if factory else {}

    # Создаём CAM задачу
    job_id = uuid.uuid4()

    # Merge: запрос > настройки фабрики > дефолты
    machine_profile = (
        req.machine_profile
        or factory_settings.get("machine_profile")
        or SETTINGS_DEFAULTS["machine_profile"]
    )

    # Собираем контекст — все параметры через merge
    context = {
        "dxf_artifact_id": str(req.dxf_artifact_id),
        "machine_profile": machine_profile,
        "spindle_speed": (
            req.spindle_speed
            if req.spindle_speed is not None
            else factory_settings.get("spindle_speed", SETTINGS_DEFAULTS["spindle_speed"])
        ),
        "feed_rate_cutting": (
            req.feed_rate_cutting
            if req.feed_rate_cutting is not None
            else factory_settings.get("feed_rate_cutting", SETTINGS_DEFAULTS["feed_rate_cutting"])
        ),
        "feed_rate_plunge": (
            req.feed_rate_plunge
            if req.feed_rate_plunge is not None
            else factory_settings.get("feed_rate_plunge", SETTINGS_DEFAULTS["feed_rate_plunge"])
        ),
        "cut_depth": (
            req.cut_depth
            if req.cut_depth is not None
            else factory_settings.get("cut_depth", SETTINGS_DEFAULTS["cut_depth"])
        ),
        "safe_height": (
            req.safe_height
            if req.safe_height is not None
            else factory_settings.get("safe_height", SETTINGS_DEFAULTS["safe_height"])
        ),
        "tool_diameter": (
            req.tool_diameter
            if req.tool_diameter is not None
            else factory_settings.get("tool_diameter", SETTINGS_DEFAULTS["tool_diameter"])
        ),
    }

    stmt = insert(CAMJob).values(
        id=job_id,
        order_id=req.order_id,
        job_kind="GCODE",
        status=JobStatusEnum.Created,
        context=context,
        idempotency_key=req.idempotency_key,
    )
    await db.execute(stmt)
    await db.commit()

    # Отправляем в очередь
    await enqueue(GCODE_QUEUE, {
        "job_id": str(job_id),
        "job_kind": "GCODE",
        "context": context,
        "idempotency_key": req.idempotency_key,
    })

    log.info(f"[CAM] Created GCODE job {job_id} from DXF {req.dxf_artifact_id}, profile={machine_profile}")

    return GCodeJobResponse(
        job_id=job_id,
        status="created",
        machine_profile=machine_profile,
        dxf_artifact_id=req.dxf_artifact_id,
    )


@router.post("/cam/drilling", response_model=DrillingGcodeResponse)
async def create_drilling_job(
    request: DrillingGcodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DrillingGcodeResponse:
    """
    Создать задачу генерации G-code присадки.

    Генерирует G-code напрямую из BOM заказа, минуя DXF.
    Возвращает ZIP архив с .nc файлами (по одному на панель).
    """
    # Проверяем заказ
    order = await crud.get_order_with_products(db, request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if order.factory_id != current_user.factory_id:
        raise HTTPException(status_code=403, detail="Нет доступа к заказу")

    # Получаем панели заказа через ProductConfig
    panels_query = await db.execute(
        select(Panel)
        .join(ProductConfig)
        .where(ProductConfig.order_id == request.order_id)
    )
    panels = panels_query.scalars().all()

    if not panels:
        raise HTTPException(status_code=400, detail="В заказе нет панелей")

    # Формируем список файлов (упрощённая транслитерация для превью)
    def simple_transliterate(text: str) -> str:
        table = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
                 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l',
                 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's',
                 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
                 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e',
                 'ю': 'yu', 'я': 'ya', ' ': '_'}
        return ''.join(table.get(c, c) for c in text.lower())

    estimated_files = []
    for panel in panels:
        name_ascii = simple_transliterate(panel.name)
        filename = f"{name_ascii}_{panel.width_mm:.0f}x{panel.height_mm:.0f}.nc"
        estimated_files.append(filename)
    estimated_files.append("README.txt")

    # Создаём задачу
    job = CAMJob(
        id=uuid.uuid4(),
        order_id=request.order_id,
        job_kind="DRILLING",
        status=JobStatusEnum.Created,
        context={
            "machine_profile": request.machine_profile,
            "output_format": request.output_format,
            "panels_count": len(panels),
        },
    )
    db.add(job)
    await db.commit()

    # Ставим в очередь
    await enqueue(DRILLING_QUEUE, {
        "job_id": str(job.id),
        "job_kind": "DRILLING",
        "order_id": str(request.order_id),
        "machine_profile": request.machine_profile,
    })

    return DrillingGcodeResponse(
        job_id=job.id,
        status="processing",
        panels_count=len(panels),
        estimated_files=estimated_files,
    )


@router.post("/cam/layout-preview", response_model=LayoutPreviewResponse)
async def layout_preview(req: LayoutPreviewRequest) -> LayoutPreviewResponse:
    """
    Предпросмотр раскладки панелей на листе (без генерации DXF).

    Использует тот же алгоритм guillotine/maxrects что и реальная генерация DXF,
    но возвращает только координаты панелей для визуализации.

    Не требует аутентификации — быстрый preview для редактора BOM.

    ## Пример запроса:
    ```json
    {
        "panels": [
            {"name": "Боковина левая", "width_mm": 720, "height_mm": 560},
            {"name": "Боковина правая", "width_mm": 720, "height_mm": 560},
            {"name": "Дно", "width_mm": 568, "height_mm": 560}
        ],
        "sheet_width_mm": 2800,
        "sheet_height_mm": 2070,
        "gap_mm": 4
    }
    ```
    """
    # Конвертируем в Panel dataclass для dxf_generator
    panels = [
        DXFPanel(
            id=str(i),
            name=p.name,
            width_mm=p.width_mm,
            height_mm=p.height_mm,
            thickness_mm=16.0,  # Не влияет на раскладку
            material="ЛДСП",
        )
        for i, p in enumerate(req.panels)
    ]

    # Вызываем оптимизатор раскладки
    layout = optimize_layout_best(
        panels=panels,
        sheet_width=req.sheet_width_mm,
        sheet_height=req.sheet_height_mm,
        gap_mm=req.gap_mm,
    )

    # Конвертируем результат в response
    placed_panels = []
    for panel, x, y, rotated in layout.placed_panels:
        # При повороте ширина и высота меняются местами
        w = panel.height_mm if rotated else panel.width_mm
        h = panel.width_mm if rotated else panel.height_mm
        placed_panels.append(PlacedPanelInfo(
            name=panel.name,
            x=x,
            y=y,
            width_mm=w,
            height_mm=h,
            rotated=rotated,
        ))

    # Названия неразмещённых панелей
    unplaced_names = [p.name for p in layout.unplaced_panels]

    # Определяем метод раскладки (guillotine если утилизация > 0 и нет unplaced)
    layout_method = "guillotine" if not layout.unplaced_panels else "guillotine"

    return LayoutPreviewResponse(
        success=True,
        placed_panels=placed_panels,
        unplaced_panels=unplaced_names,
        sheet_width_mm=req.sheet_width_mm,
        sheet_height_mm=req.sheet_height_mm,
        utilization_percent=layout.utilization,
        panels_placed=len(layout.placed_panels),
        panels_total=len(req.panels),
        layout_method=layout_method,
    )


@router.post("/cam/cutting-map-pdf")
async def generate_cutting_map_pdf(
    req: PDFCuttingMapRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Генерирует PDF карту раскроя для оператора форматника.

    PDF содержит:
    - Визуальную схему раскладки панелей на листе
    - Названия и размеры каждой панели
    - Статистику использования листа

    Пример запроса:
    ```json
    {
        "panels": [
            {"name": "Боковина левая", "width_mm": 720, "height_mm": 560},
            {"name": "Боковина правая", "width_mm": 720, "height_mm": 560},
            {"name": "Дно", "width_mm": 568, "height_mm": 560}
        ],
        "order_info": "Заказ #123 — Шкаф навесной"
    }
    ```
    """
    from fastapi.responses import Response

    from api.pdf_generator import generate_cutting_map_pdf as gen_pdf

    # Получаем настройки фабрики
    factory = await db.get(Factory, current_user.factory_id)
    factory_settings = factory.settings if factory else {}

    # Merge: запрос > настройки фабрики > дефолты
    sheet_width = (
        req.sheet_width_mm
        or factory_settings.get("sheet_width_mm")
        or SETTINGS_DEFAULTS["sheet_width_mm"]
    )
    sheet_height = (
        req.sheet_height_mm
        or factory_settings.get("sheet_height_mm")
        or SETTINGS_DEFAULTS["sheet_height_mm"]
    )

    # Конвертируем панели в DXFPanel для раскладки
    panels = [
        DXFPanel(
            id=str(i),
            name=p.name,
            width_mm=p.width_mm,
            height_mm=p.height_mm,
        )
        for i, p in enumerate(req.panels)
    ]

    # Раскладываем панели
    layout = optimize_layout_best(
        panels=panels,
        sheet_width=sheet_width,
        sheet_height=sheet_height,
        gap_mm=req.gap_mm,
    )

    # Конвертируем tuple из layout в PlacedPanel для PDF
    placed_panels = []
    for panel, x, y, rotated in layout.placed_panels:
        w = panel.height_mm if rotated else panel.width_mm
        h = panel.width_mm if rotated else panel.height_mm
        placed_panels.append(PlacedPanel(
            name=panel.name,
            x=x,
            y=y,
            width_mm=w,
            height_mm=h,
            rotated=rotated,
        ))

    # Генерируем PDF
    order_info = req.order_info or ""
    pdf_bytes = gen_pdf(
        placed_panels=placed_panels,
        sheet_width_mm=sheet_width,
        sheet_height_mm=sheet_height,
        utilization_percent=layout.utilization,
        order_info=order_info,
    )

    # Формируем имя файла (только ASCII для совместимости с HTTP заголовками)
    filename = "cutting_map.pdf"
    if req.order_info:
        # Оставляем только ASCII буквы, цифры и безопасные символы
        safe_name = "".join(c for c in req.order_info if c.isascii() and (c.isalnum() or c in " -_")).strip()
        safe_name = safe_name.replace(" ", "_")
        if safe_name:
            filename = f"cutting_map_{safe_name[:30]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@dialogue_router.post("/clarify")
async def dialogue_clarify(req: DialogueTurnRequest, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """
    Принимает текущую историю диалога и возвращает потоковый ответ от ИИ-технолога.

    Если YC_FOLDER_ID и YC_API_KEY не заданы — использует mock ответы для локальной разработки.
    """
    order = await crud.get_order_with_history(db, req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Проверяем наличие Yandex Cloud ключей
    use_mock_mode = not are_yc_keys_available()

    if use_mock_mode:
        log.warning(f"[MOCK MODE] YC keys not found. Using mock dialogue responses for order {req.order_id}")

    # Добавляем новые сообщения из запроса в БД
    current_turn = (order.dialogue_messages[-1].turn_number + 1) if order.dialogue_messages else 1
    user_message_text = ""
    for user_msg in req.messages:
        user_message_text = user_msg.content  # Сохраняем последнее сообщение пользователя
        await crud.create_dialogue_message(db, order.id, current_turn, user_msg.role, user_msg.content)

    # MOCK РЕЖИМ - используем заготовленные ответы
    if use_mock_mode:
        async def mock_response_generator():
            full_response = ""
            is_first_message = current_turn == 1

            try:
                async for chunk in generate_mock_dialogue_response(
                    order_id=order.id,
                    user_message=user_message_text,
                    is_first_message=is_first_message,
                    extracted_context=req.extracted_context
                ):
                    full_response += chunk
                    yield chunk

                # Сохраняем полный mock ответ в БД
                await crud.create_dialogue_message(db, order.id, current_turn, "assistant", full_response)
                log.info(f"[MOCK MODE] Mock response saved to DB for order {order.id}")

            except Exception as e:
                log.error(f"[MOCK MODE] Mock dialogue generation failed for order {req.order_id}: {e}")
                yield "\n\n[ОШИБКА] Не удалось сгенерировать mock ответ."

        return StreamingResponse(mock_response_generator(), media_type="text/plain")

    # PRODUCTION РЕЖИМ - используем YandexGPT через OpenAI-совместимый API
    # 1. Собираем историю для YandexGPT
    system_prompt_text = TECHNOLOGIST_SYSTEM_PROMPT

    # OpenAI-совместимый формат: "content" вместо "text"
    # Если есть извлечённый контекст из Vision OCR — добавляем в системный промпт
    if req.extracted_context:
        system_prompt_text += f"""\n\n## Данные из загруженного изображения/эскиза:
{req.extracted_context}

КРИТИЧЕСКИ ВАЖНО: Эти данные уже ПОДТВЕРЖДЕНЫ пользователем — НЕ ПЕРЕСПРАШИВАЙ их!
- Габариты (ширина, высота, глубина), материалы, толщины — используй как ФАКТЫ
- Уточняй ТОЛЬКО то, что НЕ указано выше (например: тип петель, цвет кромки, количество полок)
- Начни с краткого подтверждения что понял параметры, затем спроси про ОДНУ недостающую деталь"""

    messages = [{"role": "system", "content": system_prompt_text}]

    # Добавляем историю из БД (предыдущие сообщения)
    for msg in sorted(order.dialogue_messages, key=lambda m: m.turn_number):
        messages.append({"role": msg.role, "content": msg.content})

    # ВАЖНО: Добавляем текущее сообщение пользователя (оно уже сохранено в БД, но ещё не в order.dialogue_messages)
    if user_message_text:
        messages.append({"role": "user", "content": user_message_text})

    # 2. Готовимся к стримингу ответа через OpenAI-совместимый API
    yc_settings = YandexCloudSettings(
        yc_folder_id=os.getenv("YC_FOLDER_ID", ""),
        yc_api_key=os.getenv("YC_API_KEY", "")
    )

    async def response_generator():
        full_response = ""
        try:
            log.info(f"[PRODUCTION MODE] Using YandexGPT (OpenAI API) for order {req.order_id}")
            async with create_openai_client(yc_settings) as client:
                async for chunk in client.stream_chat_completion(
                    messages,
                    temperature=0.4,  # Немного выше для более естественных ответов
                    top_p=0.9,
                    frequency_penalty=0.3,  # Уменьшаем повторения
                ):
                    full_response += chunk
                    yield chunk

            # 3. Сохраняем полный ответ ассистента в БД
            await crud.create_dialogue_message(db, order.id, current_turn, "assistant", full_response)

        except Exception as e:
            log.error(f"Dialogue clarification failed for order {req.order_id}: {e}")
            yield "\n\n[ОШИБКА] Не удалось получить ответ от ИИ-ассистента."

    return StreamingResponse(response_generator(), media_type="text/plain")


@dialogue_router.post("/clarify-with-tools")
async def dialogue_clarify_with_tools(req: DialogueTurnRequest, db: AsyncSession = Depends(get_db)):
    """
    Диалог с ИИ-технологом с поддержкой Function Calling.

    Модель может вызывать инструменты для:
    - Поиска фурнитуры в каталоге (find_hardware)
    - Проверки совместимости (check_hardware_compatibility)
    - Получения детальной информации (get_hardware_details)
    - Расчёта количества (calculate_hardware_qty)

    Возвращает JSON с результатами, включая вызовы инструментов.
    """
    order = await crud.get_order_with_history(db, req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Проверяем наличие Yandex Cloud ключей
    if not are_yc_keys_available():
        log.warning(f"[MOCK MODE] YC keys not found for order {req.order_id}")
        return {
            "success": False,
            "error": "YC_FOLDER_ID и YC_API_KEY не настроены",
            "mock_mode": True
        }

    # Добавляем новые сообщения из запроса в БД
    current_turn = (order.dialogue_messages[-1].turn_number + 1) if order.dialogue_messages else 1
    user_message_text = ""
    for user_msg in req.messages:
        user_message_text = user_msg.content
        await crud.create_dialogue_message(db, order.id, current_turn, user_msg.role, user_msg.content)

    # Системный промпт
    system_prompt_text = TECHNOLOGIST_SYSTEM_PROMPT

    # Если есть извлечённый контекст из Vision OCR — добавляем в системный промпт
    if req.extracted_context:
        system_prompt_text += f"""\n\n## Данные из загруженного изображения/эскиза:
{req.extracted_context}

КРИТИЧЕСКИ ВАЖНО: Эти данные уже ПОДТВЕРЖДЕНЫ пользователем — НЕ ПЕРЕСПРАШИВАЙ их!
- Габариты (ширина, высота, глубина), материалы, толщины — используй как ФАКТЫ
- Уточняй ТОЛЬКО то, что НЕ указано выше (например: тип петель, цвет кромки, количество полок)
- Начни с краткого подтверждения что понял параметры, затем спроси про ОДНУ недостающую деталь"""

    # Дополняем системный промпт информацией об инструментах
    tools_info = """

## Доступные инструменты

У тебя есть доступ к каталогу фурнитуры. Используй инструменты для:
- Поиска подходящей фурнитуры по запросу клиента
- Проверки совместимости фурнитуры с материалом и толщиной
- Получения детальной информации о позициях
- Расчёта необходимого количества фурнитуры

Когда клиент спрашивает о фурнитуре или нужно подобрать комплектующие - вызывай соответствующие инструменты.
"""
    system_prompt_text += tools_info

    # Собираем историю сообщений
    messages = [{"role": "system", "content": system_prompt_text}]

    for msg in sorted(order.dialogue_messages, key=lambda m: m.turn_number):
        messages.append({"role": msg.role, "content": msg.content})

    if user_message_text:
        messages.append({"role": "user", "content": user_message_text})

    # Инициализируем клиент
    yc_settings = YandexCloudSettings(
        yc_folder_id=os.getenv("YC_FOLDER_ID", ""),
        yc_api_key=os.getenv("YC_API_KEY", "")
    )

    tools = get_tools_schema()
    max_iterations = 5  # Максимум итераций для предотвращения бесконечного цикла
    tool_calls_log = []
    final_response = None

    try:
        async with create_openai_client(yc_settings) as client:
            for iteration in range(max_iterations):
                log.info(f"[Function Calling] Iteration {iteration + 1}, messages: {len(messages)}")

                # Вызываем модель с инструментами
                response: GPTResponseWithTools = await client.chat_completion_with_tools(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.4,
                )

                # Если модель не вызвала инструменты - это финальный ответ
                if not response.tool_calls:
                    final_response = response.text
                    break

                # Добавляем ответ ассистента с tool_calls в историю
                assistant_message = {
                    "role": "assistant",
                    "content": response.text or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                            }
                        }
                        for tc in response.tool_calls
                    ]
                }
                messages.append(assistant_message)

                # Выполняем каждый вызов инструмента
                for tool_call in response.tool_calls:
                    log.info(f"[Function Calling] Executing tool: {tool_call.name}")

                    tool_result = await execute_tool_call(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments
                    )

                    tool_calls_log.append({
                        "tool": tool_call.name,
                        "arguments": tool_call.arguments,
                        "result": tool_result
                    })

                    # Добавляем результат в историю
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })

            else:
                # Превышено максимальное количество итераций
                log.warning(f"[Function Calling] Max iterations reached for order {req.order_id}")
                final_response = "Извините, не удалось получить ответ. Попробуйте переформулировать вопрос."

        # Сохраняем финальный ответ в БД
        if final_response:
            await crud.create_dialogue_message(db, order.id, current_turn, "assistant", final_response)

        return {
            "success": True,
            "response": final_response,
            "tool_calls": tool_calls_log,
            "iterations": min(iteration + 1, max_iterations) if 'iteration' in dir() else 1
        }

    except Exception as e:
        log.error(f"[Function Calling] Error for order {req.order_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_calls": tool_calls_log
        }


# ============================================================================
# Cost Estimation
# ============================================================================

@router.get("/orders/{order_id}/cost", response_model=CostEstimateResponse)
async def calculate_order_cost(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Рассчитать себестоимость заказа.
    
    Учитывает:
    - Материалы (ЛДСП, МДФ) по площади
    - Кромку по длине
    - Фурнитуру поштучно
    - Операции (распил, кромление, присадка)
    """
    order = await crud.get_order_with_products(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.products:
        return CostEstimateResponse(
            total_cost=0,
            breakdown=[],
            materials_cost=0,
            hardware_cost=0,
            operations_cost=0,
        )

    product = order.products[0]
    
    # Получаем панели
    panels_result = await db.execute(
        select(Panel).where(Panel.product_id == product.id)
    )
    panels = panels_result.scalars().all()
    
    params = product.params or {}
    hardware = params.get("hardware", [])
    fasteners = params.get("fasteners", [])
    edge_bands = params.get("edge_bands", [])
    
    breakdown = []
    
    # 1. Материалы (ЛДСП)
    # Цена за лист 2800x2070 (5.8 м2) ~ 3500 руб -> ~600 руб/м2
    MATERIAL_PRICE_M2 = 600.0 
    
    total_area_m2 = sum((p.width_mm * p.height_mm) / 1_000_000 for p in panels)
    # Учитываем обрезки (+20%)
    sheet_area_needed = total_area_m2 * 1.2
    
    breakdown.append(CostBreakdownItem(
        name=f"ЛДСП {product.material or '16мм'}",
        quantity=round(sheet_area_needed, 2),
        unit="м²",
        unit_price=MATERIAL_PRICE_M2,
        total_price=round(sheet_area_needed * MATERIAL_PRICE_M2, 2)
    ))
    
    # 2. Кромка
    # Цена 25 руб/м (2мм) и 8 руб/м (0.4мм)
    for band in edge_bands:
        breakdown.append(CostBreakdownItem(
            name=f"Кромка {band.get('type')}",
            quantity=band.get("length_m", 0),
            unit="м",
            unit_price=band.get("unit_price", 10),
            total_price=round(band.get("length_m", 0) * band.get("unit_price", 10), 2)
        ))
        
    # 3. Фурнитура
    # Примерные цены
    HARDWARE_PRICES = {
        "hinge": 120.0, # Петля с доводчиком
        "slide": 450.0, # Направляющие скрытого монтажа
        "handle": 150.0, # Ручка
        "leg": 30.0, # Опора
        "suspension": 80.0, # Навес
        "lift": 3500.0, # Aventos
        "connector": 2.0, # Конфирмат
        "other": 10.0,
    }
    
    for item in hardware:
        hw_type = item.get("type", "other")
        price = HARDWARE_PRICES.get(hw_type, 50.0)
        qty = item.get("quantity", item.get("qty", 0))
        
        breakdown.append(CostBreakdownItem(
            name=item.get("name", "Фурнитура"),
            quantity=qty,
            unit="шт",
            unit_price=price,
            total_price=qty * price
        ))
        
    for item in fasteners:
        price = item.get("unit_price", 1.0)
        qty = item.get("quantity", 0)
        breakdown.append(CostBreakdownItem(
            name=item.get("name", "Крепёж"),
            quantity=qty,
            unit="шт",
            unit_price=price,
            total_price=qty * price
        ))
        
    # 4. Операции
    # Распил: 30 руб/м погонный реза
    # Кромление: 40 руб/м
    # Присадка: 10 руб/отверстие
    
    # Оценка длины реза (периметр * 1.5)
    cut_length_m = sum((p.width_mm + p.height_mm) * 2 / 1000 for p in panels)
    breakdown.append(CostBreakdownItem(
        name="Распил ЛДСП",
        quantity=round(cut_length_m, 1),
        unit="м",
        unit_price=30.0,
        total_price=round(cut_length_m * 30.0, 2)
    ))
    
    # Кромление (сумма длин кромки)
    edge_length_m = sum(b.get("length_m", 0) for b in edge_bands)
    breakdown.append(CostBreakdownItem(
        name="Кромление",
        quantity=round(edge_length_m, 1),
        unit="м",
        unit_price=40.0,
        total_price=round(edge_length_m * 40.0, 2)
    ))
    
    # Сборка и присадка (оценка)
    parts_count = len(panels)
    breakdown.append(CostBreakdownItem(
        name="Присадка (сверление)",
        quantity=parts_count,
        unit="дет",
        unit_price=50.0,
        total_price=parts_count * 50.0
    ))

    # Суммируем
    materials_cost = sum(i.total_price for i in breakdown if "ЛДСП" in i.name or "Кромка" in i.name)
    hardware_cost = sum(i.total_price for i in breakdown if "Петля" in i.name or "Направляющие" in i.name or "Ручка" in i.name or "Фурнитура" in i.name or "Крепёж" in i.name or "Опора" in i.name)
    operations_cost = sum(i.total_price for i in breakdown if "Распил" in i.name or "Кромление" in i.name or "Присадка" in i.name)
    
    total_cost = materials_cost + hardware_cost + operations_cost

    return CostEstimateResponse(
        total_cost=round(total_cost, 2),
        currency="RUB",
        breakdown=breakdown,
        materials_cost=round(materials_cost, 2),
        hardware_cost=round(hardware_cost, 2),
        operations_cost=round(operations_cost, 2),
    )

