# CFO audit checklist and implementation evidence

Last reviewed: 2026-10-31. This portfolio uses only synthetic source data.

| CFO question | Current evidence | Boundary / missing production capability |
|---|---|---|
| Trace an exception to source? | Live Pipeline Demo lists evidence ID, CSV filename, physical row number, order and amounts. Synthetic file row 2 links FEE-001 to AMZ-1008. | Main aggregated CFO charts do not provide universal transaction-level source drill-through. |
| Does reconciliation detect errors? | Settlement arithmetic, separate synthetic GL controls, fee-policy variance, stale revisions. Turn on late correction to make GL FAIL. | Real independent ERP GL controls are not supplied. |
| Does malformed data fail? | Broken duplicate-order file rejects the batch; settlement mismatch triggers an open issue; missing-cost fixture is unavailable in the main analysis. | Currency conversion, tax-inclusive/exclusive sales and SKU crosswalk require approved source policies. |
| Are duplicate runs safe? | Composite channel + record ID key, transactions, idempotent replay and revision event history. | Pipeline database is local demo state, not a durable approved production audit system. |
| How is AI measured? | Four hand-constructed synthetic cases test **deterministic rule detection**: 4 expected signals, 4 detected, precision 100%, recall 100%. | LLM accuracy **NOT MEASURED**. No false-citation or real-world benchmark claims. |
| Is the value quantified? | $6 observed synthetic fee-policy variance, not recovered profit. Scorecard lists proposed cycle-time and hours-saved targets. | No actual employer margin recovery or time savings measured. |
| Who owns cost definitions? | Synthetic direct/product cost policy and unallocated overhead are documented in architecture. | Production metric dictionary, ERP chart of accounts, entity scope and Finance signoff still needed. |
| Does the demo match wholesale/marketplace realities? | Amazon fee/settlement vs B2B customer invoice, provisional vs reconciled, late fee adjustment. | Customer payment terms, rebates, MAP, 3PL invoices and chargebacks need real source integration and approved definitions. |

## Reproduce the intentionally broken data

- Duplicate order: tests/fixtures/broken_amazon.csv, expected batch rejection and no new events.
- Settlement mismatch: tests/fixtures/settlement_mismatch.csv, expected settlement_mismatch issue, variance -$4.00, source row 2.
- Missing SKU cost: tests/fixtures/missing_cost.csv, expected analysis_ready=false, gross profit unavailable, no profit output.
- Late fee backfill: toggle in Streamlit, expected GL status FAIL with original control snapshot; fee exception changes from $6 to $2.

Run all automated tests: python -m pytest -q

Run the small deterministic detection evaluation: python evaluate_slice.py

The evaluation deliberately reports LLM accuracy as NOT MEASURED. Four synthetic hand-constructed cases are a smoke test of rules and categories, not a statistical estimate of generalization.

## A business-facing recommendation with ownership

**Observed in synthetic data:** one platform fee is $6 above the expected rule. The settlement cash calculation is internally consistent; the variance is against the **expected fee schedule**.

**What to do:** Finance obtains the fee agreement and platform adjustment detail, checks whether $6 is authorized, and assigns a case owner. If incorrect, initiate an approved recovery request. Only booked or realized recovery should be reported as financial benefit. Do not multiply $6 by arbitrary sales volume.

**Daily vs monthly:** daily operational data stays PROVISIONAL. A monthly reporting pack can become RECONCILED only after actual independent ledger/subledger controls, scope, cutoff and Finance signoff. The synthetic GL PASS label means only the supplied demonstration totals matched.

## What Sherry can claim

The current code, SQLite demo, test cases, CFO/Sales UI, deterministic rule evaluation and guarded AI evidence process are portfolio implementation. The optional LLM can be invoked if the operator supplies an authorized key and consents. Live merchant connectors, production scheduling, security certification, durable approvals, actual AI accuracy and monetary business outcomes have not been delivered.
