"""TDD тесты для safety валидатора G-code IR.

Валидатор проверяет:
- Границы панели (panel bounds)
- Настройку/трансформ (setup consistency)
- Способность шпинделя (spindle capability)
- Соответствие инструмента (tool match)
- Глубину (depth within tool max)
- Подачи (feeds in machine and tool range)
- RPM (в диапазоне станка и инструмента)
- Безопасный отвод (safe retract before tool change)
- Финальную отмену цикла (G80 before M30)
- Финальное выключение шпинделя (M05 before M30)

Blocking findings → нет скачиваемого G-code.
"""
from __future__ import annotations

import pytest

from api.manufacturing.machine_profiles import (
    AxisLimits,
    MachineProfile,
    SpindleConfig,
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
from api.manufacturing.postprocessors.safety import (
    Finding,
    SafetyReport,
    Severity,
    validate_gcode_ir,
)
from api.manufacturing.tool_library import OperationFamily, ToolLibrary, ToolMapping

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def basic_profile() -> MachineProfile:
    """Минимальный валидный профиль станка."""
    return MachineProfile(
        profile_id="test-profile-1",
        controller="other",
        controller_version="1.0",
        units="mm",
        work_offset="G54",
        supported_faces=["top", "bottom", "front", "back", "left", "right"],
        spindles=[
            SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000),
        ],
        axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
        safe_z=5.0,
        feed_min=100,
        feed_max=8000,
        rpm_min=6000,
        rpm_max=24000,
        dwell_syntax="G4 P",
        line_ending="lf",
        certification="verified",
        postprocessor_version="1.0.0",
    )


@pytest.fixture
def basic_tool_library() -> ToolLibrary:
    """Минимальная библиотека инструментов."""
    return ToolLibrary(tools=[
        ToolMapping(
            tool_id="D5_drill",
            t_number=1,
            diameter_mm=5.0,
            operation_family=OperationFamily.DRILL,
            spindle_id=1,
            max_depth_mm=20.0,
            rpm_min=8000,
            rpm_max=18000,
            feed_min=200,
            feed_max=600,
        ),
        ToolMapping(
            tool_id="D35_hinge",
            t_number=3,
            diameter_mm=35.0,
            operation_family=OperationFamily.DRILL,
            spindle_id=1,
            max_depth_mm=12.0,
            rpm_min=3000,
            rpm_max=6000,
            feed_min=100,
            feed_max=400,
        ),
        ToolMapping(
            tool_id="slot_8mm",
            t_number=2,
            diameter_mm=8.0,
            operation_family=OperationFamily.SLOT,
            spindle_id=1,
            max_depth_mm=18.0,
            rpm_min=10000,
            rpm_max=20000,
            feed_min=300,
            feed_max=1200,
        ),
    ])


@pytest.fixture
def sample_panel_w() -> float:
    return 600.0


@pytest.fixture
def sample_panel_h() -> float:
    return 400.0


# ── Severity levels ──────────────────────────────────────────────────


class TestSeverity:
    def test_blocking_and_warning(self) -> None:
        assert Severity.BLOCKING != Severity.WARNING

    def test_finding_creation(self) -> None:
        f = Finding(severity=Severity.BLOCKING, message="test error")
        assert f.severity == Severity.BLOCKING
        assert f.message == "test error"


# ── SafetyReport ─────────────────────────────────────────────────────


class TestSafetyReport:
    def test_clean_report(self) -> None:
        report = SafetyReport(findings=[])
        assert report.is_clean is True
        assert report.has_blockers is False

    def test_report_with_warnings(self) -> None:
        report = SafetyReport(findings=[
            Finding(severity=Severity.WARNING, message="minor"),
        ])
        assert report.is_clean is False
        assert report.has_blockers is False

    def test_report_with_blockers(self) -> None:
        report = SafetyReport(findings=[
            Finding(severity=Severity.BLOCKING, message="fatal"),
        ])
        assert report.is_clean is False
        assert report.has_blockers is True

    def test_report_mixed(self) -> None:
        report = SafetyReport(findings=[
            Finding(severity=Severity.WARNING, message="minor"),
            Finding(severity=Severity.BLOCKING, message="fatal"),
        ])
        assert report.has_blockers is True


# ── Panel bounds ─────────────────────────────────────────────────────


