"""Тесты ядра redaction для observability events.

Покрытие:
- Рекурсивный redaction dict/list
- Красный список полей (auth, secret, token)
- Эвристика по паттернам значений (Bearer, JWT, hex, base64)
- Prompt/image redaction по уровням
- Truncation длинных строк
- ObservabilityEvent schema validation
- Adversarial cases: обфускация, mixed case, nested structures
"""

from __future__ import annotations

from datetime import UTC

import pytest

from api.observability import (
    ObservabilityEvent,
    RedactLevel,
    create_event,
    event_to_dict,
    redact_dict,
    redact_list,
    redact_value,
)

# ═══════════════════════════════════════════════════════════════════════════
# RedactLevel
# ═══════════════════════════════════════════════════════════════════════════


class TestRedactLevel:
    """Порядок уровней redaction."""

    def test_ordering(self) -> None:
        assert RedactLevel.NONE < RedactLevel.LIGHT < RedactLevel.STANDARD < RedactLevel.STRICT


# ═══════════════════════════════════════════════════════════════════════════
# redact_value
# ═══════════════════════════════════════════════════════════════════════════


class TestRedactValue:
    """redact_value — красит одно значение по имени и паттерну."""

    def test_none_redacted_if_field_is_sensitive(self) -> None:
        """None с именем password — красим: имя в красном списке."""
        assert redact_value(None, "password") == "[REDACTED]"

    def test_none_passthrough_if_field_not_sensitive(self) -> None:
        """None с обычным именем — как есть."""
        assert redact_value(None, "notes") is None

    def test_bool_passthrough_if_field_not_sensitive(self) -> None:
        """Bool с обычным именем — как есть."""
        assert redact_value(True, "enabled") is True

    def test_int_passthrough_if_field_not_sensitive(self) -> None:
        """Int с обычным именем — как есть."""
        assert redact_value(42, "count") == 42

    def test_redact_password_field(self) -> None:
        assert redact_value("s3cret", "password") == "[REDACTED]"

    def test_redact_api_key_field(self) -> None:
        assert redact_value("sk-12345", "api_key") == "[REDACTED]"

    def test_redact_token_field(self) -> None:
        assert redact_value("abc123", "token") == "[REDACTED]"

    def test_redact_authorization_field(self) -> None:
        assert redact_value("anything", "Authorization") == "[REDACTED]"

    def test_redact_bearer_in_value(self) -> None:
        assert redact_value("Bearer abc.def.ghi", "header") == "[REDACTED]"

    def test_redact_jwt_in_value(self) -> None:
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        assert redact_value(jwt, "some_field") == "[REDACTED]"

    def test_redact_long_hex_value(self) -> None:
        hex_val = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        assert redact_value(hex_val, "some_field") == "[REDACTED]"

    def test_truncate_long_string(self) -> None:
        long_str = "x" * 600
        result = redact_value(long_str, "notes")
        assert result.endswith("[TRUNCATED]")
        assert len(result) == 514  # 500 + len("...[TRUNCATED]") = 500 + 14

    def test_short_string_passthrough(self) -> None:
        assert redact_value("hello", "notes") == "hello"

    def test_prompt_field_redacted_at_standard(self) -> None:
        assert redact_value("Describe a cabinet", "prompt", RedactLevel.STANDARD) == "[REDACTED]"

    def test_prompt_field_kept_at_light(self) -> None:
        assert redact_value("Describe a cabinet", "prompt", RedactLevel.LIGHT) == "Describe a cabinet"

    def test_content_field_redacted_at_standard(self) -> None:
        assert redact_value("some content", "content", RedactLevel.STANDARD) == "[REDACTED]"

    def test_image_data_field_redacted(self) -> None:
        assert redact_value("base64data", "image_data", RedactLevel.STANDARD) == "[REDACTED]"


# ═══════════════════════════════════════════════════════════════════════════
# redact_dict
# ═══════════════════════════════════════════════════════════════════════════


