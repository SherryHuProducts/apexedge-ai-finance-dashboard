"""Uploaded bilingual CFO workbook fields must map without copied values."""
from data_pipeline import resolve_finance_label, ingest_finance_files


def test_bilingual_headers_are_resolved():
    assert resolve_finance_label("月份\nMonth") == "month"
    assert resolve_finance_label("净收入\nNet Revenue") == "net_revenue"
    assert resolve_finance_label("毛利\nGross Profit") == "gross_profit"
    assert resolve_finance_label("净利润\nNet Income") == "net_income"
    assert resolve_finance_label("平台佣金及支付\nMarketplace & Payment Fees") == "platform_fee"
    assert resolve_finance_label("头程运费\nInbound Freight") == "freight"


def test_monthly_summary_direct_metrics():
    text = (
        '"月份\nMonth","净收入\nNet Revenue","毛利\nGross Profit","净利润\nNet Income"\n'
        '2026-10-01,59542,21026,-2666\n'
    ).encode()
    result = ingest_finance_files((("summary.csv", text),))
    row = result["canonical"].iloc[0]
    assert row["revenue_ready"]
    assert row["net_revenue"] == 59542
    assert row["gross_profit"] == 21026
    assert row["net_income"] == -2666
