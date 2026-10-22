"""Fake channel for tests and dry runs. Records alerts, replays decisions."""
from __future__ import annotations

from typing import List, Optional

from .base import Channel, Decision


class FakeChannel(Channel):
    name = "fake"

    def __init__(self, decisions: Optional[List[Decision]] = None):
        self.alerts: List[str] = []
        self._decisions = list(decisions or [])

    def send_alert(self, text: str) -> str:
        self.alerts.append(text)
        return f"fake-{len(self.alerts)}"

    def poll_decisions(self) -> List[Decision]:
        out, self._decisions = self._decisions, []
        return out