class TestRedactDict:
    """redact_dict — рекурсивный красит dict."""

    def test_empty_dict(self) -> None:
        assert redact_dict({}) == {}

    def test_no_sensitive_fields(self) -> None:
        data = {"width": 100, "height": 200, "material": "ЛДСП"}
        assert redact_dict(data) == data

    def test_redact_single_secret(self) -> None:
        data = {"password": "s3cret", "user": "ivan"}
        result = redact_dict(data)
        assert result["password"] == "[REDACTED]"
        assert result["user"] == "ivan"

    def test_redact_multiple_secrets(self) -> None:
        data = {
            "password": "s3cret",
            "api_key": "sk-12345",
            "s3_secret_key": "minio123",
            "normal": "keep",
        }
        result = redact_dict(data)
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["s3_secret_key"] == "[REDACTED]"
        assert result["normal"] == "keep"

    def test_nested_dict_redaction(self) -> None:
        data = {
            "auth": {"token": "abc123"},
            "config": {"width": 100},
        }
        result = redact_dict(data)
        assert result["auth"]["token"] == "[REDACTED]"
        assert result["config"]["width"] == 100

    def test_deeply_nested_redaction(self) -> None:
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret": "hidden",
                        "safe": "visible",
                    }
                }
            }
        }
        result = redact_dict(data)
        assert result["level1"]["level2"]["level3"]["secret"] == "[REDACTED]"
        assert result["level1"]["level2"]["level3"]["safe"] == "visible"

    def test_list_inside_dict(self) -> None:
        data = {
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ]
        }
        result = redact_dict(data, RedactLevel.STANDARD)
        assert result["messages"][0]["content"] == "[REDACTED]"

    def test_prompt_redaction_at_standard(self) -> None:
        data = {"prompt": "Describe a wardrobe", "model": "gpt-4"}
        result = redact_dict(data, RedactLevel.STANDARD)
        assert result["prompt"] == "[REDACTED]"
        assert result["model"] == "gpt-4"

    def test_prompt_kept_at_light(self) -> None:
        data = {"prompt": "Describe a wardrobe"}
        result = redact_dict(data, RedactLevel.LIGHT)
        assert result["prompt"] == "Describe a wardrobe"

    def test_additional_redact_fields(self) -> None:
        data = {"custom_secret": "hidden", "safe": "keep"}
        result = redact_dict(data, additional_redact_fields=frozenset({"custom_secret"}))
        assert result["custom_secret"] == "[REDACTED]"
        assert result["safe"] == "keep"

    def test_original_not_mutated(self) -> None:
        data = {"password": "s3cret"}
        redact_dict(data)
        assert data["password"] == "s3cret"  # оригинал не изменён

    def test_jwt_in_value_detected(self) -> None:
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        data = {"header": f"Bearer {jwt}"}
        result = redact_dict(data)
        assert result["header"] == "[REDACTED]"

    def test_none_value_preserved(self) -> None:
        data = {"optional_field": None, "password": "x"}
        result = redact_dict(data)
        assert result["optional_field"] is None
        assert result["password"] == "[REDACTED]"


# ═══════════════════════════════════════════════════════════════════════════
# redact_list
# ═══════════════════════════════════════════════════════════════════════════


class TestRedactList:
    """redact_list — рекурсивный красит list."""

    def test_empty_list(self) -> None:
        assert redact_list([]) == []

    def test_plain_values(self) -> None:
        assert redact_list([1, "hello", None]) == [1, "hello", None]

    def test_nested_dict_in_list(self) -> None:
        data = [{"password": "s3cret", "user": "ivan"}]
        result = redact_list(data)
        assert result[0]["password"] == "[REDACTED]"
        assert result[0]["user"] == "ivan"

    def test_nested_list_in_list(self) -> None:
        data = [[{"secret": "x"}]]
        result = redact_list(data)
        assert result[0][0]["secret"] == "[REDACTED]"

    def test_truncate_long_string_in_list(self) -> None:
        data = ["x" * 600]
        result = redact_list(data)
        assert result[0].endswith("[TRUNCATED]")


# ═══════════════════════════════════════════════════════════════════════════
# ObservabilityEvent
# ═══════════════════════════════════════════════════════════════════════════


class TestObservabilityEvent:
    """Schema validation для structured event."""

    def test_valid_event(self) -> None:
        from datetime import datetime
        event = ObservabilityEvent(
            event_type="api.request",
            timestamp=datetime.now(UTC),
            severity="info",
            data={"method": "POST", "path": "/orders"},
        )
        assert event.event_type == "api.request"
        assert event.severity == "info"

    def test_empty_event_type_rejected(self) -> None:
        from datetime import datetime
        with pytest.raises(ValueError, match="event_type"):
            ObservabilityEvent(
                event_type="",
                timestamp=datetime.now(UTC),
                severity="info",
                data={},
            )

    def test_invalid_severity_rejected(self) -> None:
        from datetime import datetime
        with pytest.raises(ValueError, match="severity"):
            ObservabilityEvent(
                event_type="test",
                timestamp=datetime.now(UTC),
                severity="invalid",
                data={},
            )

    def test_valid_severities(self) -> None:
        from datetime import datetime
        for sev in ("debug", "info", "warning", "error", "critical"):
            event = ObservabilityEvent(
                event_type="test",
                timestamp=datetime.now(UTC),
                severity=sev,
                data={},
            )
            assert event.severity == sev


