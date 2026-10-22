import os
import unittest

from jobhunter.config import HuntConfig
from jobhunter.llm.base import CannedProvider
from jobhunter.models import JobPosting, MailMessage, OutgoingMail, Status
from jobhunter.pipeline import DailySendCapReached, Pipeline
from jobhunter.reach.base import StaticSource
from jobhunter.outreach.gmail_client import FakeMailClient
from jobhunter.tracker import Tracker

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "resume.txt")

GOOD = JobPosting(title="SDE1", company="Acme", url="https://x/a", source="t",
                  description="0-1 years, Python", posted_days_ago=1)
SENIOR = JobPosting(title="Staff Engineer", company="BigCo", url="https://x/b",
                    source="t", description="8+ years", posted_days_ago=1)
BLOCKED = JobPosting(title="SDE1", company="Scoutit", url="https://x/c",
                     source="t", posted_days_ago=1)
HUMAN = JobPosting(title="AI Engineer", company="Nimbus", url="https://x/d",
                   source="t", description="0-1 years", posted_days_ago=0,
                   needs_human=True)


def make_pipeline(provider, mail=None, notifier=None, **cfg_over):
    cfg = HuntConfig(resume_path=FIXTURE, **cfg_over)
    return Pipeline(cfg, provider, Tracker(":memory:"), mail=mail,
                    notifier=notifier), cfg


class ScanTests(unittest.TestCase):
    def test_end_to_end(self):
        provider = CannedProvider(["SCORE: 80\nREASON: strong",
                                   "SCORE: 75\nREASON: good"])
        handed_off = []
        pipe, _ = make_pipeline(provider, notifier=handed_off.append)
        summary = pipe.scan([StaticSource([GOOD, SENIOR, BLOCKED, HUMAN])])

        self.assertEqual(summary["seen"], 4)
        self.assertEqual(summary["matched"], 1)
        self.assertEqual(summary["skipped"], 2)
        self.assertEqual(summary["handoff"], 1)

        # LLM only saw the two gate-passing postings, never the ruled-out ones
        self.assertEqual(len(provider.calls), 2)

        self.assertEqual(pipe.tracker.by_status(Status.MATCHED)[0]["url"], GOOD.url)
        self.assertEqual(pipe.tracker.by_status(Status.HANDOFF)[0]["url"], HUMAN.url)
        self.assertEqual(len(handed_off), 1)
        self.assertIn(HUMAN.url, handed_off[0]["message"])
        skipped = {r["url"]: r["skip_reason"] for r in pipe.tracker.by_status(Status.SKIPPED)}
        self.assertIn("8+ years", skipped[SENIOR.url])
        self.assertIn("blocklist", skipped[BLOCKED.url])

    def test_second_scan_dedupes(self):
        provider = CannedProvider(["SCORE: 80\nREASON: strong"])
        pipe, _ = make_pipeline(provider)
        pipe.scan([StaticSource([GOOD])])
        summary = pipe.scan([StaticSource([GOOD])])
        self.assertEqual(summary["seen"], 1)
        self.assertEqual(summary["matched"], 0)
        self.assertEqual(len(provider.calls), 1)

    def test_low_fit_skipped_with_reason(self):
        provider = CannedProvider(["SCORE: 20\nREASON: wants java"])
        pipe, _ = make_pipeline(provider)
        summary = pipe.scan([StaticSource([GOOD])])
        self.assertEqual(summary["skipped"], 1)
        row = pipe.tracker.by_status(Status.SKIPPED)[0]
        self.assertIn("wants java", row["skip_reason"])
        self.assertEqual(row["fit_score"], 20)


class ReplyTests(unittest.TestCase):
    def test_reply_flips_status(self):
        provider = CannedProvider(["SCORE: 80\nREASON: strong"])
        mail = FakeMailClient([MailMessage(
            from_addr="Priya <priya@acme.com>", subject="Re: SDE1",
            body="Can you talk Friday?")])
        pipe, _ = make_pipeline(provider, mail=mail)
        pipe.scan([StaticSource([GOOD])])
        updated = pipe.process_replies()
        self.assertEqual(updated, [GOOD.url])
        self.assertEqual(pipe.tracker.by_status(Status.REPLIED)[0]["url"], GOOD.url)

    def test_free_webmail_sender_ignored(self):
        provider = CannedProvider(["SCORE: 80\nREASON: strong"])
        mail = FakeMailClient([MailMessage(
            from_addr="someone@gmail.com", subject="hi", body="yo")])
        pipe, _ = make_pipeline(provider, mail=mail)
        pipe.scan([StaticSource([GOOD])])
        self.assertEqual(pipe.process_replies(), [])


class SendCapTests(unittest.TestCase):
    def test_daily_cap(self):
        provider = CannedProvider([])
        mail = FakeMailClient()
        pipe, _ = make_pipeline(provider, mail=mail, daily_send_cap=1)
        mails = [OutgoingMail(to="a@acme.com", subject="s", body="b"),
                 OutgoingMail(to="b@acme.com", subject="s", body="b")]
        with self.assertRaises(DailySendCapReached):
            pipe.send_approved(mails)
        self.assertEqual(len(mail.sent), 1)


if __name__ == "__main__":
    unittest.main()
