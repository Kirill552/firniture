"""Детерминированный алгоритм раскроя: BL-упаковка прямоугольников.

Модель:
    PartRequest  — деталь для раскладки (ширина, высота, кол-во, ротация)
    SheetSpec    — лист материала (ширина, высота)
    LayoutConfig — параметры: паз, поля, зерно, список листов
    Placement    — результат размещения одной детали на листе
    LayoutResult — итог: размещённые, неразмещённые, утилизация

Алгоритм: Bottom-Left (BL) эвристика.
    1. Детали сортируются по высоте ↓, затем ширине ↓.
    2. Для каждой детали ищется самое нижнее-левое допустимое положение.
    3. Когда лист заполняется — берётся следующий.
    4. Непоместившиеся детали попадают в unplaced.

Используется изолированно — без DXF/routes/интеграций.
"""
from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# ── Перечисления ────────────────────────────────────────────────────


class GrainDirection(str, Enum):
    """Направление текстуры (волокон) материала.

    NONE       — нет ограничений, ротация всегда допустима
    VERTICAL   — волокна вдоль оси Y (ротация на 90° запрещена)
    HORIZONTAL — волокна вдоль оси X (ротация на 90° запрещена)
    """

    NONE = "none"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


# ── Валидаторы ──────────────────────────────────────────────────────


def _positive_mm(v: float, field: str = "value") -> float:
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{field} должно быть > 0, получено {v}")
    return v


def _nonneg_mm(v: float, field: str = "value") -> float:
    if not math.isfinite(v) or v < 0:
        raise ValueError(f"{field} не может быть < 0, получено {v}")
    return v


# ── Входные модели ──────────────────────────────────────────────────


class PartRequest(BaseModel):
    """Одна деталь (или пачка одинаковых) для раскладки."""

    id: str
    width_mm: float
    height_mm: float
    quantity: int = 1
    allow_rotation: bool = True

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("id детали не может быть пустым")
        return v

    @field_validator("width_mm", "height_mm")
    @classmethod
    def _validate_dims(cls, v: float) -> float:
        return _positive_mm(v, "размер детали")

    @field_validator("quantity")
    @classmethod
    def _validate_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"quantity должно быть >= 1, получено {v}")
        return v


class SheetSpec(BaseModel):
    """Лист материала для раскроя."""

    id: str
    width_mm: float
    height_mm: float

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("id листа не может быть пустым")
        return v

    @field_validator("width_mm", "height_mm")
    @classmethod
    def _validate_dims(cls, v: float) -> float:
        return _positive_mm(v, "размер листа")


class LayoutConfig(BaseModel):
    """Параметры раскладки."""

    kerf_mm: float = 3.0
    margin_mm: float = 10.0
    grain: GrainDirection = GrainDirection.NONE
    sheet_specs: list[SheetSpec] = Field(default_factory=list)

    @field_validator("kerf_mm")
    @classmethod
    def _validate_kerf(cls, v: float) -> float:
        return _nonneg_mm(v, "kerf")

    @field_validator("margin_mm")
    @classmethod
    def _validate_margin(cls, v: float) -> float:
        return _nonneg_mm(v, "margin")


# ── Результаты ──────────────────────────────────────────────────────


class Placement(BaseModel):
    """Размещённая деталь на листе."""

    part_id: str
    original_width_mm: float
    original_height_mm: float
    x_mm: float
    y_mm: float
    width_mm: float  # фактическая (после ротации)
    height_mm: float  # фактическая (после ротации)
    rotated: bool
    sheet_id: str


class UnplacedPart(BaseModel):
    """Деталь, которая не поместилась ни на один лист."""

    part_id: str
    width_mm: float
    height_mm: float
    quantity_remaining: int
    reason: str = ""


class SheetUtilization(BaseModel):
    """Статистика использования одного листа."""

    sheet_id: str
    sheet_width_mm: float
    sheet_height_mm: float
    usable_area_mm2: float  # площадь после вычета полей
    placed_area_mm2: float  # суммарная площадь размещённых деталей
    utilization: float  # placed / usable, 0.0 – 1.0
    placed_count: int


class LayoutResult(BaseModel):
    """Полный результат раскладки."""

    placements: list[Placement] = Field(default_factory=list)
    unplaced: list[UnplacedPart] = Field(default_factory=list)
    sheet_utilizations: list[SheetUtilization] = Field(default_factory=list)
    total_parts: int = 0
    placed_parts: int = 0


# ── Внутренняя модель размещённого прямоугольника ────────────────────


class _Rect:
    """Прямоугольник на листе (внутренняя структура, не Pydantic)."""

    __slots__ = ("x", "y", "w", "h", "part_id", "idx", "rotated", "orig_w", "orig_h")

    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        part_id: str,
        idx: int,
        rotated: bool,
        orig_w: float,
        orig_h: float,
    ) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.part_id = part_id
        self.idx = idx
        self.rotated = rotated
        self.orig_w = orig_w
        self.orig_h = orig_h

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def overlaps(self, other: _Rect) -> bool:
        return (
            self.x < other.right
            and self.right > other.x
            and self.y < other.bottom
            and self.bottom > other.y
        )


