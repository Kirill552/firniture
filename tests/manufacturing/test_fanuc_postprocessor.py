"""TDD тесты для FANUC постпроцессора — IR → G-code рендер.

Проверяет FanucRenderer и render_fanuc():
- Шапка/подвал программы (% delimiter, O0001, G28 G91 Z0)
- Диспетчеризация всех IR-команд
- Dwell форматирование (секунды, G4 P или G4 X)
- Нумерация строк (N10, N20...)
- ProgramEnd + footer: ровно один M30, корректный порядок
- work_offset из профиля
- DEPRECATED профиль → fail-closed
- Milliseconds dwell → fail-closed
- Неизвестный тип команды → fail-closed
- Edge cases: пустой список команд, только header/footer

Статус: DRAFT, Task20 физ.сертификация не завершена.

Зависимости: api.manufacturing.postprocessors.fanuc, base, machine_profiles.
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
from api.manufacturing.postprocessors.fanuc import (
    FanucRenderer,
    create_fanuc_renderer,
    render_fanuc,
)

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def fanuc_profile() -> MachineProfile:
    """Минимальный валидный профиль FANUC (controller=FANUC)."""
    return MachineProfile(
        profile_id="fanuc-test",
        controller=ControllerType.FANUC,
        controller_version="0i-MF-1.0",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top", "bottom", "front", "back"],
        spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
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
def fanuc_g4x_profile() -> MachineProfile:
    """Профиль FANUC с dwell через G4 X (секунды)."""
    return MachineProfile(
        profile_id="fanuc-g4x",
        controller=ControllerType.FANUC,
        controller_version="31i-B",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top"],
        spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
        axis_limits=AxisLimits(
            x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=-100, z_max=100
        ),
        safe_z=5.0,
        feed_min=100,
        feed_max=8000,
        rpm_min=6000,
        rpm_max=24000,
        dwell_syntax=DwellSyntax.G4_X,
        line_ending=LineEnding.LF,
        certification=CertificationStatus.DRAFT,
        postprocessor_version="0.1.0",
    )


@pytest.fixture
def deprecated_profile() -> MachineProfile:
    """DEPRECATED профиль — должен блокировать генерацию."""
    return MachineProfile(
        profile_id="fanuc-deprecated",
        controller=ControllerType.FANUC,
        controller_version="0i-MF",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top"],
        spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
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
def ms_dwell_profile() -> MachineProfile:
    """Профиль с миллисекундным dwell — FANUC не поддерживает."""
    return MachineProfile(
        profile_id="fanuc-ms-dwell",
        controller=ControllerType.FANUC,
        controller_version="0i-MF",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top"],
        spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
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


@pytest.fixture
def unsupported_controller_profile() -> MachineProfile:
    """Профиль с unsupported controller — должен отвергаться."""
    return MachineProfile(
        profile_id="dsp-untested",
        controller=ControllerType.DSP,
        controller_version="A11",
        units=Units.MM,
        work_offset="G54",
        supported_faces=["top"],
        spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
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


# ── Тесты: валидация профиля ─────────────────────────────────────────


class TestFanucProfileValidation:
    """Валидация профиля при создании рендерера."""

    def test_fanuc_controller_accepted(self, fanuc_profile: MachineProfile) -> None:
        """controller=FANUC — FanucRenderer создаётся."""
        renderer = FanucRenderer(fanuc_profile)
        assert renderer.profile.profile_id == "fanuc-test"

    def test_syntec_controller_accepted(self) -> None:
        """controller=SYNTEC — FanucRenderer принимает (FANUC-совместимый)."""
        profile = MachineProfile(
            profile_id="fanuc-syntec",
            controller=ControllerType.SYNTEC,
            controller_version="60W",
            units=Units.MM,
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
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
        renderer = FanucRenderer(profile)
        assert renderer.profile.profile_id == "fanuc-syntec"

    def test_dsp_controller_rejected(self, unsupported_controller_profile: MachineProfile) -> None:
        """controller=DSP — FanucRenderer отвергает."""
        with pytest.raises(ValueError, match="не поддерживает контроллер"):
            FanucRenderer(unsupported_controller_profile)

    def test_deprecated_profile_rejected(self, deprecated_profile: MachineProfile) -> None:
        """DEPRECATED профиль — fail-closed (базовый класс)."""
        with pytest.raises(ValueError, match="DEPRECATED"):
            FanucRenderer(deprecated_profile)

    def test_milliseconds_dwell_rejected(self, ms_dwell_profile: MachineProfile) -> None:
        """FANUC не поддерживает dwell в миллисекундах — fail-closed."""
        with pytest.raises(ValueError, match="миллисекундах"):
            FanucRenderer(ms_dwell_profile)


# ── Тесты: шапка программы ───────────────────────────────────────────


class TestFanucHeader:
    """Шапка программы FANUC: % → O0001 → G21 G90 G40 G49 → G17."""

    def test_percent_header(self, fanuc_profile: MachineProfile) -> None:
        """FANUC использует % в начале файла."""
        gcode = render_fanuc([], fanuc_profile)
        lines = [line.strip() for line in gcode.split("\n") if line.strip()]
        assert lines[0] == "%"

    def test_program_number(self, fanuc_profile: MachineProfile) -> None:
        """O0001 — номер программы."""
        gcode = render_fanuc([], fanuc_profile)
        assert "O0001" in gcode

    def test_metric_init(self, fanuc_profile: MachineProfile) -> None:
        """G21 — метрическая система."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G21" in gcode

    def test_absolute_coords(self, fanuc_profile: MachineProfile) -> None:
        """G90 — абсолютные координаты."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G90" in gcode

    def test_g40_cancel_radius_compensation(self, fanuc_profile: MachineProfile) -> None:
        """G40 — отмена компенсации радиуса."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G40" in gcode

    def test_g49_cancel_tool_length_offset(self, fanuc_profile: MachineProfile) -> None:
        """G49 — отмена компенсации длины инструмента (FANUC-специфично)."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G49" in gcode

    def test_g17_xy_plane(self, fanuc_profile: MachineProfile) -> None:
        """G17 — XY плоскость."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G17" in gcode

    def test_work_offset_emitted(self, fanuc_profile: MachineProfile) -> None:
        """work_offset из профиля присутствует в шапке (controller-specific)."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G54" in gcode  # default в fixture

    def test_header_contains_comment(self, fanuc_profile: MachineProfile) -> None:
        """Шапка содержит комментарии."""
        gcode = render_fanuc([], fanuc_profile)
        assert "(FANUC ISO Program)" in gcode
        assert "(Profile: fanuc-test)" in gcode

    def test_init_line_combined(self, fanuc_profile: MachineProfile) -> None:
        """G21 G90 G40 G49 на одной строке (FANUC-стиль)."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G21 G90 G40 G49" in gcode


