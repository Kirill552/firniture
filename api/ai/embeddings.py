"""Чистые доменные контракты идентичности и значений embedding.

Production-генерация намеренно недоступна до одобренной человеком интеграции
провайдера и процедуры promotion индекса. Модуль не синтезирует векторы.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import NoReturn


class EmbeddingValidationError(ValueError):
    """Идентичность или значение embedding нарушает доменный контракт."""


class ProductionEmbeddingUnavailableError(RuntimeError):
    """Запрошен production embedding до подключения одобренного провайдера."""

    def __init__(self, identity: EmbeddingIdentity) -> None:
        self.identity = identity
        super().__init__(f"Production-провайдер embedding недоступен для модели {identity.model_id}")


@dataclass(frozen=True)
class EmbeddingIdentity:
    """Версионированная идентичность для безопасного сравнения и хранения embedding."""

    model_id: str
    dimensions: int
    normalized: bool
    input_type: str
    input_version: str

    def __post_init__(self) -> None:
        _require_nonempty_text(self.model_id, "model_id")
        if isinstance(self.dimensions, bool) or not isinstance(self.dimensions, int):
            raise EmbeddingValidationError("dimensions должен быть целым числом")
        if self.dimensions <= 0:
            raise EmbeddingValidationError("dimensions должен быть положительным")
        if not isinstance(self.normalized, bool):
            raise EmbeddingValidationError("normalized должен быть bool")
        _require_nonempty_text(self.input_type, "input_type")
        _require_nonempty_text(self.input_version, "input_version")


@dataclass(frozen=True)
class EmbeddingValue:
    """Конечный вектор, связанный с полной идентичностью модели и входа."""

    identity: EmbeddingIdentity
    vector: Sequence[float]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, EmbeddingIdentity):
            raise EmbeddingValidationError("identity должен быть EmbeddingIdentity")
        vector = _validated_vector(self.vector)
        if len(vector) != self.identity.dimensions:
            raise EmbeddingValidationError(
                f"Размерность вектора {len(vector)} не совпадает с ожидаемой {self.identity.dimensions}"
            )
        object.__setattr__(self, "vector", vector)


def embed_with_production_provider(*, identity: EmbeddingIdentity, text: str) -> NoReturn:
    """Завершить запрос ошибкой до human-gated интеграции production-провайдера.

    ``text`` намеренно не добавляется в ошибку: диагностика не должна раскрывать
    исходный контент, а детерминированный fallback испортил бы индекс.
    """
    _require_nonempty_text(text, "text")
    raise ProductionEmbeddingUnavailableError(identity)


def _validated_vector(value: object) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise EmbeddingValidationError("vector должен быть последовательностью конечных чисел")
    return tuple(_finite_float(component) for component in value)


def _finite_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EmbeddingValidationError("Компоненты vector должны быть конечными числами")
    try:
        number = float(value)
    except OverflowError as error:
        raise EmbeddingValidationError("Компоненты vector должны быть конечными числами") from error
    if not isfinite(number):
        raise EmbeddingValidationError("Компоненты vector должны быть конечными числами")
    return number


def _require_nonempty_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EmbeddingValidationError(f"{field_name} должен быть непустой строкой")
