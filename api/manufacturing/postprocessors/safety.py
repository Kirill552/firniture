"""Safety валидатор для G-code IR команд.

Проверяет последовательность IR команд на безопасность перед
генерацией G-code. BLOCKING findings блокируют downloadable G-code.

Зависимости: api.manufacturing.machine_profiles, api.manufacturing.tool_library.
"""
from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel

from api.manufacturing.machine_profiles import MachineProfile
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
from api.manufacturing.tool_library import ToolLibrary

# ── Severity / Finding ───────────────────────────────────────────────


class Severity(str, Enum):
    """Уровень серьёзности finding.

    BLOCKING — генерация G-code запрещена.
    WARNING — может сопровождать вывод, но не блокирует.
    """

    BLOCKING = "blocking"
    WARNING = "warning"


class Finding(BaseModel):
    """Находка валидатора."""

    severity: Severity
    message: str


class SafetyReport(BaseModel):
    """Отчёт валидации."""

    findings: list[Finding]

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0

    @property
    def has_blockers(self) -> bool:
        return any(f.severity == Severity.BLOCKING for f in self.findings)


# ── Валидатор ────────────────────────────────────────────────────────


def validate_gcode_ir(
    *,
    commands: list[GCodeCommand],
    profile: MachineProfile,
    tool_library: ToolLibrary,
    panel_width: float,
    panel_height: float,
) -> SafetyReport:
    """Валидировать последовательность G-code IR команд.

    Проверяет:
    - Границы панели (panel bounds)
    - Соответствие инструмента (tool match)
    - Глубину (depth ≤ tool max_depth)
    - Подачи (feeds в пределах machine и tool)
    - RPM (в пределах machine, tool и spindle)
    - Шпиндель включён перед резанием
    - M05 перед сменой инструмента (spindle off)
    - Безопасный отвод (safe retract перед ToolChange)
    - Отмена цикла перед сменой инструмента
    - Финальная отмена (G80 + M05 перед M30)
    """
    findings: list[Finding] = []
    # ── finite boundary inputs (NaN/±inf → fail-closed) ──
    boundary_floats: list[tuple[str, float]] = [
        ("panel_width", panel_width),
        ("panel_height", panel_height),
        ("profile.safe_z", profile.safe_z),
        ("profile.feed_min", profile.feed_min),
        ("profile.feed_max", profile.feed_max),
    ]
    for name, val in boundary_floats:
        if not math.isfinite(val):
            findings.append(
                Finding(
                    severity=Severity.BLOCKING,
                    message=(
                        f"Граница {name} должна быть конечным числом: {val}"
                    ),
                )
            )

    # Текущее состояние
    active_tool: int | None = None
    last_z: float | None = None
    last_spindle_on = False
    cycle_active = False

    for cmd in commands:
        # ── ToolChange ──
        if isinstance(cmd, ToolChange):
            # Canned cycle must be cancelled before tool change
            if cycle_active:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Запрещённая смена инструмента: "
                            f"активен canned cycle при ToolChange T{cmd.t_number}. "
                            f"Требуется CancelCycle() (G80) перед ToolChange()."
                        ),
                    )
                )

            # M05 перед сменой
            if last_spindle_on:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Шпиндель не выключен (M05) перед "
                            f"ToolChange T{cmd.t_number}. "
                            f"Требуется SpindleOff() перед ToolChange()."
                        ),
                    )
                )

            # Безопасный отвод перед сменой
            if last_z is not None and last_z < profile.safe_z:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Нет безопасного отвода (safe_z={profile.safe_z}) "
                            f"перед ToolChange T{cmd.t_number}. "
                            f"Последняя z={last_z}. "
                            f"Требуется Rapid(z={profile.safe_z}) перед ToolChange()."
                        ),
                    )
                )

            # Tool match
            tool = tool_library.get_by_t_number(cmd.t_number)
            if tool is None:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Инструмент T{cmd.t_number} не найден в "
                            f"библиотеке инструментов."
                        ),
                    )
                )

            active_tool = cmd.t_number
            last_spindle_on = False
            # НЕ сбрасываем cycle_active — нарушение уже зафиксировано
            continue

        # ── SpindleOn ──
        if isinstance(cmd, SpindleOn):
            last_spindle_on = True

            # RPM check — non-finite (defense-in-depth, base.py rejects at construction)
            if not math.isfinite(cmd.rpm):
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"rpm должен быть конечным числом: {cmd.rpm}"
                        ),
                    )
                )

            # RPM check — machine range
            if cmd.rpm < profile.rpm_min or cmd.rpm > profile.rpm_max:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"RPM {cmd.rpm} вне диапазона станка "
                            f"[{profile.rpm_min}, {profile.rpm_max}]."
                        ),
                    )
                )

            # RPM check — tool range
            if active_tool is not None:
                tool = tool_library.get_by_t_number(active_tool)
                if tool is not None:
                    if cmd.rpm < tool.rpm_min or cmd.rpm > tool.rpm_max:
                        findings.append(
                            Finding(
                                severity=Severity.BLOCKING,
                                message=(
                                    f"RPM {cmd.rpm} вне диапазона "
                                    f"инструмента T{active_tool} "
                                    f"[{tool.rpm_min}, {tool.rpm_max}]."
                                ),
                            )
                        )

                    # RPM check — spindle max_rpm
                    spindle_cfg = next(
                        (s for s in profile.spindles
                         if s.spindle_id == tool.spindle_id),
                        None,
                    )
                    if spindle_cfg is None:
                        findings.append(
                            Finding(
                                severity=Severity.BLOCKING,
                                message=(
                                    f"Шпиндель инструмента T{active_tool} "
                                    f"(spindle_id={tool.spindle_id}) не найден "
                                    f"в профиле станка."
                                ),
                            )
                        )
                    elif cmd.rpm > spindle_cfg.max_rpm:
                        findings.append(
                            Finding(
                                severity=Severity.BLOCKING,
                                message=(
                                    f"RPM {cmd.rpm} превышает максимум шпинделя "
                                    f"{spindle_cfg.name} (id={spindle_cfg.spindle_id}) "
                                    f"[{spindle_cfg.max_rpm}]."
                                ),
                            )
                        )
            continue

        # ── SpindleOff ──
        if isinstance(cmd, SpindleOff):
            last_spindle_on = False
            continue

        # ── Rapid ──
        if isinstance(cmd, Rapid):
            # Panel bounds check (only for coordinates that are set; Rapid may omit axes)
            if cmd.x is not None:
                if cmd.x < 0 or cmd.x > panel_width:
                    findings.append(
                        Finding(
                            severity=Severity.BLOCKING,
                            message=(
                                f"Координата X={cmd.x} за пределами панели "
                                f"[0, {panel_width}]."
                            ),
                        )
                    )
            if cmd.y is not None:
                if cmd.y < 0 or cmd.y > panel_height:
                    findings.append(
                        Finding(
                            severity=Severity.BLOCKING,
                            message=(
                                f"Координата Y={cmd.y} за пределами панели "
                                f"[0, {panel_height}]."
                            ),
                        )
                    )
            if cmd.z is not None:
                last_z = cmd.z
            continue

        # ── Linear ──
        if isinstance(cmd, Linear):
            # Panel bounds
            if cmd.x < 0 or cmd.x > panel_width:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Координата X={cmd.x} за пределами панели "
                            f"[0, {panel_width}]."
                        ),
                    )
                )
            if cmd.y < 0 or cmd.y > panel_height:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Координата Y={cmd.y} за пределами панели "
                            f"[0, {panel_height}]."
                        ),
                    )
                )
            if cmd.z is not None:
                last_z = cmd.z

            # Режущее перемещение (Z < 0 — инструмент ниже поверхности)
            if cmd.z < 0:
                # Инструмент должен быть загружен
                if active_tool is None:
                    findings.append(
                        Finding(
                            severity=Severity.BLOCKING,
                            message=(
                                f"Инструмент не загружен перед Linear(z={cmd.z}) "
                                f"на ({cmd.x}, {cmd.y}). "
                                f"Требуется ToolChange() перед резанием."
                            ),
                        )
                    )

                # Шпиндель должен быть включён
                if not last_spindle_on:
                    findings.append(
                        Finding(
                            severity=Severity.BLOCKING,
                            message=(
                                f"Шпиндель не включён перед Linear(z={cmd.z}) "
                                f"на ({cmd.x}, {cmd.y}). "
                                f"Требуется SpindleOn() перед резанием."
                            ),
                        )
                    )

                # Подача — диапазон станка
                if cmd.feed < profile.feed_min or cmd.feed > profile.feed_max:
                    findings.append(
                        Finding(
                            severity=Severity.BLOCKING,
                            message=(
                                f"Подача {cmd.feed} мм/мин (Linear) вне диапазона "
                                f"станка [{profile.feed_min}, {profile.feed_max}]."
                            ),
                        )
                    )

                # Подача — диапазон инструмента
                if active_tool is not None:
                    tool = tool_library.get_by_t_number(active_tool)
                    if tool is not None:
                        if cmd.feed < tool.feed_min or cmd.feed > tool.feed_max:
                            findings.append(
                                Finding(
                                    severity=Severity.BLOCKING,
                                    message=(
                                        f"Подача {cmd.feed} мм/мин (Linear) вне диапазона "
                                        f"инструмента T{active_tool} "
                                        f"[{tool.feed_min}, {tool.feed_max}]."
                                    ),
                                )
                            )

                        # Глубина — максимум инструмента
                        depth_abs = abs(cmd.z)
                        if depth_abs > tool.max_depth_mm:
                            findings.append(
                                Finding(
                                    severity=Severity.BLOCKING,
                                    message=(
                                        f"Глубина резания Linear {depth_abs} мм "
                                        f"превышает максимальную глубину "
                                        f"инструмента T{active_tool} "
                                        f"({tool.max_depth_mm} мм)."
                                    ),
                                )
                            )

            continue

        # ── DrillCycle ──
        if isinstance(cmd, DrillCycle):
            # Шпиндель должен быть включён для резания
            if not last_spindle_on:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Шпиндель не включён перед DrillCycle на "
                            f"({cmd.x}, {cmd.y}, z={cmd.z}). "
                            f"Требуется SpindleOn() перед началом резания."
                        ),
                    )
                )

            # Инструмент должен быть загружен для резания
            if active_tool is None:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Инструмент не загружен перед DrillCycle на "
                            f"({cmd.x}, {cmd.y}, z={cmd.z}). "
                            f"Требуется ToolChange() перед началом резания."
                        ),
                    )
                )
            cycle_active = True

            # Panel bounds
            if cmd.x < 0 or cmd.x > panel_width:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Координата X={cmd.x} за пределами панели "
                            f"[0, {panel_width}]."
                        ),
                    )
                )
            if cmd.y < 0 or cmd.y > panel_height:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Координата Y={cmd.y} за пределами панели "
                            f"[0, {panel_height}]."
                        ),
                    )
                )

            # Depth check
            if active_tool is not None:
                tool = tool_library.get_by_t_number(active_tool)
                if tool is not None:
                    depth_abs = abs(cmd.z)
                    if depth_abs > tool.max_depth_mm:
                        findings.append(
                            Finding(
                                severity=Severity.BLOCKING,
                                message=(
                                    f"Глубина сверления {depth_abs} мм "
                                    f"превышает максимальную глубину "
                                    f"инструмента T{active_tool} "
                                    f"({tool.max_depth_mm} мм)."
                                ),
                            )
                        )

            # Feed check — machine range
            if cmd.feed < profile.feed_min or cmd.feed > profile.feed_max:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            f"Подача {cmd.feed} мм/мин вне диапазона "
                            f"станка [{profile.feed_min}, {profile.feed_max}]."
                        ),
                    )
                )

            # Feed check — tool range
            if active_tool is not None:
                tool = tool_library.get_by_t_number(active_tool)
                if tool is not None:
                    if cmd.feed < tool.feed_min or cmd.feed > tool.feed_max:
                        findings.append(
                            Finding(
                                severity=Severity.BLOCKING,
                                message=(
                                    f"Подача {cmd.feed} мм/мин вне диапазона "
                                    f"инструмента T{active_tool} "
                                    f"[{tool.feed_min}, {tool.feed_max}]."
                                ),
                            )
                        )

            last_z = cmd.z
            continue

        # ── CancelCycle ──
        if isinstance(cmd, CancelCycle):
            cycle_active = False
            continue

        # ── ProgramEnd ──
        if isinstance(cmd, ProgramEnd):
            # G80 before M30
            if cycle_active:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            "Нет отмены цикла (G80/CancelCycle) перед "
                            "концом программы (M30/ProgramEnd)."
                        ),
                    )
                )

            # M05 before M30
            if last_spindle_on:
                findings.append(
                    Finding(
                        severity=Severity.BLOCKING,
                        message=(
                            "Шпиндель не выключен (M05/SpindleOff) перед "
                            "концом программы (M30/ProgramEnd)."
                        ),
                    )
                )
            continue

        # ── Unknown command (exhaustive guard) ──
        findings.append(
            Finding(
                severity=Severity.BLOCKING,
                message=(
                    f"Неизвестная IR команда: {type(cmd).__name__} "
                    f"(не распознана валидатором). "
                    f"Только поддерживаемые команды допустимы."
                ),
            )
        )

    return SafetyReport(findings=findings)
