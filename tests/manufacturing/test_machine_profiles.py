"""Тесты для профилей станков и библиотеки инструментов Task 13.

Exclusive files: api/manufacturing/machine_profiles.py, api/manufacturing/tool_library.py
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.manufacturing.contracts import Face
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
from api.manufacturing.tool_library import (
    OperationFamily,
    ToolLibrary,
    ToolMapping,
)

# ── ControllerType ──────────────────────────────────────────────────


class TestControllerType:
    """Перечисление типов контроллеров станков."""

    def test_known_controllers_exist(self) -> None:
        assert ControllerType.WEIHONG.value == "weihong"
        assert ControllerType.SYNTEC.value == "syntec"
        assert ControllerType.FANUC.value == "fanuc"
        assert ControllerType.DSP.value == "dsp"
        assert ControllerType.HOMAG.value == "homag"
        assert ControllerType.BIESSE.value == "biesse"
        assert ControllerType.IKE.value == "ike"
        assert ControllerType.MARKER.value == "marker"
        assert ControllerType.WEEKE.value == "weeke"
        assert ControllerType.OTHER.value == "other"

    def test_is_str_enum(self) -> None:
        assert isinstance(ControllerType.HOMAG, str)
        assert ControllerType("homag") is ControllerType.HOMAG

    def test_invalid_controller_raises(self) -> None:
        with pytest.raises(ValueError):
            ControllerType("nonexistent_brand")


# ── Units ───────────────────────────────────────────────────────────


class TestUnits:
    def test_mm_and_inch(self) -> None:
        assert Units.MM.value == "mm"
        assert Units.INCH.value == "inch"

    def test_is_str_enum(self) -> None:
        assert isinstance(Units.MM, str)


# ── DwellSyntax ─────────────────────────────────────────────────────


class TestDwellSyntax:
    """Синтаксис выдержки (dwell) на разных контроллерах."""

    def test_known_syntaxes(self) -> None:
        assert DwellSyntax.G4_P_SECONDS.value == "G4 P"
        assert DwellSyntax.G4_P_MILLISECONDS.value == "G4 P (ms)"
        assert DwellSyntax.G4_X.value == "G4 X"

    def test_is_str_enum(self) -> None:
        assert isinstance(DwellSyntax.G4_P_SECONDS, str)


# ── LineEnding ──────────────────────────────────────────────────────


class TestLineEnding:
    def test_known_endings(self) -> None:
        assert LineEnding.LF.value == "lf"
        assert LineEnding.CRLF.value == "crlf"
        assert LineEnding.CR.value == "cr"

    def test_from_value(self) -> None:
        assert LineEnding("crlf") is LineEnding.CRLF


# ── CertificationStatus ─────────────────────────────────────────────


class TestCertificationStatus:
    def test_statuses(self) -> None:
        assert CertificationStatus.DRAFT.value == "draft"
        assert CertificationStatus.VERIFIED.value == "verified"
        assert CertificationStatus.DEPRECATED.value == "deprecated"


# ── SpindleConfig ───────────────────────────────────────────────────


class TestSpindleConfig:
    """Конфигурация шпинделя."""

    def test_valid_spindle(self) -> None:
        spindle = SpindleConfig(
            spindle_id=1,
            name="Основной шпиндель",
            max_rpm=24000,
            max_power_kw=9.0,
        )
        assert spindle.spindle_id == 1
        assert spindle.max_rpm == 24000
        assert spindle.max_power_kw == 9.0

    def test_spindle_id_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            SpindleConfig(
                spindle_id=0,
                name="Bad",
                max_rpm=10000,
                max_power_kw=5.0,
            )

    def test_spindle_id_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            SpindleConfig(
                spindle_id=-1,
                name="Negative",
                max_rpm=10000,
                max_power_kw=5.0,
            )

    def test_max_rpm_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            SpindleConfig(
                spindle_id=1,
                name="Zero RPM",
                max_rpm=0,
                max_power_kw=5.0,
            )

    def test_optional_power(self) -> None:
        spindle = SpindleConfig(spindle_id=2, name="Без мощности", max_rpm=18000)
        assert spindle.max_power_kw is None


# ── AxisLimits ──────────────────────────────────────────────────────


class TestAxisLimits:
    """Ограничения перемещения по осям."""

    def test_valid_limits(self) -> None:
        limits = AxisLimits(
            x_min=0.0, x_max=3200.0,
            y_min=0.0, y_max=2100.0,
            z_min=-120.0, z_max=0.0,
        )
        assert limits.x_max == 3200.0
        assert limits.z_min == -120.0

    def test_negative_travel_allowed(self) -> None:
        """Z может быть отрицательным (погружение в стол)."""
        limits = AxisLimits(
            x_min=0, x_max=2000,
            y_min=0, y_max=1000,
            z_min=-150, z_max=0,
        )
        assert limits.z_min == -150

    def test_max_must_exceed_min(self) -> None:
        with pytest.raises(ValidationError):
            AxisLimits(
                x_min=100, x_max=50,  # max < min
                y_min=0, y_max=1000,
                z_min=-100, z_max=0,
            )

    def test_y_max_must_exceed_y_min(self) -> None:
        with pytest.raises(ValidationError):
            AxisLimits(
                x_min=0, x_max=2000,
                y_min=500, y_max=100,  # инверсия
                z_min=-100, z_max=0,
            )


# ── MachineProfile ──────────────────────────────────────────────────


class TestMachineProfile:
    """Основная модель профиля станка."""

    @pytest.fixture()
    def homag_cnc(self) -> MachineProfile:
        """Типичный HOMAG CNC-центр."""
        return MachineProfile(
            profile_id="homag-bmw-211",
            controller=ControllerType.HOMAG,
            controller_version="12.4.1",
            units=Units.MM,
            work_offset="G54",
            supported_faces=[Face.FRONT, Face.BACK, Face.TOP, Face.BOTTOM],
            spindles=[
                SpindleConfig(spindle_id=1, name="主轴", max_rpm=24000, max_power_kw=9.0),
            ],
            axis_limits=AxisLimits(
                x_min=0, x_max=3200,
                y_min=0, y_max=2100,
                z_min=-120, z_max=0,
            ),
            safe_z=50.0,
            feed_min=1.0,
            feed_max=30000.0,
            rpm_min=3000,
            rpm_max=24000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.VERIFIED,
            postprocessor_version="3.2.0",
        )

    def test_profile_creation(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.profile_id == "homag-bmw-211"
        assert homag_cnc.controller is ControllerType.HOMAG
        assert homag_cnc.controller_version == "12.4.1"

    def test_units_mm(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.units is Units.MM

    def test_work_offset(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.work_offset == "G54"

    def test_supported_faces(self, homag_cnc: MachineProfile) -> None:
        assert len(homag_cnc.supported_faces) == 4
        assert Face.FRONT in homag_cnc.supported_faces
        assert Face.TOP in homag_cnc.supported_faces

    def test_spindles(self, homag_cnc: MachineProfile) -> None:
        assert len(homag_cnc.spindles) == 1
        assert homag_cnc.spindles[0].max_rpm == 24000

    def test_axis_limits(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.axis_limits.x_max == 3200
        assert homag_cnc.axis_limits.z_min == -120

    def test_safe_z(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.safe_z == 50.0

    def test_feed_rpm_limits(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.feed_min == 1.0
        assert homag_cnc.feed_max == 30000.0
        assert homag_cnc.rpm_min == 3000
        assert homag_cnc.rpm_max == 24000

    def test_dwell_syntax(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.dwell_syntax is DwellSyntax.G4_P_SECONDS

    def test_line_ending(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.line_ending is LineEnding.LF

    def test_certification(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.certification is CertificationStatus.VERIFIED

    def test_postprocessor_version(self, homag_cnc: MachineProfile) -> None:
        assert homag_cnc.postprocessor_version == "3.2.0"

    def test_profile_id_required(self) -> None:
        with pytest.raises(ValidationError):
            MachineProfile(
                controller=ControllerType.HOMAG,
                controller_version="1.0",
                units=Units.MM,
                work_offset="G54",
                supported_faces=[],
                spindles=[],
                axis_limits=AxisLimits(
                    x_min=0, x_max=1000,
                    y_min=0, y_max=500,
                    z_min=-50, z_max=0,
                ),
                safe_z=50.0,
                feed_min=1.0,
                feed_max=10000.0,
                rpm_min=6000,
                rpm_max=18000,
                dwell_syntax=DwellSyntax.G4_P_SECONDS,
                line_ending=LineEnding.LF,
                certification=CertificationStatus.DRAFT,
                postprocessor_version="1.0.0",
            )

    def test_feed_max_must_exceed_feed_min(self) -> None:
        with pytest.raises(ValidationError):
            MachineProfile(
                profile_id="bad-feed",
                controller=ControllerType.OTHER,
                controller_version="1.0",
                units=Units.MM,
                work_offset="G54",
                supported_faces=[],
                spindles=[],
                axis_limits=AxisLimits(
                    x_min=0, x_max=1000,
                    y_min=0, y_max=500,
                    z_min=-50, z_max=0,
                ),
                safe_z=50.0,
                feed_min=5000.0,
                feed_max=1000.0,  # max < min
                rpm_min=6000,
                rpm_max=18000,
                dwell_syntax=DwellSyntax.G4_P_SECONDS,
                line_ending=LineEnding.LF,
                certification=CertificationStatus.DRAFT,
                postprocessor_version="1.0.0",
            )

    def test_rpm_max_must_exceed_rpm_min(self) -> None:
        with pytest.raises(ValidationError):
            MachineProfile(
                profile_id="bad-rpm",
                controller=ControllerType.OTHER,
                controller_version="1.0",
                units=Units.MM,
                work_offset="G54",
                supported_faces=[],
                spindles=[],
                axis_limits=AxisLimits(
                    x_min=0, x_max=1000,
                    y_min=0, y_max=500,
                    z_min=-50, z_max=0,
                ),
                safe_z=50.0,
                feed_min=1.0,
                feed_max=10000.0,
                rpm_min=18000,
                rpm_max=6000,  # max < min
                dwell_syntax=DwellSyntax.G4_P_SECONDS,
                line_ending=LineEnding.LF,
                certification=CertificationStatus.DRAFT,
                postprocessor_version="1.0.0",
            )

    def test_safe_z_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            MachineProfile(
                profile_id="neg-safe-z",
                controller=ControllerType.OTHER,
                controller_version="1.0",
                units=Units.MM,
                work_offset="G54",
                supported_faces=[],
                spindles=[],
                axis_limits=AxisLimits(
                    x_min=0, x_max=1000,
                    y_min=0, y_max=500,
                    z_min=-50, z_max=0,
                ),
                safe_z=-10.0,  # отрицательный safe_z — ошибка
                feed_min=1.0,
                feed_max=10000.0,
                rpm_min=6000,
                rpm_max=18000,
                dwell_syntax=DwellSyntax.G4_P_SECONDS,
                line_ending=LineEnding.LF,
                certification=CertificationStatus.DRAFT,
                postprocessor_version="1.0.0",
            )

    def test_multiple_spindles(self) -> None:
        profile = MachineProfile(
            profile_id="dual-spindle",
            controller=ControllerType.BIESSE,
            controller_version="8.1",
            units=Units.MM,
            work_offset="G54",
            supported_faces=[Face.TOP, Face.BOTTOM],
            spindles=[
                SpindleConfig(spindle_id=1, name="Фрезерный", max_rpm=24000, max_power_kw=12.0),
                SpindleConfig(spindle_id=2, name="Сверлильный", max_rpm=6000, max_power_kw=3.5),
            ],
            axis_limits=AxisLimits(
                x_min=0, x_max=3100,
                y_min=0, y_max=2100,
                z_min=-100, z_max=0,
            ),
            safe_z=40.0,
            feed_min=1.0,
            feed_max=25000.0,
            rpm_min=3000,
            rpm_max=24000,
            dwell_syntax=DwellSyntax.G4_P_MILLISECONDS,
            line_ending=LineEnding.CRLF,
            certification=CertificationStatus.VERIFIED,
            postprocessor_version="5.0.1",
        )
        assert len(profile.spindles) == 2
        assert profile.spindles[1].name == "Сверлильный"

    def test_optional_notes(self) -> None:
        profile = MachineProfile(
            profile_id="with-notes",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=[],
            spindles=[],
            axis_limits=AxisLimits(
                x_min=0, x_max=1000,
                y_min=0, y_max=500,
                z_min=-50, z_max=0,
            ),
            safe_z=50.0,
            feed_min=1.0,
            feed_max=10000.0,
            rpm_min=6000,
            rpm_max=18000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="1.0.0",
            notes="Тестовый профиль",
        )
        assert profile.notes == "Тестовый профиль"

    def test_empty_supported_faces_allowed(self) -> None:
        """Профиль может не поддерживать ни одной грани (ещё не настроен)."""
        profile = MachineProfile(
            profile_id="no-faces",
            controller=ControllerType.OTHER,
            controller_version="0.1",
            units=Units.INCH,
            work_offset="G54",
            supported_faces=[],
            spindles=[],
            axis_limits=AxisLimits(
                x_min=0, x_max=500,
                y_min=0, y_max=250,
                z_min=-50, z_max=0,
            ),
            safe_z=25.0,
            feed_min=0.5,
            feed_max=15000.0,
            rpm_min=3000,
            rpm_max=18000,
            dwell_syntax=DwellSyntax.G4_X,
            line_ending=LineEnding.CR,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="0.0.1",
        )
        assert profile.supported_faces == []

    def test_supported_faces_are_canonical_face_enum(self) -> None:
        """supported_faces хранит именно Face enum, а не строки."""
        profile = MachineProfile(
            profile_id="face-enum",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=[Face.FRONT, Face.BACK],
            spindles=[],
            axis_limits=AxisLimits(
                x_min=0, x_max=1000, y_min=0, y_max=500,
                z_min=-50, z_max=0,
            ),
            safe_z=50.0, feed_min=1.0, feed_max=10000.0,
            rpm_min=3000, rpm_max=18000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="1.0.0",
        )
        assert all(isinstance(f, Face) for f in profile.supported_faces)
        assert profile.supported_faces[0] is Face.FRONT
        assert profile.supported_faces[1] is Face.BACK

    def test_supported_faces_normalizes_uppercase_input(self) -> None:
        """Входные строки в любом регистре нормализуются к canonical Face."""
        profile = MachineProfile(
            profile_id="case-norm",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=["FRONT", "Back", "top"],
            spindles=[],
            axis_limits=AxisLimits(
                x_min=0, x_max=1000, y_min=0, y_max=500,
                z_min=-50, z_max=0,
            ),
            safe_z=50.0, feed_min=1.0, feed_max=10000.0,
            rpm_min=3000, rpm_max=18000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="1.0.0",
        )
        assert profile.supported_faces == [Face.FRONT, Face.BACK, Face.TOP]
    def test_supported_faces_tuple_uppercase_normalizes(self) -> None:
        """Tuple input with uppercase strings normalizes identically to list."""
        profile_list = MachineProfile(
            profile_id="list-case",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=["FRONT", "BACK"],
            spindles=[],
            axis_limits=AxisLimits(
                x_min=0, x_max=1000, y_min=0, y_max=500,
                z_min=-50, z_max=0,
            ),
            safe_z=50.0, feed_min=1.0, feed_max=10000.0,
            rpm_min=3000, rpm_max=18000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="1.0.0",
        )
        profile_tuple = MachineProfile(
            profile_id="tuple-case",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=("FRONT", "BACK"),
            spindles=[],
            axis_limits=AxisLimits(
                x_min=0, x_max=1000, y_min=0, y_max=500,
                z_min=-50, z_max=0,
            ),
            safe_z=50.0, feed_min=1.0, feed_max=10000.0,
            rpm_min=3000, rpm_max=18000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="1.0.0",
        )
        assert profile_tuple.supported_faces == profile_list.supported_faces
        assert profile_tuple.supported_faces == [Face.FRONT, Face.BACK]
        assert isinstance(profile_tuple.supported_faces, list)

    def test_supported_faces_rejects_invalid_value(self) -> None:
        """Невалидное значение грани вызывает ошибку валидации."""
        with pytest.raises(ValidationError):
            MachineProfile(
                profile_id="bad-face",
                controller=ControllerType.OTHER,
                controller_version="1.0",
                units=Units.MM,
                work_offset="G54",
                supported_faces=["INVALID_FACE"],
                spindles=[],
                axis_limits=AxisLimits(
                    x_min=0, x_max=1000, y_min=0, y_max=500,
                    z_min=-50, z_max=0,
                ),
                safe_z=50.0, feed_min=1.0, feed_max=10000.0,
                rpm_min=3000, rpm_max=18000,
                dwell_syntax=DwellSyntax.G4_P_SECONDS,
                line_ending=LineEnding.LF,
                certification=CertificationStatus.DRAFT,
                postprocessor_version="1.0.0",
            )
    def test_supported_faces_rejects_bare_string(self) -> None:
        """Bare string 'FRONT' must raise ValidationError, not TypeError."""
        with pytest.raises(ValidationError):
            MachineProfile(
                profile_id="bare-str",
                controller=ControllerType.OTHER,
                controller_version="1.0",
                units=Units.MM,
                work_offset="G54",
                supported_faces="FRONT",
                spindles=[],
                axis_limits=AxisLimits(
                    x_min=0, x_max=1000, y_min=0, y_max=500,
                    z_min=-50, z_max=0,
                ),
                safe_z=50.0, feed_min=1.0, feed_max=10000.0,
                rpm_min=3000, rpm_max=18000,
                dwell_syntax=DwellSyntax.G4_P_SECONDS,
                line_ending=LineEnding.LF,
                certification=CertificationStatus.DRAFT,
                postprocessor_version="1.0.0",
            )

    def test_face_membership_downstream(self) -> None:
        """Face enum сравнение работает корректно в downstream-коде."""
        profile = MachineProfile(
            profile_id="membership",
            controller=ControllerType.OTHER,
            controller_version="1.0",
            units=Units.MM,
            work_offset="G54",
            supported_faces=[Face.FRONT, Face.LEFT],
            spindles=[],
            axis_limits=AxisLimits(
                x_min=0, x_max=1000, y_min=0, y_max=500,
                z_min=-50, z_max=0,
            ),
            safe_z=50.0, feed_min=1.0, feed_max=10000.0,
            rpm_min=3000, rpm_max=18000,
            dwell_syntax=DwellSyntax.G4_P_SECONDS,
            line_ending=LineEnding.LF,
            certification=CertificationStatus.DRAFT,
            postprocessor_version="1.0.0",
        )
        # Типичный downstream-паттерн: проверка вхождения Face в supported_faces
        assert Face.FRONT in profile.supported_faces
        assert Face.BACK not in profile.supported_faces
        # Сравнение через .value тоже работает
        assert Face.FRONT.value == "front"



# ── OperationFamily ─────────────────────────────────────────────────


class TestOperationFamily:
    def test_known_families(self) -> None:
        assert OperationFamily.DRILL.value == "drill"
        assert OperationFamily.SLOT.value == "slot"
        assert OperationFamily.POCKET.value == "pocket"
        assert OperationFamily.EDGE.value == "edge"
        assert OperationFamily.DRILL_SLOTTING.value == "drill_slotting"

    def test_is_str_enum(self) -> None:
        assert isinstance(OperationFamily.DRILL, str)
        assert OperationFamily("pocket") is OperationFamily.POCKET


# ── ToolMapping ─────────────────────────────────────────────────────


class TestToolMapping:
    """Маппинг инструмента на станок."""

    def test_valid_tool(self) -> None:
        tool = ToolMapping(
            tool_id="drill-32x8",
            t_number=10,
            diameter_mm=32.0,
            operation_family=OperationFamily.DRILL,
            spindle_id=1,
            max_depth_mm=40.0,
            rpm_min=12000,
            rpm_max=18000,
            feed_min=2000.0,
            feed_max=8000.0,
        )
        assert tool.tool_id == "drill-32x8"
        assert tool.t_number == 10
        assert tool.diameter_mm == 32.0

    def test_t_number_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ToolMapping(
                tool_id="bad",
                t_number=-1,
                diameter_mm=10.0,
                operation_family=OperationFamily.DRILL,
                spindle_id=1,
                max_depth_mm=20.0,
                rpm_min=6000,
                rpm_max=18000,
                feed_min=1000.0,
                feed_max=5000.0,
            )

    def test_diameter_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ToolMapping(
                tool_id="zero-dia",
                t_number=1,
                diameter_mm=0.0,
                operation_family=OperationFamily.DRILL,
                spindle_id=1,
                max_depth_mm=20.0,
                rpm_min=6000,
                rpm_max=18000,
                feed_min=1000.0,
                feed_max=5000.0,
            )

    def test_max_depth_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ToolMapping(
                tool_id="no-depth",
                t_number=1,
                diameter_mm=10.0,
                operation_family=OperationFamily.DRILL,
                spindle_id=1,
                max_depth_mm=0.0,
                rpm_min=6000,
                rpm_max=18000,
                feed_min=1000.0,
                feed_max=5000.0,
            )

    def test_rpm_max_must_exceed_rpm_min(self) -> None:
        with pytest.raises(ValidationError):
            ToolMapping(
                tool_id="bad-rpm",
                t_number=1,
                diameter_mm=10.0,
                operation_family=OperationFamily.DRILL,
                spindle_id=1,
                max_depth_mm=20.0,
                rpm_min=18000,
                rpm_max=6000,  # инверсия
                feed_min=1000.0,
                feed_max=5000.0,
            )

    def test_feed_max_must_exceed_feed_min(self) -> None:
        with pytest.raises(ValidationError):
            ToolMapping(
                tool_id="bad-feed",
                t_number=1,
                diameter_mm=10.0,
                operation_family=OperationFamily.DRILL,
                spindle_id=1,
                max_depth_mm=20.0,
                rpm_min=6000,
                rpm_max=18000,
                feed_min=5000.0,
                feed_max=1000.0,  # инверсия
            )

    def test_optional_notes(self) -> None:
        tool = ToolMapping(
            tool_id="slot-8",
            t_number=5,
            diameter_mm=8.0,
            operation_family=OperationFamily.SLOT,
            spindle_id=1,
            max_depth_mm=18.0,
            rpm_min=16000,
            rpm_max=22000,
            feed_min=3000.0,
            feed_max=12000.0,
            notes="Пазовая фреза HSS",
        )
        assert tool.notes == "Пазовая фреза HSS"

    def test_spindle_id_positive(self) -> None:
        with pytest.raises(ValidationError):
            ToolMapping(
                tool_id="bad-spindle",
                t_number=1,
                diameter_mm=10.0,
                operation_family=OperationFamily.DRILL,
                spindle_id=0,
                max_depth_mm=20.0,
                rpm_min=6000,
                rpm_max=18000,
                feed_min=1000.0,
                feed_max=5000.0,
            )


# ── ToolLibrary ─────────────────────────────────────────────────────


class TestToolLibrary:
    """Коллекция маппингов инструментов для станка."""

    @pytest.fixture()
    def sample_library(self) -> ToolLibrary:
        return ToolLibrary(
            tools=[
                ToolMapping(
                    tool_id="drill-32x8",
                    t_number=10,
                    diameter_mm=32.0,
                    operation_family=OperationFamily.DRILL,
                    spindle_id=1,
                    max_depth_mm=40.0,
                    rpm_min=12000,
                    rpm_max=18000,
                    feed_min=2000.0,
                    feed_max=8000.0,
                ),
                ToolMapping(
                    tool_id="slot-8x22",
                    t_number=11,
                    diameter_mm=8.0,
                    operation_family=OperationFamily.SLOT,
                    spindle_id=1,
                    max_depth_mm=22.0,
                    rpm_min=16000,
                    rpm_max=22000,
                    feed_min=3000.0,
                    feed_max=12000.0,
                ),
                ToolMapping(
                    tool_id="pocket-20x35",
                    t_number=12,
                    diameter_mm=20.0,
                    operation_family=OperationFamily.POCKET,
                    spindle_id=1,
                    max_depth_mm=35.0,
                    rpm_min=14000,
                    rpm_max=20000,
                    feed_min=2500.0,
                    feed_max=10000.0,
                ),
            ],
        )

    def test_tool_count(self, sample_library: ToolLibrary) -> None:
        assert len(sample_library.tools) == 3

    def test_find_tool_by_id(self, sample_library: ToolLibrary) -> None:
        tool = sample_library.get_by_tool_id("slot-8x22")
        assert tool is not None
        assert tool.t_number == 11

    def test_find_tool_by_t_number(self, sample_library: ToolLibrary) -> None:
        tool = sample_library.get_by_t_number(10)
        assert tool is not None
        assert tool.tool_id == "drill-32x8"

    def test_missing_tool_id_returns_none(self, sample_library: ToolLibrary) -> None:
        assert sample_library.get_by_tool_id("nonexistent") is None

    def test_missing_t_number_returns_none(self, sample_library: ToolLibrary) -> None:
        assert sample_library.get_by_t_number(999) is None

    def test_filter_by_operation_family(self, sample_library: ToolLibrary) -> None:
        drills = sample_library.filter_by_family(OperationFamily.DRILL)
        assert len(drills) == 1
        assert drills[0].tool_id == "drill-32x8"

    def test_filter_by_family_empty(self, sample_library: ToolLibrary) -> None:
        edges = sample_library.filter_by_family(OperationFamily.EDGE)
        assert len(edges) == 0

    def test_duplicate_t_number_raises(self) -> None:
        with pytest.raises(ValidationError, match="T-number"):
            ToolLibrary(
                tools=[
                    ToolMapping(
                        tool_id="a",
                        t_number=10,
                        diameter_mm=10.0,
                        operation_family=OperationFamily.DRILL,
                        spindle_id=1,
                        max_depth_mm=20.0,
                        rpm_min=6000,
                        rpm_max=18000,
                        feed_min=1000.0,
                        feed_max=5000.0,
                    ),
                    ToolMapping(
                        tool_id="b",
                        t_number=10,  # дубликат
                        diameter_mm=8.0,
                        operation_family=OperationFamily.SLOT,
                        spindle_id=1,
                        max_depth_mm=15.0,
                        rpm_min=8000,
                        rpm_max=20000,
                        feed_min=2000.0,
                        feed_max=6000.0,
                    ),
                ],
            )

    def test_duplicate_tool_id_raises(self) -> None:
        with pytest.raises(ValidationError, match="tool_id"):
            ToolLibrary(
                tools=[
                    ToolMapping(
                        tool_id="same-id",
                        t_number=10,
                        diameter_mm=10.0,
                        operation_family=OperationFamily.DRILL,
                        spindle_id=1,
                        max_depth_mm=20.0,
                        rpm_min=6000,
                        rpm_max=18000,
                        feed_min=1000.0,
                        feed_max=5000.0,
                    ),
                    ToolMapping(
                        tool_id="same-id",  # дубликат
                        t_number=11,
                        diameter_mm=8.0,
                        operation_family=OperationFamily.SLOT,
                        spindle_id=1,
                        max_depth_mm=15.0,
                        rpm_min=8000,
                        rpm_max=20000,
                        feed_min=2000.0,
                        feed_max=6000.0,
                    ),
                ],
            )

    def test_empty_library_valid(self) -> None:
        lib = ToolLibrary(tools=[])
        assert len(lib.tools) == 0

    def test_get_all_by_spindle(self, sample_library: ToolLibrary) -> None:
        sp1 = sample_library.get_all_by_spindle(1)
        assert len(sp1) == 3
        sp99 = sample_library.get_all_by_spindle(99)
        assert len(sp99) == 0
