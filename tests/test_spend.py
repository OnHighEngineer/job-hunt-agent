import os
import tempfile
import unittest

from jobhunter.spend import SpendCapReached, SpendLedger, estimate_cost_usd

JAN = 1767225600.0   # 2026-01-01 00:00 UTC
FEB = 1769904000.0   # 2026-02-01 00:00 UTC


class SpendTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_known_model_cost(self):
        self.assertAlmostEqual(estimate_cost_usd("gpt-4o-mini", 1000, 1000), 0.00075)

    def test_unknown_model_uses_fallback(self):
        self.assertGreater(estimate_cost_usd("mystery-9", 1000, 0), 0)

    def test_record_and_month_total(self):
        ledger = SpendLedger(self.path, now=lambda: JAN)
        ledger.record("gpt-4o-mini", 1000, 1000)
        ledger.record("gpt-4o-mini", 1000, 1000)
        self.assertAlmostEqual(ledger.month_total(), 0.0015)

    def test_month_rollover(self):
        clock = {"t": JAN}
        ledger = SpendLedger(self.path, now=lambda: clock["t"])
        ledger.record("gpt-4o-mini", 1000, 0)
        clock["t"] = FEB
        self.assertEqual(ledger.month_total(), 0.0)

    def test_cap_blocks(self):
        ledger = SpendLedger(self.path, now=lambda: JAN)
        ledger.record("grok-2-latest", 100_000, 100_000)  # way past a tiny cap
        with self.assertRaises(SpendCapReached):
            ledger.check(0.01)


if __name__ == "__main__":
    unittest.main()
