import unittest

from jobhunter.handoff import build_handoff
from jobhunter.models import JobPosting


class HandoffTests(unittest.TestCase):
    def test_entry_fields(self):
        posting = JobPosting(title="SDE1", company="Acme",
                             url="https://jobs.example.com/apply", source="t")
        entry = build_handoff(posting, "captcha", resume_path="resume.txt")
        self.assertEqual(entry["reason"], "captcha")
        self.assertIn("https://jobs.example.com/apply", entry["message"])
        self.assertIn("resume.txt", entry["message"])

    def test_unknown_reason(self):
        posting = JobPosting(title="t", company="c", url="u", source="s")
        with self.assertRaises(ValueError):
            build_handoff(posting, "whatever")


if __name__ == "__main__":
    unittest.main()