# ── Алгоритм раскладки ─────────────────────────────────────────────


def _expand_parts(parts: list[PartRequest]) -> list[tuple[str, float, float, bool]]:
    """Развернуть PartRequest → список (id, w, h, allow_rot) по quantity."""
    expanded: list[tuple[str, float, float, bool]] = []
    for p in parts:
        for i in range(p.quantity):
            suffix = f"#{i + 1}" if p.quantity > 1 else ""
            expanded.append((f"{p.id}{suffix}", p.width_mm, p.height_mm, p.allow_rotation))
    return expanded


def _can_rotate(
    orig_w: float,
    orig_h: float,
    allow_rotation: bool,
    grain: GrainDirection,
) -> list[tuple[float, float, bool]]:
    """Вернуть список допустимых ориентаций (w, h, rotated).

    Для каждой детали возвращается 1 или 2 варианта.
    Сортировка: сначала исходная ориентация, потом развёрнутая.
    """
    variants: list[tuple[float, float, bool]] = [(orig_w, orig_h, False)]

    if not allow_rotation:
        return variants

    # Ротация 90° — ширина и высота меняются местами
    if orig_w != orig_h:
        if grain == GrainDirection.NONE:
            variants.append((orig_h, orig_w, True))
        # VERTICAL / HORIZONTAL: ротация запрещена — деталь сохраняет
        # исходную ориентацию, чтобы волокна совпадали с направлением.

    return variants


def _fits_on_sheet(
    w: float,
    h: float,
    x: float,
    y: float,
    sheet_w: float,
    sheet_h: float,
    placed: list[_Rect],
    kerf: float,
) -> bool:
    """Проверить, вписывается ли прямоугольник (x, y, w, h) без пересечений."""
    # Границы листа (с учётом полей уже вычтены в sheet_w/sheet_h)
    if x < 0 or y < 0:
        return False
    if x + w > sheet_w + 1e-9 or y + h > sheet_h + 1e-9:
        return False

    # С зазором kerf
    rect = _Rect(x, y, w, h, "", 0, False, 0.0, 0.0)
    for existing in placed:
        # Проверяем пересечение с учётом kerf (каждый прямоугольник расширен на kerf/2)
        expanded = _Rect(
            existing.x - kerf / 2,
            existing.y - kerf / 2,
            existing.w + kerf,
            existing.h + kerf,
            existing.part_id,
            existing.idx,
            existing.rotated,
            existing.orig_w,
            existing.orig_h,
        )
        if rect.overlaps(expanded):
            return False

    return True


def _find_bl_position(
    w: float,
    h: float,
    sheet_w: float,
    sheet_h: float,
    placed: list[_Rect],
    kerf: float,
) -> tuple[float, float] | None:
    """Найти Bottom-Left позицию для прямоугольника (w, h).

    Алгоритм: перебираем «критические» Y-координаты (все нижние края
    уже размещённых прямоугольников + 0), для каждой — ищем минимальный X.
    Возвращает (x, y) или None.
    """
    # Собираем критические Y-позиции
    crit_y: list[float] = [0.0]
    for r in placed:
        crit_y.append(r.bottom + kerf)
    # Убираем дубликаты, сортируем
    crit_y = sorted(set(crit_y))

    best: tuple[float, float] | None = None

    for y in crit_y:
        if y + h > sheet_h + 1e-9:
            continue  # Не влезает по высоте

        # Собираем критические X для данной Y
        crit_x: list[float] = [0.0]
        for r in placed:
            # Прямоугольники, которые пересекают данную Y-полосу
            if r.y <= y + h - 1e-9 and r.bottom > y + 1e-9:
                crit_x.append(r.right + kerf)
        crit_x = sorted(set(crit_x))

        for x in crit_x:
            if x + w > sheet_w + 1e-9:
                continue
            # Проверяем пересечения с существующими
            if _fits_on_sheet(w, h, x, y, sheet_w, sheet_h, placed, kerf):
                if best is None or y < best[1] or (y == best[1] and x < best[0]):
                    best = (x, y)
                break  # Для данной Y нашли минимальный X — переходим дальше

    return best


