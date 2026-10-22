import json
import os
import tempfile
import unittest
from unittest import mock

from jobhunter.channels.base import Decision
from jobhunter.channels.telegram import TelegramChannel


def make_transport(responses):
    calls = []

    def transport(url, headers, payload, timeout):
        calls.append({"url": url, "headers": headers,
                      "payload": json.loads(payload) if payload else None})
        return responses.pop(0)

    return transport, calls


def make_channel(responses, state_path=None):
    transport, calls = make_transport(responses)
    channel = TelegramChannel(token="tok123", chat_id="chat9",
                              state_path=state_path, transport=transport)
    return channel, calls


class SendTests(unittest.TestCase):
    def test_send_alert_posts_message(self):
        channel, calls = make_channel([{"ok": True, "result": {"message_id": 42}}])
        msg_id = channel.send_alert("handoff: apply here https://x/a")
        self.assertEqual(msg_id, "42")
        self.assertEqual(len(calls), 1)
        self.assertIn("/bottok123/sendMessage", calls[0]["url"])
        self.assertEqual(calls[0]["payload"]["chat_id"], "chat9")
        self.assertIn("https://x/a", calls[0]["payload"]["text"])

    def test_api_error_raises(self):
        channel, _ = make_channel([{"ok": False, "description": "chat not found"}])
        with self.assertRaises(RuntimeError):
            channel.send_alert("hi")

    def test_missing_token_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                TelegramChannel(chat_id="c")

    def test_missing_chat_id_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                TelegramChannel(token="t")

    def test_env_credentials_used(self):
        env = {"JOBHUNTER_TELEGRAM_BOT_TOKEN": "envtok",
               "JOBHUNTER_TELEGRAM_CHAT_ID": "envchat"}
        with mock.patch.dict(os.environ, env, clear=True):
            channel = TelegramChannel(transport=make_transport(
                [{"ok": True, "result": {"message_id": 1}}])[0])
            channel.send_alert("hi")
        self.assertIn("botenvtok", channel.build_request("sendMessage", {})[0])


class ParseUpdateTests(unittest.TestCase):
    def test_parses_approve_and_skip(self):
        updates = [
            {"update_id": 10, "message": {"text": "approve ab12cd34"}},
            {"update_id": 11, "message": {"text": "Skip Acme"}},
            {"update_id": 12, "message": {"text": "just chatting"}},
            {"update_id": 13, "message": {}},
        ]
        decisions, max_id = TelegramChannel.parse_updates(updates)
        self.assertEqual(max_id, 13)
        self.assertEqual([(d.verdict, d.item_id) for d in decisions],
                         [("approve", "ab12cd34"), ("skip", "Acme")])

    def test_empty_updates(self):
        decisions, max_id = TelegramChannel.parse_updates([])
        self.assertEqual(decisions, [])
        self.assertIsNone(max_id)


class PollTests(unittest.TestCase):
    def test_poll_returns_decisions_and_persists_offset(self):
        tmp = tempfile.mkdtemp()
        state = os.path.join(tmp, "state.json")
        responses = [{"ok": True, "result": [
            {"update_id": 20, "message": {"text": "approve q1"}},
            {"update_id": 21, "message": {"text": "skip BigCo"}},
        ]}]
        channel, calls = make_channel(responses, state_path=state)
        decisions = channel.poll_decisions()
        self.assertEqual([(d.verdict, d.item_id) for d in decisions],
                         [("approve", "q1"), ("skip", "BigCo")])
        with open(state) as fh:
            self.assertEqual(json.load(fh)["offset"], 22)
        # next poll resumes from the saved offset
        channel2, calls2 = make_channel([{"ok": True, "result": []}],
                                        state_path=state)
        self.assertEqual(channel2.poll_decisions(), [])
        self.assertEqual(calls2[0]["payload"]["offset"], 22)

    def test_first_poll_has_no_offset(self):
        channel, calls = make_channel([{"ok": True, "result": []}])
        channel.poll_decisions()
        self.assertNotIn("offset", calls[0]["payload"])

    def test_corrupt_state_file_resets_offset(self):
        tmp = tempfile.mkdtemp()
        state = os.path.join(tmp, "state.json")
        with open(state, "w") as fh:
            fh.write("not json")
        channel, calls = make_channel([{"ok": True, "result": []}],
                                      state_path=state)
        self.assertEqual(channel.poll_decisions(), [])
        self.assertNotIn("offset", calls[0]["payload"])


if __name__ == "__main__":
    unittest.main()
