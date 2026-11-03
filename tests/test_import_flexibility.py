"""Regression checks for OLX file intake and safe partial reporting."""
import io

import pandas as pd

from data_pipeline import ingest_finance_files


def _xlsx_one_column(csv_text: str) -> bytes:
    output = io.BytesIO()
    pd.DataFrame({"raw": csv_text.strip().splitlines()}).to_excel(output, index=False, header=False)
    return output.getvalue()


def test_excel_single_column_delimited_export():
    payload = _xlsx_one_column(
        "date,sku,channel,net_revenue,currency\n2026-01-01,A,Web,100,GBP"
    )
    result = ingest_finance_files((("sales.xlsx", payload),))
    frame = result["canonical"]
    assert len(frame) == 1
    assert frame.iloc[0]["revenue_ready"]
    assert not frame.iloc[0]["analysis_ready"]
    assert frame.iloc[0]["net_revenue"] == 100
    assert frame.iloc[0]["currency"] == "GBP"


def test_sales_cost_settlement_merge_is_profit_ready():
    sales = "date,sku,channel,gross_sales,units\n2026-01-01,A,Web,100,2\n"
    cost = "date,sku,channel,product_cost,freight,tariff\n2026-01-01,A,Web,50,5,2\n"
    settlement = (
        "date,sku,channel,discount,returns,net_revenue,platform_fee,marketing_spend\n"
        "2026-01-01,A,Web,0,0,100,8,3\n"
    )
    result = ingest_finance_files((("sales.csv", sales.encode()), ("cost.csv", cost.encode()), ("settlement.csv", settlement.encode())))
    frame = result["canonical"]
    assert len(frame) == 1
    assert frame.iloc[0]["analysis_ready"]
    assert frame.iloc[0]["gross_profit"] == 43
    assert frame.iloc[0]["contribution_profit"] == 32


def test_duplicate_metric_ownership_blocks_revenue():
    one = b"date,sku,channel,net_revenue\n2026-01-01,A,Web,100\n"
    result = ingest_finance_files((("one.csv", one), ("two.csv", one)))
    frame = result["canonical"]
    assert len(frame) == 1
    assert not frame.iloc[0]["revenue_ready"]
    assert result["stats"]["revenue_rows"] == 0


def test_missing_cost_is_not_assumed_zero():
    result = ingest_finance_files((("sales.csv", b"date,sku,channel,net_revenue\n2026-01-01,A,Web,100\n"),))
    frame = result["canonical"]
    assert frame.iloc[0]["revenue_ready"]
    assert not frame.iloc[0]["analysis_ready"]
    assert pd.isna(frame.iloc[0]["contribution_profit"])
