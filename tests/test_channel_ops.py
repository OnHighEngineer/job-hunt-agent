import os
import tempfile
import unittest

from jobhunter.channels.base import Decision
from jobhunter.channels.fake import FakeChannel
from jobhunter.channels.ops import apply_decision, channel_notifier
from jobhunter.models import JobPosting, Status
from jobhunter.outreach.linkedin_queue import LinkedInQueue
from jobhunter.tracker import Tracker

POSTING = JobPosting(title="SDE1", company="Acme", url="https://x/a", source="t")


class NotifierTests(unittest.TestCase):
    def test_notifier_sends_handoff_message(self):
        channel = FakeChannel()
        notify = channel_notifier(channel)
        notify({"message": "Your step: SDE1 at Acme needs a human (captcha). "
                           "Apply here: https://x/a", "url": "https://x/a"})
        self.assertEqual(len(channel.alerts), 1)
        self.assertIn("https://x/a", channel.alerts[0])


class ApproveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.queue = LinkedInQueue(os.path.join(self.tmp, "queue.json"))

    def test_approve_approves_draft(self):
        item_id = self.queue.draft("Asha", "https://li/asha", "hi, love your work")
        out = apply_decision(Decision(verdict="approve", item_id=item_id),
                             queue=self.queue)
        self.assertEqual(out, f"approved {item_id}")
        self.assertEqual(self.queue.list(status="approved")[0]["id"], item_id)

    def test_approve_unknown_id(self):
        out = apply_decision(Decision(verdict="approve", item_id="nope"),
                             queue=self.queue)
        self.assertIn("no draft", out)


class SkipTests(unittest.TestCase):
    def test_skip_flips_tracker_row(self):
        tracker = Tracker(":memory:")
        tracker.add(POSTING, Status.MATCHED, fit_score=80, fit_reason="good")
        out = apply_decision(Decision(verdict="skip", item_id="acme"),
                             tracker=tracker)
        self.assertIn("skipped Acme", out)
        row = tracker.by_status(Status.SKIPPED)[0]
        self.assertEqual(row["url"], POSTING.url)
        self.assertEqual(row["status"], Status.SKIPPED.value)

    def test_skip_unknown_company(self):
        tracker = Tracker(":memory:")
        out = apply_decision(Decision(verdict="skip", item_id="ghost"),
                             tracker=tracker)
        self.assertIn("no tracker row", out)


if __name__ == "__main__":
    unittest.main()
