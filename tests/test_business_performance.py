import unittest

import pandas as pd

from business_performance import (
    aggregate_dimension, financial_period, kpis, period_rows, previous_period, source_gl_bridge,
)


class BusinessPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([
            {"date": "2025-10-01", "channel": "Retail", "net_revenue": 80,
             "gross_profit": 20, "contribution_profit": 15, "gross_sales": 90,
             "returns": 10, "units": 2, "product_cost": 60},
            {"date": "2026-09-01", "channel": "Retail", "net_revenue": 90,
             "gross_profit": 25, "contribution_profit": 17, "gross_sales": 100,
             "returns": 10, "units": 3, "product_cost": 65},
            {"date": "2026-10-01", "channel": "Retail", "net_revenue": 120,
             "gross_profit": 40, "contribution_profit": 30, "gross_sales": 135,
             "returns": 15, "units": 4, "product_cost": 80},
        ])

    def test_month_previous_month(self):
        start, end = financial_period(pd.Timestamp("2026-10-01"), "Month")
        old_start, old_end = previous_period(start, end, "Previous Period")
        self.assertEqual(str(old_start.date()), "2026-09-01")
        self.assertEqual(kpis(period_rows(self.data, old_start, old_end))["net_revenue"], 90)

    def test_prior_year(self):
        start, end = financial_period(pd.Timestamp("2026-10-01"), "Month")
        old_start, old_end = previous_period(start, end, "Prior Year")
        self.assertEqual(kpis(period_rows(self.data, old_start, old_end))["net_revenue"], 80)

    def test_quarter_scope(self):
        start, end = financial_period(pd.Timestamp("2026-10-01"), "Quarter")
        self.assertEqual(str(start.date()), "2026-10-01")
        self.assertEqual(str(end.date()), "2026-12-01")

    def test_margin_and_return_rate(self):
        current = period_rows(self.data, pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-01"))
        summary = kpis(current)
        self.assertAlmostEqual(summary["gross_margin"], 40 / 120)
        self.assertAlmostEqual(summary["return_rate"], 15 / 135)

    def test_missing_dimension_not_fabricated(self):
        self.assertTrue(aggregate_dimension(self.data, "region").empty)

    def test_gl_pass_not_inherited_for_filtered_subset(self):
        scope = period_rows(self.data, pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-01"))
        result = source_gl_bridge(scope, "PASS", pd.DataFrame({"status": ["PASS"]}))
        self.assertFalse(result["is_reconciled"])

    def test_missing_profit_not_replaced_with_zero(self):
        missing = self.data.copy()
        missing.loc[0, "gross_profit"] = None
        self.assertIsNone(kpis(missing)["gross_margin"])


if __name__ == "__main__":
    unittest.main()
