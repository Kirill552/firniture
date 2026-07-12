"""Чистые неизменяемые контракты вызовов инструментов диалога.

Лимиты по умолчанию намеренно подходят только для безопасных тестов. Production-слой
должен внедрить отдельно согласованные владельцем значения; этот модуль ничего не
сохраняет и не вызывает API.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import cast

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


class ToolErrorCode(StrEnum):
    """Стабильные причины отклонения входа инструмента."""

    INVALID_JSON = "invalid_json"
    MISSING_NAME = "missing_name"
    MISSING_ARGUMENTS = "missing_arguments"
    INVALID_ARGUMENTS = "invalid_arguments"


@dataclass(frozen=True)
class ToolError:
    """Безопасная ошибка контракта без сырого входа и исключения."""

    code: ToolErrorCode
    message: str

    def __post_init__(self) -> None:
        _require_text(self.message, "message")


@dataclass(frozen=True)
class ToolCall:
    """Явный вызов инструмента с типизированным JSON-объектом аргументов."""

    name: str
    arguments: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        _require_text(self.name, "name")
        object.__setattr__(self, "arguments", _freeze_object(self.arguments, "arguments"))

    @classmethod
    def from_json(cls, raw: str) -> ToolCall | ToolError:
        """Явно разобрать вход транспорта; строка не является неявным аргументом."""
        try:
            decoded = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return ToolError(
                ToolErrorCode.INVALID_JSON,
                "Аргументы инструмента должны быть корректным JSON-объектом",
            )
        if not isinstance(decoded, Mapping):
            return ToolError(
                ToolErrorCode.INVALID_JSON,
                "Аргументы инструмента должны быть корректным JSON-объектом",
            )
        name = decoded.get("name")
        if not _is_nonempty_text(name):
            return ToolError(ToolErrorCode.MISSING_NAME, "Для вызова инструмента требуется непустое имя")
        if "arguments" not in decoded:
            return ToolError(
                ToolErrorCode.MISSING_ARGUMENTS,
                "Для вызова инструмента требуется объект arguments",
            )
        arguments = decoded["arguments"]
        if not isinstance(arguments, Mapping):
            return ToolError(
                ToolErrorCode.INVALID_ARGUMENTS,
                "Поле arguments должно быть JSON-объектом",
            )
        try:
            return cls(name=name, arguments=cast(Mapping[str, JsonValue], arguments))
        except ValueError:
            return ToolError(
                ToolErrorCode.INVALID_ARGUMENTS,
                "Поле arguments должно содержать только JSON-значения",
            )


@dataclass(frozen=True)
class ToolResult:
    """Типизированный результат инструмента без неявного разбора JSON-строк."""

    name: str
    payload: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        _require_text(self.name, "name")
        object.__setattr__(self, "payload", _freeze_object(self.payload, "payload"))


@dataclass(frozen=True)
class DialogueLimits:
    """Границы loop и payload, которые production обязан задать явно."""

    max_iterations: int = 1
    max_parallel_calls: int = 1
    max_history_items: int = 1
    max_output_tokens: int = 1
    max_result_bytes: int = 1

    def __post_init__(self) -> None:
        for field_name in (
            "max_iterations",
            "max_parallel_calls",
            "max_history_items",
            "max_output_tokens",
            "max_result_bytes",
        ):
            _require_positive_int(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class DialogueProposal:
    """Предложение изменения: только patch, без сохранения или применения."""

    patch: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "patch", _freeze_object(self.patch, "patch"))


def _freeze_object(value: object, field_name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} должен быть JSON-объектом")
    frozen: dict[str, JsonValue] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} должен иметь строковые ключи")
        frozen[key] = _freeze_json_value(item, field_name)
    return MappingProxyType(frozen)


def _freeze_json_value(value: object, field_name: str) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return cast(JsonScalar, value)
    if isinstance(value, float):
        if isfinite(value):
            return value
        raise ValueError(f"{field_name} должен содержать конечные JSON-числа")
    if isinstance(value, Mapping):
        return _freeze_object(value, field_name)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item, field_name) for item in value)
    raise ValueError(f"{field_name} должен содержать только JSON-значения")


def _require_positive_int(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} должен быть положительным конечным целым числом")


def _require_text(value: object, field_name: str) -> None:
    if not _is_nonempty_text(value):
        raise ValueError(f"{field_name} должен быть непустой строкой")


def _is_nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
