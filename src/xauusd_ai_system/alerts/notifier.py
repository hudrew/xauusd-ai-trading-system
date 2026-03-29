from __future__ import annotations

import json
import logging
from urllib import request

from ..config.schema import NotificationConfig
from ..core.models import MarketSnapshot, VolatilityAssessment


LOGGER = logging.getLogger(__name__)


class AlertNotifier:
    """
    Formats volatility alerts for downstream channels.

    Real integrations can wrap this formatter for Telegram, WeCom, email, or
    webhooks without changing the monitor output contract.
    """

    def format_message(
        self,
        snapshot: MarketSnapshot,
        assessment: VolatilityAssessment,
    ) -> str:
        primary = assessment.primary_alert
        reasons = ", ".join(primary.reason_codes) if primary.reason_codes else "NONE"
        return (
            f"[{snapshot.symbol}] {primary.warning_level.value.upper()} "
            f"{primary.forecast_horizon_minutes}m volatility alert | "
            f"score={primary.risk_score:.2f} | action={primary.suggested_action} | "
            f"reasons={reasons}"
        )

    def send(self, message: str, config: NotificationConfig) -> None:
        if config.channel == "stdout":
            LOGGER.warning("alert_notification", extra={"extra_payload": {"message": message}})
            return
        if config.channel == "webhook":
            self._send_webhook(message, config)
            return
        raise ValueError(f"Unsupported notification channel: {config.channel}")

    def _send_webhook(self, message: str, config: NotificationConfig) -> None:
        if not config.webhook_url:
            raise ValueError("Webhook channel requires notification.webhook_url")

        payload = json.dumps({"text": message}).encode("utf-8")
        req = request.Request(
            config.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=config.timeout_seconds) as response:
            response.read()
