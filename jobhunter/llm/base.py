"""Provider interface. Anything that can complete a prompt is an LLM."""
from __future__ import annotations

from typing import List


class LLMProvider:
    name = "base"

    def complete(self, prompt: str, max_tokens: int = 512) -> str:
        raise NotImplementedError


class CannedProvider(LLMProvider):
    """Test provider: replays queued replies, records prompts. No network."""

    name = "canned"

    def __init__(self, replies: List[str]):
        self._replies = list(replies)
        self.calls: List[str] = []

    def complete(self, prompt: str, max_tokens: int = 512) -> str:
        self.calls.append(prompt)
        if not self._replies:
            raise AssertionError("CannedProvider ran out of replies")
        return self._replies.pop(0)
