import unittest

from master_data_mapping import SOURCE_RECORDS, approve, create_db, map_records, run_demo


class MasterDataMappingTests(unittest.TestCase):
    def test_unmapped_website_is_blocked_and_amount_preserved(self):
        snapshot = run_demo()["after"]
        self.assertEqual(len(snapshot["ready"]), 3)
        self.assertEqual(len(snapshot["blocked"]), 1)
        self.assertEqual(snapshot["blocked_revenue_cents"], 6000)
        self.assertEqual(snapshot["approved_revenue_cents"] + snapshot["blocked_revenue_cents"],
                         snapshot["total_revenue_cents"])
        self.assertEqual(snapshot["issues"][0]["entity"], "sku")

    def test_human_approval_releases_record(self):
        snapshot = run_demo(resolve_website=True)
        self.assertEqual(snapshot["before"]["blocked_revenue_cents"], 6000)
        self.assertEqual(snapshot["after"]["blocked_revenue_cents"], 0)
        self.assertEqual(len(snapshot["after"]["ready"]), 4)
        self.assertEqual(snapshot["after"]["ready"][-1]["canonical_sku"], "SKU-RED")
        self.assertEqual(snapshot["after"]["events"][-1]["reviewer"], "Demo Finance Reviewer")

    def test_mapping_approval_is_idempotent(self):
        with create_db() as db:
            approve(db, "ERP", "sku", "SKU-RED", "SKU-RED", "Finance")
            approve(db, "ERP", "sku", "SKU-RED", "SKU-RED", "Finance")
            count = db.execute("SELECT COUNT(*) FROM mapping_events").fetchone()[0]
        self.assertEqual(count, 1)

    def test_unauthorized_blank_approval_is_rejected(self):
        with create_db() as db:
            with self.assertRaises(ValueError):
                approve(db, "Website", "sku", "RED-V2", "SKU-RED", "")

    def test_mapping_is_system_specific(self):
        with create_db() as db:
            approve(db, "Walmart", "sku", "X", "SKU-A", "Finance")
            sample = [{"system": "Costco", "order_id": "1", "sku": "X", "customer": "Y",
                       "account": "Z", "revenue_cents": 100}]
            snapshot = map_records(db, sample)
        self.assertEqual(snapshot["blocked_revenue_cents"], 100)
        self.assertEqual(len(snapshot["issues"]), 3)


if __name__ == "__main__":
    unittest.main()
