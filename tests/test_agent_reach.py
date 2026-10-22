import os
import unittest
from types import SimpleNamespace

from jobhunter.reach.agent_reach import AgentReachSource, parse_agent_reach_output

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "agent_reach_out.jsonl")


class ParseTests(unittest.TestCase):
    def test_parses_json_lines_and_skips_junk(self):
        postings = parse_agent_reach_output(open(FIXTURE).read())
        self.assertEqual(len(postings), 2)
        self.assertEqual(postings[0].company, "Nimbus")
        self.assertEqual(postings[1].url, "https://jobs.example.com/vega/ml")
        self.assertEqual(postings[1].source, "agent-reach")


class SourceTests(unittest.TestCase):
    def test_unavailable_binary(self):
        self.assertFalse(AgentReachSource.available("definitely-not-installed-x"))

    def test_fetch_with_fake_runner(self):
        def runner(cmd, capture_output, text, timeout):
            return SimpleNamespace(returncode=0, stdout=open(FIXTURE).read(),
                                   stderr="")
        src = AgentReachSource(query="sde bengaluru", binary="sh", runner=runner)
        self.assertEqual(len(list(src.fetch())), 2)

    def test_fetch_raises_on_missing_binary(self):
        src = AgentReachSource(query="x", binary="definitely-not-installed-x")
        with self.assertRaises(RuntimeError):
            list(src.fetch())


if __name__ == "__main__":
    unittest.main()
