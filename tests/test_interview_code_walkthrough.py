"""Fast no-dependency tests for the CFO technical interview walkthrough."""
import contextlib
import io
import unittest

from interview_code_walkthrough import change_amazon_fee, run
from thin_slice import parse_csv


class InterviewCodeWalkthroughTests(unittest.TestCase):
    def test_repeat_keeps_two_business_rows_and_two_audit_events(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = run("24.00", repeat=True)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(result["gl_status"], "PASS")
        self.assertEqual(result["fee_signals"][0]["difference_cents"], 600)

    def test_late_fee_correction_updates_not_duplicates(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = run("20.00", repeat=True)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["gl_variances"]["fee_actual_cents"], -400)
        self.assertEqual(result["fee_signals"][0]["difference_cents"], 200)
        self.assertEqual(result["gl_status"], "FAIL")
        self.assertFalse(result["settlement_issues"])

    def test_invalid_precision_rejected(self):
        with self.assertRaises(ValueError):
            change_amazon_fee("24.001")

    def test_corrected_row_retains_source_line(self):
        rows = parse_csv(change_amazon_fee("20.00"), "Amazon")
        self.assertEqual(rows[0]["source_row"], 2)
        self.assertEqual(rows[0]["settlement_net_cents"], 10000)


if __name__ == "__main__":
    unittest.main()
