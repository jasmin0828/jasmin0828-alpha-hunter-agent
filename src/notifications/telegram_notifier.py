"""Telegram Bot API notifier for Alpha Hunter Market System."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_ENABLED,
    TELEGRAM_HEALTHCHECK_ENABLED,
    TELEGRAM_HEALTHCHECK_INTERVAL_HOURS,
)


class TelegramNotifier:
    """Send Alpha Hunter Market System alerts through Telegram Bot API."""

    API_BASE_URL = "https://api.telegram.org"
    REQUEST_TIMEOUT_SECONDS = 15
    MAX_MESSAGE_LENGTH = 3900
    MAX_ALERT_TOKENS = 5
    HEALTHCHECK_STATE_PATH = Path("data/telegram_healthcheck_state.json")

    def __init__(
        self,
        bot_token: str = TELEGRAM_BOT_TOKEN,
        chat_id: str = TELEGRAM_CHAT_ID,
        enabled: bool = TELEGRAM_ENABLED,
        healthcheck_enabled: bool = TELEGRAM_HEALTHCHECK_ENABLED,
        healthcheck_interval_hours: float = TELEGRAM_HEALTHCHECK_INTERVAL_HOURS,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.healthcheck_enabled = healthcheck_enabled
        self.healthcheck_interval = timedelta(hours=healthcheck_interval_hours)
        self.session = requests.Session()

    def notify_top_tokens(self, tokens: pd.DataFrame) -> None:
        """Send a Telegram message for v1.2 signal transition events."""
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

    def notify_health_status(self, snapshots: pd.DataFrame, manifest: dict[str, Any], reason: str) -> None:
        """Send a low-frequency heartbeat when scans are healthy but quiet."""
        if os.getenv("GITHUB_ACTIONS") == "true":
            self.logger.info("Telegram health check skipped in GitHub Actions")
            return

        if not self.healthcheck_enabled:
            self.logger.info("Telegram health check is disabled")
            return

        if not self.enabled:
            self.logger.info("Telegram health check skipped because Telegram is disabled")
            return

        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram health check skipped because bot token or chat ID is missing")
            return

        now = datetime.now(timezone.utc)
        if not self._should_send_healthcheck(now):
            self.logger.info("Telegram health check skipped because interval has not elapsed")
            return

        message = self._format_health_status_message(snapshots, manifest, reason, now)
        for chunk in self._split_message(message):
            self._send_message(chunk)

        self._write_healthcheck_state(now)
        self.logger.info("Telegram health check sent")

    def notify_report(self, message: str, report_type: str) -> None:
        """Send a scheduled daily or weekly report."""
        if not self.enabled:
            self.logger.info("Telegram %s report skipped because Telegram is disabled", report_type)
            return

        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram %s report skipped because bot token or chat ID is missing", report_type)
            return

        for chunk in self._split_message(message):
            self._send_message(chunk)

        self.logger.info("Telegram %s report sent", report_type)

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

    def _should_send_healthcheck(self, now: datetime) -> bool:
        """Return true when the heartbeat interval has elapsed."""
        state = self._read_healthcheck_state()
        last_sent_at = state.get("last_sent_at")
        if not last_sent_at:
            return True

        try:
            last_sent = datetime.fromisoformat(str(last_sent_at))
        except ValueError:
            return True

        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)

        return now - last_sent >= self.healthcheck_interval

    def _read_healthcheck_state(self) -> dict[str, Any]:
        """Load heartbeat state used to avoid noisy quiet-status messages."""
        try:
            return json.loads(self.HEALTHCHECK_STATE_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.warning("Failed to read Telegram health check state: %s", exc)
            return {}

    def _write_healthcheck_state(self, sent_at: datetime) -> None:
        """Persist the latest heartbeat send time."""
        try:
            self.HEALTHCHECK_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.HEALTHCHECK_STATE_PATH.write_text(
                json.dumps({"last_sent_at": sent_at.isoformat()}, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            self.logger.warning("Failed to write Telegram health check state: %s", exc)

    def _format_top_tokens_message(self, tokens: pd.DataFrame) -> str:
        """Build a compact plain-text message with the requested token fields."""
        lines = ["Alpha Hunter Market System v1.2 - Early Alpha Signals"]

        for index, token in tokens.reset_index(drop=True).iterrows():
            rank = index + 1
            lines.extend(
                [
                    "",
                    f"#{rank} {self._value(token, 'alert_level')} Signal",
                    f"{self._value(token, 'symbol')} - {self._value(token, 'token_name')}",
                    f"event_type: {self._value(token, 'event_type')}",
                    f"previous_alert_level: {self._value(token, 'previous_alert_level')}",
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

    def _format_health_status_message(
        self,
        snapshots: pd.DataFrame,
        manifest: dict[str, Any],
        reason: str,
        now: datetime,
    ) -> str:
        """Build a compact heartbeat message for quiet-but-running periods."""
        scan_summary = manifest.get("scan_summary", {})
        signal_quality = manifest.get("signal_quality", {})
        generated_at = manifest.get("generated_at", "N/A")
        alert_distribution = scan_summary.get("alert_distribution", {})

        lines = [
            "Alpha Hunter Market System v1.2 - Health Check",
            "status: running",
            f"reason: {reason}",
            f"checked_at_utc: {now.isoformat(timespec='seconds')}",
            f"latest_scan_at_utc: {generated_at}",
            f"scan_run_id: {manifest.get('scan_run_id', 'N/A')}",
            f"token_count: {scan_summary.get('token_count', 0)}",
            f"new_signal_events: {scan_summary.get('signal_event_count', 0)}",
            f"watch_count: {alert_distribution.get('WATCH', 0)}",
            f"high_count: {alert_distribution.get('HIGH', 0)}",
            f"critical_count: {alert_distribution.get('CRITICAL', 0)}",
            f"first_seen_count: {scan_summary.get('first_seen_count', 0)}",
            f"consecutive_momentum_count: {scan_summary.get('consecutive_momentum_count', 0)}",
            f"max_early_alpha_score: {self._format_number(scan_summary.get('max_early_alpha_score', 0))}",
        ]

        repeated_watch = signal_quality.get("top_repeated_watch", [])
        if repeated_watch:
            top = repeated_watch[0]
            lines.extend(
                [
                    "",
                    "top_repeated_watch:",
                    f"symbol: {top.get('symbol', 'N/A')}",
                    f"early_alpha_score: {self._format_number(top.get('early_alpha_score', 0))}",
                    f"scan_count: {top.get('scan_count', 'N/A')}",
                    f"token_age_bucket: {top.get('token_age_bucket', 'N/A')}",
                    f"rug_risk_level: {top.get('rug_risk_level', 'N/A')}",
                ]
            )
        elif not snapshots.empty:
            top = snapshots.sort_values("early_alpha_score", ascending=False).iloc[0]
            lines.extend(
                [
                    "",
                    "top_current_candidate:",
                    f"symbol: {self._value(top, 'symbol')}",
                    f"early_alpha_score: {self._format_number(top.get('early_alpha_score'))}",
                    f"alert_level: {self._value(top, 'alert_level')}",
                    f"token_age_bucket: {self._value(top, 'token_age_bucket')}",
                    f"rug_risk_level: {self._value(top, 'rug_risk_level')}",
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
