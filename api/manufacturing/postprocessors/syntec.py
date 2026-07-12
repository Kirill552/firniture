"""Постпроцессор Syntec — рендер G-code IR для контроллеров Syntec (KDT/WoodTec).

Syntec 60W/200W — FANUC-совместимый диалект, ~20-25% рынка CNC в мебельном
производстве (Россия). Используется на нестинг-центрах KDT, WoodTec.

Ключевые особенности (по контракту MachineProfile + типичным диалектам Syntec):
- G-code диалект совместим с FANUC 0i
- G04 P<секунды> (не миллисекунды; по dwell_syntax)
- Комментарии в скобках: (текст)
- Нумерация строк отключена
- Нет обязательного % в начале/конце программы
- Инициализация: G21 G90 G17 <work_offset> G40
- Безопасный отвод: G00 Z<safe_z>
- Завершение: M05 → G00 Z → G00 X0 Y0 → M30

Статус: DRAFT (экспериментальный). Не верифицирован на реальном станке.
Task 20 (физическая сертификация) не завершена.
Реализует синтаксис для профилей controller=SYNTEC (и совместимых).
"""
from __future__ import annotations

from api.manufacturing.machine_profiles import (
    ControllerType,
    MachineProfile,
)
from api.manufacturing.postprocessors._renderer import GCodeRenderer
from api.manufacturing.postprocessors.base import (
    GCodeCommand,
    ProgramEnd,
    Rapid,
)

# ── Syntec-специфичный рендерер ─────────────────────────────────────


class SyntecRenderer(GCodeRenderer):
    """Рендерер G-code для контроллеров Syntec (KDT/WoodTec).

    FANUC-совместимый диалект с характерными особенностями:
    - Инициализация: G21 G90 G17 <work_offset> G40
    - Без нумерации строк
    - Dwell: G04 P<секунды> (profile.dwell_syntax)
    - Безопасный отвод: G00 Z<safe_z>
    - Завершение: M30 (без %)
    - work_offset из MachineProfile уважается
    """

    def __init__(self, profile: MachineProfile) -> None:
        # Валидация контроллера: Syntec renderer поддерживает SYNTEC, FANUC (совместим), OTHER (эксп)
        allowed = (ControllerType.SYNTEC, ControllerType.FANUC, ControllerType.OTHER)
        if profile.controller not in allowed:
            raise ValueError(
                f"SyntecRenderer не поддерживает контроллер {profile.controller.value}. "
                "Используйте syntec, fanuc или other."
            )

        super().__init__(profile)

    # ── Шапка программы ─────────────────────────────────────────────

    def _render_header(self) -> None:
        """Syntec шапка: G21 G90 G17 <work_offset> G40, без %."""
        self._add_line(self._comment("Syntec CNC Program"), is_command=False)
        self._add_line(self._comment(f"Profile: {self.profile.profile_id}"), is_command=False)

        # Метрическая система, абсолютные координаты, XY плоскость
        self._add_line("G21")
        self._add_line("G90")
        self._add_line("G17")

        # Рабочее смещение из профиля (G54 и т.п.)
        self._add_line(self.profile.work_offset)

        # Отмена компенсации радиуса инструмента (Syntec-специфично)
        self._add_line("G40")

    # ── Подвал программы ────────────────────────────────────────────

    def _render_footer(self) -> None:
        """Syntec завершение: M05 → safe retract → M30."""
        self._add_line("M05")
        self._add_line(f"G00 Z{self.profile.safe_z:.1f}")
        self._add_line("G00 X0 Y0")
        self._add_line("M30")

    # ── Переопределение ProgramEnd ───────────────────────────────────

    def _render_program_end(self, cmd: ProgramEnd) -> None:
        """ProgramEnd — маркер конца в IR.

        Реальное завершение (M05, safe retract, M30) всегда в _render_footer
        для обеспечения корректной последовательности и отсутствия дубликатов M30.
        """
        # no-op: footer предоставляет M30
        pass

    # ── Безопасный отвод ────────────────────────────────────────────

    def _render_rapid(self, cmd: Rapid) -> None:
        """G00 X... Y... Z... — Syntec использует G00 для быстрых перемещений."""
        super()._render_rapid(cmd)


# ── Фабрика рендереров ──────────────────────────────────────────────


def create_syntec_renderer(profile: MachineProfile) -> SyntecRenderer:
    """Создаёт SyntecRenderer для профиля станка.

    Args:
        profile: Профиль станка (должен быть Syntec-совместимым).

    Returns:
        SyntecRenderer: Готовый к использованию рендерер.

    Raises:
        ValueError: Если профиль не Syntec-совместим или DEPRECATED.
        (work_offset из профиля рендерится в header.)
    """
    return SyntecRenderer(profile)


def render_syntec(
    commands: list[GCodeCommand],
    profile: MachineProfile,
) -> str:
    """Однострочная функция: IR команды → Syntec G-code текст.

    Args:
        commands: Список G-code IR команд.
        profile: Профиль станка.

    Returns:
        G-code текст для контроллера Syntec.
    """
    renderer = create_syntec_renderer(profile)
    return renderer.render(commands)
