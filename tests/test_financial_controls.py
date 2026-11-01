import io

import pandas as pd
import pytest

from inventory_metrics import inventory_kpis, inventory_snapshot
from data_pipeline import ingest_finance_files


def test_inventory_snapshot_does_not_sum_duplicate_balance_rows():
    rows = pd.DataFrame([
        {"date": "2026-01-01", "sku": "A", "channel": "DTC", "inventory_value": 100, "inventory_units": 10,
         "product_cost": 40, "freight": 5, "tariff": 5},
        {"date": "2026-01-01", "sku": "A", "channel": "DTC", "inventory_value": 100, "inventory_units": 10,
         "product_cost": 0, "freight": 0, "tariff": 0},
    ])
    stock = inventory_snapshot(rows)
    assert len(stock) == 1
    assert stock.iloc[0]["inventory_value"] == 100
    kpis = inventory_kpis(rows)
    assert kpis["inventory_value"] == 100
    assert kpis["turnover"] == pytest.approx(6)
    assert kpis["inventory_days"] == pytest.approx(365 / 6)


def test_conflicting_snapshots_do_not_silently_sum():
    frame = pd.DataFrame([
        {"date": "2026-01-01", "sku": "A", "channel": "DTC", "inventory_value": 100, "inventory_units": 10},
        {"date": "2026-01-01", "sku": "A", "channel": "DTC", "inventory_value": 120, "inventory_units": 12},
    ])
    with pytest.raises(ValueError, match="Conflicting"):
        inventory_snapshot(frame)


FIELDS = (
    "date,sku,channel,gross_sales,discount,returns,net_revenue,"
    "product_cost,freight,tariff,platform_fee,marketing_spend,inventory_value,inventory_units\n"
)


def payload(net_revenue: int = 100, gross_sales: int = 100) -> bytes:
    return (FIELDS + f"2026-01-01,A,DTC,{gross_sales},0,0,{net_revenue},50,5,5,3,2,100,10\n").encode()


def test_valid_single_source_is_analysis_ready():
    result = ingest_finance_files((("sales_2026.csv", payload()),))
    assert result["stats"]["analysis_rows"] == 1
    assert result["canonical"].iloc[0]["contribution_profit"] == pytest.approx(35)


def test_overlap_between_source_files_blocks_profit():
    result = ingest_finance_files((
        ("sales_team_2026.csv", payload()),
        ("accounting_team_2026.csv", payload(90, 90)),
    ))
    assert result["stats"]["analysis_rows"] == 0
    assert result["issues"]["Issue / 问题"].str.contains("Overlapping source ownership").any()


def test_gross_to_net_mismatch_blocks_profit():
    result = ingest_finance_files((("sales_2026.csv", payload(90, 100)),))
    assert result["stats"]["analysis_rows"] == 0
    assert result["issues"]["Issue / 问题"].str.contains("Net revenue formula mismatch").any()