class TestPanelBounds:
    """Координаты должны быть в пределах панели."""

    def test_out_of_bounds_x(self, basic_profile, basic_tool_library) -> None:
        """X за пределами панели — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=700.0, y=200.0, z=5.0),  # 700 > 600 panel width
            DrillCycle(x=700.0, y=200.0, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        blocking = [f for f in report.findings if f.severity == Severity.BLOCKING]
        assert any("bounds" in f.message.lower() or ".panel" in f.message.lower() or "координат" in f.message.lower() for f in blocking)

    def test_out_of_bounds_y(self, basic_profile, basic_tool_library) -> None:
        """Y за пределами панели — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=300.0, y=500.0, z=5.0),
            DrillCycle(x=300.0, y=500.0, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True

    def test_within_bounds(self, basic_profile, basic_tool_library) -> None:
        """Координаты в пределах панели — нет blocker по bounds."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100.0, y=100.0, z=5.0),
            DrillCycle(x=100.0, y=100.0, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        # Нет блокеров по bounds
        bounds_findings = [f for f in report.findings if "bounds" in f.message.lower() or "координат" in f.message.lower()]
        blocking_bounds = [f for f in bounds_findings if f.severity == Severity.BLOCKING]
        assert len(blocking_bounds) == 0


# ── Tool match ───────────────────────────────────────────────────────


class TestToolMatch:
    """T-номер должен существовать в библиотеке."""

    def test_wrong_t_number(self, basic_profile, basic_tool_library) -> None:
        """T99 не существует в библиотеке — blocking."""
        cmds = [
            ToolChange(t_number=99),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        tool_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "T99" in f.message]
        assert len(tool_findings) > 0

    def test_valid_t_number(self, basic_profile, basic_tool_library) -> None:
        """T1 существует — нет tool blocker."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        tool_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "инструмент" in f.message.lower()]
        assert len(tool_findings) == 0


# ── Depth ────────────────────────────────────────────────────────────


class TestDepth:
    """Глубина сверления не должна превышать max_depth инструмента."""

    def test_depth_exceeds_tool_max(self, basic_profile, basic_tool_library) -> None:
        """D5_drill: max_depth=20, а z=-30 — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-30.0, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        depth_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "глубин" in f.message.lower()]
        assert len(depth_findings) > 0

    def test_depth_within_limit(self, basic_profile, basic_tool_library) -> None:
        """D5_drill: max_depth=20, z=-12 — OK."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        depth_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "глубин" in f.message.lower()]
        assert len(depth_findings) == 0


# ── Feed validation ──────────────────────────────────────────────────


class TestFeedValidation:
    """Подача должна быть в пределах диапазона станка и инструмента."""

    def test_feed_exceeds_machine_max(self, basic_profile, basic_tool_library) -> None:
        """Подача 10000 > machine feed_max=8000 — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=10000),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        feed_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "подач" in f.message.lower()]
        assert len(feed_findings) > 0

    def test_feed_below_machine_min(self, basic_profile, basic_tool_library) -> None:
        """Подача 50 < machine feed_min=100 — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=50),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True

    def test_feed_exceeds_tool_max(self, basic_profile, basic_tool_library) -> None:
        """D5_drill: feed_max=600, подача 700 — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=700),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        tool_feed_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "инструмент" in f.message.lower()]
        assert len(tool_feed_findings) > 0

    def test_feed_within_ranges(self, basic_profile, basic_tool_library) -> None:
        """Подача 300 в пределах machine [100,8000] и tool [200,600] — OK."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        feed_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "подач" in f.message.lower()]
        assert len(feed_findings) == 0


# ── RPM validation ───────────────────────────────────────────────────


class TestRPMValidation:
    """RPM должен быть в пределах диапазона станка."""

    def test_rpm_exceeds_machine_max(self, basic_profile, basic_tool_library) -> None:
        """RPM 30000 > machine rpm_max=24000 — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=30000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        rpm_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "rpm" in f.message.lower()]
        assert len(rpm_findings) > 0

    def test_rpm_below_machine_min(self, basic_profile, basic_tool_library) -> None:
        """RPM 3000 < machine rpm_min=6000 — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=3000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True

    def test_rpm_exceeds_tool_max(self, basic_profile, basic_tool_library) -> None:
        """D5_drill: rpm_max=18000, RPM 20000 — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=20000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        tool_rpm_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "инструмент" in f.message.lower()]
        assert len(tool_rpm_findings) > 0

    def test_rpm_within_ranges(self, basic_profile, basic_tool_library) -> None:
        """RPM 18000 в пределах machine [6000,24000] и tool [8000,18000] — OK."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        rpm_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "rpm" in f.message.lower()]
        assert len(rpm_findings) == 0


# ── Missing M05 ──────────────────────────────────────────────────────


