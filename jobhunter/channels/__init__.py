"""Chat channels: alerts out, approve/skip decisions in.

A channel is how the agent reaches its human: handoff links, match
alerts, and the replies that approve a LinkedIn draft or skip a company.
Telegram is the first channel; the interface is pluggable.
"""
from .base import Channel, Decision, VERDICTS
from .fake import FakeChannel

__all__ = ["Channel", "Decision", "VERDICTS", "FakeChannel"]
