from __future__ import annotations

import unittest

import pandas as pd

from src.notifications.telegram_notifier import TelegramNotifier


class TelegramDeliveryEvidenceTests(unittest.TestCase):
    def test_disabled_and_not_configured_are_observable_without_attempt(self) -> None:
        disabled = TelegramNotifier(bot_token="", chat_id="", enabled=False)
        result = disabled.notify_top_tokens(pd.DataFrame())
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["attempted"])

        missing = TelegramNotifier(bot_token="", chat_id="", enabled=True)
        result = missing.notify_report("controlled", "daily")
        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(result["attempted"])
        self.assertNotIn("bot_token", result)
        self.assertNotIn("chat_id", result)

    def test_success_and_failure_distinguish_attempt_outcome(self) -> None:
        notifier = TelegramNotifier(bot_token="fake-token", chat_id="fake-chat", enabled=True)
        notifier._send_message = lambda message: None  # type: ignore[method-assign]
        result = notifier.notify_report("controlled", "daily")
        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["configured"])
        self.assertTrue(result["attempted"])

        def fail(_message: str) -> None:
            raise RuntimeError("controlled Telegram failure")

        notifier._send_message = fail  # type: ignore[method-assign]
        with self.assertRaises(RuntimeError):
            notifier.notify_report("controlled", "daily")

        captured = notifier.capture_delivery("daily", lambda: notifier.notify_report("controlled", "daily"))
        self.assertEqual(captured["status"], "failed")
        self.assertTrue(captured["attempted"])
        self.assertEqual(captured["error"], "RuntimeError")
        self.assertNotIn("fake-token", str(captured))

    def test_configured_but_empty_signals_are_not_attempted(self) -> None:
        notifier = TelegramNotifier(bot_token="fake-token", chat_id="fake-chat", enabled=True)
        result = notifier.notify_top_tokens(pd.DataFrame())
        self.assertEqual(result["status"], "not_attempted")
        self.assertTrue(result["configured"])
        self.assertFalse(result["attempted"])


if __name__ == "__main__":
    unittest.main()
