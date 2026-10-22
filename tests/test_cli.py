import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from jobhunter.cli import main


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg_path = os.path.join(self.tmp, "config.json")
        with open(self.cfg_path, "w") as fh:
            json.dump({
                "tracker_path": os.path.join(self.tmp, "tracker.db"),
                "linkedin_queue_path": os.path.join(self.tmp, "queue.json"),
                "resume_path": os.path.join(self.tmp, "resume.txt"),
            }, fh)

    def run_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--config", self.cfg_path, *argv])
        return code, out.getvalue()

    def test_status_empty(self):
        code, out = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("tracker is empty", out)

    def test_export(self):
        code, out = self.run_cli("export", "--out", os.path.join(self.tmp, "t.csv"))
        self.assertEqual(code, 0)
        self.assertIn("exported 0 rows", out)

    def test_linkedin_approve_missing(self):
        code, out = self.run_cli("linkedin", "approve", "nope")
        self.assertEqual(code, 1)

    def test_doctor_reports_missing_resume(self):
        code, out = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("resume file: MISSING", out)


if __name__ == "__main__":
    unittest.main()
