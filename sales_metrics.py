"""Shared, deterministic commercial metrics used by the Sales view.

No LLM-derived numbers. The same net revenue / contribution profit definitions
as CFO mode are used at SKU-channel grain.
"""
from __future__ import annotations

import pandas as pd


NUMERIC = [
    "gross_sales", "discount", "returns", "net_revenue", "product_cost",
    "freight", "tariff", "platform_fee", "marketing_spend", "gross_profit",
    "contribution_profit",
]


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.where(denominator != 0)


def commercial_summary(frame: pd.DataFrame) -> dict[str, float | None]:
    if frame.empty:
        raise ValueError("No commercial data")
    required = set(NUMERIC) | {"channel", "sku"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Missing commercial fields: {sorted(missing)}")
    totals = frame[NUMERIC].sum()
    gross_after_discount = totals["gross_sales"] - totals["discount"]
    units = float(frame["units"].sum()) if "units" in frame and frame["units"].notna().all() else None
    net_revenue = float(totals["net_revenue"])
    contribution = float(totals["contribution_profit"])
    return {
        "net_revenue": net_revenue,
        "units": units,
        "return_rate": float(totals["returns"] / gross_after_discount * 100) if gross_after_discount else None,
        "discount_rate": float(totals["discount"] / totals["gross_sales"] * 100) if totals["gross_sales"] else None,
        "contribution_profit": contribution,
        "contribution_margin": contribution / net_revenue * 100 if net_revenue else None,
        "average_selling_price": net_revenue / units if units else None,
    }


def commercial_segments(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    if not set(keys).issubset(frame.columns):
        raise ValueError(f"Missing dimensions: {set(keys) - set(frame.columns)}")
    measures = [c for c in NUMERIC if c in frame]
    if "units" in frame and frame["units"].notna().all():
        measures.append("units")
    grouped = frame.groupby(keys, dropna=False, as_index=False)[measures].sum()
    gross_after_discount = grouped["gross_sales"] - grouped["discount"]
    grouped["return_rate"] = _safe_ratio(grouped["returns"], gross_after_discount) * 100
    grouped["discount_rate"] = _safe_ratio(grouped["discount"], grouped["gross_sales"]) * 100
    grouped["gross_margin"] = _safe_ratio(grouped["gross_profit"], grouped["net_revenue"]) * 100
    grouped["contribution_margin"] = _safe_ratio(grouped["contribution_profit"], grouped["net_revenue"]) * 100
    if "units" in grouped:
        grouped["asp"] = _safe_ratio(grouped["net_revenue"], grouped["units"])
    return grouped


def commercial_worklist(frame: pd.DataFrame, minimum_revenue: float = 1) -> pd.DataFrame:
    grouped = commercial_segments(frame, ["sku", "channel"])
    if grouped.empty:
        return grouped
    grouped = grouped[grouped["net_revenue"] >= minimum_revenue].copy()
    if grouped.empty:
        return grouped
    # Relative signals are triage only, not evidence of incremental causal ROI.
    return_threshold = grouped["return_rate"].median()
    low_margin_threshold = grouped["contribution_margin"].median()
    grouped["priority_score"] = (
        grouped["return_rate"].fillna(0).clip(lower=0) * 0.4
        + (low_margin_threshold - grouped["contribution_margin"]).clip(lower=0).fillna(0) * 0.6
    )
    def recommendation(row: pd.Series) -> str:
        if pd.notna(row["return_rate"]) and row["return_rate"] > return_threshold:
            return "Investigate returns / 调查退货原因"
        if pd.notna(row["contribution_margin"]) and row["contribution_margin"] < low_margin_threshold:
            return "Review discount and channel cost / 复核折扣及渠道成本"
        return "Monitor / 持续监控"
    grouped["recommended_review"] = grouped.apply(recommendation, axis=1)
    return grouped.sort_values(["priority_score", "net_revenue"], ascending=[False, False])
