"""Period-consistent inventory KPIs.

Inventory is a point-in-time balance, not a transaction amount. The canonical
grain is month x SKU x channel (separate channel stock pools are assumed).
Do not sum repeated snapshots within that grain.
"""
from __future__ import annotations

import pandas as pd


SNAPSHOT_KEYS = ["date", "sku", "channel"]


def inventory_snapshot(frame: pd.DataFrame) -> pd.DataFrame:
    required = SNAPSHOT_KEYS + ["inventory_value", "inventory_units"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing inventory fields: {sorted(missing)}")
    if frame.empty:
        return frame[required].copy()
    stock = frame[required].copy()
    # Conflicting stock observations require a separate reconciliation decision.
    for field in ("inventory_value", "inventory_units"):
        counts = stock.groupby(SNAPSHOT_KEYS, dropna=False)[field].nunique(dropna=True)
        if (counts > 1).any():
            raise ValueError(f"Conflicting {field} snapshots for the same month/SKU/channel")
    return stock.groupby(SNAPSHOT_KEYS, dropna=False, as_index=False).agg(
        inventory_value=("inventory_value", "max"),
        inventory_units=("inventory_units", "max"),
    )


def inventory_kpis(frame: pd.DataFrame) -> dict[str, float | None]:
    """Return latest balance, annualized turns and days on hand.

    Only months with both inventory snapshots and matching COGS are used for
    turnover. COGS components are product_cost + freight + tariff in this demo;
    production mappings must follow the company's inventory capitalization policy.
    """
    snapshots = inventory_snapshot(frame)
    if snapshots.empty:
        return {"inventory_value": None, "turnover": None, "inventory_days": None}
    monthly_stock = snapshots.groupby("date")["inventory_value"].sum(min_count=1)
    latest_value = monthly_stock.sort_index().iloc[-1]
    month_cogs = frame.groupby("date")[["product_cost", "freight", "tariff"]].sum(min_count=1).sum(axis=1, min_count=3)
    matched = pd.concat([monthly_stock.rename("stock"), month_cogs.rename("cogs")], axis=1).dropna()
    matched = matched[matched["stock"] > 0]
    if matched.empty:
        return {"inventory_value": float(latest_value), "turnover": None, "inventory_days": None}
    avg_stock = matched["stock"].mean()
    annual_cogs = matched["cogs"].sum() * 12 / len(matched)
    turns = annual_cogs / avg_stock if avg_stock > 0 else None
    days = 365 / turns if turns is not None and turns > 0 else None
    return {
        "inventory_value": float(latest_value),
        "turnover": float(turns) if turns is not None else None,
        "inventory_days": float(days) if days is not None else None,
    }
