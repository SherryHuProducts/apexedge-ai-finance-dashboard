"""Period-consistent finance metrics for Business Performance Overview.

Never impute missing financial fields or invent geography for uploaded records.
"""
from __future__ import annotations

import pandas as pd

FLOW_METRICS = ("net_revenue", "gross_sales", "returns", "gross_profit", "contribution_profit", "units")
REQUIRED = ("net_revenue", "gross_profit", "contribution_profit", "date")


def financial_period(end: pd.Timestamp, kind: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    end = pd.Timestamp(end).to_period("M").to_timestamp()
    if kind == "Month":
        return end, end
    if kind == "Quarter":
        quarter = (end.month - 1) // 3
        return pd.Timestamp(end.year, quarter * 3 + 1, 1), pd.Timestamp(end.year, quarter * 3 + 3, 1)
    if kind == "Year":
        return pd.Timestamp(end.year, 1, 1), pd.Timestamp(end.year, 12, 1)
    raise ValueError(f"Unknown period: {kind}")


def previous_period(start: pd.Timestamp, end: pd.Timestamp, comparison: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    if comparison == "Previous Period":
        return start - pd.DateOffset(months=months), end - pd.DateOffset(months=months)
    if comparison == "Prior Year":
        return start - pd.DateOffset(years=1), end - pd.DateOffset(years=1)
    raise ValueError(f"Unknown comparison: {comparison}")


def period_rows(data: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    dates = pd.to_datetime(data["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    return data.loc[dates.between(start, end)].copy()


def total(data: pd.DataFrame, field: str) -> float | None:
    if data.empty or field not in data or data[field].isna().any():
        return None
    return float(pd.to_numeric(data[field], errors="coerce").sum())


def ratio(data: pd.DataFrame, numerator: str, denominator: str) -> float | None:
    n, d = total(data, numerator), total(data, denominator)
    return None if n is None or d is None or d == 0 else n / d


def kpis(data: pd.DataFrame) -> dict[str, float | None]:
    return {
        "net_revenue": total(data, "net_revenue"),
        "gross_margin": ratio(data, "gross_profit", "net_revenue"),
        "contribution_profit": total(data, "contribution_profit"),
        "units": total(data, "units"),
        "return_rate": ratio(data, "returns", "gross_sales"),
    }


def aggregate_dimension(data: pd.DataFrame, dimension: str) -> pd.DataFrame:
    if dimension not in data or data[dimension].isna().all():
        return pd.DataFrame()
    usable = data.dropna(subset=[dimension]).copy()
    if usable.empty:
        return pd.DataFrame()
    cols = [name for name in FLOW_METRICS if name in usable]
    grouped = usable.groupby(dimension, dropna=False)[cols].sum(min_count=1).reset_index()
    if "gross_profit" in grouped and "net_revenue" in grouped:
        denom = grouped["net_revenue"].where(grouped["net_revenue"] != 0)
        grouped["gross_margin_pct"] = grouped["gross_profit"] / denom * 100
    return grouped.sort_values("net_revenue", ascending=False)


def source_gl_bridge(data: pd.DataFrame, gl_status: str, gl_recon: pd.DataFrame | None) -> dict:
    """Never mislabel operational figures as reconciled GL values."""
    return {
        "source_revenue": total(data, "net_revenue"),
        "source_cogs": total(data, "product_cost"),
        "gl_status": gl_status,
        "gl_recon": gl_recon,
        # The app's GL test covers the broader data extract, not this dashboard's
        # selected channel/SKU/time slice. Scope-specific PASS must be recomputed.
        "is_reconciled": False,
    }
