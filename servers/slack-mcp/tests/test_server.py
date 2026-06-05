import os
import sys
import unittest
from unittest.mock import patch


SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import server  # noqa: E402


class SlackServerTests(unittest.TestCase):
    def test_extract_first_reply_skips_root_and_bot(self):
        messages = [
            {"ts": "1710000000.000100", "user": "BOTUSER", "text": "root"},
            {"ts": "1710000000.000200", "user": "BOTUSER", "text": "bot reply"},
            {"ts": "1710000000.000300", "user": "U123", "text": "human reply"},
        ]

        reply = server._extract_first_reply(messages, root_ts="1710000000.000100", bot_user_id="BOTUSER")

        self.assertEqual(reply, messages[2])

    def test_wait_for_reply_returns_thread_details(self):
        responses = [
            {"ok": True, "user_id": "BOTUSER"},
            {"ok": True, "ts": "1710000000.000100", "message": {"text": "hello"}},
            {"ok": True, "messages": [{"ts": "1710000000.000100", "user": "BOTUSER", "text": "hello"}]},
            {
                "ok": True,
                "messages": [
                    {"ts": "1710000000.000100", "user": "BOTUSER", "text": "hello"},
                    {"ts": "1710000000.000200", "user": "U123", "text": "reply"},
                ],
            },
        ]

        with patch.object(server, "_request", side_effect=responses), patch.object(server.time, "sleep", return_value=None):
            result = server.slack_post_message_and_wait_for_reply(
                channel_id="C123",
                message="hello",
                timeout_seconds=2,
                poll_interval_seconds=0.5,
            )

        self.assertIn('"thread_ts": "1710000000.000100"', result)
        self.assertIn('"reply": {"ts": "1710000000.000200", "user": "U123", "text": "reply"}', result)

    def test_headers_require_token(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(server, "SLACK_BOT_TOKEN", ""):
            with self.assertRaisesRegex(ValueError, "SLACK_BOT_TOKEN is required"):
                server._headers()


if __name__ == "__main__":
    unittest.main()
