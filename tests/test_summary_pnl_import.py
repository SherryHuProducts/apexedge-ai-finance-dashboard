"""Approved P&L summary ingestion and consistency controls."""
from data_pipeline import ingest_finance_files


def _load(csv: bytes):
    return ingest_finance_files((("monthly_pnl.csv",csv),))


def test_pnl_summary_can_show_net_profit_without_detailed_costs():
    result=_load(b"date,net_revenue,gross_profit,contribution_profit,net_income\n2026-01-01,100,45,20,10\n")
    row=result["canonical"].iloc[0]
    assert row["revenue_ready"]
    assert row["analysis_ready"]
    assert row["net_income"]==10
    assert row["gross_profit"]==45


def test_summary_profit_mismatch_is_blocked():
    result=_load(b"date,net_revenue,product_cost,freight,tariff,gross_profit,platform_fee,marketing_spend\n2026-01-01,100,50,5,2,60,8,3\n")
    row=result["canonical"].iloc[0]
    assert not row["analysis_ready"]
    assert row["revenue_ready"]
    assert "Gross profit summary disagrees" in " ".join(result["issues"]["Issue / 问题"].astype(str))


def test_only_selected_summary_file_is_ingested():
    a=b"date,net_revenue\n2026-01-01,100\n"
    b=b"date,net_revenue\n2026-01-01,100\n"
    result=ingest_finance_files((("summary.csv",a),("detail.csv",b)),selected_sheets=("summary.csv::CSV",))
    assert result["stats"]["revenue_rows"]==1
    assert result["stats"]["tables"]==1
