"""TDD тесты для G-code IR команд.

Typed IR команды описывают операции станка:
- Rapid: быстрое перемещение (G0)
- Linear: линейное перемещение (G1)
- ToolChange: смена инструмента (Txx M6)
- SpindleOn/SpindleOff: управление шпинделем (M3/M4, M05)
- DrillCycle: цикл сверления (G81/G82/G83)
- CancelCycle: отмена цикла (G80)
- ProgramEnd: конец программы (M30)

IR команды НЕ рендерят G-code текст — это ответственность постпроцессора.
"""
from __future__ import annotations

import pytest

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

# ── Rapid ────────────────────────────────────────────────────────────


class TestRapid:
    """Быстрое перемещение G0."""

    def test_basic_creation(self) -> None:
        cmd = Rapid(x=100.0, y=200.0, z=5.0)
        assert cmd.x == 100.0
        assert cmd.y == 200.0
        assert cmd.z == 5.0

    def test_is_gcode_command(self) -> None:
        cmd = Rapid(x=0.0, y=0.0, z=0.0)
        assert isinstance(cmd, GCodeCommand)

    def test_optional_z(self) -> None:
        cmd = Rapid(x=10.0, y=20.0)
        assert cmd.z is None

    def test_negative_coords_allowed(self) -> None:
        """Отрицательные координаты допустимы (границы панели)."""
        cmd = Rapid(x=-5.0, y=-10.0, z=0.0)
        assert cmd.x == -5.0


# ── Linear ───────────────────────────────────────────────────────────


class TestLinear:
    """Линейное перемещение G1."""

    def test_basic_creation(self) -> None:
        cmd = Linear(x=50.0, y=60.0, z=-3.0, feed=800.0)
        assert cmd.x == 50.0
        assert cmd.y == 60.0
        assert cmd.z == -3.0
        assert cmd.feed == 800.0

    def test_feed_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            Linear(x=0.0, y=0.0, z=0.0, feed=0.0)

    def test_negative_feed_rejected(self) -> None:
        with pytest.raises(ValueError):
            Linear(x=0.0, y=0.0, z=0.0, feed=-100.0)

    def test_is_gcode_command(self) -> None:
        cmd = Linear(x=0.0, y=0.0, z=0.0, feed=500.0)
        assert isinstance(cmd, GCodeCommand)


# ── ToolChange ───────────────────────────────────────────────────────


class TestToolChange:
    """Смена инструмента Txx M6."""

    def test_basic_creation(self) -> None:
        cmd = ToolChange(t_number=3)
        assert cmd.t_number == 3

    def test_t_number_must_be_nonnegative(self) -> None:
        with pytest.raises(ValueError):
            ToolChange(t_number=-1)

    def test_t_number_zero_valid(self) -> None:
        cmd = ToolChange(t_number=0)
        assert cmd.t_number == 0

    def test_is_gcode_command(self) -> None:
        cmd = ToolChange(t_number=1)
        assert isinstance(cmd, GCodeCommand)


# ── SpindleOn / SpindleOff ──────────────────────────────────────────


class TestSpindleOn:
    """Включение шпинделя M3/M4 Sxxx."""

    def test_basic_creation(self) -> None:
        cmd = SpindleOn(rpm=18000)
        assert cmd.rpm == 18000
        assert cmd.clockwise is True  # по умолчанию M3

    def test_counterclockwise(self) -> None:
        cmd = SpindleOn(rpm=18000, clockwise=False)
        assert cmd.clockwise is False

    def test_rpm_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            SpindleOn(rpm=0)

    def test_negative_rpm_rejected(self) -> None:
        with pytest.raises(ValueError):
            SpindleOn(rpm=-500)


class TestSpindleOff:
    """Выключение шпинделя M05."""

    def test_basic_creation(self) -> None:
        cmd = SpindleOff()
        assert isinstance(cmd, GCodeCommand)


# ── DrillCycle ───────────────────────────────────────────────────────


class TestDrillCycle:
    """Цикл сверления G81/G82/G83."""

    def test_basic_creation(self) -> None:
        cmd = DrillCycle(
            x=100.0, y=200.0, z=-12.0, retract=2.0, feed=300.0
        )
        assert cmd.x == 100.0
        assert cmd.y == 200.0
        assert cmd.z == -12.0
        assert cmd.retract == 2.0
        assert cmd.feed == 300.0
        assert cmd.peck is None
        assert cmd.dwell is None

    def test_with_peck(self) -> None:
        cmd = DrillCycle(
            x=10.0, y=20.0, z=-15.0, retract=2.0,
            feed=300.0, peck=5.0
        )
        assert cmd.peck == 5.0

    def test_with_dwell(self) -> None:
        cmd = DrillCycle(
            x=10.0, y=20.0, z=-10.0, retract=2.0,
            feed=300.0, dwell=1.0
        )
        assert cmd.dwell == 1.0

    def test_peck_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            DrillCycle(
                x=0.0, y=0.0, z=-5.0, retract=2.0,
                feed=300.0, peck=0.0
            )

    def test_depth_must_be_negative(self) -> None:
        """z для сверления — всегда вниз (отрицательный)."""
        with pytest.raises(ValueError):
            DrillCycle(
                x=0.0, y=0.0, z=5.0, retract=2.0, feed=300.0
            )

    def test_retract_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            DrillCycle(
                x=0.0, y=0.0, z=-5.0, retract=0.0, feed=300.0
            )

    def test_feed_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            DrillCycle(
                x=0.0, y=0.0, z=-5.0, retract=2.0, feed=0.0
            )

    def test_is_gcode_command(self) -> None:
        cmd = DrillCycle(
            x=0.0, y=0.0, z=-5.0, retract=2.0, feed=300.0
        )
        assert isinstance(cmd, GCodeCommand)


