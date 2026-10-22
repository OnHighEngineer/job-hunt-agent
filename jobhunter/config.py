"""Configuration: defaults, JSON config file, environment for secrets.

Secrets (LLM API keys, Gmail token) come from the environment only and
are never written to disk by jobhunter.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ConfigError(Exception):
    pass


# env var fallbacks per provider, first match wins
KEY_ENV_VARS: Dict[str, List[str]] = {
    "openai": ["JOBHUNTER_OPENAI_API_KEY", "OPENAI_API_KEY"],
    "gemini": ["JOBHUNTER_GEMINI_API_KEY", "GEMINI_API_KEY"],
    "grok": ["JOBHUNTER_GROK_API_KEY", "XAI_API_KEY"],
    "claude": ["JOBHUNTER_CLAUDE_API_KEY", "ANTHROPIC_API_KEY"],
}

DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "grok": "grok-2-latest",
    "claude": "claude-3-5-haiku-latest",
}

DEFAULT_RULES = {
    "roles": ["SDE1", "AI Engineer", "Applied AI", "Agentic AI", "ML Engineer"],
    "max_experience_years": 1,
    "locations": ["Bengaluru", "Remote India", "Europe", "United States"],
    "salary_min_lpa": 9,
    "salary_max_lpa": 16,
    "internship_stipend_floor": 50000,
    "max_posting_age_days": 3,
    "blocklist": ["Scoutit"],
}


@dataclass
class HuntConfig:
    roles: List[str] = field(default_factory=lambda: list(DEFAULT_RULES["roles"]))
    max_experience_years: int = DEFAULT_RULES["max_experience_years"]
    locations: List[str] = field(default_factory=lambda: list(DEFAULT_RULES["locations"]))
    salary_min_lpa: int = DEFAULT_RULES["salary_min_lpa"]
    salary_max_lpa: int = DEFAULT_RULES["salary_max_lpa"]
    internship_stipend_floor: int = DEFAULT_RULES["internship_stipend_floor"]
    max_posting_age_days: int = DEFAULT_RULES["max_posting_age_days"]
    blocklist: List[str] = field(default_factory=lambda: list(DEFAULT_RULES["blocklist"]))
    fit_threshold: int = 60
    daily_send_cap: int = 10
    provider: str = "openai"
    model: Optional[str] = None
    monthly_spend_cap_usd: float = 5.0
    resume_path: str = "resume.txt"
    tracker_path: str = "tracker.db"
    spend_log_path: str = "spend.json"
    linkedin_queue_path: str = "linkedin_queue.json"
    rss_feeds: List[str] = field(default_factory=list)
    agent_reach_queries: List[str] = field(default_factory=list)
    channel_state_path: str = "telegram_state.json"

    @classmethod
    def from_dict(cls, data: dict) -> "HuntConfig":
        valid = set(cls.__dataclass_fields__)
        unknown = set(data) - valid
        if unknown:
            raise ConfigError(f"unknown config keys: {sorted(unknown)}")
        cfg = cls(**data)
        if cfg.provider not in KEY_ENV_VARS:
            raise ConfigError(
                f"unknown provider {cfg.provider!r}; "
                f"choose from {sorted(KEY_ENV_VARS)}")
        if not 0 <= cfg.fit_threshold <= 100:
            raise ConfigError("fit_threshold must be 0-100")
        if cfg.daily_send_cap < 0:
            raise ConfigError("daily_send_cap must be >= 0")
        return cfg

    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS[self.provider]


def load_config(path: Optional[str] = None) -> HuntConfig:
    if path is None:
        return HuntConfig()
    if not os.path.exists(path):
        raise ConfigError(f"config file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return HuntConfig.from_dict(data)


def get_api_key(provider: str, env=None) -> str:
    """Resolve a provider API key from the environment. Never logs the value."""
    env = os.environ if env is None else env
    if provider not in KEY_ENV_VARS:
        raise ConfigError(f"unknown provider {provider!r}")
    for name in KEY_ENV_VARS[provider]:
        value = env.get(name, "").strip()
        if value:
            return value
    raise ConfigError(
        f"no API key for {provider}: set one of {KEY_ENV_VARS[provider]}")
