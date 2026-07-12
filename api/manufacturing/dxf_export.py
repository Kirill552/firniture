"""DXF export for single-part local-coordinate semantics.

Exports a PanelSpec to DXF with:
- Panel outline on OUTLINE layer (closed LWPOLYLINE).
- Operation geometry on per-type layers (DRILL / SLOT / POCKET).
- XDATA metadata on every operation entity: operation_id, op_type,
  face, tool_id, depth_mm, diameter/length/width/height as applicable.
- All coordinates in local mm, origin at panel bottom-left corner.

Round-trip: export → import_dxf_panel → PanelSpec.
Layout/PDF generation is deferred to a future task.
"""
from __future__ import annotations

from typing import Any

import ezdxf
from ezdxf.entities import DXFEntity
from ezdxf.math import Vec2

from api.manufacturing.contracts import (
    AnyOperation,
    DrillOperation,
    OperationType,
    PanelSpec,
    PocketOperation,
    SlotOperation,
)

# Layout support (Task 11) — dxf_export depends on cutting_map types (allowed direction)
from api.manufacturing.cutting_map import SheetLayout  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APPID = "MEBEL-AI"
DXF_VERSION = "R2013"  # AC1027 — XDATA support

# DXF group codes for XDATA
_GC_STR = 1000   # строка
_GC_FLOAT = 1040  # float
_GC_INT = 1070    # int16

# Слой → цвет (ACI)
_LAYER_COLORS: dict[str, int] = {
    "OUTLINE": 7,   # белый/чёрный
    "DRILL": 1,     # красный
    "SLOT": 3,      # зелёный
    "POCKET": 5,    # синий
}


# ---------------------------------------------------------------------------
# XDATA helpers
# ---------------------------------------------------------------------------

def _xdata_tags(pairs: list[tuple[str, Any]]) -> list[tuple[int, Any]]:
    """Преобразовать именованные пары (key, value) → DXF group code tags.

    Тип value определяет group code:
    - str  → 1000
    - float → 1040
    - int  → 1070
    """
    tags: list[tuple[int, Any]] = []
    for key, value in pairs:
        # Ключ всегда строка
        tags.append((_GC_STR, key))
        if isinstance(value, float):
            tags.append((_GC_FLOAT, value))
        elif isinstance(value, int) and not isinstance(value, bool):
            tags.append((_GC_INT, value))
        else:
            tags.append((_GC_STR, str(value)))
    return tags


def _op_xdata_pairs(op: AnyOperation) -> list[tuple[str, Any]]:
    """Именованные пары XDATA для операции."""
    pairs: list[tuple[str, Any]] = [
        ("operation_id", op.id),
        ("op_type", op.op_type.value),
        ("face", op.face.value),
    ]
    if isinstance(op, DrillOperation):
        pairs.append(("diameter_mm", op.diameter_mm))
        pairs.append(("depth_mm", op.depth_mm))
    elif isinstance(op, SlotOperation):
        pairs.append(("length_mm", op.length_mm))
        pairs.append(("width_mm", op.width_mm))
        pairs.append(("depth_mm", op.depth_mm))
    elif isinstance(op, PocketOperation):
        pairs.append(("width_mm", op.width_mm))
        pairs.append(("height_mm", op.height_mm))
        pairs.append(("depth_mm", op.depth_mm))
    return pairs


def _set_xdata(entity: DXFEntity, pairs: list[tuple[str, Any]]) -> None:
    """Записать XDATA на сущность."""
    tags = _xdata_tags(pairs)
    entity.set_xdata(APPID, tags)


