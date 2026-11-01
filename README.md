# ApexEdge AI Finance Analyst Dashboard

A bilingual CFO decision-support case for a consumer-electronics company with growing revenue and declining gross margin.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
streamlit run app.py
```

On macOS, you can also double-click `run_dashboard.command`.

## Four workflow pages / 四个工作页面

1. **Executive Overview / 管理层总览** — revenue, gross margin, contribution profit, inventory days, P&L waterfall, channel profitability, CFO summary and data reconciliation.
2. **Margin & Inventory / 毛利与库存** — SKU profitability map, channel-category margin heatmap, landed-cost stack and inventory risk worklist.
3. **What-if Scenario / 情景模拟** — interactive price, elasticity, return-rate, platform-fee, marketing, freight and tariff assumptions with a live profit bridge and recommendation.
4. **Data Intake & Quality / 数据接入与质量** — multi-file lineage, automatic header and field detection, cleaning issues, field coverage, standardized preview and downloads.

The built-in case includes 12 months, 100 SKUs and four channels: Amazon, DTC, Retail and TikTok.

## Upload finance reports / 上传财务报表

The uploader accepts multiple `.csv`, `.tsv`, `.txt`, `.xlsx`, `.xls` and `.xlsm` files at once. Every Excel worksheet is inspected. The intake pipeline:

- detects CSV encoding, delimiters and header rows;
- recognizes Chinese and English finance field aliases;
- converts wide monthly reports into standardized long records;
- cleans dates, Excel date serials, currency symbols, commas and parenthesized negatives;
- removes blank, total, subtotal and exact duplicate rows;
- infers department and reporting period from filenames when supported;
- combines sources only on exact period, SKU and channel keys;
- preserves file, worksheet and department lineage;
- keeps missing prerequisites unavailable instead of silently treating them as zero.

Minimum required columns:

- `date` / `日期`
- `revenue` or `net_revenue` / `销售额`

Supported optional fields include `sku`, `product`, `category`, `channel`, `units`, `gross_sales`, `discount`, `returns`, `product_cost`, `freight`, `tariff`, `platform_fee`, `marketing_spend`, `inventory_units` and `inventory_value`. Common Chinese column names are recognized automatically. Missing finance fields receive documented fallback assumptions so the dashboard remains usable.

## Data controls / 数据控制

The Executive Overview includes reconciliation checks for:

- `Net Revenue = Gross Sales - Discounts - Returns`
- `Gross Profit = Net Revenue - Product Cost - Freight - Tariff`


## Phase 1 financial controls / 第一阶段财务控制

- **Inventory is a snapshot:** ending inventory is de-duplicated at reporting month × SKU × channel; it is not additive across repeated exports. Channel-level stock pools are assumed independent. If inventory is shared across channels, load a separate warehouse/SKU snapshot before relying on channel turnover.
- **Turnover basis:** annualized product cost + freight + tariffs divided by average monthly inventory in matching periods. This is a management-analysis estimate; companies must align the cost basis with their GL capitalization policy.
- **Source ownership:** when separate files supply the same metric at the same date/SKU/channel grain, that metric is blocked rather than silently double-counted. The analyst must resolve source ownership or adjust the data grain.
- **Gross-to-net validation:** net revenue must equal gross sales less discounts and returns within $0.01 for each analysis record; otherwise it is blocked.
- **Missing is not zero:** missing financial prerequisites block profitability analysis. Missing inventory balance yields unavailable inventory KPIs.
- **Important limitation:** internal arithmetic checks are not GL-to-subledger reconciliation. Production use requires ERP control totals, mapping ownership, period cutoffs, source approvals, role permissions and audit evidence.

Run automated tests with `python -m pip install pytest` and `python -m pytest -q`. GitHub Actions runs the same tests on pushes to main and pull requests.

The supplied dataset is synthetic, not a company operating result. The current 'AI' label describes the target product vision; recommendations on the existing pages are deterministic rules, not an LLM or autonomous AI agent.

### Independent GL reconciliation / 独立总账勾稽

The sidebar accepts an optional CSV/XLSX *GL Control Totals* report with exactly one row per reporting month and columns:
`date, gl_net_revenue, gl_cogs, gl_inventory_value`.

These are independent accounting control totals—not another copy of the sales detail. The Data Intake & Quality page compares GL and analytical Revenue/COGS/ending Inventory, shows each variance and marks PASS/FAIL. If no GL file is provided, the status stays **NOT SUPPLIED**, never PASS.

Before production use, confirm that freight/tariffs included in analytical COGS follow the same accounting policy and that inventory is valued and scoped consistently. Do not upload confidential employer records to a public demo.

## Phase 2: Profitability intelligence / 盈利分析升级

**Gross Profit Driver Bridge:** the CFO overview now compares the most recent two selected months. An exact midpoint decomposition separates Volume, SKU/channel Mix, realized Net Price, Product Cost, Freight and Tariff. The total reconciles to the change in gross-profit dollars, within $0.02. The realized net price already incorporates discounts and returns; no second deduction is made. New/discontinued SKUs are attributed to volume/mix rather than inventing historical prices.

**Cost attribution:** the Margin & Inventory page includes a channel-level gross/contribution margin table and a disclosed cost-pool policy. Product cost, inbound freight and tariffs are treated as product-level cost components for this synthetic case; platform and marketing fees are channel costs. Shared overhead is not arbitrarily allocated. Full ABC/TDABC needs actual cost-driver records (orders, shipments, tickets, activity times), not merely the current aggregated columns.

**Reporting caveats:** the driver bridge analyzes **gross profit dollars** and separately displays gross-margin percentages; it is not yet an exact percentage-point gross-margin bridge. Forecasting, causality, and historical elasticity estimation are out of scope for this phase.
