"""Telegram Bot API notifier for Alpha Hunter Agent."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED


class TelegramNotifier:
    """Send Alpha Hunter token alerts through Telegram Bot API."""

    API_BASE_URL = "https://api.telegram.org"
    REQUEST_TIMEOUT_SECONDS = 15
    MAX_MESSAGE_LENGTH = 3900
    MAX_ALERT_TOKENS = 5

    def __init__(
        self,
        bot_token: str = TELEGRAM_BOT_TOKEN,
        chat_id: str = TELEGRAM_CHAT_ID,
        enabled: bool = TELEGRAM_ENABLED,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.session = requests.Session()

    def notify_top_tokens(self, tokens: pd.DataFrame) -> None:
        """Send a Telegram message for v1.1 calibrated early alpha alerts."""
        if not self.enabled:
            self.logger.info("Telegram notification is disabled")
            return

        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram notification skipped because bot token or chat ID is missing")
            return

        alert_tokens = self._filter_calibrated_alert_tokens(tokens)
        if alert_tokens.empty:
            self.logger.info("Telegram notification skipped because there are no Top tokens")
            return

        message = self._format_top_tokens_message(alert_tokens)
        for chunk in self._split_message(message):
            self._send_message(chunk)

        self.logger.info("Telegram notification sent for %s Top tokens", len(alert_tokens))

    def _filter_calibrated_alert_tokens(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Keep CRITICAL, HIGH, and WATCH alerts sorted by early alpha score."""
        if tokens.empty:
            return tokens
        if "alert_level" not in tokens.columns:
            return tokens.head(0)

        alert_tokens = tokens[tokens["alert_level"].isin(["CRITICAL", "HIGH", "WATCH"])].copy()
        if alert_tokens.empty:
            return alert_tokens

        if "early_alpha_score" not in alert_tokens.columns:
            alert_tokens["early_alpha_score"] = 0
        alert_tokens["agent_score"] = pd.to_numeric(alert_tokens["agent_score"], errors="coerce").fillna(0)
        alert_tokens["early_alpha_score"] = pd.to_numeric(
            alert_tokens["early_alpha_score"],
            errors="coerce",
        ).fillna(0)
        return alert_tokens.sort_values(
            ["early_alpha_score", "agent_score"],
            ascending=[False, False],
        ).head(self.MAX_ALERT_TOKENS)

    def _format_top_tokens_message(self, tokens: pd.DataFrame) -> str:
        """Build a compact plain-text message with the requested token fields."""
        lines = ["Alpha Hunter Agent v1.1 - Early Alpha Signals"]

        for index, token in tokens.reset_index(drop=True).iterrows():
            rank = index + 1
            lines.extend(
                [
                    "",
                    f"#{rank} {self._value(token, 'alert_level')} Signal",
                    f"{self._value(token, 'symbol')} - {self._value(token, 'token_name')}",
                    f"early_alpha_score: {self._format_number(token.get('early_alpha_score'))}",
                    f"early_alpha_reason: {self._value(token, 'early_alpha_reason')}",
                    f"is_first_seen: {self._value(token, 'is_first_seen')}",
                    f"scan_count: {self._value(token, 'scan_count')}",
                    f"consecutive_up_count: {self._value(token, 'consecutive_up_count')}",
                    f"token_age_bucket: {self._value(token, 'token_age_bucket')}",
                    f"alert_level: {self._value(token, 'alert_level')}",
                    f"alert_reason: {self._value(token, 'alert_reason')}",
                    f"agent_score: {self._format_number(token.get('agent_score'))}",
                    f"alpha_score: {self._format_number(token.get('alpha_score'))}",
                    f"rug_risk_level: {self._value(token, 'rug_risk_level')}",
                    f"narrative: {self._value(token, 'narrative')}",
                    f"smart_money_signal: {self._value(token, 'smart_money_signal')}",
                    f"smart_money_score: {self._format_number(token.get('smart_money_score'))}",
                    f"risk_notes: {self._value(token, 'risk_notes')}",
                    f"momentum_status: {self._value(token, 'momentum_status')}",
                    f"DexScreener URL: {self._value(token, 'url')}",
                ]
            )

        return "\n".join(lines)

    def _send_message(self, text: str) -> None:
        """Call Telegram sendMessage and raise a clear error on API failure."""
        url = f"{self.API_BASE_URL}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }

        try:
            response = self.session.post(url, json=payload, timeout=self.REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            self.logger.exception("Telegram request failed")
            raise RuntimeError("Telegram request failed") from exc
        except ValueError as exc:
            self.logger.exception("Telegram returned invalid JSON")
            raise RuntimeError("Telegram returned invalid JSON") from exc

        if not body.get("ok"):
            description = body.get("description", "unknown Telegram API error")
            self.logger.error("Telegram API rejected message: %s", description)
            raise RuntimeError(f"Telegram API rejected message: {description}")

    def _split_message(self, message: str) -> list[str]:
        """Split long messages before they reach Telegram's message size limit."""
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return [message]

        chunks: list[str] = []
        current_lines: list[str] = []
        current_length = 0

        for line in message.splitlines():
            line_length = len(line) + 1
            if current_lines and current_length + line_length > self.MAX_MESSAGE_LENGTH:
                chunks.append("\n".join(current_lines))
                current_lines = []
                current_length = 0

            current_lines.append(line)
            current_length += line_length

        if current_lines:
            chunks.append("\n".join(current_lines))

        return chunks

    def _format_number(self, value: Any) -> str:
        """Format numeric values for human-readable Telegram output."""
        if pd.isna(value):
            return "N/A"

        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return str(value)

    def _value(self, token: pd.Series, key: str) -> str:
        """Read a token field and return N/A for missing values."""
        value = token.get(key)
        if pd.isna(value) or value == "":
            return "N/A"

        return str(value)