# ═══════════════════════════════════════════════════════════════════════════
# create_event + event_to_dict
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateEvent:
    """create_event и event_to_dict — интеграция."""

    def test_event_created_with_redaction(self) -> None:
        event = create_event(
            "ai.call",
            {"model": "gpt-4", "prompt": "hello", "api_key": "sk-12345"},
        )
        assert event.event_type == "ai.call"
        assert event.data["model"] == "gpt-4"
        assert event.data["prompt"] == "[REDACTED]"
        assert event.data["api_key"] == "[REDACTED]"

    def test_event_to_dict_serializable(self) -> None:
        event = create_event("api.request", {"method": "GET"})
        d = event_to_dict(event)
        assert d["event_type"] == "api.request"
        assert "timestamp" in d
        assert isinstance(d["data"], dict)

    def test_context_preserved(self) -> None:
        event = create_event(
            "auth.login",
            {"email": "user@example.com"},
            context={"request_id": "abc-123"},
        )
        assert event.context["request_id"] == "abc-123"

    def test_default_context_is_empty(self) -> None:
        event = create_event("test", {})
        assert event.context == {}

    def test_custom_level(self) -> None:
        event = create_event(
            "ai.call",
            {"prompt": "hello", "model": "gpt-4"},
            level=RedactLevel.LIGHT,
        )
        # При LIGHT prompt не красится
        assert event.data["prompt"] == "hello"


# ═══════════════════════════════════════════════════════════════════════════
# Adversarial cases
# ═══════════════════════════════════════════════════════════════════════════


