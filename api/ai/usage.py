"""Безопасный учёт AI-usage и fail-closed решение по токенному бюджету."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UsageRecord:
    """Только metering-поля: без prompt, output, URL, заголовков или credentials."""

    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    request_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.provider, "provider")
        _require_text(self.model, "model")
        _require_nonnegative_int(self.prompt_tokens, "prompt_tokens")
        _require_nonnegative_int(self.completion_tokens, "completion_tokens")
        if self.request_id is not None:
            _require_text(self.request_id, "request_id")

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def as_redacted_dict(self) -> dict[str, str | int | None]:
        """Подготовить запись для audit/log без содержимого AI-запроса или ответа."""
        return {
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "request_id": self.request_id,
        }


@dataclass(frozen=True)
class TokenBudget:
    """Неизвестный или повреждённый бюджет запрещает списание вместо permissive fallback."""

    limit_tokens: int | None
    used_tokens: int = 0

    def reserve(self, usage: UsageRecord) -> BudgetDecision:
        """Вернуть новое состояние только для разрешённого списания."""
        if self.limit_tokens is None:
            return BudgetDecision(False, "budget_not_configured", self)
        if not _is_valid_limit_tokens(self.limit_tokens) or not _is_valid_used_tokens(self.used_tokens):
            return BudgetDecision(False, "budget_invalid", self)
        if self.limit_tokens == -1:
            return BudgetDecision(
                True,
                None,
                TokenBudget(
                    limit_tokens=self.limit_tokens,
                    used_tokens=self.used_tokens + usage.total_tokens,
                ),
            )
        next_used_tokens = self.used_tokens + usage.total_tokens
        if next_used_tokens > self.limit_tokens:
            return BudgetDecision(False, "budget_exceeded", self)
        return BudgetDecision(
            True,
            None,
            TokenBudget(limit_tokens=self.limit_tokens, used_tokens=next_used_tokens),
        )


@dataclass(frozen=True)
class BudgetDecision:
    """Явный результат, который интеграционный слой обязан сохранить атомарно."""

    allowed: bool
    reason: str | None
    next_budget: TokenBudget


def _require_text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} должен быть непустой строкой")


def _require_nonnegative_int(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} должен быть неотрицательным целым числом")


def _is_valid_limit_tokens(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= -1


def _is_valid_used_tokens(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
