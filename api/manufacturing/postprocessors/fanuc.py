"""Постпроцессор FANUC — рендер G-code IR для контроллеров FANUC (ISO 6983).

FANUC 0i/31i — промышленный стандарт ISO 6983, ~15-20% рынка CNC.
Максимальная совместимость с CAM-системами.

Ключевые особенности (по контракту MachineProfile + типичным диалектам FANUC 0i/31i):
- ISO 6983 G-code
- % program delimiter (начало и конец файла)
- Нумерация строк: N10, N20, N30...
- G04 P<секунды> или G04 X<секунды> (по dwell_syntax)
- G28 G91 Z0 / G28 X0 Y0 — machine home return в footer
- G21 G90 G40 G49 G17 <work_offset> — инициализация
- Комментарии в скобках: (текст)
- Завершение: M30 + %

Статус: DRAFT (экспериментальный). Не верифицирован на реальном станке.
Task 20 (физическая сертификация / air-cut / sacrificial) не завершена.
"""
from __future__ import annotations

from api.manufacturing.machine_profiles import (
    ControllerType,
    DwellSyntax,
    MachineProfile,
)
from api.manufacturing.postprocessors._renderer import GCodeRenderer
from api.manufacturing.postprocessors.base import (
    GCodeCommand,
    ProgramEnd,
    Rapid,
)

# ── FANUC-специфичный рендерер ──────────────────────────────────────


class FanucRenderer(GCodeRenderer):
    """Рендерер G-code для контроллеров FANUC (ISO 6983).

    Ключевые особенности:
    - Инициализация: % → O0001 → G21 G90 G40 G49 → G17 → <work_offset>
    - Нумерация строк (N10, N20...)
    - Dwell: G04 P<секунды> или G04 X<секунды> (profile.dwell_syntax)
    - Безопасный отвод: G28 G91 Z0 (machine home) в footer
    - Завершение: M05 → G28 G91 Z0 → G28 X0 Y0 → M30 → %
    - work_offset из MachineProfile уважается
    """

    def __init__(self, profile: MachineProfile) -> None:
        # Валидация контроллера: FANUC renderer поддерживает FANUC и SYNTEC (совместим)
        allowed = (ControllerType.FANUC, ControllerType.SYNTEC)
        if profile.controller not in allowed:
            raise ValueError(
                f"FanucRenderer не поддерживает контроллер {profile.controller.value}. "
                "Используйте fanuc или syntec."
            )

        # Валидация dwell: FANUC поддерживает только секунды (P или X)
        if profile.dwell_syntax == DwellSyntax.G4_P_MILLISECONDS:
            raise ValueError(
                "FANUC не поддерживает dwell в миллисекундах (G4_P_MILLISECONDS). "
                "Используйте G4_P_SECONDS или G4_X."
            )

        super().__init__(profile)
        self._line_number_increment = 10

    # ── Шапка программы ─────────────────────────────────────────────

    def _render_header(self) -> None:
        """FANUC шапка: % → Oxxxx → G21 G90 G40 G49 → G17 → work_offset."""
        # % — начало файла (FANUC-специфично)
        self._add_line("%", is_command=False)

        # Номер программы (4 цифры)
        self._add_line("O0001", is_command=False)

        self._add_line(self._comment("FANUC ISO Program"), is_command=False)
        self._add_line(self._comment(f"Profile: {self.profile.profile_id}"), is_command=False)

        # Инициализация: метрика, абсолютные координаты, отмена компенсаций
        self._add_line("G21 G90 G40 G49")

        # XY плоскость
        self._add_line("G17")

        # Рабочее смещение из профиля (G54 / G54.1 Px и т.п.)
        self._add_line(self.profile.work_offset)

    # ── Подвал программы ────────────────────────────────────────────

    def _render_footer(self) -> None:
        """FANUC завершение: M05 → G28 G91 Z0 → G28 X0 Y0 → M30 → %."""
        self._add_line("M05")

        # Возврат в machine home по Z (G28 G91 Z0 — инкрементальный)
        self._add_line("G28 G91 Z0")

        # Возврат в machine home по XY
        self._add_line("G28 X0 Y0")

        self._add_line("M30")

        # % — конец файла (FANUC-специфично)
        self._add_line("%", is_command=False)

    # ── Переопределение ProgramEnd ───────────────────────────────────

    def _render_program_end(self, cmd: ProgramEnd) -> None:
        """ProgramEnd — маркер конца в IR.

        Реальное завершение (M05, G28, M30, %) всегда в _render_footer
        для обеспечения корректной последовательности и отсутствия дубликатов M30.
        """
        # no-op: footer предоставляет M30 + % и безопасные возвраты
        pass

    # ── Нумерация строк ─────────────────────────────────────────────

    def _add_line(self, line: str, *, is_command: bool = True) -> None:
        """FANUC: нумерация строк для команд (кроме %, O)."""
        if (
            is_command
            and line.strip()
            and not line.startswith(("%", "O"))
        ):
            line = f"N{self._line_number} {line}"
            self._line_number += self._line_number_increment
        self._lines.append(line)

    # ── Безопасный отвод (home return) ──────────────────────────────

    def _render_rapid(self, cmd: Rapid) -> None:
        """G00 X... Y... Z... — FANUC использует G00 для быстрых перемещений.

        Примечание: machine home return (G28) реализуется в footer,
        не через IR команды Rapid.
        """
        super()._render_rapid(cmd)


# ── Фабрика рендереров ──────────────────────────────────────────────


def create_fanuc_renderer(profile: MachineProfile) -> FanucRenderer:
    """Создаёт FanucRenderer для профиля станка.

    Args:
        profile: Профиль станка (должен быть FANUC-совместимым).

    Returns:
        FanucRenderer: Готовый к использованию рендерер.

    Raises:
        ValueError: Если профиль не FANUC-совместим, DEPRECATED, или
            использует миллисекундный dwell.
        (work_offset из профиля рендерится в header.)
    """
    return FanucRenderer(profile)


def render_fanuc(
    commands: list[GCodeCommand],
    profile: MachineProfile,
) -> str:
    """Однострочная функция: IR команды → FANUC G-code текст.

    Args:
        commands: Список G-code IR команд.
        profile: Профиль станка.

    Returns:
        G-code текст для контроллера FANUC.
    """
    renderer = create_fanuc_renderer(profile)
    return renderer.render(commands)