class TestMissingSpindleOff:
    """Шпиндель должен быть выключен (M05) перед сменой инструмента."""

    def test_missing_m05_before_tool_change(self, basic_profile, basic_tool_library) -> None:
        """Нет M05 перед второй сменой — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            # SpindleOff() — ПРОПУЩЕН!
            ToolChange(t_number=3),
            SpindleOn(rpm=6000),
            Rapid(x=200, y=200, z=5),
            DrillCycle(x=200, y=200, z=-10, retract=2, feed=200),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        m05_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "m05" in f.message.lower()]
        assert len(m05_findings) > 0

    def test_m05_present_before_tool_change(self, basic_profile, basic_tool_library) -> None:
        """M05 перед сменой — OK."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            ToolChange(t_number=3),
            SpindleOn(rpm=6000),
            Rapid(x=200, y=200, z=5),
            DrillCycle(x=200, y=200, z=-10, retract=2, feed=200),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        m05_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "m05" in f.message.lower()]
        assert len(m05_findings) == 0


# ── Safe retract before tool change ──────────────────────────────────


class TestSafeRetract:
    """Безопасный отвод (safe_z) перед сменой инструмента."""

    def test_no_safe_retract_before_tool_change(self, basic_profile, basic_tool_library) -> None:
        """Нет отвода на safe_z перед ToolChange — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            # Нет Rapid z=5 (safe_z) перед ToolChange
            ToolChange(t_number=3),
            SpindleOn(rpm=6000),
            Rapid(x=200, y=200, z=5),
            DrillCycle(x=200, y=200, z=-10, retract=2, feed=200),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        retract_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "отвод" in f.message.lower()]
        assert len(retract_findings) > 0

    def test_safe_retract_present(self, basic_profile, basic_tool_library) -> None:
        """Rapid z=safe_z перед ToolChange — OK."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            Rapid(x=100, y=100, z=5.0),  # safe retract
            ToolChange(t_number=3),
            SpindleOn(rpm=6000),
            Rapid(x=200, y=200, z=5),
            DrillCycle(x=200, y=200, z=-10, retract=2, feed=200),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        retract_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "отвод" in f.message.lower()]
        assert len(retract_findings) == 0


# ── Final cancellation ───────────────────────────────────────────────