# ── Тесты: подвал программы ──────────────────────────────────────────


class TestFanucFooter:
    """Подвал программы FANUC: M05 → G28 G91 Z0 → G28 X0 Y0 → M30 → %."""

    def test_percent_footer(self, fanuc_profile: MachineProfile) -> None:
        """FANUC использует % в конце файла."""
        gcode = render_fanuc([], fanuc_profile)
        lines = [line.strip() for line in gcode.split("\n") if line.strip()]
        assert lines[-1] == "%"

    def test_m30_before_percent(self, fanuc_profile: MachineProfile) -> None:
        """M30 перед %."""
        gcode = render_fanuc([], fanuc_profile)
        lines = [line.strip() for line in gcode.split("\n") if line.strip()]
        assert lines[-2].split()[-1] == "M30"  # may be "Nxx M30" due to numbering

    def test_m05_spindle_off(self, fanuc_profile: MachineProfile) -> None:
        """M05 — выключение шпинделя в footer."""
        gcode = render_fanuc([], fanuc_profile)
        assert "M05" in gcode

    def test_g28_z_home_return(self, fanuc_profile: MachineProfile) -> None:
        """G28 G91 Z0 — возврат machine home по Z (FANUC-специфично)."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G28 G91 Z0" in gcode

    def test_g28_xy_home_return(self, fanuc_profile: MachineProfile) -> None:
        """G28 X0 Y0 — возврат machine home по XY."""
        gcode = render_fanuc([], fanuc_profile)
        assert "G28 X0 Y0" in gcode

    def test_footer_order(self, fanuc_profile: MachineProfile) -> None:
        """Порядок footer: M05 → G28 Z → G28 XY → M30 → %."""
        gcode = render_fanuc([], fanuc_profile)
        lines = [line.strip() for line in gcode.split("\n") if line.strip()]
        # Найти индексы команд footer
        footer_commands = ["M05", "G28 G91 Z0", "G28 X0 Y0", "M30", "%"]
        last_indices = [max(i for i, line in enumerate(lines) if cmd in line) for cmd in footer_commands]
        # Проверить порядок: каждый предыдущий индекс < следующего
        for i in range(len(last_indices) - 1):
            assert last_indices[i] < last_indices[i + 1], (
                f"Footer order violated: {footer_commands[i]} at {last_indices[i]} "
                f"should come before {footer_commands[i+1]} at {last_indices[i+1]}"
            )


# ── Тесты: нумерация строк ───────────────────────────────────────────


class TestFanucLineNumbers:
    """FANUC использует нумерацию строк N10, N20..."""

    def test_commands_have_line_numbers(self, fanuc_profile: MachineProfile) -> None:
        """G-code команды имеют N- префикс."""
        commands: list[GCodeCommand] = [
            Rapid(x=10.0, y=20.0, z=5.0),
            Rapid(x=100.0, y=200.0),
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        gcode_lines = [line.strip() for line in gcode.split("\n") if line.strip()]
        # Команды Rapid должны иметь N- префикс
        rapid_lines = [line for line in gcode_lines if line.startswith("N") and "G00" in line]
        assert len(rapid_lines) >= 2

    def test_line_number_increment(self, fanuc_profile: MachineProfile) -> None:
        """Номера строк с шагом 10: N10, N20, N30..."""
        commands: list[GCodeCommand] = [
            Rapid(x=10.0, y=20.0, z=5.0),
            Rapid(x=100.0, y=200.0),
            SpindleOn(rpm=18000),
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "N10" in gcode
        assert "N20" in gcode
        assert "N30" in gcode

    def test_no_line_numbers_for_percent(self, fanuc_profile: MachineProfile) -> None:
        """% не нумеруется."""
        gcode = render_fanuc([], fanuc_profile)
        lines = [line.strip() for line in gcode.split("\n") if line.strip()]
        assert lines[0] == "%"  # Без N- префикса

    def test_no_line_numbers_for_program_number(self, fanuc_profile: MachineProfile) -> None:
        """O0001 не нумеруется."""
        gcode = render_fanuc([], fanuc_profile)
        # O0001 должен быть без N- префикса
        assert "O0001" in gcode
        o_lines = [line for line in gcode.split("\n") if "O0001" in line]
        for line in o_lines:
            assert not line.strip().startswith("N"), (
                f"O0001 не должен нумероваться: {line}"
            )


# ── Тесты: IR-команды ────────────────────────────────────────────────


class TestFanucRapid:
    """G00 — быстрое перемещение."""

    def test_rapid_xyz(self, fanuc_profile: MachineProfile) -> None:
        """G00 X Y Z."""
        commands = [Rapid(x=10.0, y=20.0, z=5.0)]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "G00 X10.000 Y20.000 Z5.000" in gcode

    def test_rapid_with_line_number(self, fanuc_profile: MachineProfile) -> None:
        """G00 имеет номер строки."""
        commands = [Rapid(x=10.0, y=20.0)]
        gcode = render_fanuc(commands, fanuc_profile)
        rapid_lines = [line for line in gcode.split("\n") if "G00 X10.000" in line]
        assert any(line.strip().startswith("N") for line in rapid_lines)


class TestFanucLinear:
    """G01 — линейное перемещение с подачей."""

    def test_linear_xyz_feed(self, fanuc_profile: MachineProfile) -> None:
        """G01 X Y Z F."""
        commands = [Linear(x=50.0, y=100.0, z=-3.0, feed=600)]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "G01 X50.000 Y100.000 Z-3.000 F600" in gcode


class TestFanucToolChange:
    """M06 Txx — смена инструмента."""

    def test_tool_change(self, fanuc_profile: MachineProfile) -> None:
        """M06 T01."""
        commands = [ToolChange(t_number=1)]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "M06 T01" in gcode

    def test_tool_change_with_line_number(self, fanuc_profile: MachineProfile) -> None:
        """M06 T01 с номером строки."""
        commands = [ToolChange(t_number=1)]
        gcode = render_fanuc(commands, fanuc_profile)
        tc_lines = [line for line in gcode.split("\n") if "M06 T01" in line]
        assert any(line.strip().startswith("N") for line in tc_lines)


class TestFanucSpindle:
    """Sxxx M03/M04 — управление шпинделем."""

    def test_spindle_on_cw(self, fanuc_profile: MachineProfile) -> None:
        """S18000 M03 — шпиндель по часовой."""
        commands = [SpindleOn(rpm=18000, clockwise=True)]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "S18000 M03" in gcode

    def test_spindle_on_ccw(self, fanuc_profile: MachineProfile) -> None:
        """S12000 M04 — шпиндель против часовой."""
        commands = [SpindleOn(rpm=12000, clockwise=False)]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "S12000 M04" in gcode

    def test_spindle_off(self, fanuc_profile: MachineProfile) -> None:
        """M05 — выключение шпинделя."""
        commands = [SpindleOff()]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "M05" in gcode


# ── Тесты: dwell (выдержка) ──────────────────────────────────────────


class TestFanucDwell:
    """Dwell форматирование: G04 P<секунды> для FANUC."""

    def test_dwell_p_seconds(self, fanuc_profile: MachineProfile) -> None:
        """G4 P — dwell в секундах (FANUC)."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-12.0, retract=2.0,
                feed=300, dwell=1.5,
            )
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "P1.5" in gcode

    def test_dwell_g4x_seconds(self, fanuc_g4x_profile: MachineProfile) -> None:
        """G4 X — dwell в секундах через X параметр."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-12.0, retract=2.0,
                feed=300, dwell=2.0,
            )
        ]
        gcode = render_fanuc(commands, fanuc_g4x_profile)
        assert "X2.0" in gcode

    def test_dwell_zero_not_rendered(self, fanuc_profile: MachineProfile) -> None:
        """DrillCycle с dwell=0 → без dwell параметра."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-5.0, retract=2.0,
                feed=300, dwell=0.0,
            )
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "P0.0" not in gcode


