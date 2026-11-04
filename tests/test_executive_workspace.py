"""Executive reporting must never invent unavailable financial metrics."""
import pandas as pd

from executive_workspace import _total, _pct, _margin
from data_pipeline import ingest_finance_files


def test_missing_net_income_is_unavailable():
    frame=pd.DataFrame({"net_revenue":[100.0],"gross_profit":[30.0]})
    assert _total(frame,"net_income") is None
    assert _margin(frame)==30.0


def test_partial_costs_do_not_sum_into_false_profit():
    frame=pd.DataFrame({"net_revenue":[100.0,200.0],"gross_profit":[30.0,float("nan")]})
    assert _total(frame,"gross_profit") is None
    assert _margin(frame) is None


def test_zero_revenue_ratio_is_unavailable():
    assert _pct(5.0,0.0) is None


def test_choose_only_one_sheet_grain_for_reporting():
    sales=b"date,sku,channel,net_revenue\n2026-01-01,A,Web,100\n"
    cost=b"date,sku,channel,product_cost\n2026-01-01,A,Web,60\n"
    result=ingest_finance_files((("sales.csv",sales),("cost.csv",cost)),selected_sheets=("sales.csv::CSV",))
    assert result["stats"]["revenue_rows"]==1
    assert result["stats"]["tables"]==1
    assert result["canonical"]["product_cost"].isna().all()