def _get_xdata_dict(entity: DXFEntity) -> dict[str, str | float | int]:
    """Прочитать XDATA сущности как dict (key → value)."""
    try:
        tags = entity.get_xdata(APPID)
    except ezdxf.DXFKeyError:
        return {}
    if not tags:
        return {}

    result: dict[str, str | float | int] = {}
    current_key: str | None = None
    for tag in tags:
        code, value = tag.code, tag.value
        if code == _GC_STR and current_key is None:
            # Это ключ
            current_key = str(value)
        elif code == _GC_STR and current_key is not None:
            # Строка-значение
            result[current_key] = str(value)
            current_key = None
        elif code == _GC_FLOAT and current_key is not None:
            result[current_key] = float(value)
            current_key = None
        elif code == _GC_INT and current_key is not None:
            result[current_key] = int(value)
            current_key = None
        else:
            current_key = None
    return result


# ---------------------------------------------------------------------------
# Entity builders
# ---------------------------------------------------------------------------

def _add_panel_outline(doc: ezdxf.document.Drawing, panel: PanelSpec) -> None:
    """Контур панели — замкнутый прямоугольник на слое OUTLINE."""
    msp = doc.modelspace()
    pts = [
        Vec2(0, 0),
        Vec2(panel.width_mm, 0),
        Vec2(panel.width_mm, panel.height_mm),
        Vec2(0, panel.height_mm),
    ]
    pline = msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "OUTLINE"})
    pairs = [("panel_id", panel.id)]
    if panel.material:
        pairs.append(("material", panel.material))
    pairs.append(("thickness_mm", panel.thickness_mm))
    pairs.append(("width_mm", panel.width_mm))
    pairs.append(("height_mm", panel.height_mm))
    _set_xdata(pline, pairs)


def _add_drill(doc: ezdxf.document.Drawing, op: DrillOperation) -> None:
    """Сверловое отверстие — CIRCLE на слое DRILL."""
    msp = doc.modelspace()
    circle = msp.add_circle(
        center=(op.x_mm, op.y_mm),
        radius=op.diameter_mm / 2.0,
        dxfattribs={"layer": "DRILL"},
    )
    _set_xdata(circle, _op_xdata_pairs(op))


def _add_slot(doc: ezdxf.document.Drawing, op: SlotOperation) -> None:
    """Паз — прямоугольная LWPOLYLINE на слое SLOT, центрирована на (x, y)."""
    msp = doc.modelspace()
    hw = op.length_mm / 2.0
    hh = op.width_mm / 2.0
    cx, cy = op.x_mm, op.y_mm
    pts = [
        Vec2(cx - hw, cy - hh),
        Vec2(cx + hw, cy - hh),
        Vec2(cx + hw, cy + hh),
        Vec2(cx - hw, cy + hh),
    ]
    pline = msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "SLOT"})
    _set_xdata(pline, _op_xdata_pairs(op))


def _add_pocket(doc: ezdxf.document.Drawing, op: PocketOperation) -> None:
    """Карман — прямоугольная LWPOLYLINE на слое POCKET, центрирована на (x, y)."""
    msp = doc.modelspace()
    hw = op.width_mm / 2.0
    hh = op.height_mm / 2.0
    cx, cy = op.x_mm, op.y_mm
    pts = [
        Vec2(cx - hw, cy - hh),
        Vec2(cx + hw, cy - hh),
        Vec2(cx + hw, cy + hh),
        Vec2(cx - hw, cy + hh),
    ]
    pline = msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "POCKET"})
    _set_xdata(pline, _op_xdata_pairs(op))


# ---------------------------------------------------------------------------
# Public API — export
# ---------------------------------------------------------------------------

def export_panel_dxf(panel: PanelSpec) -> ezdxf.document.Drawing:
    """Экспорт PanelSpec в DXF-документ с локальными координатами.

    Каждая операция:
    - Геометрическая сущность на слое по типу (DRILL/SLOT/POCKET).
    - XDATA с operation_id, op_type, face, tool_id, depth, размеры.

    Возвращает DXF Drawing (не сохраняет на диск).
    """
    doc = ezdxf.new(DXF_VERSION)
    doc.appids.add(APPID)
    # Создать слои с цветами
    for name, color in _LAYER_COLORS.items():
        doc.layers.add(name, color=color)

    _add_panel_outline(doc, panel)

    for op in panel.operations:
        if isinstance(op, DrillOperation):
            _add_drill(doc, op)
        elif isinstance(op, SlotOperation):
            _add_slot(doc, op)
        elif isinstance(op, PocketOperation):
            _add_pocket(doc, op)

    return doc


