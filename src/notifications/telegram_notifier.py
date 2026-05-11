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
        """Send a Telegram message when filtered Top tokens are available."""
        if not self.enabled:
            self.logger.info("Telegram notification is disabled")
            return

        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram notification skipped because bot token or chat ID is missing")
            return

        if tokens.empty:
            self.logger.info("Telegram notification skipped because there are no Top tokens")
            return

        message = self._format_top_tokens_message(tokens)
        for chunk in self._split_message(message):
            self._send_message(chunk)

        self.logger.info("Telegram notification sent for %s Top tokens", len(tokens))

    def _format_top_tokens_message(self, tokens: pd.DataFrame) -> str:
        """Build a compact plain-text message with the requested token fields."""
        lines = ["Alpha Hunter Agent v0.5 - Top Tokens"]

        for index, token in tokens.reset_index(drop=True).iterrows():
            rank = index + 1
            lines.extend(
                [
                    "",
                    f"#{rank} {self._value(token, 'symbol')} - {self._value(token, 'token_name')}",
                    f"volume_24h: {self._format_number(token.get('volume_24h'))}",
                    f"liquidity_usd: {self._format_number(token.get('liquidity_usd'))}",
                    f"price_change_24h: {self._format_number(token.get('price_change_24h'))}%",
                    f"fdv: {self._format_number(token.get('fdv'))}",
                    f"alpha_score: {self._format_number(token.get('alpha_score'))}",
                    f"risk_score: {self._format_number(token.get('risk_score'))}",
                    f"AI Summary: {self._value(token, 'ai_summary')}",
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
