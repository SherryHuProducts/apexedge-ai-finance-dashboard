# Multi-Channel Data Connector Demo — Walmart + Costco (synthetic)

## What it proves

Two **different input formats** can feed **one** controlled financial data pipeline without claiming production integrations:

1. Simulated Walmart REST-style JSON → `walmart_adapter()`.
2. Simplified Costco **EDI-like** `850|...` sample → `costco_adapter()` (this is **not a standards-compliant X12 parser**).
3. Both → canonical `FIELDS` CSV → existing `thin_slice.ingest()` validation and SQLite schema.
4. Existing `thin_slice.evaluate()` checks settlement arithmetic, fee/allowance policy, and independent **fictional** GL control totals.
5. Structured `evidence_packet()` is **AI-ready**, but the demo does **not** call an LLM or verify causes.

The Costco sample uses the common finance columns `fee_actual` and `fee_expected` to represent an agreed retailer **allowance**, not a Walmart marketplace commission. In a production schema, these must be distinct cost/deduction types (with contract evidence), not aggregated as interchangeable fee categories.

## Running

From repository root:

```bash
python multi_channel_connectors.py --scenario standard
python multi_channel_connectors.py --scenario duplicate_upload
python multi_channel_connectors.py --scenario late_fee_adjustment
python multi_channel_connectors.py --scenario missing_sku
python multi_channel_connectors.py --scenario settlement_mismatch
python -m unittest discover -s tests -p 'test_multi_channel_connectors.py'
streamlit run app.py
```

In the app sidebar, select **Multi-Channel Connectors / 多渠道连接器** in CFO or Sales Mode. Choose a scenario and click **Run connector pipeline**. The page displays source last run, record counts, validation status, GL status, evidence, original example payloads, and database audit events.

## Sample financial interpretation

- Walmart synthetic sales **$100**, expected commission **$12**, charged commission **$16**, payout **$84**. Settlement math ties, but fee variance is **+$4**.
- Costco synthetic invoice **$200**, agreed allowance **$5**, receivable **$195**. The example does **not** claim payment has been collected.
- Synthetic controls: source sales **$300**, deductions **$21**, expected cash/receivable **$279**. These figures are fabricated specifically to exercise the controls.
- A revised Walmart commission of **$13** and payout **$87** changes the policy variance to **+$1** and produces a **−$3** difference relative to the *unchanged* GL fee control. Auditable `BACKFILL_UPDATE` event; two business rows remain two.
- Re-importing the same Walmart payload does not create a third source row or audit event.
- Missing SKU blocks Walmart input; settlement mismatch produces a source-row exception.

## Truthfulness, security and next steps

**Built and tested:** adapters for two *synthetic* transports, exact-cents validation, SQLite loading, repeat-safe upsert, revisions, audit log, GL demo controls, UI, tests.

**Not built:** Walmart OAuth/API access; a certified Costco EDI provider or true ANSI X12 parser; scheduling/retry/backfill orchestration; accounts receivable aging; warehouse/landed cost allocation; real GL/ERP tie-out; secrets manager; AI model inference or human-labeled LLM evaluation. No retailer credentials or proprietary data are required or stored.

**Interview answer:** “I built interchangeable source adapters with mocked payloads. The financial schema, idempotent database load, and controls are executable. Connecting live Walmart APIs would require authorized seller credentials; Costco EDI would depend on the supplier's approved EDI provider and message specifications. I would work with IT on permissions, polling, replay, and data retention before deploying.”
