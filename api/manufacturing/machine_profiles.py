"""Профили станков CNC — доменные модели.

Exclusive file. Описывает аппаратные возможности станка:
контроллер, оси, шпинделы, ограничения подач/оборотов, синтаксис выдержки (dwell_syntax),
стиль окончания строк, work_offset, сертификационный статус и версию постпроцессора.

Это источник контрактов для постпроцессоров (диалекты FANUC/Syntec/Weihong).
Статус сертификации (VERIFIED) — только по ручной проверке; Task 20 физическая
сертификация (симулятор/air-cut) не завершена и не заявляется как готовая.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from api.manufacturing.contracts import Face

# ── Перечисления ────────────────────────────────────────────────────


class ControllerType(str, Enum):
    """Тип CNC-контроллера.

    Поддерживаемые в мебельном производстве:
    weihong, syntec, fanuc, dsp, homag — основные на российском рынке.
    """

    WEIHONG = "weihong"
    SYNTEC = "syntec"
    FANUC = "fanuc"
    DSP = "dsp"
    HOMAG = "homag"
    BIESSE = "biesse"
    IKE = "ike"
    MARKER = "marker"
    WEEKE = "weeke"
    OTHER = "other"


class Units(str, Enum):
    """Единицы измерения станка."""

    MM = "mm"
    INCH = "inch"


class DwellSyntax(str, Enum):
    """Синтаксис команды выдержки (dwell) на контроллере.

    HOMAG/Biesse используют G4 P<секунды>, некоторые старые контроллеры —
    G4 P<миллисекунды> или G4 X<секунды>.
    """

    G4_P_SECONDS = "G4 P"
    G4_P_MILLISECONDS = "G4 P (ms)"
    G4_X = "G4 X"


class LineEnding(str, Enum):
    """Стиль окончания строк в G-code файле."""

    LF = "lf"
    CRLF = "crlf"
    CR = "cr"


class CertificationStatus(str, Enum):
    """Статус верификации профиля станка.

    - draft: черновик, ещё не проверен на реальном станке
    - verified: проверен оператором / инженером
    - deprecated: профиль устарел, не использовать
    """

    DRAFT = "draft"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"


# ── Вложенные модели ────────────────────────────────────────────────


class SpindleConfig(BaseModel):
    """Конфигурация одного шпинделя."""

    spindle_id: int = Field(..., gt=0, description="Идентификатор шпинделя (1, 2, ...)")
    name: str = Field(..., min_length=1, description="Название шпинделя")
    max_rpm: int = Field(..., gt=0, description="Максимальные обороты об/мин")
    max_power_kw: float | None = Field(
        default=None, gt=0, description="Мощность шпинделя, кВт"
    )


class AxisLimits(BaseModel):
    """Ограничения перемещения по осям (в мм или дюймах)."""

    x_min: float = Field(..., description="Минимальная позиция по X")
    x_max: float = Field(..., description="Максимальная позиция по X")
    y_min: float = Field(..., description="Минимальная позиция по Y")
    y_max: float = Field(..., description="Максимальная позиция по Y")
    z_min: float = Field(..., description="Минимальная позиция по Z (отрицательная = в стол)")
    z_max: float = Field(..., description="Максимальная позиция по Z")

    def model_post_init(self, __unused_context: object) -> None:
        """Валидация: max >= min для каждой оси."""
        errors: list[str] = []
        for axis, lo, hi in [
            ("X", self.x_min, self.x_max),
            ("Y", self.y_min, self.y_max),
            ("Z", self.z_min, self.z_max),
        ]:
            if hi < lo:
                errors.append(f"{axis}_max ({hi}) < {axis}_min ({lo})")
        if errors:
            raise ValueError(f"Некорректные ограничения осей: {'; '.join(errors)}")


# ── Основная модель ─────────────────────────────────────────────────


class MachineProfile(BaseModel):
    """Профиль CNC-станка.

    Описывает все аппаратные ограничения и особенности,
    которые влияют на генерацию и валидацию G-code.
    """

    profile_id: str = Field(..., min_length=1, description="Уникальный идентификатор профиля")
    controller: ControllerType = Field(..., description="Тип CNC-контроллера")
    controller_version: str = Field(
        ..., min_length=1, description="Версия прошивки / ПО контроллера"
    )
    units: Units = Field(..., description="Единицы измерения станка")
    work_offset: str = Field(
        ..., min_length=1, description="Рабочее смещение (G54, G54.1 P1, ...)"
    )
    supported_faces: list[Face] = Field(
        default_factory=list,
        description="Поддерживаемые грани панели (front, back, top, bottom, left, right)",
    )
    spindles: list[SpindleConfig] = Field(
        default_factory=list, description="Конфигурации шпинделей"
    )
    axis_limits: AxisLimits = Field(..., description="Ограничения перемещения по осям")
    safe_z: float = Field(..., ge=0, description="Безопасная высота отвода Z (мм)")
    feed_min: float = Field(..., gt=0, description="Минимальная подача, мм/мин")
    feed_max: float = Field(..., gt=0, description="Максимальная подача, мм/мин")
    rpm_min: int = Field(..., gt=0, description="Минимальные обороты, об/мин")
    rpm_max: int = Field(..., gt=0, description="Максимальные обороты, об/мин")
    dwell_syntax: DwellSyntax = Field(..., description="Синтаксис команды выдержки")
    line_ending: LineEnding = Field(..., description="Окончание строк в G-code")
    certification: CertificationStatus = Field(
        ..., description="Статус верификации профиля"
    )
    postprocessor_version: str = Field(
        ..., min_length=1, description="Версия постпроцессора"
    )
    notes: str | None = Field(default=None, description="Заметки оператора")
    @field_validator("supported_faces", mode="before")
    @classmethod
    def _normalize_faces(cls, v: object) -> list[Face]:
        """Нормализует регистр грани (FRONT → front) и отвергает невалидные.

        Принимает list или tuple — приводит к list[Face] с нижним регистром.
        Строка отвергается явно: ``"FRONT"`` не является последовательностью
        граней, а итерируется посимвольно.
        """
        if isinstance(v, str):
            raise ValueError(
                "supported_faces expects a sequence of Face values, not a string"
            )
        if isinstance(v, (list, tuple)):
            return [Face(item.lower()) if isinstance(item, str) else Face(item) for item in v]
        return v  # type: ignore[return-value]


    def model_post_init(self, __unused_context: object) -> None:
        """Валидация диапазонов подач и оборотов."""
        if self.feed_max < self.feed_min:
            raise ValueError(
                f"feed_max ({self.feed_max}) < feed_min ({self.feed_min})"
            )
        if self.rpm_max < self.rpm_min:
            raise ValueError(
                f"rpm_max ({self.rpm_max}) < rpm_min ({self.rpm_min})"
            )