# ── CancelCycle ──────────────────────────────────────────────────────


class TestCancelCycle:
    """Отмена цикла G80."""

    def test_basic_creation(self) -> None:
        cmd = CancelCycle()
        assert isinstance(cmd, GCodeCommand)


# ── ProgramEnd ───────────────────────────────────────────────────────


class TestProgramEnd:
    """Конец программы M30."""

    def test_basic_creation(self) -> None:
        cmd = ProgramEnd()
        assert isinstance(cmd, GCodeCommand)


# ── Cycle key grouping ───────────────────────────────────────────────


class TestCycleKeyGrouping:
    """Группировка циклов по ключу (tool, face/setup, depth, retract,
    feed, dwell, peck). Циклы с разными параметрами НЕ группируются."""

    def test_drill_cycle_group_key(self) -> None:
        """Ключ цикла включает все параметры, определяющие совместимость."""
        from api.manufacturing.postprocessors.base import cycle_key

        c1 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300, peck=5)
        k1 = cycle_key(3, "bottom", c1)
        assert k1.t_number == 3
        assert k1.face == "bottom"
        assert k1.depth == -12
        assert k1.retract == 2
        assert k1.feed == 300
        assert k1.peck == 5

    def test_same_params_same_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c1 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300, peck=5)
        c2 = DrillCycle(x=50, y=60, z=-12, retract=2, feed=300, peck=5)
        assert cycle_key(1, "front", c1) == cycle_key(1, "front", c2)

    def test_different_depth_different_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c1 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300)
        c2 = DrillCycle(x=10, y=20, z=-18, retract=2, feed=300)
        assert cycle_key(1, "front", c1) != cycle_key(1, "front", c2)

    def test_different_feed_different_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c1 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300)
        c2 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=500)
        assert cycle_key(1, "front", c1) != cycle_key(1, "front", c2)

    def test_different_peck_different_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c1 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300, peck=5)
        c2 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300, peck=3)
        assert cycle_key(1, "front", c1) != cycle_key(1, "front", c2)

    def test_different_tool_different_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300)
        assert cycle_key(1, "front", c) != cycle_key(3, "front", c)

    def test_different_face_different_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300)
        assert cycle_key(1, "front", c) != cycle_key(1, "back", c)

    def test_different_dwell_different_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c1 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300, dwell=1.0)
        c2 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300, dwell=2.0)
        assert cycle_key(1, "front", c1) != cycle_key(1, "front", c2)

    def test_different_retract_different_key(self) -> None:
        from api.manufacturing.postprocessors.base import cycle_key

        c1 = DrillCycle(x=10, y=20, z=-12, retract=2, feed=300)
        c2 = DrillCycle(x=10, y=20, z=-12, retract=5, feed=300)
        assert cycle_key(1, "front", c1) != cycle_key(1, "front", c2)

    def test_non_drill_not_groupable(self) -> None:
        """Только DrillCycle участвует в группировке."""
        from api.manufacturing.postprocessors.base import cycle_key

        rapid = Rapid(x=0, y=0, z=0)
        with pytest.raises(TypeError):
            cycle_key(1, "front", rapid)


# ── Union type ───────────────────────────────────────────────────────


class TestGCodeCommandUnion:
    """Все команды принадлежат общей базе GCodeCommand."""

    def test_all_commands_are_gcode_command(self) -> None:
        commands = [
            Rapid(x=0, y=0, z=0),
            Linear(x=0, y=0, z=0, feed=100),
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            SpindleOff(),
            DrillCycle(x=0, y=0, z=-5, retract=2, feed=300),
            CancelCycle(),
            ProgramEnd(),
        ]
        for cmd in commands:
            assert isinstance(cmd, GCodeCommand)


# ── Regression: non-finite numbers must fail closed (P0) ──────────────


