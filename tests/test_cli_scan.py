import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from email.utils import formatdate
from unittest import mock

from jobhunter.channels.base import Decision
from jobhunter.channels.fake import FakeChannel
from jobhunter.cli import main
from jobhunter.llm.base import CannedProvider
from jobhunter.models import JobPosting, MailMessage, Status
from jobhunter.outreach.gmail_client import FakeMailClient
from jobhunter.outreach.linkedin_queue import LinkedInQueue
from jobhunter.tracker import Tracker

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "resume.txt")

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Jobs</title>
    <item>
      <title>SDE1, Platform</title>
      <link>https://jobs.example.com/acme/sde1</link>
      <description>0-1 years, Python, Bengaluru.</description>
      <pubDate>{pubdate}</pubDate>
    </item>
  </channel>
</rss>
"""


class CLITestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg_path = os.path.join(self.tmp, "config.json")
        self.feed_path = os.path.join(self.tmp, "feed.xml")
        with open(self.feed_path, "w") as fh:
            fh.write(FEED.format(pubdate=formatdate(time.time())))
        self.cfg = {
            "tracker_path": os.path.join(self.tmp, "tracker.db"),
            "linkedin_queue_path": os.path.join(self.tmp, "queue.json"),
            "resume_path": FIXTURE,
            "rss_feeds": [self.feed_path],
            "channel_state_path": os.path.join(self.tmp, "tg_state.json"),
        }
        with open(self.cfg_path, "w") as fh:
            json.dump(self.cfg, fh)

    def run_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--config", self.cfg_path, *argv])
        return code, out.getvalue()


class ScanCLITests(CLITestBase):
    def test_scan_records_match(self):
        provider = CannedProvider(["SCORE: 85\nREASON: strong match"])
        with mock.patch("jobhunter.cli.build_provider", return_value=provider):
            code, out = self.run_cli("scan")
        self.assertEqual(code, 0)
        summary = json.loads(out[out.index("{"):])
        self.assertEqual(summary["matched"], 1)
        self.assertEqual(summary["seen"], 1)
        tracker = Tracker(self.cfg["tracker_path"])
        rows = tracker.by_status(Status.MATCHED)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://jobs.example.com/acme/sde1")
        self.assertEqual(rows[0]["fit_score"], 85)

    def test_scan_without_sources_errors(self):
        self.cfg["rss_feeds"] = []
        with open(self.cfg_path, "w") as fh:
            json.dump(self.cfg, fh)
        code, out = self.run_cli("scan")
        self.assertEqual(code, 2)
        self.assertIn("no sources configured", out)

    def test_scan_low_fit_skips(self):
        provider = CannedProvider(["SCORE: 10\nREASON: wants java"])
        with mock.patch("jobhunter.cli.build_provider", return_value=provider):
            code, out = self.run_cli("scan")
        self.assertEqual(code, 0)
        tracker = Tracker(self.cfg["tracker_path"])
        rows = tracker.by_status(Status.SKIPPED)
        self.assertEqual(len(rows), 1)
        self.assertIn("wants java", rows[0]["skip_reason"])


class RepliesCLITests(CLITestBase):
    def test_replies_flips_tracker_row(self):
        tracker = Tracker(self.cfg["tracker_path"])
        tracker.add(JobPosting(title="SDE1", company="Acme",
                               url="https://x/a", source="t"),
                    Status.MATCHED, fit_score=80, fit_reason="good")
        mail = FakeMailClient([MailMessage(
            from_addr="Priya <priya@acme.com>", subject="Re: SDE1",
            body="Can you talk Friday?")])
        with mock.patch("jobhunter.cli.build_mail", return_value=mail):
            code, out = self.run_cli("replies")
        self.assertEqual(code, 0)
        self.assertIn("replied: https://x/a", out)
        self.assertEqual(Tracker(self.cfg["tracker_path"])
                         .by_status(Status.REPLIED)[0]["url"], "https://x/a")

    def test_replies_no_match(self):
        mail = FakeMailClient([MailMessage(
            from_addr="someone@gmail.com", subject="hi", body="yo")])
        with mock.patch("jobhunter.cli.build_mail", return_value=mail):
            code, out = self.run_cli("replies")
        self.assertEqual(code, 0)
        self.assertIn("no new replies", out)


class ChannelPollCLITests(CLITestBase):
    def test_poll_applies_approve(self):
        queue = LinkedInQueue(self.cfg["linkedin_queue_path"])
        item_id = queue.draft("Asha", "https://li/asha", "hi, love your work")
        channel = FakeChannel([Decision(verdict="approve", item_id=item_id)])
        with mock.patch("jobhunter.cli.build_channel", return_value=channel):
            code, out = self.run_cli("channel", "poll")
        self.assertEqual(code, 0)
        self.assertIn(f"approved {item_id}", out)
        self.assertEqual(LinkedInQueue(self.cfg["linkedin_queue_path"])
                         .list(status="approved")[0]["id"], item_id)

    def test_poll_no_decisions(self):
        channel = FakeChannel()
        with mock.patch("jobhunter.cli.build_channel", return_value=channel):
            code, out = self.run_cli("channel", "poll")
        self.assertEqual(code, 0)
        self.assertIn("no pending decisions", out)


if __name__ == "__main__":
    unittest.main()