# ── Тесты: DrillCycle ────────────────────────────────────────────────


class TestFanucDrillCycle:
    """G81/G82/G83 — циклы сверления."""

    def test_g81_simple_drill(self, fanuc_profile: MachineProfile) -> None:
        """G81 — простое сверление."""
        commands = [
            DrillCycle(x=100.0, y=200.0, z=-8.0, retract=2.0, feed=300)
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "G81" in gcode
        assert "X100.000" in gcode
        assert "Y200.000" in gcode
        assert "Z-8.000" in gcode
        assert "R2.0" in gcode

    def test_g82_drill_with_dwell(self, fanuc_profile: MachineProfile) -> None:
        """G82 — сверление с выдержкой на дне."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-12.0, retract=2.0,
                feed=300, dwell=2.0,
            )
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "G82" in gcode
        assert "P2.0" in gcode

    def test_g83_peck_drill(self, fanuc_profile: MachineProfile) -> None:
        """G83 — глубокое сверление с peck."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-20.0, retract=2.0,
                feed=300, peck=5.0,
            )
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "G83" in gcode
        assert "Q5.0" in gcode

    def test_g83_peck_overrides_dwell(self, fanuc_profile: MachineProfile) -> None:
        """G83 приоритетнее G82: peck + dwell → G83 (peck dominant)."""
        commands = [
            DrillCycle(
                x=100.0, y=200.0, z=-20.0, retract=2.0,
                feed=300, peck=5.0, dwell=1.0,
            )
        ]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "G83" in gcode
        assert "G82" not in gcode