def save_dxf(panel: PanelSpec, path: str) -> ezdxf.document.Drawing:
    """Экспорт и сохранение DXF на диск. Возвращает Drawing."""
    doc = export_panel_dxf(panel)
    doc.saveas(path)
    return doc


# ---------------------------------------------------------------------------
# Public API — import (round-trip)
# ---------------------------------------------------------------------------

def import_panel_dxf(doc: ezdxf.document.Drawing) -> PanelSpec:
    """Импортировать PanelSpec из DXF-документа.

    Читает XDATA контура панели для panel-level полей.
    Координаты операций восстанавливаются из геометрии DXF-сущностей.
    """
    msp = doc.modelspace()

    # Найти контур панели (OUTLINE layer, XDATA с panel_id)
    panel_meta: dict[str, str | float | int] = {}
    for entity in msp:
        if entity.dxf.layer == "OUTLINE":
            xd = _get_xdata_dict(entity)
            if "panel_id" in xd:
                panel_meta = xd
                break

    if not panel_meta:
        raise ValueError("DXF не содержит контура панели с XDATA (panel_id)")

    # Собрать операции из DXF-сущностей
    ops: list[AnyOperation] = []
    op_map: dict[str, AnyOperation] = {}

    for entity in msp:
        xd = _get_xdata_dict(entity)
        if not xd or "op_type" not in xd:
            continue
        op_type_str = str(xd["op_type"])
        face_val = str(xd["face"])
        base = {
            "id": str(xd["operation_id"]),
            "face": face_val,
        }
        # Координаты по умолчанию — из XDATA, потом обновим из геометрии
        base["x_mm"] = 0.0
        base["y_mm"] = 0.0

        if op_type_str == OperationType.DRILL.value:
            op = DrillOperation(
                **base,
                diameter_mm=float(xd["diameter_mm"]),
                depth_mm=float(xd["depth_mm"]),
            )
        elif op_type_str == OperationType.SLOT.value:
            op = SlotOperation(
                **base,
                length_mm=float(xd["length_mm"]),
                width_mm=float(xd["width_mm"]),
                depth_mm=float(xd["depth_mm"]),
            )
        elif op_type_str == OperationType.POCKET.value:
            op = PocketOperation(
                **base,
                width_mm=float(xd["width_mm"]),
                height_mm=float(xd["height_mm"]),
                depth_mm=float(xd["depth_mm"]),
            )
        else:
            continue

        # Восстановить координаты из геометрии DXF
        if entity.dxftype() == "CIRCLE":
            op.x_mm = entity.dxf.center.x
            op.y_mm = entity.dxf.center.y
        elif entity.dxftype() == "LWPOLYLINE":
            pts = list(entity.get_points(format="xy"))
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                op.x_mm = (min(xs) + max(xs)) / 2.0
                op.y_mm = (min(ys) + max(ys)) / 2.0

        ops.append(op)
        op_map[op.id] = op

    return PanelSpec(
        id=str(panel_meta["panel_id"]),
        width_mm=float(panel_meta.get("width_mm", 0)),
        height_mm=float(panel_meta.get("height_mm", 0)),
        thickness_mm=float(panel_meta.get("thickness_mm", 0)),
        material=str(panel_meta["material"]) if "material" in panel_meta else None,
        operations=ops,
    )


# ---------------------------------------------------------------------------
# Layout DXF (Task 11 Step 2) — separate visualization, transformed copies only
# Local part coordinates in export_panel_dxf are NEVER mutated or overwritten.
# ---------------------------------------------------------------------------