class TestRapidNonFinite:
    """Rapid с NaN/±inf координатами — ValueError."""

    @pytest.mark.parametrize("bad_x", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_x_rejected(self, bad_x: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            Rapid(x=bad_x, y=0.0)

    @pytest.mark.parametrize("bad_y", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_y_rejected(self, bad_y: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            Rapid(x=0.0, y=bad_y)

    @pytest.mark.parametrize("bad_z", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_z_rejected(self, bad_z: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            Rapid(x=0.0, y=0.0, z=bad_z)

    def test_finite_valid(self) -> None:
        cmd = Rapid(x=10.0, y=20.0, z=5.0)
        assert cmd.x == 10.0

    def test_z_none_valid(self) -> None:
        cmd = Rapid(x=10.0, y=20.0)
        assert cmd.z is None


class TestLinearNonFinite:
    """Linear с NaN/±inf — ValueError."""

    @pytest.mark.parametrize("bad_x", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_x_rejected(self, bad_x: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            Linear(x=bad_x, y=0.0, z=-1.0, feed=100.0)

    @pytest.mark.parametrize("bad_y", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_y_rejected(self, bad_y: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            Linear(x=0.0, y=bad_y, z=-1.0, feed=100.0)

    @pytest.mark.parametrize("bad_z", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_z_rejected(self, bad_z: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            Linear(x=0.0, y=0.0, z=bad_z, feed=100.0)

    @pytest.mark.parametrize("bad_feed", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_feed_rejected(self, bad_feed: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            Linear(x=0.0, y=0.0, z=-1.0, feed=bad_feed)


class TestDrillCycleNonFinite:
    """DrillCycle с NaN/±inf — ValueError."""

    @pytest.mark.parametrize("bad_x", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_x_rejected(self, bad_x: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            DrillCycle(x=bad_x, y=0.0, z=-5.0, retract=2.0, feed=300.0)

    @pytest.mark.parametrize("bad_y", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_y_rejected(self, bad_y: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            DrillCycle(x=0.0, y=bad_y, z=-5.0, retract=2.0, feed=300.0)

    @pytest.mark.parametrize("bad_z", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_z_rejected(self, bad_z: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            DrillCycle(x=0.0, y=0.0, z=bad_z, retract=2.0, feed=300.0)

    @pytest.mark.parametrize("bad_retract", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_retract_rejected(self, bad_retract: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            DrillCycle(x=0.0, y=0.0, z=-5.0, retract=bad_retract, feed=300.0)

    @pytest.mark.parametrize("bad_feed", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_feed_rejected(self, bad_feed: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            DrillCycle(x=0.0, y=0.0, z=-5.0, retract=2.0, feed=bad_feed)

    @pytest.mark.parametrize("bad_peck", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_peck_rejected(self, bad_peck: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            DrillCycle(x=0.0, y=0.0, z=-5.0, retract=2.0, feed=300.0, peck=bad_peck)

    @pytest.mark.parametrize("bad_dwell", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_dwell_rejected(self, bad_dwell: float) -> None:
        with pytest.raises(ValueError, match="конечным числом"):
            DrillCycle(x=0.0, y=0.0, z=-5.0, retract=2.0, feed=300.0, dwell=bad_dwell)


# ── Regression: strict int types for ToolChange / SpindleOn (P0) ──────


class TestToolChangeStrictInt:
    """t_number должен быть строго int, не bool/float."""

    def test_bool_true_rejected(self) -> None:
        with pytest.raises(TypeError, match="int"):
            ToolChange(t_number=True)  # type: ignore[arg-type]

    def test_bool_false_rejected(self) -> None:
        with pytest.raises(TypeError, match="int"):
            ToolChange(t_number=False)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad_val", [1.0, 0.0, 3.5])
    def test_float_rejected(self, bad_val: float) -> None:
        with pytest.raises(TypeError, match="int"):
            ToolChange(t_number=bad_val)  # type: ignore[arg-type]

    def test_valid_int_accepted(self) -> None:
        cmd = ToolChange(t_number=3)
        assert cmd.t_number == 3

    def test_zero_accepted(self) -> None:
        cmd = ToolChange(t_number=0)
        assert cmd.t_number == 0


class TestSpindleOnStrictInt:
    """rpm должен быть строго int, не bool/float; положительный и конечный."""

    def test_bool_true_rejected(self) -> None:
        with pytest.raises(TypeError, match="int"):
            SpindleOn(rpm=True)  # type: ignore[arg-type]

    def test_bool_false_rejected(self) -> None:
        with pytest.raises(TypeError, match="int"):
            SpindleOn(rpm=False)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad_val", [18000.0, 1.0, 0.5])
    def test_float_rejected(self, bad_val: float) -> None:
        with pytest.raises(TypeError, match="int"):
            SpindleOn(rpm=bad_val)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad_rpm", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_rejected(self, bad_rpm: float) -> None:
        """float NaN/inf caught by int type check (TypeError)."""
        with pytest.raises(TypeError, match="int"):
            SpindleOn(rpm=bad_rpm)  # type: ignore[arg-type]

    def test_valid_positive_int_accepted(self) -> None:
        cmd = SpindleOn(rpm=18000)
        assert cmd.rpm == 18000
