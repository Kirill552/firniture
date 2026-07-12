"""G-code IR — типизированные промежуточные команды.

Каждая команда описывает *что* делать, не *как* рендерить G-code.
Постпроцессор (Task 15+) переводит IR в текст контроллера.

Зависимости: только pydantic, dataclasses.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# ── Базовый класс ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class GCodeCommand:
    """Базовый класс для всех IR команд G-code.

    Frozen dataclass: иммутабельность, хешируемость, нет pydantic overhead.
    """


# ── Команды перемещения ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Rapid(GCodeCommand):
    """Быстрое перемещение G0.

    x, y, z — координаты (None = не изменять по этой оси).
    Хотя бы одна координата должна быть задана.
    """
    x: float | None = None
    y: float | None = None
    z: float | None = None

    def __post_init__(self) -> None:
        errors: list[str] = []
        for name, val in [("x", self.x), ("y", self.y), ("z", self.z)]:
            if val is not None and not math.isfinite(val):
                errors.append(f"{name} должен быть конечным числом: {val}")
        if self.x is None and self.y is None and self.z is None:
            errors.append("Rapid должен иметь хотя бы одну не-None координату")
        if errors:
            raise ValueError("; ".join(errors))


@dataclass(frozen=True, slots=True)
class Linear(GCodeCommand):
    """Линейное перемещение G1 с подачей.

    feed > 0 — скорость подачи, мм/мин.
    z может быть None (движение в плоскости без смены Z).
    """

    x: float
    y: float
    feed: float
    z: float | None = None

    def __post_init__(self) -> None:
        errors: list[str] = []
        if not math.isfinite(self.x):
            errors.append(f"x должен быть конечным числом: {self.x}")
        if not math.isfinite(self.y):
            errors.append(f"y должен быть конечным числом: {self.y}")
        if self.z is not None and not math.isfinite(self.z):
            errors.append(f"z должен быть конечным числом: {self.z}")
        if not math.isfinite(self.feed) or self.feed <= 0:
            errors.append(f"feed должен быть положительным конечным числом: {self.feed}")
        if errors:
            raise ValueError("; ".join(errors))


# ── Управление инструментом ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ToolChange(GCodeCommand):
    """Смена инструмента Txx M6.

    t_number — номер в магазине инструментов (≥ 0).
    """

    t_number: int

    def __post_init__(self) -> None:
        if isinstance(self.t_number, bool) or not isinstance(self.t_number, int):
            raise TypeError(
                f"t_number должен быть int, "
                f"получен {type(self.t_number).__name__}: {self.t_number!r}"
            )
        if self.t_number < 0:
            raise ValueError(f"t_number не может быть отрицательным: {self.t_number}")


# ── Управление шпинделем ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SpindleOn(GCodeCommand):
    """Включение шпинделя M3 (по часовой) / M4 (против).

    rpm > 0 — скорость вращения.
    """

    rpm: int
    clockwise: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.rpm, bool) or not isinstance(self.rpm, int):
            raise TypeError(
                f"rpm должен быть int, "
                f"получен {type(self.rpm).__name__}: {self.rpm!r}"
            )
        if not math.isfinite(self.rpm):
            raise ValueError(f"rpm должен быть конечным числом: {self.rpm}")
        if self.rpm <= 0:
            raise ValueError(f"rpm должен быть положительным: {self.rpm}")


@dataclass(frozen=True, slots=True)
class SpindleOff(GCodeCommand):
    """Выключение шпинделя M05."""


# ── Циклы ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DrillCycle(GCodeCommand):
    """Цикл сверления G81/G82/G83.

    z — глубина (отрицательная, вниз от поверхности).
    retract — высота отвода при подаче (положительная).
    peck — шаг погружения для G83 (None = G81/G82 без peck).
    dwell — время выдержки на дне, сек (None = без выдержки).
    feed — подача, мм/мин.
    """

    x: float
    y: float
    z: float
    retract: float
    feed: float
    peck: float | None = None
    dwell: float | None = None

    def __post_init__(self) -> None:
        errors: list[str] = []
        # ── finite checks first (NaN/±inf bypass sign checks) ──
        if not math.isfinite(self.x):
            errors.append(f"x должен быть конечным числом: {self.x}")
        if not math.isfinite(self.y):
            errors.append(f"y должен быть конечным числом: {self.y}")
        if not math.isfinite(self.z):
            errors.append(f"z должен быть конечным числом: {self.z}")
        if not math.isfinite(self.retract):
            errors.append(f"retract должен быть конечным числом: {self.retract}")
        if not math.isfinite(self.feed):
            errors.append(f"feed должен быть конечным числом: {self.feed}")
        if self.peck is not None and not math.isfinite(self.peck):
            errors.append(f"peck должен быть конечным числом: {self.peck}")
        if self.dwell is not None and not math.isfinite(self.dwell):
            errors.append(f"dwell должен быть конечным числом: {self.dwell}")
        # ── sign / range checks ──
        if self.z >= 0:
            errors.append(f"z для сверления должен быть отрицательным: {self.z}")
        if self.retract <= 0:
            errors.append(f"retract должен быть положительным: {self.retract}")
        if self.feed <= 0:
            errors.append(f"feed должен быть положительным: {self.feed}")
        if self.peck is not None and self.peck <= 0:
            errors.append(f"peck должен быть положительным: {self.peck}")
        if self.dwell is not None and self.dwell < 0:
            errors.append(f"dwell не может быть отрицательным: {self.dwell}")
        if errors:
            raise ValueError("; ".join(errors))


@dataclass(frozen=True, slots=True)
class CancelCycle(GCodeCommand):
    """Отмена активного цикла G80."""


# ── Конец программы ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProgramEnd(GCodeCommand):
    """Конец программы M30."""


# ── Группировка циклов ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CycleKey:
    """Ключ для группировки совместимых DrillCycle.

    Циклы с одинаковым ключом рендерятся одной группой (G81 ...).
    Разный ключ → новая группа (G80 + G81).
    """

    t_number: int
    face: str
    depth: float
    retract: float
    feed: float
    dwell: float | None
    peck: float | None


def cycle_key(t_number: int, face: str, cycle: DrillCycle) -> CycleKey:
    """Вычислить ключ группировки для DrillCycle.

    Аргументы:
        t_number: номер активного инструмента.
        face: текущая грань панели.
        cycle: команда цикла.

    Raises:
        TypeError: если cycle не DrillCycle.
    """
    if not isinstance(cycle, DrillCycle):
        raise TypeError(
            f"cycle_key() принимает только DrillCycle, получено: {type(cycle).__name__}"
        )
    return CycleKey(
        t_number=t_number,
        face=face,
        depth=cycle.z,
        retract=cycle.retract,
        feed=cycle.feed,
        dwell=cycle.dwell,
        peck=cycle.peck,
    )