def export_layout_dxf(
    layout: SheetLayout,
    order_id: str = "",
    revision: str = "1",
    kerf_mm: float = 4.0,
    margin_mm: float = 10.0,
) -> ezdxf.document.Drawing:
    """Генерирует DXF раскладки (sheet view) отдельно от part DXF.

    - Sheet boundary + размещённые панели (трансформированные копии).
    - Координаты частей в layout — это размещение на листе.
    - Каждая part остаётся в своём локальном DXF с origin (0,0).
    - Слои: SHEET, PART, LABEL.
    - Метаданные: order, revision, kerf, margin в XDATA на SHEET.
    """
    doc = ezdxf.new(DXF_VERSION)
    doc.appids.add(APPID)

    layer_defs = {
        "SHEET": 8,
        "PART": 7,
        "LABEL": 3,
    }
    for name, color in layer_defs.items():
        if name not in [layer.dxf.name for layer in doc.layers]:
            doc.layers.add(name, color=color)

    msp = doc.modelspace()

    sw = float(layout.sheet_width)
    sh = float(layout.sheet_height)

    # Sheet boundary (rectangle)
    sheet_pts = [Vec2(0, 0), Vec2(sw, 0), Vec2(sw, sh), Vec2(0, sh)]
    sheet = msp.add_lwpolyline(sheet_pts, close=True, dxfattribs={"layer": "SHEET"})
    # XDATA for sheet level info
    sheet_pairs = [
        ("order_id", order_id or ""),
        ("revision", revision),
        ("kerf_mm", kerf_mm),
        ("margin_mm", margin_mm),
        ("sheet_width", sw),
        ("sheet_height", sh),
    ]
    _set_xdata(sheet, sheet_pairs)

    # Placed panels as simple rects (transformed copies)
    for item in getattr(layout, "placed_panels", []):
        if isinstance(item, (list, tuple)) and len(item) >= 4:
            panel, px, py, rotated = item[0], float(item[1]), float(item[2]), bool(item[3])
        else:
            # PlacedPanel dataclass fallback
            panel = item
            px = float(getattr(panel, "x", 0.0))
            py = float(getattr(panel, "y", 0.0))
            rotated = bool(getattr(panel, "rotated", False))

        # Determine visual dims (swap on rotate)
        pw = float(panel.height_mm if rotated else panel.width_mm)
        ph = float(panel.width_mm if rotated else panel.height_mm)

        # Draw rect at (px, py) — copy, not reference to local
        cx, cy = px, py
        pts = [
            Vec2(cx, cy),
            Vec2(cx + pw, cy),
            Vec2(cx + pw, cy + ph),
            Vec2(cx, cy + ph),
        ]
        part_pl = msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "PART"})

        # XDATA on the placed part copy (reference to original panel id + placement info)
        part_meta = [
            ("panel_id", getattr(panel, "id", "")),
            ("name", getattr(panel, "name", "")),
            ("rotated", 1 if rotated else 0),
            ("placed_x", px),
            ("placed_y", py),
            ("width_mm", float(getattr(panel, "width_mm", pw))),
            ("height_mm", float(getattr(panel, "height_mm", ph))),
        ]
        _set_xdata(part_pl, part_meta)

        # Label as TEXT near the part
        label = f"{getattr(panel, 'name', panel.id)} {int(pw)}x{int(ph)}"
        if rotated:
            label += " R"
        try:
            msp.add_text(
                label,
                dxfattribs={
                    "layer": "LABEL",
                    "height": 20,
                    "insert": (px + 5, py + ph + 5),
                },
            )
        except Exception:
            pass  # text optional for basic geom

    # Unplaced note as mtext if any
    if getattr(layout, "unplaced_panels", []):
        up = len(layout.unplaced_panels)
        try:
            msp.add_mtext(
                f"UNPLACED: {up}",
                dxfattribs={"layer": "LABEL", "char_height": 15, "insert": (sw + 20, sh - 30)},
            )
        except Exception:
            pass

    return doc


def save_layout_dxf(layout: SheetLayout, path: str, **meta) -> ezdxf.document.Drawing:
    """Сохранить layout DXF. Возвращает doc."""
    doc = export_layout_dxf(layout, **meta)
    doc.saveas(path)
    return doc
