"""Wire channels into the rest of jobhunter.

channel_notifier adapts a Channel to the pipeline's notifier callable, so
handoffs arrive as chat alerts. apply_decision turns one approve/skip
decision into a LinkedIn-queue or tracker change. The channel itself
never applies, emails, or messages anyone.
"""
from __future__ import annotations

from ..models import Status
from .base import Channel, Decision


def channel_notifier(channel: Channel):
    """Adapt a Channel to Pipeline(notifier=...)."""
    def notify(entry: dict) -> None:
        channel.send_alert(entry.get("message", str(entry)))
    return notify


def apply_decision(decision: Decision, queue=None, tracker=None) -> str:
    """Apply one decision. Returns a human-readable outcome line."""
    if decision.verdict == "approve":
        if queue is None:
            return f"approve {decision.item_id}: no queue configured"
        if queue.approve(decision.item_id):
            return f"approved {decision.item_id}"
        return f"no draft {decision.item_id} waiting for approval"
    if decision.verdict == "skip":
        if tracker is None:
            return f"skip {decision.item_id}: no tracker configured"
        row = tracker.find_by_company_token(decision.item_id)
        if row is None:
            return f"no tracker row matching {decision.item_id}"
        tracker.set_status(row["url"], Status.SKIPPED,
                           next_step="none (skipped via channel)")
        return f"skipped {row['company']} ({row['url']})"
    return f"unknown verdict {decision.verdict!r}"
