"""Exact, auditable month-over-month gross profit driver bridge.

Uses midpoint decomposition at SKU x channel grain. Discounts and returns are
reflected in realized net price, not double-counted as separate cost drivers.
New/discontinued combinations inherit their observed price/cost in the missing
period, so the entry/exit effect is attributed to volume/mix.
"""
from __future__ import annotations

import pandas as pd


KEYS = ["sku", "channel"]
COSTS = ["product_cost", "freight", "tariff"]
BRIDGE_DRIVERS = ["Volume", "Mix", "Net price", "Product cost", "Freight", "Tariff"]


def margin_driver_bridge(frame: pd.DataFrame) -> dict:
    required = set(KEYS + ["date", "units", "net_revenue", "gross_profit"] + COSTS)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing bridge fields: {sorted(missing)}")
    periods = sorted(pd.to_datetime(frame["date"]).dropna().unique())
    if len(periods) < 2:
        raise ValueError("At least two reporting periods are required")
    first, last = periods[-2:]
    rows = []
    for date in (first, last):
        portion = frame.loc[pd.to_datetime(frame["date"]) == date]
        grouped = portion.groupby(KEYS, as_index=False)[["units", "net_revenue", "gross_profit"] + COSTS].sum()
        grouped = grouped.set_index(KEYS)
        if (grouped["units"] <= 0).any():
            raise ValueError("Bridge requires positive unit counts for every populated SKU/channel")
        rows.append(grouped)
    prior, current = rows
    index = prior.index.union(current.index)
    prior, current = prior.reindex(index), current.reindex(index)
    q0, q1 = prior["units"].fillna(0), current["units"].fillna(0)
    Q0, Q1 = q0.sum(), q1.sum()
    if Q0 <= 0 or Q1 <= 0:
        raise ValueError("Both periods must have positive sales units")

    prices = []
    costs = {k: [] for k in COSTS}
    for table in (prior, current):
        units = table["units"]
        prices.append(table["net_revenue"] / units)
        for field in COSTS:
            costs[field].append(table[field] / units)
    p0, p1 = prices
    p0, p1 = p0.fillna(p1), p1.fillna(p0)
    c0, c1 = {}, {}
    for field in COSTS:
        a, b = costs[field]
        c0[field], c1[field] = a.fillna(b), b.fillna(a)

    m0 = p0 - sum(c0.values())
    m1 = p1 - sum(c1.values())
    avg_margin = (m0 + m1) / 2
    avg_quantity = (Q0 + Q1) / 2
    s0, s1 = q0 / Q0, q1 / Q1
    avg_share = (s0 + s1) / 2
    avg_q = (q0 + q1) / 2

    # Identity: q1-q0 = (Q1-Q0) * avg_share + avg_quantity * (s1-s0)
    effects = {
        "Volume": float((Q1 - Q0) * (avg_share * avg_margin).sum()),
        "Mix": float((avg_quantity * (s1 - s0) * avg_margin).sum()),
        "Net price": float(((p1 - p0) * avg_q).sum()),
        "Product cost": float((-(c1["product_cost"] - c0["product_cost"]) * avg_q).sum()),
        "Freight": float((-(c1["freight"] - c0["freight"]) * avg_q).sum()),
        "Tariff": float((-(c1["tariff"] - c0["tariff"]) * avg_q).sum()),
    }
    gp0 = float(prior["gross_profit"].sum())
    gp1 = float(current["gross_profit"].sum())
    calculated0 = float((q0 * m0).sum())
    calculated1 = float((q1 * m1).sum())
    # Do not invent a driver explanation if the source gross-profit formula fails.
    if abs(calculated0 - gp0) > .02 or abs(calculated1 - gp1) > .02:
        raise ValueError("Source gross profit does not reconcile to net revenue and cost components")
    residual = (gp1 - gp0) - sum(effects.values())
    if abs(residual) > .02:
        raise ValueError(f"Gross profit bridge does not reconcile: {residual:.2f}")
    revenue0 = float(prior["net_revenue"].sum())
    revenue1 = float(current["net_revenue"].sum())
    return {
        "prior_date": pd.Timestamp(first), "current_date": pd.Timestamp(last),
        "prior_profit": gp0, "current_profit": gp1,
        "prior_revenue": revenue0, "current_revenue": revenue1,
        "prior_margin": gp0 / revenue0 * 100 if revenue0 else None,
        "current_margin": gp1 / revenue1 * 100 if revenue1 else None,
        "effects": effects, "residual": residual,
    }
