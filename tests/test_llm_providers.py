import json
import unittest

from jobhunter.llm.providers import (ClaudeProvider, GeminiProvider, GrokProvider,
                                     OpenAIProvider, get_provider)


def fake_transport(payload_out):
    def transport(url, headers, payload, timeout):
        transport.seen = (url, headers, json.loads(payload.decode()))
        return payload_out
    return transport


class OpenAIShapeTests(unittest.TestCase):
    def test_openai_request_and_parse(self):
        out = {"choices": [{"message": {"content": "SCORE: 80\nREASON: ok"}}]}
        p = OpenAIProvider(api_key="k", transport=fake_transport(out))
        self.assertEqual(p.complete("hi"), "SCORE: 80\nREASON: ok")
        url, headers, body = p._transport.seen
        self.assertEqual(url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer k")
        self.assertEqual(body["model"], "gpt-4o-mini")
        self.assertEqual(body["messages"][0]["content"], "hi")

    def test_grok_uses_xai_host(self):
        p = GrokProvider(api_key="k")
        url, _, _ = p.build_request("hi", 512)
        self.assertTrue(url.startswith("https://api.x.ai/"))

    def test_empty_key_rejected(self):
        with self.assertRaises(ValueError):
            OpenAIProvider(api_key="")


class GeminiTests(unittest.TestCase):
    def test_request_and_parse(self):
        out = {"candidates": [{"content": {"parts": [{"text": "SCORE: 50\nREASON: x"}]}}]}
        p = GeminiProvider(api_key="gk", transport=fake_transport(out))
        self.assertIn("SCORE: 50", p.complete("hi"))
        url, _, body = p._transport.seen
        self.assertIn("key=gk", url)
        self.assertIn("gemini-2.0-flash", url)
        self.assertEqual(body["contents"][0]["parts"][0]["text"], "hi")


class ClaudeTests(unittest.TestCase):
    def test_request_and_parse(self):
        out = {"content": [{"type": "text", "text": "SCORE: 70\nREASON: y"}]}
        p = ClaudeProvider(api_key="ck", transport=fake_transport(out))
        self.assertIn("SCORE: 70", p.complete("hi"))
        _, headers, _ = p._transport.seen
        self.assertEqual(headers["x-api-key"], "ck")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")


class FactoryTests(unittest.TestCase):
    def test_unknown_provider(self):
        with self.assertRaises(ValueError):
            get_provider("palm", api_key="k")

    def test_factory_builds(self):
        self.assertEqual(get_provider("openai", api_key="k").name, "openai")


if __name__ == "__main__":
    unittest.main()
