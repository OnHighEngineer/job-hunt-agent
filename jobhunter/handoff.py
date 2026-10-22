"""Human handoff: the agent stops and hands over a link.

Captchas, logins, and risky forms are the user's step, not the agent's.
A handoff entry says where to go, what to use, and why the agent stopped.
"""
from __future__ import annotations

from typing import Optional

from .models import JobPosting

HUMAN_REASONS = ("captcha", "login_required", "risky_form", "uncertain_field")


def build_handoff(posting: JobPosting, reason: str,
                  resume_path: Optional[str] = None) -> dict:
    if reason not in HUMAN_REASONS:
        raise ValueError(f"unknown handoff reason {reason!r}; "
                         f"choose from {HUMAN_REASONS}")
    return {
        "url": posting.url,
        "company": posting.company,
        "title": posting.title,
        "reason": reason,
        "resume_path": resume_path or "",
        "message": (f"Your step: {posting.title} at {posting.company} needs a human "
                    f"({reason}). Apply here: {posting.url}"
                    + (f" with resume {resume_path}" if resume_path else "")),
    }