# ── Тесты: CancelCycle ───────────────────────────────────────────────


class TestFanucCancelCycle:
    """G80 — отмена цикла."""

    def test_cancel_cycle(self, fanuc_profile: MachineProfile) -> None:
        """G80 — отмена активного цикла."""
        commands = [CancelCycle()]
        gcode = render_fanuc(commands, fanuc_profile)
        assert "G80" in gcode


# ── Тесты: пустой список команд ──────────────────────────────────────


class TestFanucEmptyCommands:
    """Пустой список команд — только header + footer."""

    def test_empty_commands(self, fanuc_profile: MachineProfile) -> None:
        """Пустой список → header + footer (M30 + %)."""
        gcode = render_fanuc([], fanuc_profile)
        assert "%" in gcode
        assert "M30" in gcode
        assert "G21" in gcode

    def test_program_end_no_dup_m30(self, fanuc_profile: MachineProfile) -> None:
        """ProgramEnd + footer → ровно один M30 (не дублируется)."""
        gcode = render_fanuc([ProgramEnd()], fanuc_profile)
        m30_count = sum(1 for line in gcode.splitlines() if "M30" in line)
        assert m30_count == 1, f"Ожидался 1 M30, найдено {m30_count}:\n{gcode}"


# ── Тесты: полная последовательность ─────────────────────────────────


