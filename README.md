# ApexEdge AI Finance Analyst Dashboard

A bilingual CFO decision-support case for a consumer-electronics company with growing revenue and declining gross margin.

## Project deliverables / 项目交付内容

- [Architecture & Finance/Sales operating model](docs/architecture.md) — accounting responsibilities, canonical finance data, cost attribution and AI/human decision controls.
- [Portfolio case study](docs/portfolio_case_study.md) — business problem, solution, tradeoffs and measured/testable artifacts.
- [15-minute CFO & Sales presentation script](docs/presentation_script.md) — an interview-ready narrative with Q&A.
- [Deployment guide](DEPLOYMENT.md) — Streamlit Community Cloud instructions and production-readiness checklist.
- [Test evidence and limits](docs/test_evidence.md) — reproducible checks and honest scope.

**Demo vs production:** ApexEdge is a fictional business, the included transactions are synthetic, and this is a decision-support prototype. No live ERP/CRM connection, durable access control, durable approval database or autonomous business execution is claimed. An optional GL control file is required for independent accounting reconciliation; until supplied, the status is **NOT SUPPLIED**, not PASS. Any optional AI explanation requires the user's explicit consent.

## Interview vertical slice / 面试财务闭环演示

A runnable synthetic two-channel **Amazon + B2B → SQLite → controls → fee exception → opt-in AI explanation → human review** example is now available in both CFO and Sales navigation under **Live Pipeline Demo / 财务数据闭环**. It is a small, end-to-end case, not a claim of a live automated enterprise pipeline.

- [Interview walkthrough, controls, scorecard and Q&A](docs/thin_slice_interview.md)
- [Clean architecture diagram](docs/thin_slice_architecture.svg)
- CLI: `python thin_slice.py`
- Demo fact: a **$6 expected-vs-actual platform fee variance** is visible even when settlement arithmetic and the initial synthetic GL control match. Its cause is not established.
- Replaying identical source data adds no business rows. A late source adjustment is logged and causes the original GL control to fail until investigated.
- Operational monitoring is always **PROVISIONAL**. A synthetic monthly control match is not production Accounting signoff.
- The live API connectors, daily scheduler, durable approvals and measured monetary ROI are **not implemented**.

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

## Phase 3: CFO / Sales role-based views / 双角色视图

Use the sidebar **Audience** selector:

- **CFO Mode:** executive performance, exact gross-profit driver bridge, cost attribution and inventory, what-if scenario, data controls.
- **Sales Mode:** channel and SKU contribution economics, net revenue, returns and discount rates, SKU/channel review queue, and additional-discount break-even volume sensitivity.
- **Data Intake & Quality** remains accessible from either mode. Both views consume the same validated canonical data; switching the audience does not change financial definitions or underlying figures.

**Commercial promotion break-even:** the Sales view models an extra discount against current realized net selling price. It holds per-unit product/freight/tariff and marketing costs constant and lets percentage platform fees move with selling price. It computes the volume increase needed to preserve current contribution profit, **not** a demand forecast. It does not claim measured elasticity, advertising incrementality or causal uplift. When volume data is missing, the model is unavailable instead of inventing units.

**Action queue:** relative return-rate and contribution-margin signals are deterministic triage priorities, not AI-generated investment advice. No prices, promotions or purchase orders are automatically changed.

## Phase 4: Decision Intelligence / 决策智能

Both CFO and Sales audiences can open **Decision Intelligence**:

1. **Deterministic signals:** finance and commercial anomalies are calculated from the validated canonical dataset, with metric, baseline, observed value, difference, threshold and evidence. A signal is a review priority, **not proof of its cause**.
2. **Optional live LLM explanation:** configure `OPENAI_API_KEY` in your local environment and optionally `OPENAI_MODEL` (default: `gpt-6-luna`). The app previews the exact outbound evidence and requires an explicit consent checkbox and Generate click. It sends only rounded aggregate KPIs and a few signal records, never raw uploaded spreadsheets, SKU identifiers, person names or transaction rows. The Responses API request uses `store: false` and a fixed HTTPS endpoint. Without a key, the app works fully in deterministic mode. API usage may incur charges; do not connect confidential employer data without authorization.
3. **Human decision review:** creating a proposal never triggers a price, purchase-order, ERP or payment action. Allowed states: Proposed → Approved/Rejected → In progress → Completed/Rejected. Approval requires an owner; completion requires a measured result or documented outcome.
4. **Event export:** proposals and review events are kept in Streamlit **session state only** in this MVP. Export the audit log CSV before the session ends. This is not a durable, enterprise audit store or authorization system.

The app separates deterministic calculations, AI commentary and human approvals. Generated text must be reviewed and is not evidence of financial accuracy. `Decision Intelligence` does not perform automated execution.

### Validation

`tests/test_app_smoke.py` exercises the CFO landing page, Sales audience switch and Decision page through Streamlit's AppTest harness. The pure-function tests check accounting parity, signal evidence and decision-state transitions. CI workflow configuration exists, but a successful GitHub-hosted run should be confirmed in the repository Actions tab before claiming full end-to-end verification.
