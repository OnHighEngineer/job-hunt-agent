import os
import unittest
from email.utils import parsedate_to_datetime

from jobhunter.reach.rss import RSSSource

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "feed.xml")
NOW = parsedate_to_datetime("Thu, 22 Oct 2026 12:00:00 +0530").timestamp()

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Agentic AI Engineer</title>
    <link href="https://jobs.example.com/zephyr/agentic"/>
    <summary>0-1 years, remote India</summary>
    <updated>2026-10-22T06:00:00Z</updated>
  </entry>
</feed>
"""


class RSSTests(unittest.TestCase):
    def test_parse_items(self):
        src = RSSSource(open(FIXTURE).read(), name="test", now=NOW)
        postings = list(src.fetch())
        self.assertEqual(len(postings), 2)
        self.assertEqual(postings[0].title, "SDE1, Platform")
        self.assertEqual(postings[0].url, "https://jobs.example.com/acme/sde1")

    def test_posted_days_ago(self):
        src = RSSSource(open(FIXTURE).read(), now=NOW)
        fresh, stale = list(src.fetch())
        self.assertEqual(fresh.posted_days_ago, 1)
        self.assertEqual(stale.posted_days_ago, 17)

    def test_atom_entry_with_href_link(self):
        src = RSSSource(ATOM, now=NOW)
        (posting,) = list(src.fetch())
        self.assertEqual(posting.url, "https://jobs.example.com/zephyr/agentic")
        self.assertEqual(posting.posted_days_ago, 0)


if __name__ == "__main__":
    unittest.main()
