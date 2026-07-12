"""Setup transforms — top/bottom/four-edge CNC panel mounting.

Setup = how a panel is physically positioned on the CNC table.
Each setup determines:
  - Which face is accessible from above
  - Coordinate transforms for operations
  - Whether a horizontal aggregate is required

Business rules:
  - 3-axis machines (axis_count < 4): only flat setups (top/bottom)
  - Edge setups require horizontal aggregate
  - Aggregate usage requires certified profile (CertificationStatus.VERIFIED)
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from api.manufacturing.machine_profiles import (
    CertificationStatus,
    MachineProfile,
)

if TYPE_CHECKING:
    from api.manufacturing.contracts import AnyOperation


# ---------------------------------------------------------------------------
# Setup type
# ---------------------------------------------------------------------------

class SetupType(str, Enum):
    """Тип установки панели на столе станка.

    Flat setups: панель лежит горизонтально.
    Edge setups: панель стоит на торце (требует агрегат).
    """

    TOP = "top"
    BOTTOM = "bottom"
    LEFT_EDGE = "left_edge"
    RIGHT_EDGE = "right_edge"
    FRONT_EDGE = "front_edge"
    BACK_EDGE = "back_edge"


# Flat vs edge classification

_FLAT_SETUPS: frozenset[SetupType] = frozenset({SetupType.TOP, SetupType.BOTTOM})
_EDGE_SETUPS: frozenset[SetupType] = frozenset({
    SetupType.LEFT_EDGE,
    SetupType.RIGHT_EDGE,
    SetupType.FRONT_EDGE,
    SetupType.BACK_EDGE,
})

# Mapping: edge setup → which Face is accessible from above after rotation
_EDGE_ACCESSIBLE_FACE: dict[SetupType, str] = {
    SetupType.LEFT_EDGE: "left",
    SetupType.RIGHT_EDGE: "right",
    SetupType.FRONT_EDGE: "front",
    SetupType.BACK_EDGE: "back",
}


# ---------------------------------------------------------------------------
# Setup errors
# ---------------------------------------------------------------------------

class SetupError(Exception):
    """Setup incompatible with machine capabilities."""


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def setup_requires_aggregate(setup_type: SetupType) -> bool:
    """Torцевые установки требуют горизонтального агрегата."""
    return setup_type in _EDGE_SETUPS


def accessible_face(setup_type: SetupType) -> str:
    """Какая грань доступна сверху при данной установке.

    Flat setups → face-up: TOP exposes front, BOTTOM exposes back.
    Edge setups → the edge face itself is accessible from above.
    """
    if setup_type == SetupType.TOP:
        return "front"
    if setup_type == SetupType.BOTTOM:
        return "back"
    return _EDGE_ACCESSIBLE_FACE[setup_type]


def is_flat_setup(setup_type: SetupType) -> bool:
    return setup_type in _FLAT_SETUPS


# ---------------------------------------------------------------------------
# Coordinate transforms
# ---------------------------------------------------------------------------

def apply_flat_transform(
    x_mm: float,
    y_mm: float,
    setup_type: SetupType,
    *,
    panel_h: float,
) -> tuple[float, float]:
    """Transform coordinates for flat (top/bottom) setups.

    TOP: identity — front face up, no change.
    BOTTOM: Y-mirror — panel flipped, y → panel_h - y.
    """
    if setup_type == SetupType.TOP:
        return x_mm, y_mm
    if setup_type == SetupType.BOTTOM:
        return x_mm, panel_h - y_mm
    raise ValueError(f"apply_flat_transform called with non-flat setup: {setup_type}")


def apply_edge_transform(
    x_mm: float,
    y_mm: float,
    setup_type: SetupType,
    *,
    panel_w: float,
    panel_h: float,
) -> tuple[float, float]:
    """Transform coordinates for edge setups.

    Edge setups rotate the panel 90° around Z so the edge face points up.
    Coordinate mapping after rotation:

    LEFT_EDGE:  (x, y) → (y, thickness)   — left face becomes top
    RIGHT_EDGE: (x, y) → (panel_h - y, thickness) — right face becomes top
    FRONT_EDGE: (x, y) → (panel_w - x, thickness) — front face becomes top
    BACK_EDGE:  (x, y) → (x, thickness)   — back face becomes top

    thickness is passed separately because the edge depth becomes the
    Z-height after rotation (not used in X/Y transform here).
    """
    match setup_type:
        case SetupType.LEFT_EDGE:
            return y_mm, x_mm
        case SetupType.RIGHT_EDGE:
            return panel_h - y_mm, x_mm
        case SetupType.FRONT_EDGE:
            return panel_w - x_mm, y_mm
        case SetupType.BACK_EDGE:
            return x_mm, y_mm
    raise ValueError(f"apply_edge_transform called with non-edge setup: {setup_type}")


def apply_setup_transform(
    x_mm: float,
    y_mm: float,
    setup_type: SetupType,
    *,
    panel_w: float,
    panel_h: float,
    thickness_mm: float,
) -> tuple[float, float]:
    """Unified dispatch: apply the correct transform for any setup type."""
    if is_flat_setup(setup_type):
        return apply_flat_transform(x_mm, y_mm, setup_type, panel_h=panel_h)
    return apply_edge_transform(
        x_mm, y_mm, setup_type, panel_w=panel_w, panel_h=panel_h,
    )


# ---------------------------------------------------------------------------
# Machine validation
# ---------------------------------------------------------------------------

def validate_setup_for_profile(
    setup_type: SetupType,
    profile: MachineProfile,
    *,
    axis_count: int = 3,
) -> list[str]:
    """Validate that a setup is compatible with a machine profile.

    Rules:
      1. Flat setups always allowed.
      2. Edge setups blocked on 3-axis machines (axis_count < 4).
      3. Edge setups on 4+ axis machines require profile.certification == VERIFIED.

    Returns a list of blocking error messages (empty = valid).
    """
    errors: list[str] = []
    if is_flat_setup(setup_type):
        return errors

    # Edge setup requires aggregate → need 4+ axes
    if axis_count < 4:
        errors.append(
            f"Edge setup '{setup_type.value}' requires horizontal aggregate "
            f"but machine '{profile.profile_id}' is {axis_count}-axis"
        )
        return errors

    # 4+ axis machine: check certification for aggregate
    if profile.certification != CertificationStatus.VERIFIED:
        errors.append(
            f"Horizontal aggregate requires VERIFIED profile, "
            f"got '{profile.certification.value}' for '{profile.profile_id}'"
        )

    return errors


def validate_setup_or_raise(
    setup_type: SetupType,
    profile: MachineProfile,
    *,
    axis_count: int = 3,
) -> None:
    """Like validate_setup_for_profile but raises SetupError on failure."""
    errors = validate_setup_for_profile(
        setup_type, profile, axis_count=axis_count,
    )
    if errors:
        raise SetupError("; ".join(errors))


# ---------------------------------------------------------------------------
# Apply transforms to operations
# ---------------------------------------------------------------------------

def transform_operations(
    operations: list[AnyOperation],
    setup_type: SetupType,
    *,
    panel_w: float,
    panel_h: float,
    thickness_mm: float,
) -> list[AnyOperation]:
    """Apply setup coordinate transform to a list of operations.

    Returns new operations with transformed x_mm/y_mm.
    Flat setups mirror Y for BOTTOM.
    Edge setups rotate coordinates and update the face field.
    """
    result: list[AnyOperation] = []
    for op in operations:
        new_x, new_y = apply_setup_transform(
            op.x_mm,
            op.y_mm,
            setup_type,
            panel_w=panel_w,
            panel_h=panel_h,
            thickness_mm=thickness_mm,
        )
        result.append(op.model_copy(update={"x_mm": new_x, "y_mm": new_y}))
    return result
