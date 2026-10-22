import unittest

from jobhunter.config import HuntConfig
from jobhunter.models import JobPosting
from jobhunter.rules import company_blocked, evaluate_rules, extract_min_years


def posting(**kw):
    base = dict(title="SDE1", company="Acme", url="https://x/1", source="t",
                posted_days_ago=1)
    base.update(kw)
    return JobPosting(**base)


class ExtractYearsTests(unittest.TestCase):
    def test_range_takes_lower_bound(self):
        self.assertEqual(extract_min_years("2-4 years of experience"), 2)

    def test_plus(self):
        self.assertEqual(extract_min_years("3+ years required"), 3)

    def test_zero_to_one(self):
        self.assertEqual(extract_min_years("0-1 years"), 0)

    def test_no_requirement(self):
        self.assertIsNone(extract_min_years("Bachelor's degree preferred"))

    def test_plain_years(self):
        self.assertEqual(extract_min_years("5 years of experience"), 5)


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.cfg = HuntConfig()

    def test_fresh_junior_role_passes(self):
        self.assertEqual(evaluate_rules(posting(), self.cfg), [])

    def test_blocklist(self):
        self.assertTrue(company_blocked("Scoutit Labs", self.cfg.blocklist))
        fails = evaluate_rules(posting(company="Scoutit"), self.cfg)
        self.assertEqual([f.rule for f in fails], ["blocklist"])

    def test_stale_posting(self):
        fails = evaluate_rules(posting(posted_days_ago=30), self.cfg)
        self.assertEqual([f.rule for f in fails], ["freshness"])

    def test_experience_over_cap(self):
        fails = evaluate_rules(
            posting(description="Needs 3+ years of experience"), self.cfg)
        self.assertEqual([f.rule for f in fails], ["experience"])

    def test_intern_without_stipend(self):
        fails = evaluate_rules(posting(title="AI Intern"), self.cfg)
        self.assertEqual([f.rule for f in fails], ["internship_stipend"])

    def test_intern_with_good_stipend_passes(self):
        fails = evaluate_rules(
            posting(title="AI Intern", stipend_monthly=60000), self.cfg)
        self.assertEqual(fails, [])

    def test_multiple_failures_all_reported(self):
        fails = evaluate_rules(
            posting(company="Scoutit", posted_days_ago=30), self.cfg)
        self.assertEqual([f.rule for f in fails], ["blocklist", "freshness"])


if __name__ == "__main__":
    unittest.main()