class TestFinalCancellation:
    """G80 и M05 должны быть перед M30."""

    def test_missing_g80_before_m30(self, basic_profile, basic_tool_library) -> None:
        """Нет CancelCycle() перед ProgramEnd() — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            # Нет CancelCycle()
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        g80_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "g80" in f.message.lower()]
        assert len(g80_findings) > 0

    def test_missing_m05_before_m30(self, basic_profile, basic_tool_library) -> None:
        """Нет M05 перед ProgramEnd() — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            # Нет SpindleOff()
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        m05_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and "m05" in f.message.lower()]
        assert len(m05_findings) > 0

    def test_all_present_before_m30(self, basic_profile, basic_tool_library) -> None:
        """SpindleOff + CancelCycle + ProgramEnd — OK."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        cancellation_findings = [f for f in report.findings if f.severity == Severity.BLOCKING and ("g80" in f.message.lower() or "m05" in f.message.lower())]
        assert len(cancellation_findings) == 0


# ── Happy path (no blockers) ────────────────────────────────────────


class TestHappyPath:
    """Последовательность команд проходит все проверки."""

    def test_valid_single_tool_sequence(
        self, basic_profile, basic_tool_library
    ) -> None:
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            DrillCycle(x=200, y=200, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is False

    def test_valid_multi_tool_sequence(
        self, basic_profile, basic_tool_library
    ) -> None:
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),               # отмена цикла перед сменой
            Rapid(x=200, y=200, z=5.0),  # safe retract
            ToolChange(t_number=3),
            SpindleOn(rpm=6000),
            Rapid(x=300, y=200, z=5),
            DrillCycle(x=300, y=200, z=-10, retract=2, feed=200),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is False


# ── Empty commands ───────────────────────────────────────────────────


class TestEmptyCommands:
    def test_empty_command_list(self, basic_profile, basic_tool_library) -> None:
        """Пустой список команд — нет блокеров (ничего делать не надо)."""
        report = validate_gcode_ir(
            commands=[],
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is False


# ── Regression: DrillCycle without spindle on ────────────────────────


class TestDrillWithoutSpindleOn:
    """DrillCycle при выключенном шпинделе — BLOCKING."""

    def test_drill_without_spindle_on(self, basic_profile, basic_tool_library) -> None:
        """DrillCycle без предшествующего SpindleOn — blocking."""
        cmds = [
            ToolChange(t_number=1),
            # SpindleOn() — ПРОПУЩЕН!
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "шпиндель не включён" in f.message.lower()
        ]
        assert len(spindle_findings) > 0

    def test_drill_after_spindle_off(self, basic_profile, basic_tool_library) -> None:
        """DrillCycle после SpindleOff — blocking (шпиндель снова выкл)."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            # SpindleOff → шпиндель выключен
            DrillCycle(x=200, y=200, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "шпиндель не включён" in f.message.lower()
        ]
        assert len(spindle_findings) > 0

    def test_drill_with_spindle_on_ok(self, basic_profile, basic_tool_library) -> None:
        """DrillCycle после SpindleOn — OK (нет spindle blocker)."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "шпиндель не включён" in f.message.lower()
        ]
        assert len(spindle_findings) == 0


# ── Regression: SpindleConfig.max_rpm enforcement ────────────────────


class TestSpindleMaxRpm:
    """RPM должен соответствовать максимуму конкретного шпинделя."""

    def _make_profile_and_tool(
        self,
    ) -> tuple[MachineProfile, ToolLibrary]:
        """Профиль с двумя шпинделями: OS1=24000, OS2=12000."""
        profile = MachineProfile(
            profile_id="test-profile-dual",
            controller="other",
            controller_version="1.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top", "bottom"],
            spindles=[
                SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000),
                SpindleConfig(spindle_id=2, name="OS2", max_rpm=12000),
            ],
            axis_limits=AxisLimits(
                x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100,
            ),
            safe_z=5.0,
            feed_min=100,
            feed_max=8000,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="verified",
            postprocessor_version="1.0.0",
        )
        tools = ToolLibrary(tools=[
            ToolMapping(
                tool_id="D5_drill_s2",
                t_number=10,
                diameter_mm=5.0,
                operation_family=OperationFamily.DRILL,
                spindle_id=2,  # на шпинделе OS2 (max_rpm=12000)
                max_depth_mm=20.0,
                rpm_min=8000,
                rpm_max=20000,  # допуск инструмента выше максимума шпинделя
                feed_min=200,
                feed_max=600,
            ),
        ])
        return profile, tools

    def test_rpm_exceeds_spindle_max(self) -> None:
        """RPM 15000 > spindle OS2.max_rpm=12000 — blocking.

        При этом RPM в пределах machine [6000,24000] и tool [8000,20000].
        """
        profile, tools = self._make_profile_and_tool()
        cmds = [
            ToolChange(t_number=10),
            SpindleOn(rpm=15000),  # 15000 > spindle 12000
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=profile,
            tool_library=tools,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "шпинделя" in f.message.lower()
            and "os2" in f.message.lower()
        ]
        assert len(spindle_findings) > 0

    def test_rpm_within_spindle_max(self) -> None:
        """RPM 10000 < spindle OS2.max_rpm=12000 — OK."""
        profile, tools = self._make_profile_and_tool()
        cmds = [
            ToolChange(t_number=10),
            SpindleOn(rpm=10000),  # 10000 < spindle 12000
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=profile,
            tool_library=tools,
            panel_width=600.0,
            panel_height=400.0,
        )
        spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "шпинделя" in f.message.lower()
        ]
        assert len(spindle_findings) == 0




# ── Regression: unknown spindle_id in tool mapping ─────────────────


class TestUnknownSpindleId:
    """Tool referencing spindle_id absent from profile must BLOCK."""

    def test_unknown_spindle_blocks(self) -> None:
        """Tool with spindle_id=99 not in profile.spindles — blocking."""
        profile = MachineProfile(
            profile_id="test-unknown-spindle",
            controller="other",
            controller_version="1.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top", "bottom"],
            spindles=[
                SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000),
            ],
            axis_limits=AxisLimits(
                x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100,
            ),
            safe_z=5.0,
            feed_min=100,
            feed_max=8000,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="verified",
            postprocessor_version="1.0.0",
        )
        tools = ToolLibrary(tools=[
            ToolMapping(
                tool_id="mystery_tool",
                t_number=5,
                diameter_mm=10.0,
                operation_family=OperationFamily.SLOT,
                spindle_id=99,  # не существует в profile.spindles
                max_depth_mm=18.0,
                rpm_min=8000,
                rpm_max=20000,
                feed_min=200,
                feed_max=600,
            ),
        ])
        cmds = [
            ToolChange(t_number=5),
            SpindleOn(rpm=12000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=profile,
            tool_library=tools,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        unknown_spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "не найден" in f.message.lower()
            and "spindle_id=99" in f.message
        ]
        assert len(unknown_spindle_findings) > 0

    def test_known_spindle_no_false_positive(self) -> None:
        """Tool with spindle_id=1 present in profile — no unknown spindle finding."""
        profile = MachineProfile(
            profile_id="test-known-spindle",
            controller="other",
            controller_version="1.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top", "bottom"],
            spindles=[
                SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000),
            ],
            axis_limits=AxisLimits(
                x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100,
            ),
            safe_z=5.0,
            feed_min=100,
            feed_max=8000,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="verified",
            postprocessor_version="1.0.0",
        )
        tools = ToolLibrary(tools=[
            ToolMapping(
                tool_id="known_tool",
                t_number=3,
                diameter_mm=8.0,
                operation_family=OperationFamily.SLOT,
                spindle_id=1,  # существует в profile.spindles
                max_depth_mm=18.0,
                rpm_min=8000,
                rpm_max=20000,
                feed_min=200,
                feed_max=600,
            ),
        ])
        cmds = [
            ToolChange(t_number=3),
            SpindleOn(rpm=12000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=profile,
            tool_library=tools,
            panel_width=600.0,
            panel_height=400.0,
        )
        unknown_spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "не найден" in f.message.lower()
        ]
        assert len(unknown_spindle_findings) == 0
# ── Regression: ToolChange during active canned cycle ────────────────


class TestToolChangeDuringActiveCycle:
    """ToolChange при активном canned cycle — BLOCKING."""

    def test_tool_change_during_cycle(self, basic_profile, basic_tool_library) -> None:
        """ToolChange без G80 при активном DrillCycle — blocking."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            # Нет CancelCycle() — cycle_active仍True
            Rapid(x=200, y=200, z=5.0),
            ToolChange(t_number=3),  # ← нарушение!
            SpindleOn(rpm=6000),
            Rapid(x=300, y=200, z=5),
            DrillCycle(x=300, y=200, z=-10, retract=2, feed=200),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        cycle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "canned cycle" in f.message.lower()
        ]
        assert len(cycle_findings) > 0

    def test_tool_change_after_cancel_cycle_ok(
        self, basic_profile, basic_tool_library,
    ) -> None:
        """ToolChange после CancelCycle — OK (нет cycle blocker)."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),  # ← G80 перед сменой
            Rapid(x=200, y=200, z=5.0),
            ToolChange(t_number=3),
            SpindleOn(rpm=6000),
            Rapid(x=300, y=200, z=5),
            DrillCycle(x=300, y=200, z=-10, retract=2, feed=200),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        cycle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "canned cycle" in f.message.lower()
        ]
        assert len(cycle_findings) == 0

# ── Regression: DrillCycle without ToolChange ────────────────────────


class TestDrillCycleWithoutTool:
    """DrillCycle без загруженного инструмента — BLOCKING (fail-open fix)."""

    def test_drill_without_tool_change(self, basic_profile, basic_tool_library) -> None:
        """SpindleOn -> DrillCycle без ToolChange — blocking.

        Шпиндель включён, но инструмент не загружен (active_tool=None).
        """
        cmds = [
            # ToolChange — ПРОПУЩЕН!
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        tool_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "инструмент" in f.message.lower()
            and "не загружен" in f.message.lower()
        ]
        assert len(tool_findings) > 0

    def test_drill_with_tool_change_ok(self, basic_profile, basic_tool_library) -> None:
        """ToolChange -> SpindleOn -> DrillCycle — OK (инструмент загружен)."""
        cmds = [
            ToolChange(t_number=1),
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            SpindleOff(),
            CancelCycle(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        tool_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "инструмент" in f.message.lower()
            and "не загружен" in f.message.lower()
        ]
        assert len(tool_findings) == 0


# ── Regression: Linear cutting without tool/spindle ──────────────────


class TestLinearCuttingWithoutToolSpindle:
    """Linear с Z < 0 без инструмента/шпинделя — BLOCKING (fail-open fix)."""

    def test_linear_cutting_without_tool(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-5) без ToolChange — blocking (нет загруженного инструмента)."""
        cmds = [
            # ToolChange — ПРОПУЩЕН!
            SpindleOn(rpm=18000),
            Linear(x=100, y=100, z=-5, feed=400),
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        tool_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "инструмент" in f.message.lower()
            and "не загружен" in f.message.lower()
        ]
        assert len(tool_findings) > 0

    def test_linear_cutting_without_spindle(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-5) без SpindleOn — blocking (шпиндель не включён)."""
        cmds = [
            ToolChange(t_number=1),
            # SpindleOn — ПРОПУЩЕН!
            Linear(x=100, y=100, z=-5, feed=400),
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "шпиндель не включён" in f.message.lower()
            and "linear" in f.message.lower()
        ]
        assert len(spindle_findings) > 0

    def test_linear_cutting_with_tool_and_spindle_ok(
        self, basic_profile, basic_tool_library,
    ) -> None:
        """ToolChange -> SpindleOn -> Linear(z=-5) — OK."""
        cmds = [
            ToolChange(t_number=2),  # slot_8mm: feed_min=300, feed_max=1200
            SpindleOn(rpm=15000),
            Linear(x=100, y=100, z=-5, feed=400),
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        tool_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "инструмент" in f.message.lower()
            and "не загружен" in f.message.lower()
        ]
        spindle_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "шпиндель не включён" in f.message.lower()
        ]
        assert len(tool_findings) == 0
        assert len(spindle_findings) == 0


# ── Regression: Linear cutting feed validation ───────────────────────


class TestLinearCuttingFeed:
    """Подача Linear при резании должна соответствовать станку и инструменту."""

    def test_feed_below_tool_min(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-5, feed=50) feed < tool.feed_min(300) — blocking."""
        cmds = [
            ToolChange(t_number=1),  # D5_drill: feed_min=200, feed_max=600
            SpindleOn(rpm=18000),
            Linear(x=100, y=100, z=-5, feed=50),  # 50 < 200
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        feed_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "подача" in f.message.lower()
            and "linear" in f.message.lower()
        ]
        assert len(feed_findings) > 0

    def test_feed_above_tool_max(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-5, feed=900) feed > tool.feed_max(600) — blocking."""
        cmds = [
            ToolChange(t_number=1),  # D5_drill: feed_min=200, feed_max=600
            SpindleOn(rpm=18000),
            Linear(x=100, y=100, z=-5, feed=900),  # 900 > 600
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        feed_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "подача" in f.message.lower()
            and "linear" in f.message.lower()
        ]
        assert len(feed_findings) > 0

    def test_feed_within_range_ok(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-5, feed=400) feed в [200,600] — OK."""
        cmds = [
            ToolChange(t_number=1),  # D5_drill: feed_min=200, feed_max=600
            SpindleOn(rpm=18000),
            Linear(x=100, y=100, z=-5, feed=400),  # OK
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        feed_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "подача" in f.message.lower()
            and "linear" in f.message.lower()
        ]
        assert len(feed_findings) == 0

    def test_feed_above_machine_max(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-5, feed=9000) feed > profile.feed_max(8000) — blocking."""
        cmds = [
            ToolChange(t_number=2),  # slot_8mm: feed_min=300, feed_max=1200
            SpindleOn(rpm=15000),
            Linear(x=100, y=100, z=-5, feed=9000),  # 9000 > 8000 machine max
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        feed_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "подача" in f.message.lower()
            and "станка" in f.message.lower()
        ]
        assert len(feed_findings) > 0


# ── Regression: Linear cutting depth bound ────────────────────────────


class TestLinearCuttingDepth:
    """Глубина резания Linear не должна превышать max_depth инструмента."""

    def test_depth_exceeds_tool_max(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-25) depth > tool.max_depth(20) — blocking."""
        cmds = [
            ToolChange(t_number=1),  # D5_drill: max_depth=20
            SpindleOn(rpm=18000),
            Linear(x=100, y=100, z=-25, feed=400),  # 25 > 20
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        depth_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "глубина" in f.message.lower()
            and "linear" in f.message.lower()
        ]
        assert len(depth_findings) > 0

    def test_depth_within_limit_ok(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=-15) depth < tool.max_depth(20) — OK."""
        cmds = [
            ToolChange(t_number=1),  # D5_drill: max_depth=20
            SpindleOn(rpm=18000),
            Linear(x=100, y=100, z=-15, feed=400),  # 15 < 20
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        depth_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "глубина" in f.message.lower()
            and "linear" in f.message.lower()
        ]
        assert len(depth_findings) == 0


# ── Regression: Linear safe rapid (z >= 0) ───────────────────────────


class TestLinearSafeRapid:
    """Linear с Z >= 0 — безопасное перемещение, без дополнительных проверок."""

    def test_linear_at_surface_no_checks(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=0) без tool/spindle — OK (не режет)."""
        cmds = [
            Linear(x=100, y=100, z=0, feed=400),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        # z=0 — не режет, нет дополнительных блокеров
        cutting_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and ("инструмент" in f.message.lower() or "шпиндель" in f.message.lower())
        ]
        assert len(cutting_findings) == 0

    def test_linear_above_surface_no_checks(self, basic_profile, basic_tool_library) -> None:
        """Linear(z=5) без tool/spindle — OK (не режет)."""
        cmds = [
            Linear(x=100, y=100, z=5, feed=400),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        cutting_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and ("инструмент" in f.message.lower() or "шпиндель" in f.message.lower())
        ]
        assert len(cutting_findings) == 0

    def test_rapid_always_safe(self, basic_profile, basic_tool_library) -> None:
        """Rapid(z=-10) без tool/spindle — OK (rapid не режет)."""
        cmds = [
            Rapid(x=100, y=100, z=-10),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        cutting_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and ("инструмент" in f.message.lower() or "шпиндель" in f.message.lower())
        ]
        assert len(cutting_findings) == 0


