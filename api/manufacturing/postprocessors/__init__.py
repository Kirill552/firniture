"""G-code IR и валидация безопасности постпроцессоров.

Типизированные промежуточные команды (IR) описывают *что* делать,
а не *как* рендерить G-code текст. Валидатор проверяет безопасность
и целостность последовательности команд.

Публичный импорт:
    from api.manufacturing.postprocessors import (
        GCodeCommand, Rapid, Linear, ToolChange, SpindleOn, SpindleOff,
        DrillCycle, CancelCycle, ProgramEnd,
        Severity, Finding, SafetyReport, validate_gcode_ir,
    )
"""
from api.manufacturing.postprocessors.base import (
    CancelCycle,
    DrillCycle,
    GCodeCommand,
    Linear,
    ProgramEnd,
    Rapid,
    SpindleOff,
    SpindleOn,
    ToolChange,
)
from api.manufacturing.postprocessors.safety import (
    Finding,
    SafetyReport,
    Severity,
    validate_gcode_ir,
)

__all__ = [
    # IR commands
    "GCodeCommand",
    "Rapid",
    "Linear",
    "ToolChange",
    "SpindleOn",
    "SpindleOff",
    "DrillCycle",
    "CancelCycle",
    "ProgramEnd",
    # Safety
    "Severity",
    "Finding",
    "SafetyReport",
    "validate_gcode_ir",
]
