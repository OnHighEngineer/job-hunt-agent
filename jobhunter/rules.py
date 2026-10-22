"""Deterministic, no-LLM gates.

Cheap rules run before any paid model call. A posting that fails a rule
is skipped with the reason logged; the LLM never sees it.
"""
from __future__ import annotations

import re
from typing import List

from .models import JobPosting, RuleVerdict

_RANGE = re.compile(r"(\d+)\s*(?:-|\u2013|to)\s*(\d+)\s*\+?\s*(?:years?|yrs?)", re.I)
_PLUS = re.compile(r"(\d+)\s*\+\s*(?:years?|yrs?)", re.I)
_PLAIN = re.compile(r"(\d+)\s*(?:years?|yrs?)", re.I)


def extract_min_years(text: str):
    """Smallest lower-bound years-of-experience requirement in the text, else None.

    "2-4 years" -> 2, "3+ years" -> 3, "0-1 years" -> 0.
    """
    if not text:
        return None
    candidates = [int(m.group(1)) for m in _RANGE.finditer(text)]
    if not candidates:
        candidates = [int(m.group(1)) for m in _PLUS.finditer(text)]
    if not candidates:
        # Plain "N years" is a weak signal (could be company age), only use
        # it when nothing stronger matched and the number is plausible.
        candidates = [int(m.group(1)) for m in _PLAIN.finditer(text)
                      if int(m.group(1)) <= 15]
    return min(candidates) if candidates else None


def company_blocked(company: str, blocklist: List[str]) -> bool:
    low = company.lower()
    return any(b.lower() in low for b in blocklist if b.strip())


def evaluate_rules(posting: JobPosting, config) -> List[RuleVerdict]:
    """Return the list of failed rules. Empty list means the posting passes."""
    failures: List[RuleVerdict] = []

    if company_blocked(posting.company, config.blocklist):
        failures.append(RuleVerdict(
            ok=False, rule="blocklist",
            reason=f"{posting.company} is on the blocklist"))

    if (posting.posted_days_ago is not None
            and posting.posted_days_ago > config.max_posting_age_days):
        failures.append(RuleVerdict(
            ok=False, rule="freshness",
            reason=f"posted {posting.posted_days_ago} days ago "
                   f"(limit {config.max_posting_age_days})"))

    years = extract_min_years(f"{posting.title}\n{posting.description}")
    if years is not None and years > config.max_experience_years:
        failures.append(RuleVerdict(
            ok=False, rule="experience",
            reason=f"asks {years}+ years (cap {config.max_experience_years})"))

    if "intern" in posting.title.lower():
        stipend = posting.stipend_monthly
        if stipend is None or stipend < config.internship_stipend_floor:
            failures.append(RuleVerdict(
                ok=False, rule="internship_stipend",
                reason="internship without a stipend of at least "
                       f"{config.internship_stipend_floor}/month"))

    return failures
