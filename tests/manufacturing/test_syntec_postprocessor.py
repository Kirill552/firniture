"""TDD тесты для Syntec постпроцессора — IR → G-code рендер.

Проверяет SyntecRenderer и render_syntec():
- Шапка/подвал программы
- Диспетчеризация всех IR-команд
- Dwell форматирование (секунды)
- Нумерация строк (отсутствует для Syntec)
- % отсутствует
- G40 в инициализации
- Безопасный отвод (G00 Z)
- ProgramEnd + footer: ровно один M30
- work_offset из профиля
- DEPRECATED профиль → fail-closed
- Неизвестный тип команды → fail-closed
- Edge cases: пустой список команд, только header/footer

Статус: DRAFT, Task20 физ.сертификация не завершена.

Зависимости: api.manufacturing.postprocessors.syntec, base, machine_profiles.
"""
from __future__ import annotations

import pytest

from api.manufacturing.machine_profiles import (
    AxisLimits,
    CertificationStatus,
    ControllerType,
    DwellSyntax,
    LineEnding,
    MachineProfile,
    SpindleConfig,
    Units,
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
from api.manufacturing.postprocessors.syntec import (
    SyntecRenderer,
    create_syntec_renderer,
    render_syntec,
)

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def syntec_profile() -> MachineProfile:
    """Минимальный валидный профиль Syntec (controller=SYNTEC)."""
    return MachineProfile(
        profile_id="syntec-test",
        controller=ControllerType.SYNTEC,
        controller_version="60W-1.0",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top", "bottom", "front", "back"],
        spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
        axis_limits=AxisLimits(
            x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=-100, z_max=100
        ),
        safe_z=5.0,
        feed_min=100,
        feed_max=8000,
        rpm_min=6000,
        rpm_max=24000,
        dwell_syntax=DwellSyntax.G4_P_SECONDS,
        line_ending=LineEnding.LF,
        certification=CertificationStatus.DRAFT,
        postprocessor_version="0.1.0-experimental",
    )


@pytest.fixture
def deprecated_profile() -> MachineProfile:
    """DEPRECATED профиль — должен блокировать генерацию."""
    return MachineProfile(
        profile_id="syntec-deprecated",
        controller=ControllerType.SYNTEC,
        controller_version="60W-1.0",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top"],
        spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
        axis_limits=AxisLimits(
            x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=-100, z_max=100
        ),
        safe_z=5.0,
        feed_min=100,
        feed_max=8000,
        rpm_min=6000,
        rpm_max=24000,
        dwell_syntax=DwellSyntax.G4_P_SECONDS,
        line_ending=LineEnding.LF,
        certification=CertificationStatus.DEPRECATED,
        postprocessor_version="0.1.0",
    )


@pytest.fixture
def fanuc_controller_profile() -> MachineProfile:
    """Профиль с controller=FANUC — SyntecRenderer должен принять."""
    return MachineProfile(
        profile_id="syntec-on-fanuc",
        controller=ControllerType.FANUC,
        controller_version="0i-MF",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top"],
        spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
        axis_limits=AxisLimits(
            x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=-100, z_max=100
        ),
        safe_z=5.0,
        feed_min=100,
        feed_max=8000,
        rpm_min=6000,
        rpm_max=24000,
        dwell_syntax=DwellSyntax.G4_P_SECONDS,
        line_ending=LineEnding.LF,
        certification=CertificationStatus.DRAFT,
        postprocessor_version="0.1.0",
    )


@pytest.fixture
def unsupported_controller_profile() -> MachineProfile:
    """Профиль с unsupported controller — должен отвергаться."""
    return MachineProfile(
        profile_id="weihong-untested",
        controller=ControllerType.WEIHONG,
        controller_version="5.0",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top"],
        spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
        axis_limits=AxisLimits(
            x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=-100, z_max=100
        ),
        safe_z=5.0,
        feed_min=100,
        feed_max=8000,
        rpm_min=6000,
        rpm_max=24000,
        dwell_syntax=DwellSyntax.G4_P_MILLISECONDS,
        line_ending=LineEnding.LF,
        certification=CertificationStatus.DRAFT,
        postprocessor_version="0.1.0",
    )


# ── Тесты: валидация профиля ─────────────────────────────────────────


class TestSyntecProfileValidation:
    """Валидация профиля при создании рендерера."""

    def test_syntec_controller_accepted(self, syntec_profile: MachineProfile) -> None:
        """controller=SYNTEC — SyntecRenderer создаётся."""
        renderer = SyntecRenderer(syntec_profile)
        assert renderer.profile.profile_id == "syntec-test"

    def test_fanuc_controller_accepted(self, fanuc_controller_profile: MachineProfile) -> None:
        """controller=FANUC — SyntecRenderer принимает (FANUC-совместимый)."""
        renderer = SyntecRenderer(fanuc_controller_profile)
        assert renderer.profile.profile_id == "syntec-on-fanuc"

    def test_other_controller_accepted(self) -> None:
        """controller=OTHER — SyntecRenderer принимает (экспериментальный)."""
        profile = MachineProfile(
            profile_id="other-test",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(
                x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=-100, z_max=100
            ),
            safe_z=5.0,
            feed_min=100,
            feed_max=8000,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="0.1.0",
        )
        renderer = SyntecRenderer(profile)
        assert renderer.profile.profile_id == "other-test"

    def test_weihong_controller_rejected(self, unsupported_controller_profile: MachineProfile) -> None:
        """controller=WEIHONG — SyntecRenderer отвергает."""
        with pytest.raises(ValueError, match="не поддерживает контроллер"):
            SyntecRenderer(unsupported_controller_profile)

    def test_deprecated_profile_rejected(self, deprecated_profile: MachineProfile) -> None:
        """DEPRECATED профиль — fail-closed."""
        with pytest.raises(ValueError, match="DEPRECATED"):
            SyntecRenderer(deprecated_profile)


# ── Тесты: шапка программы ───────────────────────────────────────────


class TestSyntecHeader:
    """Шапка программы Syntec: G21 G90 G17 G40, без %."""

    def test_no_percent_header(self, syntec_profile: MachineProfile) -> None:
        """Syntec НЕ использует % в шапке (в отличие от FANUC)."""
        gcode = render_syntec([], syntec_profile)
        assert "%" not in gcode

    def test_metric_init(self, syntec_profile: MachineProfile) -> None:
        """G21 — метрическая система."""
        gcode = render_syntec([], syntec_profile)
        assert "G21" in gcode

    def test_absolute_coords(self, syntec_profile: MachineProfile) -> None:
        """G90 — абсолютные координаты."""
        gcode = render_syntec([], syntec_profile)
        assert "G90" in gcode

    def test_xy_plane(self, syntec_profile: MachineProfile) -> None:
        """G17 — XY плоскость."""
        gcode = render_syntec([], syntec_profile)
        assert "G17" in gcode

    def test_g40_cancel_radius_compensation(self, syntec_profile: MachineProfile) -> None:
        """G40 — отмена компенсации радиуса (Syntec-специфично)."""
        gcode = render_syntec([], syntec_profile)
        assert "G40" in gcode

    def test_work_offset_emitted(self, syntec_profile: MachineProfile) -> None:
        """work_offset из профиля присутствует в шапке (controller-specific)."""
        gcode = render_syntec([], syntec_profile)
        assert "G54" in gcode

    def test_header_contains_comment(self, syntec_profile: MachineProfile) -> None:
        """Шапка содержит комментарий с профилем."""
        gcode = render_syntec([], syntec_profile)
        assert "(Syntec CNC Program)" in gcode
        assert "(Profile: syntec-test)" in gcode


# ── Тесты: подвал программы ──────────────────────────────────────────


class TestSyntecFooter:
    """Подвал программы Syntec: M05 → G00 Z → G00 X0 Y0 → M30."""

    def test_m30_program_end(self, syntec_profile: MachineProfile) -> None:
        """M30 — конец программы."""
        gcode = render_syntec([], syntec_profile)
        assert "M30" in gcode

    def test_m05_spindle_off(self, syntec_profile: MachineProfile) -> None:
        """M05 — выключение шпинделя в footer."""
        gcode = render_syntec([], syntec_profile)
        assert "M05" in gcode

    def test_safe_retract_z(self, syntec_profile: MachineProfile) -> None:
        """G00 Z5.0 — безопасный отвод (Syntec: G00, не G28)."""
        gcode = render_syntec([], syntec_profile)
        assert "G00 Z5.0" in gcode

    def test_home_xy(self, syntec_profile: MachineProfile) -> None:
        """G00 X0 Y0 — возврат в начало координат."""
        gcode = render_syntec([], syntec_profile)
        assert "G00 X0 Y0" in gcode

    def test_no_percent_footer(self, syntec_profile: MachineProfile) -> None:
        """Syntec НЕ использует % в footer."""
        gcode = render_syntec([], syntec_profile)
        # footer: M30 — последняя команда, не %
        lines = [line for line in gcode.strip().split("\n") if line.strip()]
        assert lines[-1] == "M30"


# ── Тесты: нумерация строк ───────────────────────────────────────────


class TestSyntecLineNumbers:
    """Syntec не использует нумерацию строк."""

    def test_no_line_numbers(self, syntec_profile: MachineProfile) -> None:
        """G-code команды без N- префикса."""
        commands: list[GCodeCommand] = [
            Rapid(x=10.0, y=20.0, z=5.0),
            Rapid(x=100.0, y=200.0),
        ]
        gcode = render_syntec(commands, syntec_profile)
        # Нет строк вида "N10 G00"
        for line in gcode.split("\n"):
            stripped = line.strip()
            if stripped and stripped.startswith("G"):
                assert not stripped.startswith("N"), (
                    f"Syntec не должен использовать нумерацию строк: {stripped}"
                )


# ── Тесты: IR-команды ────────────────────────────────────────────────


class TestSyntecRapid:
    """G00 — быстрое перемещение."""

    def test_rapid_xyz(self, syntec_profile: MachineProfile) -> None:
        """G00 X Y Z."""
        commands = [Rapid(x=10.0, y=20.0, z=5.0)]
        gcode = render_syntec(commands, syntec_profile)
        assert "G00 X10.000 Y20.000 Z5.000" in gcode

    def test_rapid_xy_only(self, syntec_profile: MachineProfile) -> None:
        """G00 X Y (без Z)."""
        commands = [Rapid(x=100.0, y=200.0)]
        gcode = render_syntec(commands, syntec_profile)
        assert "G00 X100.000 Y200.000" in gcode
        assert "Z" not in gcode.split("G00 X100.000 Y200.000")[1].split("\n")[0]

    def test_rapid_z_only(self, syntec_profile: MachineProfile) -> None:
        """G00 Z (подъём/опускание)."""
        commands = [Rapid(z=50.0)]
        gcode = render_syntec(commands, syntec_profile)
        assert "G00 Z50.000" in gcode


class TestSyntecLinear:
    """G01 — линейное перемещение с подачей."""

    def test_linear_xyz_feed(self, syntec_profile: MachineProfile) -> None:
        """G01 X Y Z F."""
        commands = [Linear(x=50.0, y=100.0, z=-3.0, feed=600)]
        gcode = render_syntec(commands, syntec_profile)
        assert "G01 X50.000 Y100.000 Z-3.000 F600" in gcode

    def test_linear_xy_feed(self, syntec_profile: MachineProfile) -> None:
        """G01 X Y F (без Z)."""
        commands = [Linear(x=50.0, y=100.0, feed=800)]
        gcode = render_syntec(commands, syntec_profile)
        assert "G01 X50.000 Y100.000 F800" in gcode


class TestSyntecToolChange:
    """M06 Txx — смена инструмента."""

    def test_tool_change(self, syntec_profile: MachineProfile) -> None:
        """M06 T01."""
        commands = [ToolChange(t_number=1)]
        gcode = render_syntec(commands, syntec_profile)
        assert "M06 T01" in gcode

    def test_tool_change_double_digit(self, syntec_profile: MachineProfile) -> None:
        """M06 T12 — двузначный номер."""
        commands = [ToolChange(t_number=12)]
        gcode = render_syntec(commands, syntec_profile)
        assert "M06 T12" in gcode


class TestSyntecSpindle:
    """Sxxx M03/M04 — управление шпинделем."""

    def test_spindle_on_cw(self, syntec_profile: MachineProfile) -> None:
        """S18000 M03 — шпиндель по часовой."""
        commands = [SpindleOn(rpm=18000, clockwise=True)]
        gcode = render_syntec(commands, syntec_profile)
        assert "S18000 M03" in gcode

    def test_spindle_on_ccw(self, syntec_profile: MachineProfile) -> None:
        """S12000 M04 — шпиндель против часовой."""
        commands = [SpindleOn(rpm=12000, clockwise=False)]
        gcode = render_syntec(commands, syntec_profile)
        assert "S12000 M04" in gcode

    def test_spindle_off(self, syntec_profile: MachineProfile) -> None:
        """M05 — выключение шпинделя."""
        commands = [SpindleOff()]
        gcode = render_syntec(commands, syntec_profile)
        assert "M05" in gcode


# ── Тесты: dwell (выдержка) ──────────────────────────────────────────


class TestSyntecDwell:
    """Dwell форматирование: G04 P<секунды> для Syntec."""

    def test_dwell_in_drill_cycle(self, syntec_profile: MachineProfile) -> None:
        """DrillCycle с dwell → P<секунды> (не миллисекунды)."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-12.0, retract=2.0,
                feed=300, dwell=1.5,
            )
        ]
        gcode = render_syntec(commands, syntec_profile)
        assert "P1.5" in gcode

    def test_dwell_zero_not_rendered(self, syntec_profile: MachineProfile) -> None:
        """DrillCycle с dwell=0 → без dwell параметра."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-5.0, retract=2.0,
                feed=300, dwell=0.0,
            )
        ]
        gcode = render_syntec(commands, syntec_profile)
        # dwell=0 → не должен добавлять P параметр
        assert "P0.0" not in gcode


