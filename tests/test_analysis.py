import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analysis  # noqa: E402

ROWS = [{"month": m, "x": v} for m, v in [("2008-01", 100.0), ("2008-06", 90.0), ("2009-01", 80.0),
                                           ("2010-01", 95.0), ("2011-01", 101.0), ("2012-01", 99.0)]]


class AnalysisTests(unittest.TestCase):
    def test_peak_trough_recovery(self):
        r = analysis.peak_trough(ROWS, "x")
        self.assertEqual((r["peak_month"], r["trough_month"], r["recovered_month"]), ("2008-01", "2009-01", "2011-01"))
        self.assertEqual(r["drop_pct"], -20.0)
        self.assertEqual(r["months_to_recover"], 24)
        self.assertEqual(r["end_vs_peak_pct"], -1.0)

    def test_never_recovered(self):
        rows = [{"month": m, "x": v} for m, v in [("2008-01", 100.0), ("2009-01", 70.0), ("2012-01", 90.0)]]
        self.assertIsNone(analysis.peak_trough(rows, "x")["recovered_month"])

    def test_no_decline(self):
        rows = [{"month": m, "x": v} for m, v in [("2008-01", 90.0), ("2009-12", 100.0), ("2012-01", 120.0)]]
        r = analysis.peak_trough(rows, "x")
        self.assertTrue(r["no_decline"])
        self.assertEqual(r["drop_pct"], 0.0)

    def test_months_between(self):
        self.assertEqual(analysis.months_between("2010-02", "2014-05"), 51)

    def test_index_series(self):
        self.assertEqual(analysis.index_series(ROWS, "x", "2008-01")[2], 80.0)

    def test_real_data_headline(self):
        rows = analysis.load(os.path.join(analysis.HERE, "data", "us-employment.csv"))
        out = analysis.build(rows)
        self.assertEqual(len(rows), 120)
        self.assertEqual(out["total"]["peak_month"], "2008-01")
        self.assertEqual(out["total"]["trough_month"], "2010-02")
        self.assertEqual(out["total"]["recovered_month"], "2014-05")
        self.assertEqual(len(out["sectors"]), 11)


if __name__ == "__main__":
    unittest.main()
