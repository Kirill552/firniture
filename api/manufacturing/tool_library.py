"""Библиотека инструментов — маппинги tool_id → T-номер и параметры.

Exclusive file для Task 13. Связывает логические идентификаторы инструментов
с аппаратными параметрами станка: T-номер, диаметр, семейство операций,
номер шпинделя, максимальная глубина, диапазоны RPM и подачи.

Зависимости: только pydantic, стандартная библиотека.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

# ── Перечисления ────────────────────────────────────────────────────


class OperationFamily(str, Enum):
    """Семейство операций, которое выполняет инструмент."""

    DRILL = "drill"
    SLOT = "slot"
    POCKET = "pocket"
    EDGE = "edge"
    DRILL_SLOTTING = "drill_slotting"


# ── Маппинг инструмента ────────────────────────────────────────────


class ToolMapping(BaseModel):
    """Маппинг одного инструмента на параметры станка.

    Логический ``tool_id`` (напр. ``drill-32x8``) связывается
    с физическим T-номером в магазине инструментов.
    """

    tool_id: str = Field(..., min_length=1, description="Логический идентификатор инструмента")
    t_number: int = Field(..., ge=0, description="T-номер в магазине инструментов")
    diameter_mm: float = Field(..., gt=0, description="Рабочий диаметр, мм")
    operation_family: OperationFamily = Field(..., description="Семейство операций")
    spindle_id: int = Field(..., gt=0, description="Номер шпинделя")
    max_depth_mm: float = Field(..., gt=0, description="Максимальная глубина резания, мм")
    rpm_min: int = Field(..., gt=0, description="Минимальные рекомендованные об/мин")
    rpm_max: int = Field(..., gt=0, description="Максимальные рекомендованные об/мин")
    feed_min: float = Field(..., gt=0, description="Минимальная рекомендованная подача, мм/мин")
    feed_max: float = Field(..., gt=0, description="Максимальная рекомендованная подача, мм/мин")
    notes: str | None = Field(default=None, description="Примечания по инструменту")

    @model_validator(mode="after")
    def _validate_ranges(self) -> ToolMapping:
        """Диапазоны RPM и подачи должны быть корректными."""
        if self.rpm_max < self.rpm_min:
            raise ValueError(
                f"rpm_max ({self.rpm_max}) < rpm_min ({self.rpm_min})"
            )
        if self.feed_max < self.feed_min:
            raise ValueError(
                f"feed_max ({self.feed_max}) < feed_min ({self.feed_min})"
            )
        return self


# ── Библиотека инструментов ─────────────────────────────────────────


class ToolLibrary(BaseModel):
    """Коллекция маппингов инструментов для конкретного станка.

    Гарантирует уникальность ``tool_id`` и ``t_number`` в пределах библиотеки.
    """

    tools: list[ToolMapping] = Field(default_factory=list, description="Список инструментов")

    @model_validator(mode="after")
    def _validate_uniqueness(self) -> ToolLibrary:
        """T-номера и tool_id должны быть уникальными."""
        t_seen: dict[int, int] = {}
        id_seen: dict[str, int] = {}
        for idx, tool in enumerate(self.tools):
            if tool.t_number in t_seen:
                raise ValueError(
                    f"T-number {tool.t_number} дублируется "
                    f"(позиции {t_seen[tool.t_number]} и {idx})"
                )
            t_seen[tool.t_number] = idx

            if tool.tool_id in id_seen:
                raise ValueError(
                    f"tool_id '{tool.tool_id}' дублируется "
                    f"(позиции {id_seen[tool.tool_id]} и {idx})"
                )
            id_seen[tool.tool_id] = idx
        return self

    def get_by_tool_id(self, tool_id: str) -> ToolMapping | None:
        """Найти инструмент по логическому идентификатору."""
        for tool in self.tools:
            if tool.tool_id == tool_id:
                return tool
        return None

    def get_by_t_number(self, t_number: int) -> ToolMapping | None:
        """Найти инструмент по T-номеру."""
        for tool in self.tools:
            if tool.t_number == t_number:
                return tool
        return None

    def filter_by_family(self, family: OperationFamily) -> list[ToolMapping]:
        """Получить все инструменты указанного семейства операций."""
        return [t for t in self.tools if t.operation_family is family]

    def get_all_by_spindle(self, spindle_id: int) -> list[ToolMapping]:
        """Получить все инструменты, назначенные на указанный шпиндель."""
        return [t for t in self.tools if t.spindle_id == spindle_id]
