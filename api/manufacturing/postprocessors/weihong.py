"""Weihong NCStudio postprocessor — типизированный IR → G-code.

Рендерит детерминированный ASCII G-code из IR команд (base.py)
для контроллеров Weihong NCStudio по контракту MachineProfile.

Диалект-специфика (Weihong NCStudio):
- G04 P<мс> (P в циклах G82 — миллисекунды; IR dwell в секундах → ×1000)
- G81/G82/G83 — стандартные циклы сверления NCStudio
- ToolChange: M05 → G00 Z<safe_z> → T<номер> M06 (безопасная seq)
- Ровно один M30 в конце (ProgramEnd игнорируется для M30)
- G21 G90 G17 <work_offset> G80 в preamble
- work_offset, safe_z, line_ending из профиля

Статус: DRAFT. Профиль в тестах — uncertified (draft).
Task 20 физическая сертификация (симулятор/air-cut/sacrificial) не завершена.

Зависимости: api.manufacturing.postprocessors.base,
             api.manufacturing.machine_profiles.
"""
from __future__ import annotations

from typing import TextIO

from api.manufacturing.machine_profiles import (
    CertificationStatus,
    ControllerType,
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

# ── Константы ────────────────────────────────────────────────────────

# Группа 01 G-кодов — отменяют активный canned cycle при появлении
_GROUP01_CODES = frozenset({"G00", "G01", "G02", "G03"})

# Маппинг LineEnding → символ окончания строки
_LINE_END_MAP: dict[LineEnding, str] = {
    LineEnding.LF: "\n",
    LineEnding.CRLF: "\r\n",
    LineEnding.CR: "\r",
}


# ── Форматирование чисел ────────────────────────────────────────────

def _fmt_coord(value: float) -> str:
    """Форматировать координату: всегда 3 знака после точки."""
    return f"{value:.3f}"


def _fmt_feed(value: float) -> str:
    """Форматировать подачу: целое число."""
    return f"{value:.0f}"


def _fmt_rpm(value: int) -> str:
    """Форматировать обороты: целое число."""
    return str(value)


def _fmt_peck(value: float) -> str:
    """Форматировать peck: 3 знака после точки."""
    return f"{value:.3f}"


def _fmt_dwell_ms(seconds: float) -> str:
    """Конвертировать секунды → целые миллисекунды (NCStudio P_)."""
    ms = round(seconds * 1000)
    return str(ms)


# ── Постпроцессор ────────────────────────────────────────────────────


class WeihongPostprocessor:
    """Рендер IR команд → Weihong NCStudio G-code.

    Параметры:
        profile: Профиль станка (определяет line_ending, safe_z, work_offset).
        comment_tool_change: Добавлять комментарии при смене инструмента.

    Пример::

        pp = WeihongPostprocessor(profile)
        gcode = pp.render([Rapid(x=0, y=0, z=5), Linear(x=10, y=0, z=-2, feed=800)])
    """

    def __init__(
        self,
        profile: MachineProfile,
        *,
        comment_tool_change: bool = True,
    ) -> None:
        # Валидация контроллера: Weihong поддерживает WEIHONG и OTHER (для тестов/эксп)
        allowed = (ControllerType.WEIHONG, ControllerType.OTHER)
        if profile.controller not in allowed:
            raise ValueError(
                f"WeihongPostprocessor не поддерживает контроллер {profile.controller.value}. "
                "Используйте weihong или other."
            )

        if profile.certification == CertificationStatus.DEPRECATED:
            raise ValueError(
                f"Профиль {profile.profile_id} помечен как DEPRECATED — "
                "генерация G-code запрещена."
            )

        self._profile = profile
        self._comment_tool_change = comment_tool_change
        self._line_end = _LINE_END_MAP[profile.line_ending]

    # ── Публичное API ──────────────────────────────────────────────

    def render(self, commands: list[GCodeCommand]) -> str:
        """Рендер списка IR команд в G-code строку.

        Гарантирует:
        - Preamble: G21 G90 G17 <work_offset> G80
        - M05 перед каждой ToolChange + safe retract (Weihong-специфично)
        - Одно M30 в конце (даже при ProgramEnd)
        - Консистентные line endings

        Raises:
            ValueError: Если команда не является известным типом GCodeCommand.
        """
        lines: list[str] = []

        # ── Preamble ─────────────────────────────────────────────
        lines.append("G21")       # метрические единицы
        lines.append("G90")       # абсолютное программирование
        lines.append("G17")       # плоскость XY
        lines.append(self._profile.work_offset)  # G54 / G54.1 P1 / ...
        lines.append("G80")       # отмена активного цикла

        # ── Команды ──────────────────────────────────────────────
        for cmd in commands:
            lines.extend(self._render_command(cmd))

        # ── Конец программы ──────────────────────────────────────
        lines.append("M30")

        return self._line_end.join(lines) + self._line_end

    def render_to_file(self, commands: list[GCodeCommand], fp: TextIO) -> None:
        """Рендер и записать в файловый объект."""
        fp.write(self.render(commands))

    # ── Внутренний рендеринг ──────────────────────────────────────

    def _render_command(self, cmd: GCodeCommand) -> list[str]:
        """Рендер одной IR команды в одну или несколько строк G-code."""
        if isinstance(cmd, Rapid):
            return [self._render_rapid(cmd)]
        if isinstance(cmd, Linear):
            return [self._render_linear(cmd)]
        if isinstance(cmd, SpindleOn):
            return [self._render_spindle_on(cmd)]
        if isinstance(cmd, SpindleOff):
            return [self._render_spindle_off(cmd)]
        if isinstance(cmd, ToolChange):
            return self._render_tool_change(cmd)
        if isinstance(cmd, DrillCycle):
            return [self._render_drill_cycle(cmd)]
        if isinstance(cmd, CancelCycle):
            return ["G80"]
        if isinstance(cmd, ProgramEnd):
            # M30 добавляется автоматически в render() — не дублируем
            return []
        raise ValueError(
            f"Неизвестный тип IR команды: {type(cmd).__name__}"
        )

    def _render_rapid(self, cmd: Rapid) -> str:
        """G00 X_ Y_ Z_"""
        parts = ["G00"]
        if cmd.x is not None:
            parts.append(f"X{_fmt_coord(cmd.x)}")
        if cmd.y is not None:
            parts.append(f"Y{_fmt_coord(cmd.y)}")
        if cmd.z is not None:
            parts.append(f"Z{_fmt_coord(cmd.z)}")
        return " ".join(parts)

    def _render_linear(self, cmd: Linear) -> str:
        """G01 X_ Y_ Z_ F_"""
        parts = [
            "G01",
            f"X{_fmt_coord(cmd.x)}",
            f"Y{_fmt_coord(cmd.y)}",
        ]
        if cmd.z is not None:
            parts.append(f"Z{_fmt_coord(cmd.z)}")
        parts.append(f"F{_fmt_feed(cmd.feed)}")
        return " ".join(parts)

    def _render_spindle_on(self, cmd: SpindleOn) -> str:
        """S<rpm> M03|M04"""
        m_code = "M03" if cmd.clockwise else "M04"
        return f"S{_fmt_rpm(cmd.rpm)} {m_code}"

    def _render_spindle_off(self, cmd: SpindleOff) -> str:
        """M05"""
        return "M05"

    def _render_tool_change(self, cmd: ToolChange) -> list[str]:
        """M05 → safe retract → Txx M06.

        Безопасная последовательность смены инструмента (NCStudio):
        1. M05 — остановка шпинделя
        2. G00 Z<safe_z> — безопасный отвод по Z
        3. T<номер> M06 — смена инструмента
        """
        lines: list[str] = []

        if self._comment_tool_change:
            lines.append(f"; --- tool change T{cmd.t_number} ---")

        # 1. Остановка шпинделя
        lines.append("M05")

        # 2. Безопасный отвод по Z
        safe_z = self._profile.safe_z
        lines.append(f"G00 Z{_fmt_coord(safe_z)}")

        # 3. Смена инструмента
        lines.append(f"T{cmd.t_number} M06")

        return lines

    def _render_drill_cycle(self, cmd: DrillCycle) -> str:
        """G81/G82/G83 X_ Y_ Z_ R_ [Q_] [P_] F_

        Маппинг IR → NCStudio G-code:
        - peck=None, dwell=None → G81 (простое сверление)
        - peck=None, dwell>0   → G82 (с выдержкой на дне)
        - peck>0               → G83 (погружение с отводом)

        NCStudio G04 P_ принимает миллисекунды.
        DrillCycle.dwell хранится в секундах → конвертация ×1000.
        """
        # Определяем тип цикла
        if cmd.peck is not None and cmd.peck > 0:
            g_code = "G83"
        elif cmd.dwell is not None and cmd.dwell > 0:
            g_code = "G82"
        else:
            g_code = "G81"

        parts = [
            g_code,
            f"X{_fmt_coord(cmd.x)}",
            f"Y{_fmt_coord(cmd.y)}",
            f"Z{_fmt_coord(cmd.z)}",
            f"R{_fmt_coord(cmd.retract)}",
        ]

        # Q — peck depth (только G83)
        if g_code == "G83" and cmd.peck is not None:
            parts.append(f"Q{_fmt_peck(cmd.peck)}")

        # P — dwell в мс (только G82)
        if g_code == "G82" and cmd.dwell is not None:
            parts.append(f"P{_fmt_dwell_ms(cmd.dwell)}")

        # F — подача
        parts.append(f"F{_fmt_feed(cmd.feed)}")

        return " ".join(parts)
