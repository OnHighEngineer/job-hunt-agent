import os
import tempfile
import unittest

from jobhunter.models import JobPosting, Status
from jobhunter.tracker import Tracker


def posting(url="https://x/1", company="Acme"):
    return JobPosting(title="SDE1", company=company, url=url, source="t")


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = Tracker(":memory:")

    def tearDown(self):
        self.tracker.close()

    def test_add_and_has(self):
        self.assertFalse(self.tracker.has("https://x/1"))
        self.tracker.add(posting(), Status.MATCHED, fit_score=80)
        self.assertTrue(self.tracker.has("https://x/1"))

    def test_status_transition(self):
        self.tracker.add(posting(), Status.MATCHED)
        self.assertTrue(self.tracker.set_status("https://x/1", Status.APPLIED))
        self.assertFalse(self.tracker.set_status("https://missing", Status.APPLIED))
        rows = self.tracker.by_status(Status.APPLIED)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "Acme")

    def test_find_by_company_token(self):
        self.tracker.add(posting(company="Acme Corp"), Status.MATCHED)
        row = self.tracker.find_by_company_token("acme")
        self.assertIsNotNone(row)
        self.assertIsNone(self.tracker.find_by_company_token("zzz"))

    def test_send_log(self):
        self.tracker.record_send("a@b.co", "hi", "2026-10-22")
        self.tracker.record_send("c@d.co", "hi", "2026-10-22")
        self.assertEqual(self.tracker.sends_today("2026-10-22"), 2)
        self.assertEqual(self.tracker.sends_today("2026-10-23"), 0)

    def test_export_csv(self):
        self.tracker.add(posting(), Status.SKIPPED, skip_reason="stale")
        with tempfile.NamedTemporaryFile("r", suffix=".csv", delete=False) as fh:
            path = fh.name
        try:
            self.assertEqual(self.tracker.export_csv(path), 1)
            content = open(path).read()
            self.assertIn("url,first_seen,source", content.splitlines()[0])
            self.assertIn("https://x/1", content)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
