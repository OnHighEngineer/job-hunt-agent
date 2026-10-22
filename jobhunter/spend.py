"""Monthly LLM spend ledger with a hard cap.

Every paid call is recorded locally. When the month's estimated cost
reaches the cap, further calls raise SpendCapReached instead of spending.
"""
from __future__ import annotations

import json
import os
import time
from typing import Callable, Dict, Optional, Tuple

# (prompt, completion) USD per 1K tokens, conservative public-list approximations.
COST_PER_1K_USD: Dict[str, Tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gemini-2.0-flash": (0.0001, 0.0004),
    "grok-2-latest": (0.002, 0.01),
    "claude-3-5-haiku-latest": (0.0008, 0.004),
}
_FALLBACK_COST = (0.002, 0.01)


class SpendCapReached(Exception):
    pass


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pin, pout = COST_PER_1K_USD.get(model, _FALLBACK_COST)
    return (prompt_tokens * pin + completion_tokens * pout) / 1000.0


class SpendLedger:
    def __init__(self, path: str, now: Optional[Callable[[], float]] = None):
        self.path = path
        self._now = now or time.time
        self._entries = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                self._entries = json.load(fh).get("entries", [])

    def _month(self) -> str:
        return time.strftime("%Y-%m", time.localtime(self._now()))

    def record(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
        self._entries.append({
            "month": self._month(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": round(cost, 6),
        })
        self._save()
        return cost

    def month_total(self, month: Optional[str] = None) -> float:
        month = month or self._month()
        return round(sum(e["cost_usd"] for e in self._entries
                         if e["month"] == month), 6)

    def check(self, cap_usd: float) -> None:
        total = self.month_total()
        if total >= cap_usd:
            raise SpendCapReached(
                f"monthly spend {total:.4f} USD reached cap {cap_usd:.2f} USD")

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"entries": self._entries}, fh, indent=2)
