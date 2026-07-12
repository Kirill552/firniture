"""Manufacturing domain: contracts, coordinate transforms, hashing, DXF export, setups.

Публичный импорт:
    from api.manufacturing import (
        Face, OperationType, Unit, DrillOperation, SlotOperation, PocketOperation,
        AnyOperation, PanelSpec, ManufacturingSpec,
        face_to_panel, panel_to_gcode, gcode_to_panel,
        mirror_operation_x, mirror_operation_y, rotate_operation_cw,
        SetupType, setup_requires_aggregate, accessible_face, is_flat_setup,
        apply_setup_transform, validate_setup_for_profile, transform_operations,
        canonical_json, spec_hash,
        export_panel_dxf, import_panel_dxf, save_dxf,
    )
"""
from api.manufacturing.contracts import (
    AnyOperation,
    DrillOperation,
    Face,
    ManufacturingSpec,
    OperationType,
    PanelSpec,
    PocketOperation,
    SlotOperation,
    Unit,
)
from api.manufacturing.coordinates import (
    canonical_json,
    face_to_panel,
    gcode_to_panel,
    mirror_operation_x,
    mirror_operation_y,
    panel_to_gcode,
    rotate_operation_cw,
    spec_hash,
)
from api.manufacturing.dxf_export import (
    export_panel_dxf,
    import_panel_dxf,
    save_dxf,
)
from api.manufacturing.setups import (
    SetupError,
    SetupType,
    accessible_face,
    apply_setup_transform,
    is_flat_setup,
    setup_requires_aggregate,
    transform_operations,
    validate_setup_for_profile,
    validate_setup_or_raise,
)

__all__ = [
    # Enums
    "Face",
    "OperationType",
    "Unit",
    # Operations
    "DrillOperation",
    "SlotOperation",
    "PocketOperation",
    "AnyOperation",
    # Spec
    "PanelSpec",
    "ManufacturingSpec",
    # Coordinates
    "face_to_panel",
    "panel_to_gcode",
    "gcode_to_panel",
    "mirror_operation_x",
    "mirror_operation_y",
    "rotate_operation_cw",
    # Serialization
    "canonical_json",
    "spec_hash",
    # Setups
    "SetupType",
    "SetupError",
    "setup_requires_aggregate",
    "accessible_face",
    "is_flat_setup",
    "apply_setup_transform",
    "validate_setup_for_profile",
    "validate_setup_or_raise",
    "transform_operations",
    # DXF
    "export_panel_dxf",
    "import_panel_dxf",
    "save_dxf",
]
