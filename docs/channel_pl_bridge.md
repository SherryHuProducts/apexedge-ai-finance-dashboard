# JD B — Trustworthy Channel P&L (synthetic, executable)

This module combines the **same synthetic source orders and approved SKU/customer/account mapping registry** from the Master Data demo with **separate synthetic order-cost evidence** to produce an explainable profit bridge. It is not a live ERP integration or a certified financial statement.

## Accounting policy for this case

1. Gross sales less returns = **net revenue**. Example rebates are modeled as *channel deductions below gross profit*, not reductions to GAAP revenue; real treatment must follow contract and Controller policy.
2. Net revenue less **product COGS, freight, tariff** = **case gross profit**. Real GAAP classification depends on landed-cost accounting and policy approval.
3. Gross profit less **marketplace fees, advertising and wholesale rebates** = **contribution profit before shared costs**.
4. **Unallocated shared costs = $20**, shown explicitly, not silently prorated or claimed as operating income.
5. A source row missing an approved SKU/customer/account mapping or any required cost stays **blocked / unavailable**, and its amount is separately reported. Partial calculated-only totals are not presented as the full company P&L.

## End-to-end example

| Case state | Net revenue included | Contribution profit included | Reconciliation |
| --- | ---: | ---: | --- |
| Website SKU unmapped | $400 | $101 | NOT RECONCILED; $60 source gross sales blocked |
| Finance approves Website `RED-V2 → SKU-RED` | $455 | $109 | DEMO PASS versus pre-specified $455 net revenue / $260 COGS controls |
| Costco COGS removed after approval | Partial only | Unavailable for Costco | NOT RECONCILED; $200 source gross sales blocked from complete margin |

The fully approved synthetic bridge is:

```
Gross sales                       $460
Less: returns                     ($5)
Net revenue                       $455
Less: product COGS               ($260)
Less: freight                     ($28)
Less: tariffs                     ($13)
Case gross profit                 $154
Less: marketplace fees            ($21)
Less: advertising                 ($14)
Less: wholesale rebates           ($10)
Contribution profit               $109
Unallocated shared costs           $20 (not assigned)
```

Every cost record is keyed by `(source_system, order_id)`. The reconciliation control totals are defined **independently of the calculated total** in the demo, so missing or excluded source rows cause a visible failed comparison.

## Try it

```bash
python channel_pl.py
python channel_pl.py --approve-website
python channel_pl.py --approve-website --missing-cost
python -m unittest discover -s tests -p 'test_channel_pl.py'
streamlit run app.py
```

Open **Channel P&L Bridge / 渠道利润桥表**, toggle the approved Website mapping, then remove Costco cost evidence. Show the CFO exactly why the first number is incomplete, why approved mappings release the row, and why a missing cost requires a blocked rather than an artificially high margin.

## English interview explanation

“A dashboard can show a margin, but Finance needs to know whether that margin is complete. I built an executable channel P&L that joins source orders to approved master-data mappings and transaction-level costs. It distinguishes returns, landed costs, marketplace fees, advertising, rebates, and unallocated shared costs. When a Website SKU is unmapped, the related sales stay in an exception bucket. When Costco COGS is missing, I deliberately block its contribution profit instead of treating cost as zero. Only when all records are complete do I test the total against independently specified demo GL controls. The real next step is the company's approved cost allocation and true source-to-GL reconciliation.”

## Implementation gaps

- This is **synthetic four-order data**, not a real historical company P&L.
- Existing ERP invoice, COGS, 3PL, freight, advertising and settlement connectors are *not* wired to live systems.
- True landed cost, timing of sales/returns, allowance classification, customer incentives, FX, tax, shared-cost allocation and Controller signoff need policy decisions and production evidence.
- The P&L slice is linked to the **Master Data mapping logic** but is not yet the main 24-month Business Performance model; shared production orchestration remains an integration task.
