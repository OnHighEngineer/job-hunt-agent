"""Channel interface. A channel sends alerts and collects decisions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

VERDICTS = ("approve", "skip")


@dataclass
class Decision:
    """One human decision received on a channel."""

    verdict: str   # "approve" or "skip"
    item_id: str   # queue id for approve, company token for skip
    text: str = ""  # raw message, for logging


class Channel:
    name = "base"

    def send_alert(self, text: str) -> str:
        """Send one alert message. Returns a message id."""
        raise NotImplementedError

    def poll_decisions(self) -> List[Decision]:
        """Collect new approve/skip decisions since the last poll."""
        raise NotImplementedError
