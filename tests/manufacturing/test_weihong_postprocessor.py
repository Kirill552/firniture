"""TDD тесты для Weihong NCStudio постпроцессора.

Рендерит детерминированный ASCII G-code из IR команд по контракту проекта.

Тесты покрывают:
- Preamble (G21/G90/G17/<work_offset>/G80)
- Rapid, Linear, SpindleOn/Off, DrillCycle (G81/G82/G83), CancelCycle
- Tool change: M05 → safe retract → Txx M06 (специфично для NCStudio)
- Dwell: секунды IR → миллисекунды (P в G82)
- Line endings (LF, CRLF, CR)
- Empty / invalid edge cases
- Golden fixtures (two depths, hinge cup, slots, tool change)
- ProgramEnd: ровно одно M30 в конце
- Валидация контроллера и DEPRECATED

Профиль remains uncertified (draft) — Task20 simulator/air-cut/sacrificial sign-off pending.
Физическая сертификация не заявлена как готовая.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.manufacturing.machine_profiles import (
    AxisLimits,
    CertificationStatus,
    ControllerType,
    MachineProfile,
    SpindleConfig,
)
from api.manufacturing.postprocessors.base import (
    CancelCycle,
    DrillCycle,
    Linear,
    ProgramEnd,
    Rapid,
    SpindleOff,
    SpindleOn,
    ToolChange,
)
from api.manufacturing.postprocessors.weihong import (
    WeihongPostprocessor,
    _fmt_coord,
    _fmt_dwell_ms,
    _fmt_feed,
    _fmt_peck,
)

# ── Paths ────────────────────────────────────────────────────────────

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "cam" / "weihong"


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def weihong_profile() -> MachineProfile:
    """Валидный профиль Weihong NCStudio из fixture."""
    data = json.loads((FIXTURE_DIR / "profile.json").read_text())
    return MachineProfile(**data)


@pytest.fixture
def crlf_profile(weihong_profile: MachineProfile) -> MachineProfile:
    """Профиль с CRLF окончанием строк."""
    raw = json.loads((FIXTURE_DIR / "profile.json").read_text())
    raw["line_ending"] = "crlf"
    return MachineProfile(**raw)


@pytest.fixture
def cr_profile(weihong_profile: MachineProfile) -> MachineProfile:
    """Профиль с CR окончанием строк."""
    raw = json.loads((FIXTURE_DIR / "profile.json").read_text())
    raw["line_ending"] = "cr"
    return MachineProfile(**raw)


@pytest.fixture
def pp(weihong_profile: MachineProfile) -> WeihongPostprocessor:
    """Постпроцессор с LF окончанием."""
    return WeihongPostprocessor(weihong_profile)


@pytest.fixture
def pp_crlf(crlf_profile: MachineProfile) -> WeihongPostprocessor:
    """Постпроцессор с CRLF окончанием."""
    return WeihongPostprocessor(crlf_profile)


@pytest.fixture
def pp_cr(cr_profile: MachineProfile) -> WeihongPostprocessor:
    """Постпроцессор с CR окончанием."""
    return WeihongPostprocessor(cr_profile)


# ── Number formatting helpers ────────────────────────────────────────


class TestFormatting:
    """Детерминированный формат чисел."""

    def test_fmt_coord(self) -> None:
        assert _fmt_coord(0.0) == "0.000"
        assert _fmt_coord(-12.5) == "-12.500"
        assert _fmt_coord(100.123456) == "100.123"

    def test_fmt_feed(self) -> None:
        assert _fmt_feed(800.0) == "800"
        # Python .0f rounds to even (banker's rounding): 1500.5 → 1500
        assert _fmt_feed(1500.5) == "1500"

    def test_fmt_peck(self) -> None:
        assert _fmt_peck(3.0) == "3.000"
        assert _fmt_peck(2.5) == "2.500"

    def test_fmt_dwell_ms(self) -> None:
        """NCStudio G04 P_ принимает миллисекунды."""
        assert _fmt_dwell_ms(1.0) == "1000"
        assert _fmt_dwell_ms(1.5) == "1500"
        assert _fmt_dwell_ms(0.5) == "500"
        assert _fmt_dwell_ms(0.001) == "1"


# ── Валидация профиля (controller + certification) ───────────────────


class TestWeihongProfileValidation:
    """Валидация профиля при создании WeihongPostprocessor."""

    def test_weihong_controller_accepted(self, weihong_profile: MachineProfile) -> None:
        """controller=WEIHONG — принимается."""
        pp = WeihongPostprocessor(weihong_profile)
        assert pp._profile.profile_id == "weihong-fixture"

    def test_other_controller_accepted(self) -> None:
        """controller=OTHER — принимается (эксп/тесты)."""
        profile = MachineProfile(
            profile_id="weihong-other",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
            safe_z=5.0,
            feed_min=100, feed_max=8000,
            rpm_min=6000, rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="draft",
            postprocessor_version="1.0.0",
        )
        pp = WeihongPostprocessor(profile)
        assert pp._profile.controller is ControllerType.OTHER

    def test_unsupported_controller_rejected(self) -> None:
        """controller=FANUC — отвергается WeihongPostprocessor."""
        profile = MachineProfile(
            profile_id="fanuc-on-weihong",
            controller=ControllerType.FANUC,
            controller_version="0i",
            units="mm",
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="SP1", max_rpm=24000)],
            axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
            safe_z=5.0, feed_min=100, feed_max=8000,
            rpm_min=6000, rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="draft",
            postprocessor_version="1.0.0",
        )
        with pytest.raises(ValueError, match="не поддерживает контроллер"):
            WeihongPostprocessor(profile)

    def test_deprecated_profile_rejected(self) -> None:
        """DEPRECATED профиль — fail-closed."""
        profile = MachineProfile(
            profile_id="weihong-depr",
            controller=ControllerType.WEIHONG,
            controller_version="5.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
            safe_z=5.0, feed_min=100, feed_max=8000,
            rpm_min=6000, rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification=CertificationStatus.DEPRECATED,
            postprocessor_version="1.0.0",
        )
        with pytest.raises(ValueError, match="DEPRECATED"):
            WeihongPostprocessor(profile)


# ── Preamble ─────────────────────────────────────────────────────────


class TestPreamble:
    """Прелюдия: G21 G90 G17 G54 G80."""

    def test_preamble_present(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([])
        lines = result.split("\n")
        # Первые 5 строк — preamble
        assert lines[0] == "G21"  # метрика
        assert lines[1] == "G90"  # абсолют
        assert lines[2] == "G17"  # плоскость XY
        assert lines[3] == "G54"  # WCS
        assert lines[4] == "G80"  # отмена цикла

    def test_preamble_custom_work_offset(self) -> None:
        """G54.1 P1 вместо G54."""
        profile = MachineProfile(
            profile_id="test",
            controller="other",
            controller_version="1.0",
            units="mm",
            work_offset="G54.1 P1",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
            safe_z=5.0,
            feed_min=100, feed_max=8000,
            rpm_min=6000, rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="draft",
            postprocessor_version="1.0.0",
        )
        result = WeihongPostprocessor(profile).render([])
        lines = result.split("\n")
        assert lines[3] == "G54.1 P1"


# ── Rapid / Linear ───────────────────────────────────────────────────


class TestRapid:
    """G00 X_ Y_ Z_"""

    def test_rapid_xyz(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([Rapid(x=10.0, y=20.0, z=5.0)])
        lines = result.split("\n")
        # Строка 5 (после preamble) — первая команда
        assert lines[5] == "G00 X10.000 Y20.000 Z5.000"

    def test_rapid_xy_only(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([Rapid(x=100.0, y=200.0)])
        lines = result.split("\n")
        assert lines[5] == "G00 X100.000 Y200.000"

    def test_rapid_negative(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([Rapid(x=-50.0, y=-100.0, z=-10.0)])
        lines = result.split("\n")
        assert lines[5] == "G00 X-50.000 Y-100.000 Z-10.000"

    def test_rapid_zero(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([Rapid(x=0.0, y=0.0, z=0.0)])
        lines = result.split("\n")
        assert lines[5] == "G00 X0.000 Y0.000 Z0.000"


class TestLinear:
    """G01 X_ Y_ Z_ F_"""

    def test_linear_xyzf(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([Linear(x=50.0, y=20.0, z=-2.0, feed=800)])
        lines = result.split("\n")
        assert lines[5] == "G01 X50.000 Y20.000 Z-2.000 F800"

    def test_linear_high_feed(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([Linear(x=0.0, y=0.0, z=-1.0, feed=6000)])
        lines = result.split("\n")
        assert lines[5] == "G01 X0.000 Y0.000 Z-1.000 F6000"


# ── Spindle ──────────────────────────────────────────────────────────


class TestSpindleOn:
    """S<rpm> M03|M04"""

    def test_spindle_cw(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([SpindleOn(rpm=12000)])
        lines = result.split("\n")
        assert lines[5] == "S12000 M03"

    def test_spindle_ccw(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([SpindleOn(rpm=18000, clockwise=False)])
        lines = result.split("\n")
        assert lines[5] == "S18000 M04"


class TestSpindleOff:
    """M05"""

    def test_spindle_off(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([SpindleOff()])
        lines = result.split("\n")
        assert lines[5] == "M05"


# ── DrillCycle: G81/G82/G83 ─────────────────────────────────────────


class TestDrillCycleG81:
    """G81 X_ Y_ Z_ R_ F_ — простое сверление (без peck, без dwell)."""

    def test_g81_basic(self, pp: WeihongPostprocessor) -> None:
        cmd = DrillCycle(x=100.0, y=50.0, z=-12.0, retract=3.0, feed=600)
        result = pp.render([cmd])
        lines = result.split("\n")
        assert lines[5] == "G81 X100.000 Y50.000 Z-12.000 R3.000 F600"

    def test_g81_no_peck_no_dwell(self, pp: WeihongPostprocessor) -> None:
        """peck=None и dwell=None → G81."""
        cmd = DrillCycle(x=0.0, y=0.0, z=-5.0, retract=2.0, feed=800, peck=None, dwell=None)
        result = pp.render([cmd])
        assert "G81" in result.split("\n")[5]


class TestDrillCycleG82:
    """G82 X_ Y_ Z_ R_ P_ F_ — сверление с выдержкой на дне."""

    def test_g82_dwell(self, pp: WeihongPostprocessor) -> None:
        cmd = DrillCycle(x=50.0, y=100.0, z=-12.0, retract=3.0, feed=400, dwell=1.5)
        result = pp.render([cmd])
        line = result.split("\n")[5]
        assert line.startswith("G82")
        assert "P1500" in line  # 1.5s → 1500ms
        assert "F400" in line

    def test_g82_dwell_1s(self, pp: WeihongPostprocessor) -> None:
        cmd = DrillCycle(x=0.0, y=0.0, z=-8.0, retract=2.0, feed=500, dwell=1.0)
        result = pp.render([cmd])
        assert "P1000" in result.split("\n")[5]


class TestDrillCycleG83:
    """G83 X_ Y_ Z_ R_ Q_ F_ — глубокое сверление с отводом."""

    def test_g83_peck(self, pp: WeihongPostprocessor) -> None:
        cmd = DrillCycle(x=200.0, y=50.0, z=-18.0, retract=3.0, feed=600, peck=3.0)
        result = pp.render([cmd])
        line = result.split("\n")[5]
        assert line.startswith("G83")
        assert "Q3.000" in line
        assert "F600" in line

    def test_g83_peck_priority_over_dwell(self, pp: WeihongPostprocessor) -> None:
        """peck > 0 имеет приоритет над dwell → G83."""
        cmd = DrillCycle(x=0.0, y=0.0, z=-20.0, retract=3.0, feed=500, peck=5.0, dwell=0.5)
        result = pp.render([cmd])
        assert result.split("\n")[5].startswith("G83")


class TestDrillCycleDwellConversion:
    """NCStudio G04 P_ принимает миллисекуны; IR dwell в секундах."""

    def test_dwell_2s(self, pp: WeihongPostprocessor) -> None:
        cmd = DrillCycle(x=0.0, y=0.0, z=-10.0, retract=3.0, feed=800, dwell=2.0)
        result = pp.render([cmd])
        assert "P2000" in result.split("\n")[5]

    def test_dwell_half_second(self, pp: WeihongPostprocessor) -> None:
        cmd = DrillCycle(x=0.0, y=0.0, z=-5.0, retract=2.0, feed=800, dwell=0.5)
        result = pp.render([cmd])
        assert "P500" in result.split("\n")[5]


# ── CancelCycle / ProgramEnd ─────────────────────────────────────────


class TestCancelCycle:
    """G80 — отмена активного цикла."""

    def test_cancel_cycle(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([CancelCycle()])
        lines = result.split("\n")
        assert lines[5] == "G80"


class TestProgramEnd:
    """M30 — ровно одно в конце."""

    def test_single_m30(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([ProgramEnd()])
        lines = [line for line in result.split("\n") if line.strip()]
        assert lines[-1] == "M30"

    def test_no_duplicate_m30(self, pp: WeihongPostprocessor) -> None:
        """ProgramEnd в IR не дублирует M30."""
        result = pp.render([ProgramEnd(), ProgramEnd()])
        m30_count = sum(1 for line in result.split("\n") if line.strip() == "M30")
        assert m30_count == 1

    def test_m30_always_present(self, pp: WeihongPostprocessor) -> None:
        """M30 есть даже для пустого списка команд."""
        result = pp.render([])
        lines = [line for line in result.split("\n") if line.strip()]
        assert lines[-1] == "M30"


# ── Tool change: M05 → safe retract → Txx M06 ───────────────────────


class TestToolChange:
    """Безопасная последовательность смены инструмента.

    NCStudio диалект:
    1. M05 — остановка шпинделя
    2. G00 Z<safe_z> — безопасный отвод
    3. T<номер> M06 — смена инструмента
    """

    def test_tool_change_sequence(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([ToolChange(t_number=2)])
        lines = [line for line in result.split("\n") if line.strip()]
        # preamble = 5 строк (0-4), затем tool change:
        # lines[5] = "; --- tool change T2 ---"
        # lines[6] = "M05"
        # lines[7] = "G00 Z5.000"
        # lines[8] = "T2 M06"
        assert lines[5] == "; --- tool change T2 ---"
        assert lines[6] == "M05"
        assert lines[7] == "G00 Z5.000"
        assert lines[8] == "T2 M06"

    def test_tool_change_m05_before_retract(self, pp: WeihongPostprocessor) -> None:
        """M05 ДО safe retract."""
        result = pp.render([ToolChange(t_number=1)])
        lines = [line for line in result.split("\n") if line.strip()]
        idx_m05 = next(i for i, line in enumerate(lines) if line == "M05" and i >= 5)
        idx_retract = next(i for i, line in enumerate(lines) if "G00 Z" in line and i >= 5)
        assert idx_m05 < idx_retract

    def test_tool_change_t_number_in_output(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([ToolChange(t_number=3)])
        assert "T3 M06" in result

    def test_tool_change_comment(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([ToolChange(t_number=2)])
        assert "; --- tool change T2 ---" in result

    def test_tool_change_no_comment(self, weihong_profile: MachineProfile) -> None:
        pp_no_comment = WeihongPostprocessor(weihong_profile, comment_tool_change=False)
        result = pp_no_comment.render([ToolChange(t_number=1)])
        assert "tool change" not in result


# ── Line endings ─────────────────────────────────────────────────────


class TestLineEndings:
    """Конфигурируемые окончания строк."""

    def test_lf(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([])
        assert "\n" in result
        assert "\r" not in result

    def test_crlf(self, pp_crlf: WeihongPostprocessor) -> None:
        result = pp_crlf.render([])
        assert "\r\n" in result

    def test_cr(self, pp_cr: WeihongPostprocessor) -> None:
        result = pp_cr.render([])
        # CR: строки разделены \r, не \n
        lines = result.split("\r")
        assert lines[0] == "G21"


# ── Edge cases: empty / invalid ──────────────────────────────────────


class TestEdgeCases:
    """Граничные случаи: пустой ввод, некорректные данные."""

    def test_empty_commands(self, pp: WeihongPostprocessor) -> None:
        """Пустой список команд — только preamble + M30."""
        result = pp.render([])
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) == 6  # G21 G90 G17 G54 G80 M30
        assert lines[-1] == "M30"

    def test_single_rapid(self, pp: WeihongPostprocessor) -> None:
        result = pp.render([Rapid(x=0.0, y=0.0, z=0.0)])
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) == 7  # preamble + 1 command + M30

    def test_unknown_command_raises(self, pp: WeihongPostprocessor) -> None:
        """Неизвестный тип команды → ValueError."""
        # Создаём объект, не являющийся GCodeCommand
        class FakeCommand:
            pass

        with pytest.raises(ValueError, match="Неизвестный тип"):
            pp.render([FakeCommand()])  # type: ignore[list-item]

    def test_deterministic_output(self, pp: WeihongPostprocessor) -> None:
        """Два одинаковых вызова → идентичный вывод."""
        cmds = [
            Rapid(x=10.0, y=20.0, z=5.0),
            DrillCycle(x=100.0, y=50.0, z=-12.0, retract=3.0, feed=600),
            CancelCycle(),
            ProgramEnd(),
        ]
        assert pp.render(cmds) == pp.render(cmds)


# ── Golden fixtures ──────────────────────────────────────────────────


class TestGoldenFixtures:
    """Сравнение с golden G-code файлами."""

    @pytest.fixture(autouse=True)
    def _load_pp(self, pp: WeihongPostprocessor) -> None:
        self.pp = pp

    def _load_golden(self, name: str) -> str:
        path = FIXTURE_DIR / name
        return path.read_text()

    def test_golden_two_depths(self) -> None:
        """Два отверстия: G81 (5мм) + G83 peck (18мм)."""
        commands = [
            Rapid(x=0.0, y=0.0, z=5.0),
            SpindleOn(rpm=12000),
            DrillCycle(x=100.0, y=50.0, z=-5.0, retract=3.0, feed=800),
            DrillCycle(x=200.0, y=50.0, z=-18.0, retract=3.0, feed=600, peck=3.0),
            CancelCycle(),
            SpindleOff(),
            ProgramEnd(),
        ]
        assert self.pp.render(commands) == self._load_golden("golden_two_depths.gcode")

    def test_golden_hinge_cup(self) -> None:
        """Чашка петли 35мм с dwell на дне."""
        commands = [
            Rapid(x=0.0, y=0.0, z=5.0),
            SpindleOn(rpm=10000),
            DrillCycle(x=50.0, y=100.0, z=-12.0, retract=3.0, feed=400, dwell=1.0),
            CancelCycle(),
            SpindleOff(),
            ProgramEnd(),
        ]
        assert self.pp.render(commands) == self._load_golden("golden_hinge_cup.gcode")

    def test_golden_slots(self) -> None:
        """Паз — линейная фрезеровка (Rapid + Linear)."""
        commands = [
            Rapid(x=0.0, y=0.0, z=5.0),
            SpindleOn(rpm=18000),
            Rapid(x=10.0, y=200.0, z=5.0),
            Linear(x=10.0, y=200.0, z=-10.0, feed=1500),
            Linear(x=390.0, y=200.0, z=-10.0, feed=3000),
            Linear(x=390.0, y=200.0, z=5.0, feed=1500),
            Rapid(x=0.0, y=0.0, z=5.0),
            SpindleOff(),
            ProgramEnd(),
        ]
        assert self.pp.render(commands) == self._load_golden("golden_slots.gcode")

    def test_golden_toolchange(self) -> None:
        """Смена инструмента: M05 → retract → T M06."""
        commands = [
            Rapid(x=0.0, y=0.0, z=5.0),
            SpindleOn(rpm=12000),
            DrillCycle(x=100.0, y=50.0, z=-12.0, retract=3.0, feed=600),
            SpindleOff(),
            ToolChange(t_number=2),
            SpindleOn(rpm=10000),
            DrillCycle(x=200.0, y=100.0, z=-12.0, retract=3.0, feed=400, dwell=1.5),
            CancelCycle(),
            SpindleOff(),
            ProgramEnd(),
        ]
        assert self.pp.render(commands) == self._load_golden("golden_toolchange.gcode")

    def test_golden_empty(self) -> None:
        """Пустой список — preamble + M30."""
        assert self.pp.render([]) == self._load_golden("golden_empty.gcode")


# ── Integration: full panel-like workflow ─────────────────────────────


class TestFullWorkflow:
    """Интеграционный тест: типичный сценарий обработки панели."""

    def test_door_panel_workflow(self, pp: WeihongPostprocessor) -> None:
        """Фронт двери: 2 отверстия под петли + паз под заднюю стенку."""
        commands = [
            # Позиционирование
            Rapid(x=0.0, y=0.0, z=5.0),
            # Шпиндель для петель
            SpindleOn(rpm=10000),
            # Петля 1
            DrillCycle(x=50.0, y=100.0, z=-12.0, retract=3.0, feed=400, dwell=1.0),
            # Петля 2
            DrillCycle(x=50.0, y=400.0, z=-12.0, retract=3.0, feed=400, dwell=1.0),
            CancelCycle(),
            SpindleOff(),
            # Смена на фрезу для паза
            ToolChange(t_number=3),
            SpindleOn(rpm=18000),
            # Паз: заход
            Rapid(x=10.0, y=550.0, z=5.0),
            Linear(x=10.0, y=550.0, z=-10.0, feed=1500),
            # Паз: горизонтальный проход
            Linear(x=590.0, y=550.0, z=-10.0, feed=3000),
            # Паз: выход
            Linear(x=590.0, y=550.0, z=5.0, feed=1500),
            Rapid(x=0.0, y=0.0, z=5.0),
            SpindleOff(),
            ProgramEnd(),
        ]

        result = pp.render(commands)
        lines = result.split("\n")

        # Preamble
        assert lines[0] == "G21"
        assert lines[1] == "G90"
        assert lines[2] == "G17"
        assert lines[3] == "G54"
        assert lines[4] == "G80"

        # M30 в конце
        non_empty = [line for line in lines if line.strip()]
        assert non_empty[-1] == "M30"

        # Ровно одно M30
        assert sum(1 for line in lines if line.strip() == "M30") == 1

        # Tool change содержит M05 + safe retract
        assert "M05" in result
        assert "G00 Z5.000" in result
        assert "T3 M06" in result

        # Dwell в миллисекундах (1.0s → P1000)
        assert "P1000" in result

        # G82 для петель (dwell > 0)
        g82_count = sum(1 for line in lines if line.startswith("G82"))
        assert g82_count == 2

        # G80 перед сменой инструмента
        assert "G80" in result