class TestFanucFullSequence:
    """Полная последовательность: % → header → tool → spindle → cut → footer → %."""

    def test_full_program(self, fanuc_profile: MachineProfile) -> None:
        """Полная программа: % → O0001 → G21... → M06 → M03 → cuts → M05 → G28 → M30 → %."""
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
        gcode = render_fanuc(commands, fanuc_profile)
        lines = [line.strip() for line in gcode.split("\n") if line.strip()]

        # Шапка: % и O0001
        assert lines[0] == "%"
        assert "O0001" in lines[1]

        # Инициализация
        assert "G21 G90 G40 G49" in gcode
        assert "G17" in gcode

        # Команды с номерами строк
        assert "N" in gcode  # Есть нумерация

        # Tool change
        assert "M06 T01" in gcode
        assert "S18000 M03" in gcode

        # Movements (Z included; N- prefix for FANUC)
        assert "Z5.000" in gcode
        assert "G01 X100.000 Y0.000 Z-3.000 F600" in gcode
        assert "G01 X100.000 Y100.000 Z-3.000 F600" in gcode

        # Footer: M05 → G28 G91 Z0 → G28 X0 Y0 → M30 → %
        assert "M05" in gcode
        assert "G28 G91 Z0" in gcode
        assert "G28 X0 Y0" in gcode
        assert "M30" in gcode
        assert lines[-1] == "%"


# ── Тесты: неизвестный тип команды ───────────────────────────────────


class TestFanucUnknownCommand:
    """Неизвестный тип IR-команды → fail-closed."""

    def test_unknown_command_type(self, fanuc_profile: MachineProfile) -> None:
        """Неизвестный тип команды → ValueError."""
        class FakeCommand(GCodeCommand):
            """Фиктивная команда для теста."""
            pass

        with pytest.raises(ValueError, match="Неизвестный тип IR-команды"):
            renderer = FanucRenderer(fanuc_profile)
            renderer.render([FakeCommand()])  # type: ignore[arg-type]


# ── Тесты: factory ───────────────────────────────────────────────────


class TestFanucFactory:
    """Фабричные функции."""

    def test_create_fanuc_renderer(self, fanuc_profile: MachineProfile) -> None:
        """create_fanuc_renderer → FanucRenderer."""
        renderer = create_fanuc_renderer(fanuc_profile)
        assert isinstance(renderer, FanucRenderer)

    def test_render_fanuc_shortcut(self, fanuc_profile: MachineProfile) -> None:
        """render_fanuc → G-code текст."""
        gcode = render_fanuc([ProgramEnd()], fanuc_profile)
        assert isinstance(gcode, str)
        assert "M30" in gcode


# ── Тесты: line endings ──────────────────────────────────────────────


class TestFanucLineEnding:
    """Разные стили окончания строк."""

    def test_lf_line_ending(self, fanuc_profile: MachineProfile) -> None:
        """LF: строки разделены \\n."""
        gcode = render_fanuc([ProgramEnd()], fanuc_profile)
        assert "\r\n" not in gcode
        assert "\n" in gcode

    def test_crlf_line_ending(self) -> None:
        """CRLF: строки разделены \\r\\n."""
        profile = MachineProfile(
            profile_id="fanuc-crlf",
            controller=ControllerType.FANUC,
            controller_version="0i-MF",
            units=Units.MM,
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
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
        gcode = render_fanuc([ProgramEnd()], profile)
        assert "\r\n" in gcode