# ── Regression: No fail-open DrillCycle/cutting Linear sequence ──────


class TestNoFailOpenMachiningSequence:
    """Комплексная проверка: все machining moves требуют tool+spindle."""

    def test_drill_and_linear_both_need_tool(self, basic_profile, basic_tool_library) -> None:
        """SpindleOn -> DrillCycle + Linear(z<0) без ToolChange — оба blocking."""
        cmds = [
            # ToolChange — ПРОПУЩЕН!
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            CancelCycle(),
            Linear(x=200, y=200, z=-5, feed=400),
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        # Должны быть блокеры и для DrillCycle, и для Linear
        tool_findings = [
            f for f in report.findings
            if f.severity == Severity.BLOCKING
            and "инструмент" in f.message.lower()
            and "не загружен" in f.message.lower()
        ]
        assert len(tool_findings) >= 2  # DrillCycle + Linear

    def test_valid_sequence_passes(self, basic_profile, basic_tool_library) -> None:
        """ToolChange -> SpindleOn -> DrillCycle + Linear(z<0) — OK."""
        cmds = [
            ToolChange(t_number=1),  # D5_drill: feed 200-600, depth 20
            SpindleOn(rpm=18000),
            Rapid(x=100, y=100, z=5),
            DrillCycle(x=100, y=100, z=-12, retract=2, feed=300),
            CancelCycle(),
            Linear(x=200, y=200, z=-5, feed=400),
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=cmds,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is False


# ── Regression: non-finite boundary inputs → BLOCKING (P0) ───────────


class TestNonFiniteBoundaryInputs:
    """NaN/±inf в границах панели/профиля — BLOCKING, fail-closed."""

    def _make_empty_program(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> list[GCodeCommand]:
        """Minimal valid program ending with ProgramEnd."""
        return [
            SpindleOff(),
            ProgramEnd(),
        ]

    @pytest.mark.parametrize("bad_width", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_panel_width_blocks(
        self,
        bad_width: float,
        basic_profile: MachineProfile,
        basic_tool_library: ToolLibrary,
    ) -> None:
        report = validate_gcode_ir(
            commands=self._make_empty_program(basic_profile, basic_tool_library),
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=bad_width,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        finite_findings = [f for f in report.findings if "panel_width" in f.message]
        assert len(finite_findings) == 1
        assert finite_findings[0].severity == Severity.BLOCKING

    @pytest.mark.parametrize("bad_height", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_panel_height_blocks(
        self,
        bad_height: float,
        basic_profile: MachineProfile,
        basic_tool_library: ToolLibrary,
    ) -> None:
        report = validate_gcode_ir(
            commands=self._make_empty_program(basic_profile, basic_tool_library),
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=bad_height,
        )
        assert report.has_blockers is True
        finite_findings = [f for f in report.findings if "panel_height" in f.message]
        assert len(finite_findings) == 1
        assert finite_findings[0].severity == Severity.BLOCKING

    @pytest.mark.parametrize("bad_safe_z", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_safe_z_blocks(
        self,
        bad_safe_z: float,
        basic_tool_library: ToolLibrary,
    ) -> None:
        profile = MachineProfile.model_construct(
            profile_id="test",
            controller="other",
            controller_version="1.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
            safe_z=bad_safe_z,
            feed_min=100,
            feed_max=8000,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="verified",
            postprocessor_version="1.0.0",
        )
        report = validate_gcode_ir(
            commands=[SpindleOff(), ProgramEnd()],
            profile=profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        finite_findings = [f for f in report.findings if "safe_z" in f.message]
        assert len(finite_findings) == 1
        assert finite_findings[0].severity == Severity.BLOCKING

    @pytest.mark.parametrize("bad_feed_min", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_feed_min_blocks(
        self,
        bad_feed_min: float,
        basic_tool_library: ToolLibrary,
    ) -> None:
        profile = MachineProfile.model_construct(
            profile_id="test",
            controller="other",
            controller_version="1.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
            safe_z=5.0,
            feed_min=bad_feed_min,
            feed_max=bad_feed_min,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="verified",
            postprocessor_version="1.0.0",
        )
        report = validate_gcode_ir(
            commands=[SpindleOff(), ProgramEnd()],
            profile=profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        finite_findings = [f for f in report.findings if "feed_min" in f.message]
        assert len(finite_findings) == 1
        assert finite_findings[0].severity == Severity.BLOCKING

    @pytest.mark.parametrize("bad_feed_max", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_feed_max_blocks(
        self,
        bad_feed_max: float,
        basic_tool_library: ToolLibrary,
    ) -> None:
        profile = MachineProfile.model_construct(
            profile_id="test",
            controller="other",
            controller_version="1.0",
            units="mm",
            work_offset="G54",
            supported_faces=["top"],
            spindles=[SpindleConfig(spindle_id=1, name="OS1", max_rpm=24000)],
            axis_limits=AxisLimits(x_min=0, x_max=3000, y_min=0, y_max=1500, z_min=0, z_max=100),
            safe_z=5.0,
            feed_min=bad_feed_max,
            feed_max=bad_feed_max,
            rpm_min=6000,
            rpm_max=24000,
            dwell_syntax="G4 P",
            line_ending="lf",
            certification="verified",
            postprocessor_version="1.0.0",
        )
        report = validate_gcode_ir(
            commands=[SpindleOff(), ProgramEnd()],
            profile=profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        finite_findings = [f for f in report.findings if "feed_max" in f.message]
        assert len(finite_findings) == 1
        assert finite_findings[0].severity == Severity.BLOCKING


# ── Regression: ToolChange→SpindleOn(NaN)→cut must BLOCK (P0) ────────


class TestToolChangeSpindleNanCut:
    """ToolChange → SpindleOn(NaN) → Linear(cut) — BLOCKING, fail-closed.

    NaN RPM через SpindleOn должен быть заблокирован safety-валидатором
    (defense-in-depth), даже если construction check обойдён.
    """

    @staticmethod
    def _make_spindle_on_nan() -> SpindleOn:
        """Construct SpindleOn with NaN bypassing __post_init__ (defense-in-depth)."""
        cmd = SpindleOn.__new__(SpindleOn)
        object.__setattr__(cmd, "rpm", float("nan"))
        object.__setattr__(cmd, "clockwise", True)
        return cmd

    def test_nan_rpm_blocks_cut(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> None:
        """SpindleOn(NaN) → Linear(z=-2) must BLOCK."""
        nan_spindle = self._make_spindle_on_nan()
        commands: list[GCodeCommand] = [
            ToolChange(t_number=1),
            Rapid(x=0.0, y=0.0, z=basic_profile.safe_z),
            nan_spindle,
            Linear(x=10.0, y=0.0, z=-2.0, feed=3000),
            SpindleOff(),
            ProgramEnd(),
        ]
        report = validate_gcode_ir(
            commands=commands,
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        assert report.has_blockers is True
        rpm_findings = [f for f in report.findings if "rpm" in f.message.lower()]
        assert len(rpm_findings) >= 1
        assert rpm_findings[0].severity == Severity.BLOCKING

    def test_bool_rpm_blocks_cut(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> None:
        """SpindleOn(True) → Linear(z=-2) must BLOCK at construction."""
        with pytest.raises(TypeError, match="int"):
            SpindleOn(rpm=True)  # type: ignore[arg-type]

    def test_bool_tnumber_blocks(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> None:
        """ToolChange(True) must BLOCK at construction."""
        with pytest.raises(TypeError, match="int"):
            ToolChange(t_number=True)  # type: ignore[arg-type]

    def test_float_rpm_blocks_cut(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> None:
        """SpindleOn(18000.0) → Linear(z=-2) must BLOCK at construction."""
        with pytest.raises(TypeError, match="int"):
            SpindleOn(rpm=18000.0)  # type: ignore[arg-type]


# ── Regression: unknown GCodeCommand type → BLOCKING ─────────────────


class TestUnknownCommandType:
    """Unrecognised GCodeCommand subclass must BLOCK — exhaustive guard."""

    def test_base_gcode_command_blocks(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> None:
        """Bare GCodeCommand() is not a recognised type → BLOCKING."""
        report = validate_gcode_ir(
            commands=[GCodeCommand()],
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        unknown_findings = [
            f for f in report.findings
            if "Неизвестная IR команда" in f.message
        ]
        assert len(unknown_findings) == 1
        assert unknown_findings[0].severity == Severity.BLOCKING
        assert "GCodeCommand" in unknown_findings[0].message

    def test_custom_subclass_blocks(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> None:
        """Custom subclass not in the dispatch table → BLOCKING."""

        class MysteryCommand(GCodeCommand):
            """Unregistered command type."""
            pass

        report = validate_gcode_ir(
            commands=[MysteryCommand()],
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        unknown_findings = [
            f for f in report.findings
            if "Неизвестная IR команда" in f.message
        ]
        assert len(unknown_findings) == 1
        assert unknown_findings[0].severity == Severity.BLOCKING
        assert "MysteryCommand" in unknown_findings[0].message

    def test_known_commands_still_pass(
        self, basic_profile: MachineProfile, basic_tool_library: ToolLibrary
    ) -> None:
        """Known commands (Rapid, SpindleOff, CancelCycle, ProgramEnd) must NOT
        trigger the unknown-command guard."""
        report = validate_gcode_ir(
            commands=[
                Rapid(x=10.0, y=10.0, z=50.0),
                SpindleOff(),
                CancelCycle(),
                ProgramEnd(),
            ],
            profile=basic_profile,
            tool_library=basic_tool_library,
            panel_width=600.0,
            panel_height=400.0,
        )
        unknown_findings = [
            f for f in report.findings
            if "Неизвестная IR команда" in f.message
        ]
        assert len(unknown_findings) == 0