class TestAdversarialRedaction:
    """Edge cases и поптки обхода redaction."""

    def test_mixed_case_field_name(self) -> None:
        """PASSWORD vs password — должно красить."""
        data = {"PASSWORD": "s3cret", "Api_Key": "sk-123"}
        result = redact_dict(data)
        assert result["PASSWORD"] == "[REDACTED]"
        assert result["Api_Key"] == "[REDACTED]"

    def test_whitespace_in_field_name(self) -> None:
        """Поля с пробелами: ' password '."""
        data = {" password ": "s3cret"}
        result = redact_dict(data)
        assert result[" password "] == "[REDACTED]"

    def test_empty_string_value_not_secret(self) -> None:
        """Пустая строка — не похожа на секрет."""
        data = {"password": ""}
        result = redact_dict(data)
        assert result["password"] == "[REDACTED]"  # имя в красном списке

    def test_short_hex_not_detected(self) -> None:
        """Короткий hex (16 символов) — не красится по паттерну."""
        data = {"code": "a1b2c3d4e5f6a1b2"}
        result = redact_dict(data)
        assert result["code"] == "a1b2c3d4e5f6a1b2"

    def test_regular_url_not_detected(self) -> None:
        """Обычный URL — не похож на токен."""
        data = {"url": "https://example.com/api/orders"}
        result = redact_dict(data)
        assert result["url"] == "https://example.com/api/orders"

    def test_nested_auth_in_ai_messages(self) -> None:
        """AI messages с auth context — красим content."""
        data = {
            "messages": [
                {"role": "user", "content": "Describe a cabinet"},
                {"role": "assistant", "content": "Here is..."},
            ],
            "model": "gpt-4",
        }
        result = redact_dict(data, RedactLevel.STANDARD)
        for msg in result["messages"]:
            assert msg["content"] == "[REDACTED]"
        assert result["model"] == "gpt-4"

    def test_s3_credentials_in_settings(self) -> None:
        """S3 credentials — все красные."""
        data = {
            "s3_access_key": "minio",
            "s3_secret_key": "minio123",
            "s3_bucket": "artifacts",
        }
        result = redact_dict(data)
        assert result["s3_access_key"] == "[REDACTED]"
        assert result["s3_secret_key"] == "[REDACTED]"
        assert result["s3_bucket"] == "artifacts"

    def test_jwt_secret_in_nested_config(self) -> None:
        """JWT_SECRET в глубоко вложенном config."""
        data = {
            "config": {
                "auth": {
                    "jwt_secret": "super_secret",
                    "algorithm": "HS256",
                }
            }
        }
        result = redact_dict(data)
        assert result["config"]["auth"]["jwt_secret"] == "[REDACTED]"
        assert result["config"]["auth"]["algorithm"] == "HS256"

    def test_image_base64_in_vision_request(self) -> None:
        """Base64 image data красится по полю и по паттерну."""
        fake_b64 = "A" * 100  # короткий, но имя поля красное
        data = {"image_base64": fake_b64}
        result = redact_dict(data, RedactLevel.STANDARD)
        assert result["image_base64"] == "[REDACTED]"

    def test_long_base64_value_detected(self) -> None:
        """Длинный base64 — красится по паттерну (не по имени)."""
        long_b64 = "A" * 60 + "="  # > 40 символов, base64 pattern
        data = {"some_field": long_b64}
        result = redact_dict(data)
        assert result["some_field"] == "[REDACTED]"

    def test_rusernder_api_key(self) -> None:
        """RUSENDER_API_KEY — в красном списке."""
        data = {"rusernder_api_key": "abc123"}
        result = redact_dict(data)
        assert result["rusernder_api_key"] == "[REDACTED]"

    def test_nested_list_with_sensitive_dicts(self) -> None:
        """Список dicts с secrets внутри."""
        data = {
            "items": [
                {"name": "panel1", "api_key": "hidden"},
                {"name": "panel2", "token": "xyz"},
            ]
        }
        result = redact_dict(data)
        assert result["items"][0]["api_key"] == "[REDACTED]"
        assert result["items"][0]["name"] == "panel1"
        assert result["items"][1]["token"] == "[REDACTED]"

    def test_content_field_at_light_level_not_redacted(self) -> None:
        """При LIGHT уровень content не красится."""
        data = {"content": "user input text"}
        result = redact_dict(data, RedactLevel.LIGHT)
        assert result["content"] == "user input text"

    def test_truncation_boundary_exactly_500(self) -> None:
        """Ровно 500 символов — не обрезается."""
        val = "x" * 500
        assert redact_value(val, "text") == val

    def test_truncation_boundary_501(self) -> None:
        """501 символ — обрезается."""
        val = "x" * 501
        result = redact_value(val, "text")
        assert result.endswith("[TRUNCATED]")
        assert len(result) == 514  # 500 + len("...[TRUNCATED]") = 500 + 14

    def test_none_values_in_list_preserved(self) -> None:
        """None в списке не ломается."""
        result = redact_list([None, 42, "text"])
        assert result == [None, 42, "text"]

    def test_boolean_values_always_redacted_by_name(self) -> None:
        """Bool с именем password красится — имя в красном списке."""
        result = redact_dict({"password": True})
        assert result["password"] == "[REDACTED]"

    def test_int_secret_value_not_overredacted(self) -> None:
        """Числовое значение с именем password — красится по имени."""
        result = redact_dict({"password": 12345})
        # Имя в красном списке — красим regardless of type
        assert result["password"] == "[REDACTED]"

    def test_multiple_redaction_levels(self) -> None:
        """Разные уровни дают разный результат."""
        data = {"prompt": "hello", "password": "s3cret", "normal": "keep"}

        light = redact_dict(data, RedactLevel.LIGHT)
        assert light["prompt"] == "hello"       # не красим при LIGHT
        assert light["password"] == "[REDACTED]"  # красим всегда
        assert light["normal"] == "keep"

        standard = redact_dict(data, RedactLevel.STANDARD)
        assert standard["prompt"] == "[REDACTED]"  # красим при STANDARD
        assert standard["password"] == "[REDACTED]"
        assert standard["normal"] == "keep"


# ═══════════════════════════════════════════════════════════════════════════
# Context redaction — create_event redacts context same as data
# ═══════════════════════════════════════════════════════════════════════════


