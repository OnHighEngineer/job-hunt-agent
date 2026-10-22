"""Agent-Reach (github.com/Panniantong/Agent-Reach) as the reach layer.

Agent-Reach is an external MIT-licensed CLI that gives agents read-only
internet reach: web search, clean page reads, RSS, public LinkedIn pages.
jobhunter shells out to it when installed and parses its JSON output.
It is never vendored and never required: any JobSource works without it.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Callable, Iterable, List

from ..models import JobPosting
from .base import JobSource


def parse_agent_reach_output(text: str, source_name: str = "agent-reach"
                             ) -> List[JobPosting]:
    """Parse JSON-lines search results into postings.

    Expected per line: {"title": ..., "url"/"link": ..., "snippet"/"description": ...,
    optional "company": ...}
    """
    postings = []
    for line in text.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        title = data.get("title", "").strip()
        url = (data.get("url") or data.get("link") or "").strip()
        if not title or not url:
            continue
        postings.append(JobPosting(
            title=title,
            company=data.get("company", ""),
            url=url,
            source=source_name,
            description=data.get("snippet") or data.get("description") or ""))
    return postings


class AgentReachSource(JobSource):
    """Runs `agent-reach <channel> <query>` and parses its output."""

    def __init__(self, channel: str = "web-search", query: str = "",
                 binary: str = "agent-reach",
                 runner: Callable = subprocess.run, timeout: float = 120.0):
        self.channel = channel
        self.query = query
        self.binary = binary
        self._runner = runner
        self._timeout = timeout
        self.name = f"agent-reach:{channel}"

    @staticmethod
    def available(binary: str = "agent-reach") -> bool:
        return shutil.which(binary) is not None

    def fetch(self) -> Iterable[JobPosting]:
        if not self.available(self.binary):
            raise RuntimeError(
                f"{self.binary!r} not found. Install Agent-Reach from "
                "https://github.com/Panniantong/Agent-Reach or use another source.")
        proc = self._runner(
            [self.binary, self.channel, self.query],
            capture_output=True, text=True, timeout=self._timeout)
        if proc.returncode != 0:
            raise RuntimeError(
                f"agent-reach exited {proc.returncode}: {proc.stderr.strip()[:200]}")
        return parse_agent_reach_output(proc.stdout, source_name=self.name)
