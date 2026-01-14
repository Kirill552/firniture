"""
RuSender клиент для отправки Magic Link писем.

Mock-режим: если RUSENDER_API_KEY пустой, письма логируются но не отправляются.
"""

import logging

import httpx

from api.settings import settings

logger = logging.getLogger(__name__)


class EmailClient:
    """Клиент для отправки email через RuSender API."""

    BASE_URL = "https://api.rusender.ru/api/v1"

    def __init__(self):
        self.api_key = settings.RUSENDER_API_KEY
        self.email_from = settings.EMAIL_FROM
        self.frontend_url = settings.FRONTEND_URL
        self.is_mock = not self.api_key

        if self.is_mock:
            logger.warning("RuSender API key not set — running in MOCK mode")

    async def send_magic_link(
        self,
        email: str,
        token: str,
        user_name: str | None = None,
        is_registration: bool = False
    ) -> str | None:
        """
        Отправить Magic Link для входа/регистрации.

        Args:
            email: Email получателя
            token: Magic token для ссылки
            user_name: Имя пользователя (опционально)
            is_registration: True если это регистрация

        Returns:
            UUID письма от RuSender или None в mock режиме
        """
        magic_url = f"{self.frontend_url}/login/verify?token={token}"

        subject = "Регистрация в Мебель-ИИ" if is_registration else "Вход в Мебель-ИИ"
        action_text = "Завершить регистрацию" if is_registration else "Войти в Мебель-ИИ"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #1a1a1a;">{subject}</h2>

    <p style="color: #4a4a4a; font-size: 16px; line-height: 1.5;">
        {"Добро пожаловать! " if is_registration else ""}Для входа в систему нажмите кнопку:
    </p>

    <p style="margin: 30px 0;">
        <a href="{magic_url}"
           style="background: #2563eb; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 8px; display: inline-block;
                  font-weight: 500; font-size: 16px;">
            {action_text}
        </a>
    </p>

    <p style="color: #888; font-size: 14px; line-height: 1.5;">
        Ссылка действительна 15 минут.<br>
        Если вы не запрашивали {"регистрацию" if is_registration else "вход"} — проигнорируйте это письмо.
    </p>

    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

    <p style="color: #aaa; font-size: 12px;">
        Мебель-ИИ — AI-платформа для мебельных фабрик
    </p>
</body>
</html>
"""

        if self.is_mock:
            logger.info(f"[MOCK EMAIL] To: {email}, Subject: {subject}")
            logger.info(f"[MOCK EMAIL] Magic Link: {magic_url}")
            # В mock режиме возвращаем URL для отображения в dev UI
            return f"mock:{magic_url}"

        idempotency_key = f"magic-{token}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/external-mails/send",
                    headers={"X-Api-Key": self.api_key},
                    json={
                        "idempotencyKey": idempotency_key,
                        "mail": {
                            "to": {"email": email, "name": user_name or email},
                            "from": {"email": self.email_from, "name": "Мебель-ИИ"},
                            "subject": subject,
                            "previewTitle": "Нажмите кнопку для входа в Мебель-ИИ",
                            "html": html
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Email sent to {email}, uuid: {result.get('uuid')}")
                return result.get("uuid")

        except httpx.HTTPStatusError as e:
            logger.error(f"RuSender API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise


# Singleton instance
email_client = EmailClient()


async def send_magic_link(
    email: str,
    token: str,
    user_name: str | None = None,
    is_registration: bool = False
) -> str | None:
    """Удобная функция для отправки magic link."""
    return await email_client.send_magic_link(email, token, user_name, is_registration)