class TestContextRedaction:
    """create_event применяет redact_dict к context."""

    def test_secret_in_context_redacted(self) -> None:
        """api_key в context красится — name в красном списке."""
        event = create_event(
            "api.request",
            {"method": "GET"},
            context={"api_key": "sk-12345", "request_id": "req-abc"},
        )
        assert event.context["api_key"] == "[REDACTED]"
        assert event.context["request_id"] == "req-abc"

    def test_bearer_token_in_context_redacted(self) -> None:
        """Bearer токен в context красится по паттерну."""
        event = create_event(
            "api.request",
            {"method": "GET"},
            context={"authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"},
        )
        assert event.context["authorization"] == "[REDACTED]"

    def test_prompt_in_context_redacted_at_standard(self) -> None:
        """prompt в context красится при STANDARD."""
        event = create_event(
            "ai.call",
            {"model": "gpt-4"},
            context={"prompt": "Describe a cabinet"},
        )
        assert event.context["prompt"] == "[REDACTED]"

    def test_prompt_in_context_kept_at_light(self) -> None:
        """prompt в context НЕ красится при LIGHT."""
        event = create_event(
            "ai.call",
            {"model": "gpt-4"},
            context={"prompt": "Describe a cabinet"},
            level=RedactLevel.LIGHT,
        )
        assert event.context["prompt"] == "Describe a cabinet"

    def test_jwt_in_context_value_redacted(self) -> None:
        """JWT-значение в context красится по паттерну."""
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        event = create_event(
            "api.request",
            {"method": "GET"},
            context={"token": jwt},
        )
        assert event.context["token"] == "[REDACTED]"

    def test_nested_secret_in_context_redacted(self) -> None:
        """Вложенный secret в context красится рекурсивно."""
        event = create_event(
            "api.request",
            {"method": "GET"},
            context={"config": {"auth": {"jwt_secret": "super_secret"}}},
        )
        assert event.context["config"]["auth"]["jwt_secret"] == "[REDACTED]"

    def test_context_serialized_through_event_to_dict(self) -> None:
        """event_to_dict выводит ужеoredacted context."""
        event = create_event(
            "api.request",
            {"method": "GET"},
            context={"api_key": "sk-leaked", "request_id": "safe-id"},
        )
        d = event_to_dict(event)
        assert d["context"]["api_key"] == "[REDACTED]"
        assert d["context"]["request_id"] == "safe-id"

    def test_image_in_context_redacted(self) -> None:
        """image_data в context красится при STANDARD."""
        event = create_event(
            "ai.vision",
            {"model": "gpt-4"},
            context={"image_data": "base64payload"},
        )
        assert event.context["image_data"] == "[REDACTED]"

    def test_empty_context_stays_empty(self) -> None:
        """Пустой context — как есть."""
        event = create_event("test", {}, context={})
        assert event.context == {}

    def test_none_context_stays_empty(self) -> None:
        """None context → пустой dict."""
        event = create_event("test", {}, context=None)
        assert event.context == {}


# ═══════════════════════════════════════════════════════════════════════════
# _IDFIELD_NAMES — ID masking at STRICT level
# ═══════════════════════════════════════════════════════════════════════════


class TestIdFieldRedaction:
    """_IDFIELD_NAMES маскируются при level >= STRICT."""

    def test_user_id_masked_at_strict(self) -> None:
        """user_id маскируется до префикса при STRICT."""
        result = redact_value("usr_abc123def456", "user_id", RedactLevel.STRICT)
        assert result == "usr_abc1[...MASKED]"

    def test_user_id_short_value_fully_masked(self) -> None:
        """Короткий user_id (<8) — полностью маскируется."""
        result = redact_value("usr1", "user_id", RedactLevel.STRICT)
        assert result == "[...MASKED]"

    def test_user_id_not_masked_at_standard(self) -> None:
        """user_id НЕ маскируется при STANDARD."""
        result = redact_value("usr_abc123def456", "user_id", RedactLevel.STANDARD)
        assert result == "usr_abc123def456"

    def test_order_id_masked_at_strict(self) -> None:
        """order_id маскируется при STRICT."""
        result = redact_dict(
            {"order_id": "ord_9876543210", "item": "panel"},
            RedactLevel.STRICT,
        )
        assert result["order_id"] == "ord_9876[...MASKED]"
        assert result["item"] == "panel"

    def test_factory_id_masked_at_strict(self) -> None:
        """factory_id маскируется при STRICT."""
        result = redact_value("fac-1234567890", "factory_id", RedactLevel.STRICT)
        assert result == "fac-1234[...MASKED]"

    def test_job_id_masked_at_strict(self) -> None:
        """job_id маскируется при STRICT."""
        result = redact_value("job-abcdefghij", "job_id", RedactLevel.STRICT)
        assert result == "job-abcd[...MASKED]"

    def test_id_in_context_masked_at_strict(self) -> None:
        """user_id в context маскируется при STRICT через create_event."""
        event = create_event(
            "api.request",
            {"method": "GET"},
            context={"user_id": "usr_secret123"},
            level=RedactLevel.STRICT,
        )
        assert event.context["user_id"] == "usr_secr[...MASKED]"

    def test_id_in_context_not_masked_at_standard(self) -> None:
        """user_id в context НЕ маскируется при STANDARD."""
        event = create_event(
            "api.request",
            {"method": "GET"},
            context={"user_id": "usr_secret123"},
            level=RedactLevel.STANDARD,
        )
        assert event.context["user_id"] == "usr_secret123"

    def test_nested_id_masked_in_dict(self) -> None:
        """Вложенный user_id маскируется рекурсивно при STRICT."""
        data = {"request": {"user_id": "long-user-id-value-here"}}
        result = redact_dict(data, RedactLevel.STRICT)
        assert result["request"]["user_id"] == "long-use[...MASKED]"

    def test_non_id_field_not_affected(self) -> None:
        """Обычные поля не маскируются при STRICT."""
        result = redact_value("regular text", "notes", RedactLevel.STRICT)
        assert result == "regular text"

    def test_id_integer_value_masked(self) -> None:
        """Числовой id маскируется при STRICT (не строка)."""
        result = redact_value(12345, "order_id", RedactLevel.STRICT)
        assert result == "[...MASKED]"

    def test_id_bool_value_masked(self) -> None:
        """Bool значение с именем user_id маскируется при STRICT."""
        result = redact_value(True, "user_id", RedactLevel.STRICT)
        assert result == "[...MASKED]"

    def test_id_short_string_exactly_8(self) -> None:
        """Ровно 8 символов — полностью маскируется (не > 8)."""
        result = redact_value("12345678", "user_id", RedactLevel.STRICT)
        assert result == "[...MASKED]"

    def test_id_exactly_9_chars_masks_one(self) -> None:
        """9 символов — маскируется до 8 + [..MASKED]."""
        result = redact_value("123456789", "user_id", RedactLevel.STRICT)
        assert result == "12345678[...MASKED]"


