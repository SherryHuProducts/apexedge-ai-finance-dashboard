"""Transparent management-cost attribution for the synthetic SKU/channel case.

This is a traceable cost waterfall, not an arbitrary allocation of corporate
overhead and not full ABC/TDABC (which requires activity drivers not in the
current input schema).
"""
from __future__ import annotations

import pandas as pd


POLICY = [
    ("Product COGS", "product_cost", "SKU / units", "Direct trace or inventory cost roll-forward"),
    ("Inbound freight", "freight", "Shipment / weight", "Current data uses SKU-channel amounts; validate capitalized vs outbound shipping"),
    ("Tariffs", "tariff", "Import value / customs line", "Allocate by import declaration or shipment when actual invoices exist"),
    ("Platform fees", "platform_fee", "Channel / order", "Trace marketplace settlement fees to order/channel"),
    ("Marketing", "marketing_spend", "Campaign / SKU", "Use attributable campaigns; keep shared brand spend separate"),
    ("Returns", "returns", "Order / SKU", "Contra-revenue, not an additional cost deduction"),
]


def channel_unit_economics(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["channel", "gross_sales", "discount", "returns", "net_revenue",
                "product_cost", "freight", "tariff", "platform_fee", "marketing_spend"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    if frame.empty:
        return pd.DataFrame()
    grouped = frame.groupby("channel", as_index=False)[required[1:]].sum()
    grouped["gross_profit"] = (
        grouped["net_revenue"] - grouped["product_cost"]
        - grouped["freight"] - grouped["tariff"]
    )
    grouped["contribution_profit"] = (
        grouped["gross_profit"] - grouped["platform_fee"] - grouped["marketing_spend"]
    )
    grouped["gross_margin_pct"] = grouped["gross_profit"] / grouped["net_revenue"].replace(0, float("nan")) * 100
    grouped["contribution_margin_pct"] = grouped["contribution_profit"] / grouped["net_revenue"].replace(0, float("nan")) * 100
    return grouped


def validate_cost_bridge(frame: pd.DataFrame, tolerance: float = .01) -> None:
    if frame.empty:
        raise ValueError("No channel cost data")
    revenue_diff = (frame["gross_sales"] - frame["discount"] - frame["returns"] - frame["net_revenue"]).abs()
    if (revenue_diff > tolerance).any():
        raise ValueError("Gross-to-net revenue does not reconcile")
    if "gross_profit" in frame:
        diff = (frame["net_revenue"] - frame["product_cost"] - frame["freight"] - frame["tariff"] - frame["gross_profit"]).abs()
        if (diff > tolerance).any():
            raise ValueError("Gross profit does not reconcile")
    if "contribution_profit" in frame:
        diff = (frame["net_revenue"] - frame["product_cost"] - frame["freight"] - frame["tariff"] - frame["platform_fee"] - frame["marketing_spend"] - frame["contribution_profit"]).abs()
        if (diff > tolerance).any():
            raise ValueError("Contribution profit does not reconcile")
