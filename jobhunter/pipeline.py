"""The scan loop: fetch -> rule gates -> LLM fit -> tracker -> route.

Every posting is logged, matched or skipped, with the reason. Matched
postings route to handoff (human step known) or stay matched for the
outreach review step. Reply watching flips tracker rows.
"""
from __future__ import annotations

import time
from typing import Callable, Iterable, List, Optional

from .handoff import build_handoff
from .models import JobPosting, MailMessage, OutgoingMail, Status
from .rules import evaluate_rules
from .scorer import score_fit
from .tracker import Tracker


class DailySendCapReached(Exception):
    pass


class Pipeline:
    def __init__(self, config, provider, tracker: Tracker,
                 mail=None, notifier: Optional[Callable[[dict], None]] = None,
                 now: Optional[Callable[[], float]] = None):
        self.config = config
        self.provider = provider
        self.tracker = tracker
        self.mail = mail
        self.notifier = notifier or (lambda entry: None)
        self._now = now or time.time

    def _load_resume(self) -> str:
        with open(self.config.resume_path, "r", encoding="utf-8") as fh:
            return fh.read()

    def scan(self, sources: Iterable) -> dict:
        resume = self._load_resume()
        summary = {"matched": 0, "skipped": 0, "handoff": 0, "seen": 0}
        for source in sources:
            for posting in source.fetch():
                summary["seen"] += 1
                if self.tracker.has(posting.url):
                    continue
                failures = evaluate_rules(posting, self.config)
                if failures:
                    reason = "; ".join(f.reason for f in failures)
                    self.tracker.add(posting, Status.SKIPPED, skip_reason=reason,
                                     next_step="none")
                    summary["skipped"] += 1
                    continue
                fit = score_fit(self.provider, resume, posting, self.config)
                if not fit.matched:
                    self.tracker.add(posting, Status.SKIPPED, fit_score=fit.score,
                                     skip_reason=f"fit {fit.score}: {fit.reason}",
                                     next_step="none")
                    summary["skipped"] += 1
                    continue
                if posting.needs_human:
                    entry = build_handoff(posting, "captcha",
                                          resume_path=self.config.resume_path)
                    self.tracker.add(posting, Status.HANDOFF, fit_score=fit.score,
                                     fit_reason=fit.reason,
                                     next_step=f"human: {posting.url}")
                    self.notifier(entry)
                    summary["handoff"] += 1
                else:
                    self.tracker.add(posting, Status.MATCHED, fit_score=fit.score,
                                     fit_reason=fit.reason,
                                     next_step="agent: prepare outreach for approval")
                    summary["matched"] += 1
        return summary

    def process_replies(self, query: str = "") -> List[str]:
        """Match inbox replies to tracker rows and flip them to replied."""
        if self.mail is None:
            raise RuntimeError("no mail client configured")
        updated = []
        for msg in self.mail.search_replies(query=query):
            token = self._company_token(msg)
            if not token:
                continue
            row = self.tracker.find_by_company_token(token)
            if row is None or row["status"] in (Status.REPLIED.value,
                                                Status.REJECTED.value):
                continue
            self.tracker.set_status(row["url"], Status.REPLIED,
                                    next_step="human: read and answer")
            updated.append(row["url"])
        return updated

    @staticmethod
    def _company_token(msg: MailMessage) -> str:
        """Best-effort company hint: domain of the sender, minus TLD."""
        addr = msg.from_addr
        if "@" not in addr:
            return ""
        domain = addr.rsplit("@", 1)[-1].strip(">").lower()
        if domain in ("gmail.com", "outlook.com", "yahoo.com", "hotmail.com"):
            return ""
        return domain.split(".")[0]

    def send_approved(self, mails: List[OutgoingMail]) -> int:
        """Send user-approved mails, enforcing the daily cap. Returns count sent."""
        if self.mail is None:
            raise RuntimeError("no mail client configured")
        day = time.strftime("%Y-%m-%d", time.localtime(self._now()))
        sent = 0
        for mail in mails:
            if self.tracker.sends_today(day) >= self.config.daily_send_cap:
                raise DailySendCapReached(
                    f"daily send cap {self.config.daily_send_cap} reached; "
                    f"{len(mails) - sent} approved mail(s) left unsent")
            self.mail.send(mail)
            self.tracker.record_send(mail.to, mail.subject, day)
            sent += 1
        return sent
