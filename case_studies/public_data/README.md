# Real public sales data / 公开真实销售数据

- **Source:** UCI Machine Learning Repository, *Online Retail* (Daqing Chen), DOI: https://doi.org/10.24432/C5BW33
- **Subset:** First 500 source rows mirrored at [rkharwar-nv/dataset_analysis](https://github.com/rkharwar-nv/dataset_analysis/blob/main/samples/uci-online-retail-sample.csv); 491 rows with positive quantity and unit price retained.
- **License:** Source dataset CC BY 4.0. Attribution preserved here.
- **History:** December 1, 2010 only; historical, not OLX, JLA HOME, or current-year financial results.
- **Currency:** Original prices in GBP. No FX conversion.
- **Transformation:** `InvoiceDate → date`, `StockCode → sku`, `Description → product`, `Quantity → units`, `UnitPrice → list_price`, `Country → region`; `net_revenue = Quantity × UnitPrice` for retained positive sales only. `channel = UK Online Retail` is a descriptive source label, **not a source marketplace channel**. `customer_id`, `invoice_no`, `currency` retained for lineage.
- **Exclusions:** Zero/negative quantities and nonpositive prices. Returns/cancellations were excluded rather than inventing their accounting treatment.
- **Important limitations:** Source includes **no COGS, freight, tariff, marketplace fees, advertising or independent GL/settlement records**. Do not interpret calculated sales as margin/profit or a reconciled P&L. Current OLX primary pipeline requires those cost fields and will intentionally show missing-data errors and zero analysis-ready rows; this file is a valid **data-intake/control smoke test**, not a full report demo. Only one calendar day exists, so MoM/YoY comparisons are impossible.
- **Privacy:** Original UCI pseudonymous CustomerID only; do not mix with real employer data.

Use this sample in **ERP Integration / ERP 集成 → Source reports → Validate & Load**.

## 12-month paired upload pack / 12个月联动测试包

Upload **all three files together** (separate sources, identical month + SKU + channel keys):

1. [OLX_UCI_12month_REAL_sales.csv](OLX_UCI_12month_REAL_sales.csv) — **REAL historical sales** from UCI Online Retail; positive UK invoices, Dec 2010–Nov 2011, 20 repeat SKUs, monthly SKU aggregates. `gross_sales`, `units`, SKU and product come from the source.
2. [OLX_UCI_12month_SIMULATED_costs.csv](OLX_UCI_12month_SIMULATED_costs.csv) — **FICTIONAL cost assumptions**: product cost = 61% of gross invoice sales, freight = 4.5%, tariff = 1.5%, rounded per SKU-month. None are actual UCI costs.
3. [OLX_UCI_12month_SIMULATED_settlements.csv](OLX_UCI_12month_SIMULATED_settlements.csv) — **FICTIONAL settlement assumptions**: discount = 0, returns = 0, net_revenue = gross_sales, platform_fee = 7.5%, marketing_spend = 3.5%, and illustrative settlement_cash = net_revenue – platform_fee. Neither these fees nor this cash amount appear in the original source.

**Source subset:** [caendeith/customer-churn-prediction](https://github.com/caendeith/customer-churn-prediction/blob/main/data/sample/online_retail_sample.csv), a UCI Online Retail sample of 55,177 rows across the original date range. Filtered to UK, invoices without a cancellation prefix, positive quantities and prices, Dec 2010–Nov 2011, and 20 product SKUs appearing in at least 11 months. **1,592 original positive source rows** consolidated into **240 month × SKU records**. Positive invoice sales total **GBP 38,254.65**. The sample is selected from a customer-subset, so it does not represent the retailer's total sales. Original transaction IDs are not present in the aggregates; use the upstream sample for transaction-level audit.

**Data model note:** The three files do not duplicate metric ownership: real sales supplies `gross_sales` and `units`; simulated costs supply COGS/freight/tariff; simulated settlements supply net revenue, discounts, returns, platform fee and marketing. Join at `date + sku + channel`. The `settlement_cash` column is **not a supported canonical field** and is retained for manual reference only. The main dashboard has **no independent GL file**, so GL reconciliation must remain **NOT SUPPLIED**. This pack demonstrates conditional finance arithmetic and reporting UI, not real reconciliation or profitability.

**Currency caveat:** All values are in **GBP**. The present Streamlit dashboard's `money()` formatter displays a **$ sign regardless of currency**; while testing with these files, interpret every displayed dollar-denominated value as **GBP**. This is a **known reporting bug** to fix before showing external users. There is no FX conversion.

**Expected test:** 3 input files; 240 analysis-ready monthly SKU records (subject to any later pipeline changes); 12 reporting months; MoM trends visible; gross-to-net arithmetic matches; GL status **NOT SUPPLIED**. All shown margin or contribution economics are **synthetic scenario outputs**, not historical financial facts.

Do not mix this pack with the one-day sample above in one upload: they overlap in December 2010.

