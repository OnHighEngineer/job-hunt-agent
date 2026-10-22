"""Core data types shared across jobhunter."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional


class Status(str, enum.Enum):
    """Tracker statuses. A row moves forward through these."""

    FOUND = "found"
    MATCHED = "matched"
    SKIPPED = "skipped"
    APPLIED = "applied"
    HANDOFF = "handoff"      # waiting on a human step (captcha, login, risky form)
    REPLIED = "replied"
    INTERVIEW = "interview"
    REJECTED = "rejected"


# Statuses that mean "no action pending from the agent".
TERMINAL = {Status.SKIPPED, Status.REJECTED}


@dataclass
class JobPosting:
    title: str
    company: str
    url: str
    source: str
    description: str = ""
    location: str = ""
    posted_days_ago: Optional[int] = None
    stipend_monthly: Optional[int] = None  # INR per month, internships only
    salary_note: str = ""
    needs_human: bool = False  # known captcha / login / risky form up front


@dataclass
class RuleVerdict:
    """Outcome of one deterministic rule. ok=False means skip."""

    ok: bool
    rule: str
    reason: str = ""


@dataclass
class FitResult:
    score: int  # 0-100
    reason: str
    matched: bool


@dataclass
class OutgoingMail:
    to: str
    subject: str
    body: str


@dataclass
class MailMessage:
    from_addr: str
    subject: str
    body: str
    thread_id: str = ""
    received_ts: float = 0.0
