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
        self.sending_key_id = settings.RUSENDER_SENDING_KEY_ID
        self.email_from = settings.EMAIL_FROM
        self.frontend_url = settings.FRONTEND_URL
        self.is_mock = not self.api_key or not self.sending_key_id

        if self.is_mock:
            logger.warning(
                "RuSender API token or sending key ID not set — running in MOCK mode"
            )

    async def send_magic_link(
        self,
        email: str,
        token: str,
        user_name: str | None = None,
        is_registration: bool = False,
        return_to: str | None = None,
        entry: str | None = None,
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
        if return_to:
            import urllib.parse
            magic_url += f"&returnTo={urllib.parse.quote(return_to)}"
        if entry:
            import urllib.parse
            magic_url += f"&entry={urllib.parse.quote(entry)}"

        subject = "Регистрация в АвтоРаскрой" if is_registration else "Вход в АвтоРаскрой"
        action_text = "Завершить регистрацию" if is_registration else "Войти в АвтоРаскрой"
        lead_text = (
            "Добро пожаловать! Остался один шаг — подтвердите почту,"
            if is_registration
            else "С возвращением! Нажмите кнопку, чтобы войти в личный кабинет."
        )
        hero_url = f"{self.frontend_url}/hero-kitchen-seamless.webp"

        # Бренд-шаблон в стиле лендинга (Scandinavian Industrial).
        # Email-safe: таблицы, инлайн-стили, без flex/grid.
        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f6f8;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f6f8; padding: 24px 12px;">
        <tr>
            <td align="center">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; background-color: #ffffff; border: 1px solid #d7dde2; border-radius: 12px; overflow: hidden;">
                    <!-- Шапка -->
                    <tr>
                        <td style="padding: 24px 32px; border-bottom: 1px solid #d7dde2;">
                            <table role="presentation" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="background-color: #171a1d; color: #c7ff00; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; font-weight: 800; font-size: 18px; width: 36px; height: 36px; text-align: center; border-radius: 8px; line-height: 36px;">АР</td>
                                    <td style="padding-left: 12px; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; font-weight: 800; font-size: 17px; color: #171a1d;">АвтоРаскрой</td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Hero -->
                    <tr>
                        <td>
                            <img src="{hero_url}" alt="Эскиз, детали и собранная кухня" width="600" style="display: block; width: 100%; height: auto; border: 0;">
                        </td>
                    </tr>

                    <!-- Тело -->
                    <tr>
                        <td style="padding: 32px;">
                            <h1 style="margin: 0 0 16px; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; font-size: 26px; font-weight: 800; letter-spacing: -0.5px; color: #171a1d; line-height: 1.15;">{subject}</h1>

                            <p style="margin: 0 0 28px; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; color: #66707a; font-size: 15px; line-height: 1.6;">
                                {lead_text}
                            </p>

                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 0 0 28px;">
                                <tr>
                                    <td style="background-color: #171a1d; border-radius: 10px;">
                                        <a href="{magic_url}"
                                           style="display: inline-block; padding: 15px 32px; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 16px;">
                                            {action_text} &#8594;
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; color: #66707a; font-size: 13px; line-height: 1.6;">
                                Ссылка действительна 15 минут.<br>
                                Если вы не запрашивали {"регистрацию" if is_registration else "вход"} — просто проигнорируйте это письмо.
                            </p>
                        </td>
                    </tr>

                    <!-- Подвал -->
                    <tr>
                        <td style="padding: 20px 32px; border-top: 1px solid #d7dde2; background-color: #f3f6f8;">
                            <p style="margin: 0; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; color: #66707a; font-size: 12px; line-height: 1.5;">
                                АвтоРаскрой — эскиз клиента в точный заказ: распознавание, спецификация, DXF и PDF.<br>
                                <a href="{self.frontend_url}" style="color: #171a1d; text-decoration: underline;">avtoraskroy.ru</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
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
                    f"{self.BASE_URL}/external-mails/send/{self.sending_key_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "idempotencyKey": idempotency_key,
                        "mail": {
                            "to": {"email": email, "name": user_name or email},
                            "from": {"email": self.email_from, "name": "АвтоРаскрой"},
                            "subject": subject,
                            "previewTitle": lead_text,
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
    is_registration: bool = False,
    return_to: str | None = None,
    entry: str | None = None,
) -> str | None:
    """Удобная функция для отправки magic link."""
    return await email_client.send_magic_link(email, token, user_name, is_registration, return_to, entry)
