# Master Data Mapping & Validation — JD A technical evidence

This is a **standalone, executable synthetic mapping-control slice** shown in the Streamlit navigation, not a production customer/SKU master, nor a live integration with the separate Business Performance dataset.

## The business question

Walmart calls a product `WM-RED-001`, Costco calls it `CT-1001`, and the ERP calls it `SKU-RED`. The Website exports `RED-V2`, which has not yet been approved. How do we prevent erroneous cross-channel profit aggregation?

## What is implemented

- Separate `(system, entity, source_value)` business keys for `sku`, `customer`, and `account`; SQLite registry with a composite primary key.
- Canonical values selected by an explicit mapping decision; no fuzzy auto-match or generative AI deciding ledger mappings.
- Records with *any* missing required mapping are **BLOCKED**, including their revenue, which stays in a separate exception total rather than becoming zero.
- Approved records become available for cross-channel analysis; reviewer identity and old/new mapping changes are logged.
- Reapproval of an identical mapping does not create a second event.

## Demo outcome (fictional)

| Source | Source SKU | Canonical SKU | Status |
| --- | --- | --- | --- |
| Walmart | WM-RED-001 | SKU-RED | APPROVED |
| Costco | CT-1001 | SKU-RED | APPROVED |
| ERP | SKU-RED | SKU-RED | APPROVED |
| Website | RED-V2 | — | BLOCKED |

The four mock financial records total **$460**; **$60** from Website is blocked until a reviewer approves `RED-V2 → SKU-RED`. After approval, all four map. The example demonstrates **eligibility for analysis**, **not** financial close or margin calculation: cost, freight and settlement evidence have not been provided for this small dataset.

## Run

```bash
python master_data_mapping.py
python master_data_mapping.py --approve-website
python -m unittest discover -s tests -p 'test_master_data_mapping.py'
streamlit run app.py
```

In the sidebar choose **Master Data Mapping / 主数据映射** and toggle the reviewer approval checkbox.

## CFO explanation (45 seconds)

“Different retailers and internal systems identify the same product differently. I created a canonical mapping registry for SKUs, customers and GL accounts. Each mapping has an owning source, an approval label and audit history. If a required mapping is missing, that record is blocked from downstream profit aggregation instead of being guessed or counted as zero. In my demo, one Website SKU blocks sixty dollars until Finance reviews and approves the mapping. This prevents misleading channel-level margins when master data is inconsistent.”

## Limitations

- Approvals use a demo reviewer label; **authentication, authorization, separation of duties and human sign-off are not implemented**.
- This miniature mapping registry is not yet wired into the other dashboard's independent synthetic dataset; integration would require applying the mapping gate at the shared ingestion layer.
- No effective dates, historical entity mergers, hierarchy versions, currency policy, production data migration or ERP master-data writes.
