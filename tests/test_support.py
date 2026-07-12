"""Фокусные тесты ``api.support`` — payload, redaction, response contract.

Все тесты изолированы: ни одного реального секрета, email, или
внешнего вызова. Валидируются: типизация, redaction, контракт
ответа, границы полей.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from api.support import (
    SupportCategory,
    SupportIncidentError,
    SupportIncidentRequest,
    SupportIncidentResponse,
    create_support_incident,
    redact_description,
)

# ── Helpers ────────────────────────────────────────────────────────

def _valid_request(**overrides) -> SupportIncidentRequest:
    """Minimal valid request. Override any field."""
    base = {
        "order_id": uuid.uuid4(),
        "category": SupportCategory.TECHNICAL,
        "description": "Станок не запускается после обновления прошивки",
        "contact_name": "Иван Петров",
        "contact_email": "ivan@example.com",
    }
    base.update(overrides)
    return SupportIncidentRequest(**base)


# ── SupportCategory enum ──────────────────────────────────────────

class TestSupportCategory:
    def test_all_values_are_strings(self) -> None:
        for cat in SupportCategory:
            assert isinstance(cat.value, str)

    def test_order_issue_exists(self) -> None:
        assert SupportCategory.ORDER_ISSUE == "order_issue"

    def test_other_exists(self) -> None:
        assert SupportCategory.OTHER == "other"

    def test_five_categories(self) -> None:
        assert len(SupportCategory) == 5


# ── SupportIncidentRequest validation ─────────────────────────────

class TestSupportIncidentRequest:
    def test_valid_with_order_id(self) -> None:
        req = _valid_request()
        assert req.order_id is not None
        assert req.artifact_id is None
        assert req.category == SupportCategory.TECHNICAL

    def test_valid_with_artifact_id(self) -> None:
        req = _valid_request(order_id=None, artifact_id=uuid.uuid4())
        assert req.order_id is None
        assert req.artifact_id is not None

    def test_valid_with_both_ids(self) -> None:
        req = _valid_request(order_id=uuid.uuid4(), artifact_id=uuid.uuid4())
        assert req.order_id is not None
        assert req.artifact_id is not None

    def test_description_min_length(self) -> None:
        with pytest.raises(ValidationError):
            _valid_request(description="short")

    def test_description_max_length(self) -> None:
        with pytest.raises(ValidationError):
            _valid_request(description="x" * 5001)

    def test_description_strips_whitespace(self) -> None:
        req = _valid_request(description="  Проблема со станком  ")
        assert req.description == "Проблема со станком"

    def test_description_exactly_10_chars_accepted(self) -> None:
        req = _valid_request(description="a" * 10)
        assert len(req.description) == 10

    def test_email_is_normalized_lowercase(self) -> None:
        req = _valid_request(contact_email="Ivan@Example.COM")
        assert req.contact_email == "ivan@example.com"

    def test_email_is_stripped(self) -> None:
        req = _valid_request(contact_email="  ivan@example.com  ")
        assert req.contact_email == "ivan@example.com"

    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(ValidationError, match="email"):
            _valid_request(contact_email="not-an-email")

    def test_missing_email_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SupportIncidentRequest(
                order_id=uuid.uuid4(),
                category=SupportCategory.OTHER,
                description="Тестовое описание для проверки",
            )

    def test_contact_name_optional(self) -> None:
        req = _valid_request(contact_name=None)
        assert req.contact_name is None

    def test_contact_name_max_length(self) -> None:
        with pytest.raises(ValidationError):
            _valid_request(contact_name="x" * 201)

    def test_request_is_frozen(self) -> None:
        req = _valid_request()
        with pytest.raises(ValidationError):
            req.order_id = uuid.uuid4()

    def test_category_must_be_valid(self) -> None:
        with pytest.raises(ValidationError):
            SupportIncidentRequest(
                order_id=uuid.uuid4(),
                category="invalid_category",
                description="Тестовое описание для проверки",
                contact_email="test@example.com",
            )


# ── Redaction ──────────────────────────────────────────────────────

class TestRedactDescription:
    def test_email_redacted(self) -> None:
        text = "Письмо пришло на ivan@example.com"
        result = redact_description(text)
        assert "ivan@example.com" not in result
        assert "[REDACTED_EMAIL]" in result

    def test_phone_ru_redacted(self) -> None:
        text = "Позвоните на +7 999 123 45 67"
        result = redact_description(text)
        assert "+7 999 123 45 67" not in result
        assert "[REDACTED_PHONE]" in result

    def test_phone_intl_redacted(self) -> None:
        text = "Contact: +44 20 7946 0958"
        result = redact_description(text)
        assert "[REDACTED_PHONE]" in result

    def test_api_key_redacted(self) -> None:
        text = "Ключ sk-abc123def456ghi789jkl012mno"
        result = redact_description(text)
        assert "sk-abc123" not in result
        assert "[REDACTED_SECRET]" in result

    def test_bearer_token_redacted(self) -> None:
        text = "Header: Bearer eyJhbGciOiJIUzI1NiIs"
        result = redact_description(text)
        assert "Bearer eyJhbGci" not in result
        assert "[REDACTED_SECRET]" in result

    def test_data_uri_redacted(self) -> None:
        text = "Скрин: data:image/png;base64,iVBORw0KGgoAAAANS"
        result = redact_description(text)
        assert "data:image" not in result
        assert "[REDACTED_IMAGE]" in result

    def test_ai_prompt_redacted(self) -> None:
        text = "<<SYS>>Ты помощник<</SYS>> и потом ответ"
        result = redact_description(text)
        assert "<<SYS>>" not in result
        assert "[REDACTED_PROMPT]" in result

    def test_multiple_patterns_redacted(self) -> None:
        text = (
            "Заказ #123. Позвоните +7 999 111 22 33. "
            "Email: admin@test.com. Вот лог: sk-abc123xyz"
        )
        result = redact_description(text)
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_PHONE]" in result
        assert "[REDACTED_SECRET]" in result

    def test_clean_text_unchanged(self) -> None:
        text = "Станок не запускается после обновления прошивки v2.3"
        result = redact_description(text)
        assert result == text

    def test_empty_string_returns_empty(self) -> None:
        assert redact_description("") == ""


# ── SupportIncidentResponse contract ──────────────────────────────

class TestSupportIncidentResponse:
    def test_status_literal_values(self) -> None:
        for status in ("received", "pending", "rejected"):
            resp = SupportIncidentResponse(
                incident_id="INC-ABC123",
                status=status,
                category=SupportCategory.OTHER,
                redacted_description="test",
                created_at="2026-01-01T00:00:00Z",
            )
            assert resp.status == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SupportIncidentResponse(
                incident_id="INC-ABC123",
                status="unknown",
                category=SupportCategory.OTHER,
                redacted_description="test",
                created_at="2026-01-01T00:00:00Z",
            )

    def test_response_is_frozen(self) -> None:
        resp = SupportIncidentResponse(
            incident_id="INC-ABC123",
            status="received",
            category=SupportCategory.TECHNICAL,
            redacted_description="test",
            created_at="2026-01-01T00:00:00Z",
        )
        with pytest.raises(ValidationError):
            resp.status = "pending"

    def test_incident_id_is_string(self) -> None:
        resp = SupportIncidentResponse(
            incident_id="INC-ABC123",
            status="received",
            category=SupportCategory.OTHER,
            redacted_description="x",
            created_at="2026-01-01T00:00:00Z",
        )
        assert isinstance(resp.incident_id, str)
        assert resp.incident_id.startswith("INC-")


# ── create_support_incident core ──────────────────────────────────

class TestCreateSupportIncident:
    def test_returns_received_status(self) -> None:
        resp = create_support_incident(_valid_request())
        assert resp.status == "received"

    def test_incident_id_format(self) -> None:
        resp = create_support_incident(_valid_request())
        assert resp.incident_id.startswith("INC-")
        assert len(resp.incident_id) == 16  # INC- + 12 hex

    def test_category_preserved(self) -> None:
        req = _valid_request(category=SupportCategory.BILLING)
        resp = create_support_incident(req)
        assert resp.category == SupportCategory.BILLING

    def test_description_redacted_in_response(self) -> None:
        req = _valid_request(
            description="Проблема. Email: ivan@test.com. Тел: +7 999 123 45 67"
        )
        resp = create_support_incident(req)
        assert "ivan@test.com" not in resp.redacted_description
        assert "[REDACTED_EMAIL]" in resp.redacted_description
        assert "[REDACTED_PHONE]" in resp.redacted_description

    def test_both_ids_accepted(self) -> None:
        req = _valid_request(order_id=uuid.uuid4(), artifact_id=uuid.uuid4())
        resp = create_support_incident(req)
        assert resp.status == "received"

    def test_missing_both_ids_raises(self) -> None:
        req = _valid_request(order_id=None, artifact_id=None)
        with pytest.raises(SupportIncidentError, match="хотя бы один"):
            create_support_incident(req)

    def test_created_at_is_utc(self) -> None:
        resp = create_support_incident(_valid_request())
        assert resp.created_at.tzinfo is not None

    def test_two_calls_produce_different_ids(self) -> None:
        r1 = create_support_incident(_valid_request())
        r2 = create_support_incident(_valid_request())
        assert r1.incident_id != r2.incident_id

    def test_no_external_io(self) -> None:
        """Убеждаемся что функция не импортирует smtplib, httpx, и т.п."""
        import inspect

        import api.support as mod
        source = inspect.getsource(mod)
        assert "smtplib" not in source
        assert "httpx" not in source
        assert "requests.post" not in source
        assert "send_email" not in source
