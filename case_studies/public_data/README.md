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
