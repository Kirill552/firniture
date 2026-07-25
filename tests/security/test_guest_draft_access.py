import hashlib
import hmac
import json
from datetime import UTC, datetime

from fastapi import Response

from api.guest_drafts import (
    COOKIE_NAME,
    clear_guest_draft_cookie,
    create_guest_draft_token,
    is_guest_draft_cookie_secure,
    set_guest_draft_cookie,
    verify_guest_draft_token,
)

SECRET = "test_guest_draft_upload_secret_key_123"


def _make_token(payload: dict, secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"{body.hex()}.{signature}"


def test_create_and_verify_valid_token() -> None:
    order_id = "abc-123"
    guest_session_id = "session-999"

    token = create_guest_draft_token(order_id, guest_session_id, SECRET)
    assert token is not None
    assert "." in token

    payload = verify_guest_draft_token(token, SECRET)
    assert payload is not None
    assert payload["purpose"] == "guest_draft"
    assert payload["order_id"] == order_id
    assert payload["guest_session_id"] == guest_session_id
    assert payload["exp"] > datetime.now(UTC).timestamp()


def test_verify_tampered_signature() -> None:
    order_id = "abc-123"
    guest_session_id = "session-999"
    token = create_guest_draft_token(order_id, guest_session_id, SECRET)

    body, signature = token.split(".", 1)
    tampered_signature = signature[:-2] + "00"
    tampered_token = f"{body}.{tampered_signature}"

    assert verify_guest_draft_token(tampered_token, SECRET) is None


def test_verify_tampered_body() -> None:
    order_id = "abc-123"
    guest_session_id = "session-999"
    token = create_guest_draft_token(order_id, guest_session_id, SECRET)

    body, signature = token.split(".", 1)
    tampered_body = body[:-2] + "00"
    tampered_token = f"{tampered_body}.{signature}"

    assert verify_guest_draft_token(tampered_token, SECRET) is None


def test_verify_expired_token() -> None:
    order_id = "abc-123"
    guest_session_id = "session-999"
    token = create_guest_draft_token(order_id, guest_session_id, SECRET, ttl_seconds=-10)

    assert verify_guest_draft_token(token, SECRET) is None


def test_verify_wrong_secret() -> None:
    order_id = "abc-123"
    guest_session_id = "session-999"
    token = create_guest_draft_token(order_id, guest_session_id, SECRET)

    assert verify_guest_draft_token(token, "different_secret") is None


def test_verify_wrong_purpose() -> None:
    payload = {
        "purpose": "malicious",
        "order_id": "abc-123",
        "guest_session_id": "session-999",
        "exp": int(datetime.now(UTC).timestamp()) + 3600,
    }
    token = _make_token(payload, SECRET)

    assert verify_guest_draft_token(token, SECRET) is None


def test_verify_wrong_order_id_binding() -> None:
    token = create_guest_draft_token("order-a", "session-1", SECRET)

    assert verify_guest_draft_token(token, SECRET, expected_order_id="order-b") is None
    assert verify_guest_draft_token(token, SECRET, expected_order_id="order-a") is not None


def test_verify_wrong_guest_session_binding() -> None:
    token = create_guest_draft_token("order-a", "session-1", SECRET)

    assert verify_guest_draft_token(token, SECRET, expected_guest_session_id="session-2") is None
    assert (
        verify_guest_draft_token(token, SECRET, expected_guest_session_id="session-1") is not None
    )


def test_is_guest_draft_cookie_secure_local(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENVIRONMENT", raising=False)
    assert is_guest_draft_cookie_secure() is False


def test_is_guest_draft_cookie_secure_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    assert is_guest_draft_cookie_secure() is True


def test_set_and_clear_cookie() -> None:
    response = Response()
    token = "some_signed_token_value"

    set_guest_draft_cookie(response, token, secure=True, ttl_seconds=3600)

    headers = response.headers.getlist("set-cookie")
    assert len(headers) == 1
    cookie_header = headers[0]

    assert COOKIE_NAME in cookie_header
    assert token in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert "Secure" in cookie_header
    assert "Max-Age=3600" in cookie_header

    clear_guest_draft_cookie(response)
    clear_headers = response.headers.getlist("set-cookie")
    assert len(clear_headers) == 2
    delete_header = clear_headers[1]
    assert COOKIE_NAME in delete_header
    assert (
        "Max-Age=0" in delete_header
        or 'expires="Thu, 01 Jan 1970 00:00:00 GMT"' in delete_header
        or "expires=Thu, 01-Jan-1970 00:00:00 GMT" in delete_header
    )


def test_set_guest_draft_cookie_default_local(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENVIRONMENT", raising=False)
    response = Response()
    set_guest_draft_cookie(response, "token_value")

    header = response.headers.getlist("set-cookie")[0]
    assert COOKIE_NAME in header
    assert "Secure" not in header


def test_set_guest_draft_cookie_default_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    response = Response()
    set_guest_draft_cookie(response, "token_value")

    header = response.headers.getlist("set-cookie")[0]
    assert COOKIE_NAME in header
    assert "Secure" in header
