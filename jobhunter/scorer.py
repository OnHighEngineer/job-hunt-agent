"""Resume-vs-JD fit scoring with the user's chosen LLM.

The model answers in a strict two-line format so the result parses
deterministically:

    SCORE: <0-100>
    REASON: <one line>
"""
from __future__ import annotations

import re

from .models import FitResult, JobPosting


class FitParseError(ValueError):
    pass


PROMPT_TEMPLATE = """You are a strict job-fit screener. Decide whether this candidate
should apply for this role.

Candidate rules:
- Target roles: {roles}
- At most {max_years} year(s) of experience; skip roles needing more
- Locations, in order: {locations}

RESUME:
{resume}

JOB DESCRIPTION ({title} at {company}, {location}):
{description}

Answer in exactly this format:
SCORE: <integer 0-100, how well the resume fits this JD>
REASON: <one line, the deciding factor>
"""


def build_fit_prompt(resume_text: str, posting: JobPosting, config) -> str:
    return PROMPT_TEMPLATE.format(
        roles=", ".join(config.roles),
        max_years=config.max_experience_years,
        locations=", ".join(config.locations),
        resume=resume_text.strip(),
        title=posting.title,
        company=posting.company,
        location=posting.location or "unspecified",
        description=posting.description.strip(),
    )


def parse_fit_reply(text: str) -> FitResult:
    m = re.search(r"SCORE:\s*(\d{1,3})", text)
    if not m:
        raise FitParseError(f"no SCORE line in reply: {text[:120]!r}")
    score = int(m.group(1))
    if score > 100:
        raise FitParseError(f"score out of range: {score}")
    r = re.search(r"REASON:\s*(.+)", text)
    if not r:
        raise FitParseError(f"no REASON line in reply: {text[:120]!r}")
    reason = r.group(1).strip()
    return FitResult(score=score, reason=reason, matched=False)


def score_fit(provider, resume_text: str, posting: JobPosting, config) -> FitResult:
    prompt = build_fit_prompt(resume_text, posting, config)
    reply = provider.complete(prompt)
    result = parse_fit_reply(reply)
    result.matched = result.score >= config.fit_threshold
    return result
