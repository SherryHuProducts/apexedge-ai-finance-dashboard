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

