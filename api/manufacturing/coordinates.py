"""Coordinate transforms, canonical serialization, SHA-256.

Преобразования между локальными координатами граней панели,
каноническими координатами, G-code, отражениями и поворотами.
Детерминированная сериализация для хеширования спецификаций.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.manufacturing.contracts import (
        AnyOperation,
        Face,
        ManufacturingSpec,
    )


# ---------------------------------------------------------------------------
# Face-local → canonical panel coordinates
# ---------------------------------------------------------------------------

def face_to_panel(
    face: Face,
    local_x: float,
    local_y: float,
    *,
    panel_w: float,
    panel_h: float,
    thickness: float,
) -> tuple[float, float]:
    """Конвертировать локальные координаты грани в канонические (panel_x, panel_y).

    FRONT  — local (x, y) → panel (x, y) без изменений
    BACK   — local (x, y) → panel (panel_w - x, y)
    LEFT   — local (x, y) → panel (0, y)  (x = глубина в торец, игнорируется)
    RIGHT  — local (x, y) → panel (panel_w, y)
    TOP    — local (x, y) → panel (x, panel_h)
    BOTTOM — local (x, y) → panel (x, 0)
    """
    match face.value:
        case "front":
            return local_x, local_y
        case "back":
            return panel_w - local_x, local_y
        case "left":
            return 0.0, local_y
        case "right":
            return panel_w, local_y
        case "top":
            return local_x, panel_h
        case "bottom":
            return local_x, 0.0
    raise ValueError(f"неизвестная грань: {face}")


# ---------------------------------------------------------------------------
# Panel coords ↔ G-code coords
# ---------------------------------------------------------------------------

def panel_to_gcode(
    panel_x: float,
    panel_y: float,
    *,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> tuple[float, float]:
    """Канонические координаты панели → координаты G-code (смещение на столе)."""
    return panel_x + offset_x, panel_y + offset_y


def gcode_to_panel(
    gcode_x: float,
    gcode_y: float,
    *,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> tuple[float, float]:
    """Координаты G-code → канонические координаты панели."""
    return gcode_x - offset_x, gcode_y - offset_y


# ---------------------------------------------------------------------------
# Operation transforms
# ---------------------------------------------------------------------------

def mirror_operation_x(
    op: AnyOperation,
    panel_w: float,
) -> AnyOperation:
    """Отразить операцию по горизонтали (x → panel_w - x)."""
    return op.model_copy(update={"x_mm": panel_w - op.x_mm})


def mirror_operation_y(
    op: AnyOperation,
    panel_h: float,
) -> AnyOperation:
    """Отразить операцию по вертикали (y → panel_h - y)."""
    return op.model_copy(update={"y_mm": panel_h - op.y_mm})


def rotate_operation_cw(
    op: AnyOperation,
    panel_w: float,
    panel_h: float,
) -> AnyOperation:
    """Повернуть операцию на 90° по часовой стрелке вокруг центра панели.

    Формула (90° CW, CNC y-down):  (dx, dy) → (-dy, dx)
    Сдвиг через центр: cx = panel_w/2, cy = panel_h/2
    """
    cx, cy = panel_w / 2, panel_h / 2
    # Перенос в начало координат, поворот, возврат
    dx = op.x_mm - cx
    dy = op.y_mm - cy
    # 90° CW в CNC (y-down): (dx, dy) → (-dy, dx)
    new_x = -dy + cx
    new_y = dx + cy
    return op.model_copy(update={"x_mm": new_x, "y_mm": new_y})

# ---------------------------------------------------------------------------
# Setup-aware coordinate helpers
# ---------------------------------------------------------------------------


def setup_local_to_canonical(
    face: Face,
    local_x: float,
    local_y: float,
    setup_type: str,
    *,
    panel_w: float,
    panel_h: float,
    thickness: float,
) -> tuple[float, float]:
    """Face-local coords → canonical panel coords, accounting for setup.

    Combines face_to_panel() with setup transform.  For flat setups
    the face mapping is standard; for edge setups coordinates are
    first mapped to canonical panel coords, then rotated for the edge.
    """
    # Step 1: standard face-to-panel mapping
    px, py = face_to_panel(
        face, local_x, local_y,
        panel_w=panel_w, panel_h=panel_h, thickness=thickness,
    )
    # Step 2: apply setup transform
    from api.manufacturing.setups import (
        SetupType,
        apply_edge_transform,
        apply_flat_transform,
        is_flat_setup,
    )
    st = SetupType(setup_type)
    if is_flat_setup(st):
        return apply_flat_transform(px, py, st, panel_h=panel_h)
    return apply_edge_transform(px, py, st, panel_w=panel_w, panel_h=panel_h)



# ---------------------------------------------------------------------------
# Canonical serialization & hashing
# ---------------------------------------------------------------------------

def canonical_json(spec: ManufacturingSpec) -> str:
    """Детерминированная JSON-сериализация (sorted keys, no whitespace).

    Модель конвертируется через Pydantic `model_dump()` с сортировкой ключей.
    """
    data = spec.to_canonical_dict()
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def spec_hash(spec: ManufacturingSpec) -> str:
    """SHA-256 хеш канонического JSON-представления спецификации."""
    payload = canonical_json(spec).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
