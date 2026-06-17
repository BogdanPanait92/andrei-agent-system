"""WhatsApp Business Cloud API for alerts, briefings, and reminders."""

import httpx

from src.integrations.notifier_base import NotifierMixin, strip_markdown
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

WHATSAPP_API = "https://graph.facebook.com/{version}/{phone_id}/messages"


class WhatsAppNotifier(NotifierMixin):
    """
    WhatsApp Business Cloud API (Meta).

    Pentru mesaje proactive (daily briefing, alerte):
    - În fereastra de 24h (după ce Andrei a scris business number-ului): text liber
    - În afara ferestrei: necesită template-uri aprobate (configurează WHATSAPP_TEMPLATE_*)
    """

    def __init__(self) -> None:
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.recipient = _normalize_phone(settings.whatsapp_recipient)
        self.api_version = settings.whatsapp_api_version
        self._enabled = bool(self.access_token and self.phone_number_id and self.recipient)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _api_url(self) -> str:
        return WHATSAPP_API.format(version=self.api_version, phone_id=self.phone_number_id)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self._enabled:
            logger.warning("whatsapp_not_configured")
            return False

        plain = strip_markdown(text)
        chunks = self.split_message(plain, max_len=4096)

        with httpx.Client(timeout=30.0) as client:
            for chunk in chunks:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": self.recipient,
                    "type": "text",
                    "text": {"preview_url": False, "body": chunk},
                }
                try:
                    response = client.post(self._api_url(), headers=self._headers(), json=payload)
                    if response.status_code == 200:
                        continue
                    # Outside 24h window — try template fallback
                    if response.status_code in (400, 403, 470) and self._try_template_fallback(client, chunk):
                        continue
                    response.raise_for_status()
                except httpx.HTTPError as e:
                    logger.error("whatsapp_send_failed", error=str(e))
                    return False
        return True

    def _try_template_fallback(self, client: httpx.Client, text: str) -> bool:
        template = settings.whatsapp_template_general
        if not template:
            return False

        preview = text[:500] if len(text) > 500 else text
        payload = {
            "messaging_product": "whatsapp",
            "to": self.recipient,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": settings.whatsapp_template_language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": preview}],
                    }
                ],
            },
        }
        try:
            response = client.post(self._api_url(), headers=self._headers(), json=payload)
            if response.status_code == 200:
                logger.info("whatsapp_template_fallback_ok", template=template)
                return True
            logger.warning("whatsapp_template_fallback_failed", status=response.status_code)
        except httpx.HTTPError as e:
            logger.error("whatsapp_template_error", error=str(e))
        return False

    def send_daily_briefing(self, briefing: str) -> bool:
        if settings.whatsapp_template_daily and not self._in_session_window_assumed():
            return self._send_named_template(settings.whatsapp_template_daily, briefing[:500])
        return super().send_daily_briefing(briefing)

    def send_weekly_review(self, review: str) -> bool:
        if settings.whatsapp_template_weekly and not self._in_session_window_assumed():
            return self._send_named_template(settings.whatsapp_template_weekly, review[:500])
        return super().send_weekly_review(review)

    def _send_named_template(self, template_name: str, body_text: str) -> bool:
        if not self._enabled:
            return False
        payload = {
            "messaging_product": "whatsapp",
            "to": self.recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": settings.whatsapp_template_language},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": body_text[:1024]}]},
                ],
            },
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self._api_url(), headers=self._headers(), json=payload)
                response.raise_for_status()
                return True
        except httpx.HTTPError as e:
            logger.error("whatsapp_template_send_failed", template=template_name, error=str(e))
            return False

    @staticmethod
    def _in_session_window_assumed() -> bool:
        """Optimistic: try text first; API errors trigger template fallback."""
        return True


def _normalize_phone(phone: str) -> str:
    """E.164 without + (e.g. 40722123456 for RO)."""
    return "".join(c for c in phone if c.isdigit())