def layout_parts(config: LayoutConfig, parts: list[PartRequest]) -> LayoutResult:
    """Выполнить детерминированную раскладку деталей на листах.

    Алгоритм:
        1. Детали сортируются по высоте ↓, затем ширине ↓.
        2. Для каждой детали — BL-поиск позиции с учётом зазора kerf.
        3. Листы берутся по порядку из config.sheet_specs.
        4. Непоместившиеся детали → unplaced.

    Возвращает LayoutResult с размещениями, неразмещёнными и утилизацией.
    """
    # Пустые детали — но утилизация по листам всё равно нужна
    if not parts:
        empty_utils = [
            SheetUtilization(
                sheet_id=s.id,
                sheet_width_mm=s.width_mm,
                sheet_height_mm=s.height_mm,
                usable_area_mm2=max(
                    0.0,
                    (s.width_mm - 2 * config.margin_mm)
                    * (s.height_mm - 2 * config.margin_mm),
                ),
                placed_area_mm2=0.0,
                utilization=0.0,
                placed_count=0,
            )
            for s in config.sheet_specs
        ]
        return LayoutResult(sheet_utilizations=empty_utils)

    if not config.sheet_specs:
        return LayoutResult(
            unplaced=[
                UnplacedPart(
                    part_id=p.id,
                    width_mm=p.width_mm,
                    height_mm=p.height_mm,
                    quantity_remaining=p.quantity,
                    reason="нет листов в конфигурации",
                )
                for p in parts
            ],
            total_parts=sum(p.quantity for p in parts),
        )

    # 1. Развернуть детали
    expanded = _expand_parts(parts)

    # 2. Сортировка: по высоте ↓, затем ширине ↓ (BL-эвристика)
    expanded.sort(key=lambda e: (-e[2], -e[1], e[0]))

    # 3. Раскладка
    placements: list[Placement] = []
    unplaced: list[UnplacedPart] = []

    # Карта: sheet_id → list[_Rect]
    sheet_rects: dict[str, list[_Rect]] = {}
    sheet_area_used: dict[str, float] = {}

    # Используем листы по порядку
    sheet_idx = 0

    for part_id, orig_w, orig_h, allow_rot in expanded:
        variants = _can_rotate(orig_w, orig_h, allow_rot, config.grain)

        placed = False
        # Пробуем листы по порядку, начиная с текущего
        for try_idx in range(sheet_idx, len(config.sheet_specs)):
            sheet = config.sheet_specs[try_idx]

            # Доступная область после полей
            usable_w = sheet.width_mm - 2 * config.margin_mm
            usable_h = sheet.height_mm - 2 * config.margin_mm

            if usable_w <= 0 or usable_h <= 0:
                continue

            rects_on_sheet = sheet_rects.get(sheet.id, [])

            for w, h, rotated in variants:
                # Проверяем, влезет ли вообще по размерам
                if w > usable_w + 1e-9 or h > usable_h + 1e-9:
                    continue

                pos = _find_bl_position(
                    w, h, usable_w, usable_h, rects_on_sheet, config.kerf_mm
                )
                if pos is None:
                    continue

                x, y = pos
                # Смещаем с учётом полей
                abs_x = x + config.margin_mm
                abs_y = y + config.margin_mm

                new_rect = _Rect(
                    x=x, y=y, w=w, h=h,
                    part_id=part_id, idx=len(rects_on_sheet),
                    rotated=rotated, orig_w=orig_w, orig_h=orig_h,
                )
                rects_on_sheet.append(new_rect)
                sheet_rects[sheet.id] = rects_on_sheet

                placements.append(
                    Placement(
                        part_id=part_id,
                        original_width_mm=orig_w,
                        original_height_mm=orig_h,
                        x_mm=abs_x,
                        y_mm=abs_y,
                        width_mm=w,
                        height_mm=h,
                        rotated=rotated,
                        sheet_id=sheet.id,
                    )
                )

                # Обновляем площадь
                area = sheet_area_used.get(sheet.id, 0.0)
                sheet_area_used[sheet.id] = area + w * h

                # После успешного размещения на этом листе —
                # следующая деталь начинает поиск с того же листа
                if try_idx == sheet_idx:
                    pass  # оставляем sheet_idx как есть
                else:
                    sheet_idx = try_idx

                placed = True
                break  # Вариант найден, выходим из цикла по variants

            if placed:
                break  # Лист найден, выходим из цикла по sheet_idx

        if not placed:
            unplaced.append(
                UnplacedPart(
                    part_id=part_id,
                    width_mm=orig_w,
                    height_mm=orig_h,
                    quantity_remaining=1,
                    reason="не помещается ни на один лист",
                )
            )

    # 4. Утилизация по листам
    sheet_utils: list[SheetUtilization] = []
    for sheet in config.sheet_specs:
        usable_area = max(
            0.0,
            (sheet.width_mm - 2 * config.margin_mm)
            * (sheet.height_mm - 2 * config.margin_mm),
        )
        used = sheet_area_used.get(sheet.id, 0.0)
        rects_on = sheet_rects.get(sheet.id, [])
        util = used / usable_area if usable_area > 0 else 0.0

        sheet_utils.append(
            SheetUtilization(
                sheet_id=sheet.id,
                sheet_width_mm=sheet.width_mm,
                sheet_height_mm=sheet.height_mm,
                usable_area_mm2=usable_area,
                placed_area_mm2=used,
                utilization=round(util, 6),
                placed_count=len(rects_on),
            )
        )

    total_parts = sum(p.quantity for p in parts)
    placed_count = len(placements)

    return LayoutResult(
        placements=placements,
        unplaced=unplaced,
        sheet_utilizations=sheet_utils,
        total_parts=total_parts,
        placed_parts=placed_count,
    )
