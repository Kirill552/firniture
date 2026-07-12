"""Базовый рендерер G-code IR → текст для контроллеров.

Совместная логика диспетчеризации IR-команд и форматирования строк.
Контроллеры наследуют и переопределяют header/footer/специфичные методы.

Зависимости: api.manufacturing.postprocessors.base, api.manufacturing.machine_profiles.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from api.manufacturing.machine_profiles import (
    CertificationStatus,
    DwellSyntax,
    LineEnding,
    MachineProfile,
)
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

if TYPE_CHECKING:
    pass


# ── Линейные окончания ──────────────────────────────────────────────

_LINE_END: dict[LineEnding, str] = {
    LineEnding.LF: "\n",
    LineEnding.CRLF: "\r\n",
    LineEnding.CR: "\r",
}


# ── Базовый рендерер ────────────────────────────────────────────────


class GCodeRenderer(ABC):
    """Абстрактный рендерер G-code IR → текст.

    Диспетчеризует IR-команды на контроллер-специфичные методы.
    Контроллеры реализуют: header, footer, dwell formatting, home return.
    """

    def __init__(self, profile: MachineProfile) -> None:
        if profile.certification == CertificationStatus.DEPRECATED:
            raise ValueError(
                f"Профиль {profile.profile_id} помечен как DEPRECATED — "
                "генерация G-code запрещена."
            )
        self.profile = profile
        self._lines: list[str] = []
        self._line_number: int = 10
        self._line_number_increment: int = 10

    # ── Публичный API ───────────────────────────────────────────────

    def render(self, commands: list[GCodeCommand]) -> str:
        """Рендерит список IR-команд в G-code текст контроллера."""
        self._lines = []
        self._line_number = 10
        self._line_number_increment = 10

        self._render_header()
        for cmd in commands:
            self._dispatch(cmd)
        self._render_footer()

        eol = _LINE_END.get(self.profile.line_ending, "\n")
        return eol.join(self._lines)

    # ── Диспетчеризация ─────────────────────────────────────────────

    def _dispatch(self, cmd: GCodeCommand) -> None:
        """Маппит IR-команду на метод рендера."""
        if isinstance(cmd, Rapid):
            self._render_rapid(cmd)
        elif isinstance(cmd, Linear):
            self._render_linear(cmd)
        elif isinstance(cmd, ToolChange):
            self._render_tool_change(cmd)
        elif isinstance(cmd, SpindleOn):
            self._render_spindle_on(cmd)
        elif isinstance(cmd, SpindleOff):
            self._render_spindle_off(cmd)
        elif isinstance(cmd, DrillCycle):
            self._render_drill_cycle(cmd)
        elif isinstance(cmd, CancelCycle):
            self._render_cancel_cycle(cmd)
        elif isinstance(cmd, ProgramEnd):
            self._render_program_end(cmd)
        else:
            raise ValueError(
                f"Неизвестный тип IR-команды: {type(cmd).__name__}. "
                "Постпроцессор не поддерживает эту команду."
            )

    # ── Добавление строк ────────────────────────────────────────────

    def _add_line(self, line: str, *, is_command: bool = True) -> None:
        """Добавляет строку с опциональной нумерацией.

        Нумерация строк (N10, N20...) — ответственность FanucRenderer.
        Базовый метод просто добавляет; FanucRenderer переопределяет _add_line.
        """
        self._lines.append(line)

    def _comment(self, text: str) -> str:
        """Форматирует комментарий для контроллера."""
        return f"({text})"

    # ── Форматирование dwell ────────────────────────────────────────

    def _format_dwell(self, seconds: float) -> str:
        """Форматирует параметр dwell (G04) согласно синтаксису контроллера."""
        syntax = self.profile.dwell_syntax
        if syntax == DwellSyntax.G4_P_MILLISECONDS:
            return f"G04 P{int(seconds * 1000)}"
        elif syntax == DwellSyntax.G4_P_SECONDS:
            return f"G04 P{seconds:.1f}"
        elif syntax == DwellSyntax.G4_X:
            return f"G04 X{seconds:.1f}"
        else:
            # Fail-closed: неизвестный синтаксис dwell
            raise ValueError(
                f"Неподдерживаемый dwell_syntax: {syntax}. "
                "Рендерер не может сформировать команду выдержки."
            )

    # ── Рендереры команд ────────────────────────────────────────────

    def _render_rapid(self, cmd: Rapid) -> None:
        """G00 X... Y... Z..."""
        parts: list[str] = []
        if cmd.x is not None:
            parts.append(f"X{cmd.x:.3f}")
        if cmd.y is not None:
            parts.append(f"Y{cmd.y:.3f}")
        if cmd.z is not None:
            parts.append(f"Z{cmd.z:.3f}")
        if parts:
            self._add_line(f"G00 {' '.join(parts)}")

    def _render_linear(self, cmd: Linear) -> None:
        """G01 X... Y... Z... F..."""
        parts: list[str] = []
        if cmd.x is not None:
            parts.append(f"X{cmd.x:.3f}")
        if cmd.y is not None:
            parts.append(f"Y{cmd.y:.3f}")
        if cmd.z is not None:
            parts.append(f"Z{cmd.z:.3f}")
        parts.append(f"F{cmd.feed:.0f}")
        self._add_line(f"G01 {' '.join(parts)}")

    def _render_tool_change(self, cmd: ToolChange) -> None:
        """M06 Txx — смена инструмента."""
        self._add_line(f"M06 T{cmd.t_number:02d}")

    def _render_spindle_on(self, cmd: SpindleOn) -> None:
        """Sxxx M03/M04 — включение шпинделя."""
        m_code = "M03" if cmd.clockwise else "M04"
        self._add_line(f"S{cmd.rpm} {m_code}")

    def _render_spindle_off(self, cmd: SpindleOff) -> None:
        """M05 — выключение шпинделя."""
        self._add_line("M05")

    def _render_drill_cycle(self, cmd: DrillCycle) -> None:
        """G81/G82/G83 — цикл сверления."""
        cycle_code = self._select_drill_cycle_code(cmd)
        parts = [
            cycle_code,
            f"X{cmd.x:.3f}",
            f"Y{cmd.y:.3f}",
            f"Z{cmd.z:.3f}",
            f"R{cmd.retract:.1f}",
        ]
        if cmd.peck is not None:
            parts.append(f"Q{cmd.peck:.1f}")
        if cmd.dwell is not None and cmd.dwell > 0:
            dwell_param = self._format_dwell_parameter(cmd.dwell)
            parts.append(dwell_param)
        parts.append(f"F{cmd.feed:.0f}")
        self._add_line(" ".join(parts))

    def _select_drill_cycle_code(self, cmd: DrillCycle) -> str:
        """Выбирает код цикла сверления: G83(peck) / G82(dwell) / G81."""
        if cmd.peck is not None and cmd.peck > 0:
            return "G83"
        if cmd.dwell is not None and cmd.dwell > 0:
            return "G82"
        return "G81"

    def _format_dwell_parameter(self, seconds: float) -> str:
        """Форматирует dwell-параметр ВНУТРИ цикла свверления (без G04)."""
        syntax = self.profile.dwell_syntax
        if syntax == DwellSyntax.G4_P_MILLISECONDS:
            return f"P{int(seconds * 1000)}"
        elif syntax == DwellSyntax.G4_P_SECONDS:
            return f"P{seconds:.1f}"
        elif syntax == DwellSyntax.G4_X:
            return f"X{seconds:.1f}"
        raise ValueError(
            f"Неподдерживаемый dwell_syntax: {syntax}"
        )

    def _render_cancel_cycle(self, cmd: CancelCycle) -> None:
        """G80 — отмена цикла."""
        self._add_line("G80")

    def _render_program_end(self, cmd: ProgramEnd) -> None:
        """M30 — конец программы (базовая реализация)."""
        self._add_line("M30")

    # ── Шапка / подвал ──────────────────────────────────────────────

    @abstractmethod
    def _render_header(self) -> None:
        """Генерирует шапку программы (специфично для контроллера)."""
        ...

    @abstractmethod
    def _render_footer(self) -> None:
        """Генерирует завершение программы (специфично для контроллера)."""
        ...
