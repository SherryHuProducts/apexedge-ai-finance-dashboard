"""Optional independent GL control-total reconciliation.

GL control file columns: date, gl_net_revenue, gl_cogs, gl_inventory_value.
Use monthly closing balances for inventory and monthly flows for revenue/COGS.
The result is explicitly UNVERIFIED when no independent GL file is provided.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from inventory_metrics import inventory_snapshot


FIELDS = ["date", "gl_net_revenue", "gl_cogs", "gl_inventory_value"]


def parse_gl_control_file(filename: str, content: bytes) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        raw = pd.read_csv(io.BytesIO(content))
    elif suffix == ".xlsx":
        raw = pd.read_excel(io.BytesIO(content))
    else:
        raise ValueError("GL control file must be CSV or XLSX")
    missing = set(FIELDS) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing GL control fields: {sorted(missing)}")
    gl = raw[FIELDS].copy()
    gl["date"] = pd.to_datetime(gl["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    if gl["date"].isna().any():
        raise ValueError("Invalid GL reporting date")
    if gl["date"].duplicated().any():
        raise ValueError("Exactly one GL control row per month is required")
    for field in FIELDS[1:]:
        gl[field] = pd.to_numeric(gl[field], errors="coerce")
    if gl[FIELDS[1:]].isna().any().any():
        raise ValueError("GL control totals must all be numeric")
    return gl


def reconcile_gl(analysis: pd.DataFrame, gl: pd.DataFrame, tolerance: float = 0.01) -> pd.DataFrame:
    if analysis.empty:
        raise ValueError("No analysis-ready data to reconcile")
    required = ["date", "net_revenue", "product_cost", "freight", "tariff", "sku", "channel", "inventory_value", "inventory_units"]
    missing = set(required) - set(analysis.columns)
    if missing:
        raise ValueError(f"Missing analytical fields: {sorted(missing)}")
    flow = analysis.groupby("date", as_index=False).agg(
        revenue=("net_revenue", "sum"),
        product_cost=("product_cost", "sum"),
        freight=("freight", "sum"),
        tariff=("tariff", "sum"),
    )
    flow["cogs"] = flow["product_cost"] + flow["freight"] + flow["tariff"]
    balances = inventory_snapshot(analysis).groupby("date", as_index=False)["inventory_value"].sum(min_count=1)
    observed = flow.merge(balances, on="date", how="left")
    result = gl.merge(observed, on="date", how="outer", indicator=True).sort_values("date")
    comparisons = [
        ("Revenue", "gl_net_revenue", "revenue"),
        ("COGS", "gl_cogs", "cogs"),
        ("Inventory", "gl_inventory_value", "inventory_value"),
    ]
    for name, ledger, analytical in comparisons:
        result[f"{name} variance"] = result[analytical] - result[ledger]
        result[f"{name} status"] = result.apply(
            lambda row: "PASS" if row["_merge"] == "both" and
                pd.notna(row[analytical]) and pd.notna(row[ledger]) and
                abs(row[analytical] - row[ledger]) <= tolerance else "FAIL", axis=1
        )
    return result.drop(columns="_merge")
