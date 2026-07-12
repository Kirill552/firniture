import asyncio

import pytest

from api.ai.client import ProviderAwareAIClient
from api.ai.contracts import (
    ProviderResponse,
    ProviderSettings,
    ProviderTransportError,
    TransportErrorKind,
    TransportMode,
)
from api.ai.usage import TokenBudget, UsageRecord


class ScriptedSender:
    def __init__(self, outcomes: list[ProviderResponse | BaseException | object]) -> None:
        self._outcomes = outcomes
        self.calls = 0

    async def __call__(self, _: object) -> ProviderResponse:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome  # type: ignore[return-value]


async def _no_sleep(_: float) -> None:
    return None


def _production_settings(max_attempts: int = 3) -> ProviderSettings:
    return ProviderSettings(
        provider="openrouter",
        mode=TransportMode.PRODUCTION,
        base_url="https://openrouter.example/v1",
        api_key="test-key",
        max_attempts=max_attempts,
    )


def _response(status_code: int) -> ProviderResponse:
    return ProviderResponse(provider="openrouter", status_code=status_code, payload={"id": "req-1"})


@pytest.mark.parametrize("status_code", [400, 401, 402])
async def test_does_not_retry_non_retryable_client_statuses(status_code: int) -> None:
    sender = ScriptedSender([_response(status_code)])
    client = ProviderAwareAIClient(_production_settings(), sender, sleep=_no_sleep)

    with pytest.raises(ProviderTransportError) as raised:
        await client.execute(operation="chat_completion", payload={"model": "test-model"})

    error = raised.value
    assert error.status_code == status_code
    assert error.retryable is False
    assert error.attempts == 1
    assert sender.calls == 1


@pytest.mark.parametrize("status_code", [408, 429, 500, 503])
async def test_retries_retryable_http_statuses_only_up_to_configured_bound(status_code: int) -> None:
    sender = ScriptedSender([_response(status_code), _response(status_code), _response(status_code)])
    delays: list[float] = []

    async def record_delay(delay: float) -> None:
        delays.append(delay)

    client = ProviderAwareAIClient(_production_settings(max_attempts=3), sender, sleep=record_delay)

    with pytest.raises(ProviderTransportError) as raised:
        await client.execute(operation="chat_completion", payload={"model": "test-model"})

    error = raised.value
    assert error.status_code == status_code
    assert error.retryable is True
    assert error.attempts == 3
    assert sender.calls == 3
    assert len(delays) == 2


async def test_retries_timeout_then_returns_success_without_network() -> None:
    sender = ScriptedSender([TimeoutError(), _response(200)])
    client = ProviderAwareAIClient(_production_settings(), sender, sleep=_no_sleep)

    response = await client.execute(operation="chat_completion", payload={"model": "test-model"})

    assert response.status_code == 200
    assert sender.calls == 2


async def test_retries_disconnect_then_returns_success_without_network() -> None:
    sender = ScriptedSender([ConnectionError("disconnect"), _response(200)])
    client = ProviderAwareAIClient(_production_settings(), sender, sleep=_no_sleep)

    response = await client.execute(operation="chat_completion", payload={"model": "test-model"})

    assert response.status_code == 200
    assert sender.calls == 2


async def test_propagates_cancellation_without_retrying() -> None:
    sender = ScriptedSender([asyncio.CancelledError()])
    client = ProviderAwareAIClient(_production_settings(), sender, sleep=_no_sleep)

    with pytest.raises(asyncio.CancelledError):
        await client.execute(operation="chat_completion", payload={"model": "test-model"})

    assert sender.calls == 1


async def test_rejects_malformed_sender_response_without_retrying() -> None:
    sender = ScriptedSender([object()])
    client = ProviderAwareAIClient(_production_settings(), sender, sleep=_no_sleep)

    with pytest.raises(ProviderTransportError) as raised:
        await client.execute(operation="chat_completion", payload={"model": "test-model"})

    error = raised.value
    assert error.kind is TransportErrorKind.MALFORMED_RESPONSE
    assert error.retryable is False
    assert error.attempts == 1
    assert sender.calls == 1


def test_local_mock_settings_prohibit_provider_credentials_and_production_requires_them() -> None:
    local = ProviderSettings.local_mock()

    assert local.mode is TransportMode.LOCAL_MOCK
    assert local.base_url is None
    assert local.api_key is None
    assert local.max_attempts == 1

    with pytest.raises(ValueError, match="production"):
        ProviderSettings(provider="openrouter", mode=TransportMode.PRODUCTION)
    with pytest.raises(ValueError, match="local mock"):
        ProviderSettings(
            provider="local-mock",
            mode=TransportMode.LOCAL_MOCK,
            api_key="test-key",
        )


def test_usage_record_exposes_only_redacted_metering_fields() -> None:
    record = UsageRecord(
        provider="openrouter",
        model="test-model",
        prompt_tokens=11,
        completion_tokens=7,
        request_id="req-1",
    )

    assert record.total_tokens == 18
    assert record.as_redacted_dict() == {
        "provider": "openrouter",
        "model": "test-model",
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
        "request_id": "req-1",
    }


def test_budget_denies_usage_when_limit_is_unknown_or_exceeded() -> None:
    record = UsageRecord(
        provider="openrouter",
        model="test-model",
        prompt_tokens=11,
        completion_tokens=7,
    )

    unknown = TokenBudget(limit_tokens=None).reserve(record)
    exceeded = TokenBudget(limit_tokens=17).reserve(record)
    admitted = TokenBudget(limit_tokens=18).reserve(record)

    assert unknown.allowed is False
    assert unknown.reason == "budget_not_configured"
    assert exceeded.allowed is False
    assert exceeded.reason == "budget_exceeded"
    assert admitted.allowed is True
    assert admitted.next_budget == TokenBudget(limit_tokens=18, used_tokens=18)


def test_budget_rejects_negative_used_tokens_even_when_limit_is_unlimited() -> None:
    record = UsageRecord(
        provider="openrouter",
        model="test-model",
        prompt_tokens=11,
        completion_tokens=7,
    )

    decision = TokenBudget(limit_tokens=-1, used_tokens=-1).reserve(record)

    assert decision.allowed is False
    assert decision.reason == "budget_invalid"
    assert decision.next_budget == TokenBudget(limit_tokens=-1, used_tokens=-1)

def test_unlimited_budget_reserves_usage_in_a_new_budget_for_audit_metering() -> None:
    record = UsageRecord(
        provider="openrouter",
        model="test-model",
        prompt_tokens=11,
        completion_tokens=7,
    )
    budget = TokenBudget(limit_tokens=-1, used_tokens=5)

    decision = budget.reserve(record)

    assert decision.allowed is True
    assert decision.reason is None
    assert decision.next_budget == TokenBudget(limit_tokens=-1, used_tokens=23)
    assert decision.next_budget is not budget
