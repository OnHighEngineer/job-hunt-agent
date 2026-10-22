import os
import unittest

from jobhunter.config import HuntConfig
from jobhunter.llm.base import CannedProvider
from jobhunter.models import JobPosting
from jobhunter.scorer import (FitParseError, build_fit_prompt, parse_fit_reply,
                              score_fit)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "resume.txt")


class PromptTests(unittest.TestCase):
    def test_prompt_carries_resume_jd_and_rules(self):
        cfg = HuntConfig()
        resume = open(FIXTURE).read()
        posting = JobPosting(title="AI Engineer", company="Nimbus",
                             url="https://x", source="t",
                             description="0-1 yrs, LLM apps", location="Bengaluru")
        prompt = build_fit_prompt(resume, posting, cfg)
        self.assertIn("LLM audit agent", prompt)
        self.assertIn("0-1 yrs, LLM apps", prompt)
        self.assertIn("SDE1", prompt)
        self.assertIn("Bengaluru", prompt)


class ParseTests(unittest.TestCase):
    def test_good_reply(self):
        r = parse_fit_reply("SCORE: 85\nREASON: strong match")
        self.assertEqual((r.score, r.reason), (85, "strong match"))

    def test_no_score(self):
        with self.assertRaises(FitParseError):
            parse_fit_reply("REASON: nothing")

    def test_score_out_of_range(self):
        with self.assertRaises(FitParseError):
            parse_fit_reply("SCORE: 140\nREASON: x")

    def test_no_reason(self):
        with self.assertRaises(FitParseError):
            parse_fit_reply("SCORE: 40")


class ScoreFitTests(unittest.TestCase):
    def test_threshold_boundary(self):
        cfg = HuntConfig(fit_threshold=60)
        resume = open(FIXTURE).read()
        posting = JobPosting(title="t", company="c", url="u", source="s")
        hit = score_fit(CannedProvider(["SCORE: 60\nREASON: edge"]), resume, posting, cfg)
        self.assertTrue(hit.matched)
        miss = score_fit(CannedProvider(["SCORE: 59\nREASON: close"]), resume, posting, cfg)
        self.assertFalse(miss.matched)


if __name__ == "__main__":
    unittest.main()
