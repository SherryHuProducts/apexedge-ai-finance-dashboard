import unittest

from channel_pl import build_pl, money


class ChannelPLTests(unittest.TestCase):
    def test_unmapped_website_is_excluded_and_flagged(self):
        result = build_pl()
        self.assertFalse(result["profit_complete"])
        self.assertEqual(result["blocked_mapping_cents"], 6000)
        self.assertEqual(result["totals"]["net_revenue_cents"], 40000)
        self.assertEqual(result["totals"]["contribution_profit_cents"], 10100)
        self.assertEqual(result["gl_status"], "NOT RECONCILED")

    def test_approved_master_data_yields_complete_demo_bridge(self):
        result = build_pl(approve_website=True)
        self.assertTrue(result["profit_complete"])
        self.assertEqual(result["totals"]["net_revenue_cents"], 45500)
        self.assertEqual(result["totals"]["cogs_cents"], 26000)
        self.assertEqual(result["totals"]["gross_profit_cents"], 15400)
        self.assertEqual(result["totals"]["contribution_profit_cents"], 10900)
        self.assertEqual(result["gl_status"], "DEMO PASS")
        self.assertEqual(result["unallocated_shared_cents"], 2000)

    def test_missing_cogs_never_becomes_zero(self):
        result = build_pl(approve_website=True, missing_cost=True)
        self.assertFalse(result["profit_complete"])
        self.assertEqual(result["blocked_cost_cents"], 20000)
        self.assertEqual(result["gl_status"], "NOT RECONCILED")
        cost_issue = next(i for i in result["exceptions"] if i["entity"] == "cost")
        self.assertEqual(cost_issue["source_value"], "cogs")
        excluded = next(r for r in result["details"] if r["order_id"] == "CT-1")
        self.assertIsNone(excluded["contribution_profit_cents"])

    def test_components_add_to_bridge(self):
        t = build_pl(approve_website=True)["totals"]
        self.assertEqual(t["net_revenue_cents"], t["revenue_cents"] - t["returns_cents"])
        self.assertEqual(t["gross_profit_cents"], t["net_revenue_cents"] - t["cogs_cents"] - t["freight_cents"] - t["tariff_cents"])
        self.assertEqual(t["contribution_profit_cents"], t["gross_profit_cents"] - t["platform_fee_cents"] - t["advertising_cents"] - t["rebate_cents"])

    def test_decimal_policy(self):
        self.assertEqual(money("12.30"), 1230)
        with self.assertRaises(ValueError):
            money("12.301")


if __name__ == "__main__":
    unittest.main()
