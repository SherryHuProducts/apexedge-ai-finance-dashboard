import unittest

from multi_channel_connectors import (
    COSTCO_EDI_LIKE, WALMART_RESPONSE, costco_adapter, run_demo, walmart_adapter,
)


class MultiChannelConnectorTests(unittest.TestCase):
    def test_standard_both_channels_and_gl(self):
        result = run_demo()
        self.assertEqual({r["channel"] for r in result["result"]["rows"]}, {"Walmart", "Costco"})
        self.assertEqual(result["result"]["gl_status"], "PASS")
        self.assertEqual(result["result"]["event_count"], 2)
        self.assertEqual(result["result"]["fee_signals"][0]["difference_cents"], 400)
        self.assertTrue(all(source["validation"] == "PASS" for source in result["sources"]))

    def test_duplicate_is_idempotent(self):
        result = run_demo("duplicate_upload")
        self.assertEqual(result["result"]["event_count"], 2)
        self.assertEqual(len(result["result"]["rows"]), 2)
        self.assertEqual(result["sources"][0]["unchanged"], 1)

    def test_backfill_changes_gl_without_duplicating(self):
        result = run_demo("late_fee_adjustment")
        self.assertEqual(result["result"]["event_count"], 3)
        self.assertEqual(len(result["result"]["rows"]), 2)
        self.assertEqual(result["result"]["gl_status"], "FAIL")
        self.assertEqual(result["result"]["gl_variances"]["fee_actual_cents"], -300)
        self.assertEqual(result["result"]["fee_signals"][0]["difference_cents"], 100)

    def test_missing_sku_is_blocked(self):
        result = run_demo("missing_sku")
        self.assertTrue(result["sources"][0]["validation"].startswith("FAIL"))
        self.assertEqual(result["sources"][0]["loaded"], 0)
        self.assertEqual(len(result["result"]["rows"]), 1)
        self.assertEqual(result["result"]["gl_status"], "FAIL")

    def test_settlement_mismatch_detected_even_when_fee_policy_flagged(self):
        result = run_demo("settlement_mismatch")
        self.assertEqual(len(result["result"]["settlement_issues"]), 1)
        self.assertEqual(result["result"]["settlement_issues"][0]["difference_cents"], 100)

    def test_adapters_reject_malformed_inputs(self):
        self.assertEqual(walmart_adapter(WALMART_RESPONSE)[0]["record_id"], "WM-801")
        self.assertEqual(costco_adapter(COSTCO_EDI_LIKE)[0]["record_id"], "CT-902")
        with self.assertRaises(ValueError):
            costco_adapter("850|INVALID")


if __name__ == "__main__":
    unittest.main()
