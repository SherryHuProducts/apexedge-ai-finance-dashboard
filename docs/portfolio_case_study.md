# Finance Intelligence Hub: Consumer Electronics Profitability

**Portfolio owner:** Xinlei (Sherry) Hu  
**Case:** ApexEdge, a fictional consumer-electronics business  
**Status:** Synthetic-data prototype. No company financial data is represented.

## Business problem

A business can grow revenue while gross margin falls. Sales teams see orders, discounts and campaigns; accounting teams close the books; finance leadership lacks consistent SKU/channel contribution economics and a timely explanation of changing profitability.

The goal is one reusable finance model that answers two different questions:

- **CFO:** Which economic drivers explain margin changes, which risks deserve capital, and how reliable are the figures?
- **Sales:** Which SKU/channel decisions might create more contribution profit, and what sales volume is needed to justify an additional discount?

## My approach

1. Build synthetic 12-month data for 100 SKUs across Amazon, DTC, Retail and TikTok.
2. Validate multi-source inputs, financial identities and independent GL controls when provided.
3. Define consistent Revenue, Gross Profit and Contribution Profit.
4. Decompose month-over-month gross profit into volume, mix, realized net price, product cost, freight and tariff effects.
5. Create role-specific dashboards sharing the same metric contract.
6. Add rule-based anomalies, optional consent-based AI interpretation and human decision tracking.

## What this prototype demonstrates

| Capability | Implementation |
| --- | --- |
| Engineering | Python, pandas, Streamlit, Plotly, multi-file intake, regression tests |
| Finance | Gross-to-net, COGS bridge, contribution economics, inventory, optional GL controls |
| Commercial | SKU/channel analysis, discount break-even, return flags, action queue |
| AI governance | Aggregate-only prompt packet, explicit consent, no automatic action |
| Operating model | Accounting controls remain; analysts automate integration; Sales executes decisions |

## Evidence and limitations

- 30 automated tests passed in an isolated local validation on the earlier Phase 3/4 version. Re-run tests after each later update.
- Dashboard uses synthetic data; no claimed actual margin improvement.
- Price sensitivity is a scenario, not estimated elasticity.
- The cost-pool map is a management-cost prototype, not measured ABC/TDABC.
- Decision log is session-only; production requires persistence and access control.
- An online Streamlit deployment must be authorized before sharing the private repository or API secrets.

## Interview narrative

**Problem → Financial controls → Profit driver analysis → CFO/Sales decision support → Human-approved action → Measurement.**

The key value is not an AI-generated commentary. It is a reliable computation layer that lets Finance and Sales debate the same economics and decide what to test.