# ── Тесты: DrillCycle ────────────────────────────────────────────────


class TestSyntecDrillCycle:
    """G81/G82/G83 — циклы сверления."""

    def test_g81_simple_drill(self, syntec_profile: MachineProfile) -> None:
        """G81 — простое сверление (без peck, без dwell)."""
        commands = [
            DrillCycle(x=100.0, y=200.0, z=-8.0, retract=2.0, feed=300)
        ]
        gcode = render_syntec(commands, syntec_profile)
        assert "G81" in gcode
        assert "X100.000" in gcode
        assert "Y200.000" in gcode
        assert "Z-8.000" in gcode
        assert "R2.0" in gcode

    def test_g82_drill_with_dwell(self, syntec_profile: MachineProfile) -> None:
        """G82 — сверление с выдержкой на дне."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-12.0, retract=2.0,
                feed=300, dwell=2.0,
            )
        ]
        gcode = render_syntec(commands, syntec_profile)
        assert "G82" in gcode
        assert "P2.0" in gcode

    def test_g83_peck_drill(self, syntec_profile: MachineProfile) -> None:
        """G83 — глубокое сверление с peck."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-20.0, retract=2.0,
                feed=300, peck=5.0,
            )
        ]
        gcode = render_syntec(commands, syntec_profile)
        assert "G83" in gcode
        assert "Q5.0" in gcode

    def test_g83_peck_overrides_dwell(self, syntec_profile: MachineProfile) -> None:
        """G83 приоритетнее G82: если есть peck, используется G83."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-20.0, retract=2.0,
                feed=300, peck=5.0, dwell=1.0,
            )
        ]
        gcode = render_syntec(commands, syntec_profile)
        assert "G83" in gcode
        assert "G82" not in gcode


# ── Тесты: CancelCycle ───────────────────────────────────────────────


class TestSyntecCancelCycle:
    """G80 — отмена цикла."""

    def test_cancel_cycle(self, syntec_profile: MachineProfile) -> None:
        """G80 — отмена активного цикла."""
        commands = [CancelCycle()]
        gcode = render_syntec(commands, syntec_profile)
        assert "G80" in gcode


# ── Тесты: пустой список команд ──────────────────────────────────────


class TestSyntecEmptyCommands:
    """Пустой список команд — только header + footer."""

    def test_empty_commands(self, syntec_profile: MachineProfile) -> None:
        """Пустой список → header + footer (M30)."""
        gcode = render_syntec([], syntec_profile)
        # Должен содержать минимум: G21, G90, G17, G40, M05, M30
        assert "G21" in gcode
        assert "M30" in gcode

    def test_program_end_no_dup_m30(self, syntec_profile: MachineProfile) -> None:
        """ProgramEnd + footer → ровно один M30 (не дублируется)."""
        gcode = render_syntec([ProgramEnd()], syntec_profile)
        m30_count = sum(1 for line in gcode.splitlines() if "M30" in line)
        assert m30_count == 1, f"Ожидался 1 M30, найдено {m30_count}:\n{gcode}"


# ── Тесты: полная последовательность ─────────────────────────────────


class TestSyntecFullSequence:
    """Полная последовательность: header → tool → spindle → cut → footer."""

    def test_full_program(self, syntec_profile: MachineProfile) -> None:
        """Полная программа: tool change → spindle → rapid → linear → stop → end."""
        commands: list[GCodeCommand] = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=0.0, y=0.0, z=5.0),
            Rapid(x=0.0, y=0.0),
            Linear(x=100.0, y=0.0, z=-3.0, feed=600),
            Linear(x=100.0, y=100.0, z=-3.0, feed=600),
            SpindleOff(),
            ProgramEnd(),
        ]
        gcode = render_syntec(commands, syntec_profile)
        # Шапка
        assert "G21" in gcode
        assert "G90" in gcode
        assert "G40" in gcode

        # Команды
        assert "M06 T01" in gcode
        assert "S18000 M03" in gcode
        assert "Z5.000" in gcode
        assert "G00 X0.000 Y0.000" in gcode
        assert "G01 X100.000 Y0.000 Z-3.000 F600" in gcode
        assert "G01 X100.000 Y100.000 Z-3.000 F600" in gcode
        assert "M05" in gcode
        assert "M30" in gcode

        # Footer
        assert "G00 Z5.0" in gcode
        assert "G00 X0 Y0" in gcode


# ── Тесты: неизвестный тип команды ───────────────────────────────────


class TestSyntecUnknownCommand:
    """Неизвестный тип IR-команды → fail-closed."""

    def test_unknown_command_type(self, syntec_profile: MachineProfile) -> None:
        """Неизвестный тип команды → ValueError."""
        # Создаём "мок" команды через наследование
        class FakeCommand(GCodeCommand):
            """Фиктивная команда для теста."""
            pass

        with pytest.raises(ValueError, match="Неизвестный тип IR-команды"):
            renderer = SyntecRenderer(syntec_profile)
            renderer.render([FakeCommand()])  # type: ignore[arg-type]


# ── Тесты: factory ───────────────────────────────────────────────────


class TestSyntecFactory:
    """Фабричные функции."""

    def test_create_syntec_renderer(self, syntec_profile: MachineProfile) -> None:
        """create_syntec_renderer → SyntecRenderer."""
        renderer = create_syntec_renderer(syntec_profile)
        assert isinstance(renderer, SyntecRenderer)

    def test_render_syntec_shortcut(self, syntec_profile: MachineProfile) -> None:
        """render_syntec → G-code текст."""
        gcode = render_syntec([ProgramEnd()], syntec_profile)
        assert isinstance(gcode, str)
        assert "M30" in gcode


# ── Тесты: line endings ──────────────────────────────────────────────


class TestSyntecLineEnding:
    """Разные стили окончания строк."""

    def test_lf_line_ending(self, syntec_profile: MachineProfile) -> None:
        """LF: строки разделены \\n."""
        gcode = render_syntec([ProgramEnd()], syntec_profile)
        assert "\r\n" not in gcode
        assert "\n" in gcode

    def test_crlf_line_ending(self) -> None:
        """CRLF: строки разделены \\r\\n."""
        profile = MachineProfile(
            profile_id="syntec-crlf",
            controller=ControllerType.SYNTEC,
            controller_version="60W-1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(
                x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=-100, z_max=100
            ),
            safe_z=5.0,
            feed_min=100,
            feed_max=8000,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.CRLF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="0.1.0",
        )
        gcode = render_syntec([ProgramEnd()], profile)
        assert "\r\n" in gcode
