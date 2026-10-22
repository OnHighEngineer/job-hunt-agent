import unittest

from jobhunter.reach.rss import RSSSource, _company_from_url

FEED_NO_COMPANY = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Jobs</title>
  <item>
    <title>SDE1</title>
    <link>https://boards.example.io/acme/sde1</link>
    <description>0-1 years</description>
  </item>
</channel></rss>
"""

FEED_WITH_COMPANY = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Jobs</title>
  <item>
    <title>SDE1</title>
    <link>https://boards.example.io/wrong/sde1</link>
    <company>Acme</company>
    <description>0-1 years</description>
  </item>
</channel></rss>
"""


class CompanyFromURLTests(unittest.TestCase):
    def test_first_path_segment_wins(self):
        self.assertEqual(
            _company_from_url("https://boards.example.io/acme/sde1"), "acme")

    def test_generic_path_falls_back_to_domain(self):
        self.assertEqual(
            _company_from_url("https://example.com/jobs/123"), "example")

    def test_bare_domain(self):
        self.assertEqual(
            _company_from_url("https://acme.com"), "acme")


class RSSCompanyTests(unittest.TestCase):
    def test_company_derived_from_link_when_tag_missing(self):
        (posting,) = RSSSource(FEED_NO_COMPANY).fetch()
        self.assertEqual(posting.company, "acme")

    def test_explicit_company_tag_wins(self):
        (posting,) = RSSSource(FEED_WITH_COMPANY).fetch()
        self.assertEqual(posting.company, "Acme")


if __name__ == "__main__":
    unittest.main()
