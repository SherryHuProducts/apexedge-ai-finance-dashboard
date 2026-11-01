# Business Performance Overview — operating results before AI analysis

This page is the **first page** in both CFO and Sales modes. It is a Salesforce-inspired operating view backed by the existing ApexEdge financial data pipeline.

## Features

- Month, quarter and year views; previous-period and prior-year comparatives. Missing comparison periods show `N/A`, never zero growth.
- Net Revenue, Gross Margin, Contribution Profit, Units, Return Rate.
- Revenue and contribution trends; filters for channel, category, SKU and **region only when provided**.
- Grouped drill-down by channel, category, SKU, region, city or customer ID where available.
- Transaction/source-detail table and CSV export. The built-in sample is **SKU × channel × month** grain, not individual orders.
- Operational totals and independent GL status are displayed separately. An overall GL status is **not** treated as reconciliation of a narrower SKU/period selection.
- 24-month simulated history for previous-year comparisons, with **synthetic** region/city labels. No synthetic geography is invented for uploaded files.

## Demo vs finance controls

The built-in demo contains synthetic consumer-electronics sales and costs, not JLA HOME financial statements. Inventory balances in other modules should not be summed over monthly snapshots. This page only sums period **flow** metrics. Uploaded data cannot claim customer, geographic, or GL coverage unless those are supplied and reconciled at a matching grain and period.

An operational 'gross margin' in this portfolio is calculated from the existing model: `(net_revenue - product_cost - freight - tariff) / net_revenue`. Corporate GAAP gross margin policies may differ; Finance must approve actual reporting definitions. Contribution profit further deducts platform fees and advertising.

## Verify

```bash
python -m unittest discover -s tests -p 'test_business_performance.py'
streamlit run app.py
```

Open **Business Performance / 经营业绩看板** in either role. Filter to a SKU or channel, change Month/Quarter/Year and Prior Year/Previous Period, then scroll to **Transaction Drill-down** to see the contributing source-level rows.

## Production gaps

- Real retailer customer, regional and source-order IDs; automated authoritative geographic/customer master data.
- Scoped GL-to-source reconciliation, financial-calendar alignment, source-to-GL account mapping, accounting close signoff.
- Validated monthly inventory snapshots and entity/consolidation controls.
- Historical data coverage checks and partial-period comparisons for multiple fiscal calendars.