# ═══════════════════════════════════════════════════════════════════════════
# event_to_dict serialization safety
# ═══════════════════════════════════════════════════════════════════════════


class TestEventToDictSafety:
    """event_to_dict не должен выводить чувствительные данные."""

    def test_secret_not_in_serialized_output(self) -> None:
        """api_key не появляется в сериализованном event."""
        event = create_event("test", {"api_key": "sk-leaked"})
        d = event_to_dict(event)
        assert d["data"]["api_key"] == "[REDACTED]"

    def test_auth_token_not_in_serialized_output(self) -> None:
        """authorization header не появляется в сериализованном event."""
        event = create_event(
            "api.request",
            {},
            context={"authorization": "Bearer secret-token"},
        )
        d = event_to_dict(event)
        assert d["context"]["authorization"] == "[REDACTED]"

    def test_user_id_in_serialized_at_standard(self) -> None:
        """user_id виден при STANDARD — маскирование только при STRICT."""
        event = create_event(
            "api.request",
            {"user_id": "usr_visible"},
            context={"user_id": "usr_visible"},
            level=RedactLevel.STANDARD,
        )
        d = event_to_dict(event)
        assert d["data"]["user_id"] == "usr_visible"
        assert d["context"]["user_id"] == "usr_visible"

    def test_user_id_masked_in_serialized_at_strict(self) -> None:
        """user_id маскируется в сериализованном event при STRICT."""
        event = create_event(
            "api.request",
            {"user_id": "usr_secret123"},
            context={"user_id": "usr_secret123"},
            level=RedactLevel.STRICT,
        )
        d = event_to_dict(event)
        assert d["data"]["user_id"] == "usr_secr[...MASKED]"
        assert d["context"]["user_id"] == "usr_secr[...MASKED]"

    def test_prompt_in_data_not_in_serialized(self) -> None:
        """prompt в data не появляется в сериализованном event при STANDARD."""
        event = create_event(
            "ai.call",
            {"prompt": "secret instructions"},
            level=RedactLevel.STANDARD,
        )
        d = event_to_dict(event)
        assert d["data"]["prompt"] == "[REDACTED]"

    def test_nested_secret_not_leaked(self) -> None:
        """Вложенные secrets не утекают через event_to_dict."""
        event = create_event(
            "api.request",
            {"config": {"database": {"password": "db-pass"}}},
        )
        d = event_to_dict(event)
        assert d["data"]["config"]["database"]["password"] == "[REDACTED]"

    def test_empty_data_and_context(self) -> None:
        """Пустые data/context — безопасная сериализация."""
        event = create_event("test", {})
        d = event_to_dict(event)
        assert d["data"] == {}
        assert d["context"] == {}
