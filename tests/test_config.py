import json
import os
import tempfile
import unittest

from jobhunter.config import (ConfigError, HuntConfig, get_api_key, load_config)


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        cfg = HuntConfig()
        self.assertEqual(cfg.max_experience_years, 1)
        self.assertEqual(cfg.fit_threshold, 60)
        self.assertIn("Scoutit", cfg.blocklist)

    def test_from_dict_override(self):
        cfg = HuntConfig.from_dict({"fit_threshold": 70, "provider": "claude"})
        self.assertEqual(cfg.fit_threshold, 70)
        self.assertEqual(cfg.provider, "claude")

    def test_unknown_key_rejected(self):
        with self.assertRaises(ConfigError):
            HuntConfig.from_dict({"nope": 1})

    def test_unknown_provider_rejected(self):
        with self.assertRaises(ConfigError):
            HuntConfig.from_dict({"provider": "palm"})

    def test_threshold_range(self):
        with self.assertRaises(ConfigError):
            HuntConfig.from_dict({"fit_threshold": 101})

    def test_load_missing_file(self):
        with self.assertRaises(ConfigError):
            load_config("/no/such/file.json")

    def test_load_roundtrip(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"daily_send_cap": 3}, fh)
            path = fh.name
        try:
            self.assertEqual(load_config(path).daily_send_cap, 3)
        finally:
            os.unlink(path)

    def test_api_key_env_precedence(self):
        env = {"OPENAI_API_KEY": "sk-plain", "JOBHUNTER_OPENAI_API_KEY": "sk-job"}
        self.assertEqual(get_api_key("openai", env), "sk-job")

    def test_api_key_missing(self):
        with self.assertRaises(ConfigError):
            get_api_key("claude", {})


if __name__ == "__main__":
    unittest.main()
