from unittest.mock import AsyncMock, MagicMock

import pytest

from api.settings import settings
from shared.email import EmailClient


@pytest.mark.asyncio
async def test_rusender_uses_bearer_token_and_sending_key_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RUSENDER_API_KEY", "rs_ck_v1_test_token")
    object.__setattr__(settings, "RUSENDER_SENDING_KEY_ID", "42")

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"uuid": "message-uuid"}

    client_context = AsyncMock()
    client_context.__aenter__.return_value.post = AsyncMock(return_value=response)
    monkeypatch.setattr("shared.email.httpx.AsyncClient", lambda **_: client_context)

    try:
        result = await EmailClient().send_magic_link("user@example.com", "magic-token")
    finally:
        object.__delattr__(settings, "RUSENDER_SENDING_KEY_ID")

    assert result == "message-uuid"
    post = client_context.__aenter__.return_value.post
    assert post.call_args.args[0].endswith("/external-mails/send/42")
    assert post.call_args.kwargs["headers"] == {
        "Authorization": "Bearer rs_ck_v1_test_token"
    }
