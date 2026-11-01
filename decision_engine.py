"""Deterministic finance signals and decision evidence; AI never computes KPIs."""
from __future__ import annotations

import hashlib
import json

import pandas as pd

from sales_metrics import commercial_segments, commercial_summary


def _id(kind: str, scope: str, date: str) -> str:
    return hashlib.sha256(f"{kind}|{scope}|{date}".encode()).hexdigest()[:12]


def detect_signals(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "channel", "net_revenue", "gross_profit", "contribution_profit"}
    if frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame(columns=["id", "audience", "severity", "signal", "metric", "observed", "baseline", "delta", "evidence", "suggested_review"])
    rows: list[dict] = []
    periods = sorted(pd.to_datetime(frame["date"]).dropna().unique())
    if len(periods) >= 2:
        monthly = frame.groupby("date")[["net_revenue", "gross_profit", "contribution_profit"]].sum().sort_index()
        prior, latest = monthly.iloc[-2], monthly.iloc[-1]
        date = pd.Timestamp(monthly.index[-1]).strftime("%Y-%m")
        gm0 = prior["gross_profit"] / prior["net_revenue"] * 100 if prior["net_revenue"] else None
        gm1 = latest["gross_profit"] / latest["net_revenue"] * 100 if latest["net_revenue"] else None
        if gm0 is not None and gm1 is not None and gm1 < gm0 - 1:
            rows.append({
                "id": _id("gm_drop", "all", date), "audience": "CFO",
                "severity": "High" if gm0 - gm1 >= 3 else "Medium",
                "signal": "Gross margin compression / 毛利率下降", "metric": "Gross Margin %",
                "observed": round(float(gm1), 2), "baseline": round(float(gm0), 2),
                "delta": round(float(gm1 - gm0), 2),
                "evidence": "Latest vs previous month gross profit / net revenue (percentage points)",
                "suggested_review": "Inspect exact price-volume-mix-cost bridge / 分析价格、销量、组合及成本驱动",
            })
        cp_change = float(latest["contribution_profit"] - prior["contribution_profit"])
        if cp_change < 0:
            rows.append({
                "id": _id("cp_decline", "all", date), "audience": "CFO",
                "severity": "High" if prior["contribution_profit"] > 0 and cp_change / prior["contribution_profit"] < -.1 else "Medium",
                "signal": "Contribution profit decline / 贡献利润下降", "metric": "Contribution Profit $",
                "observed": round(float(latest["contribution_profit"]), 2),
                "baseline": round(float(prior["contribution_profit"]), 2),
                "delta": round(cp_change, 2),
                "evidence": "Latest minus previous month contribution profit",
                "suggested_review": "Review channel cost and discount drivers / 检查渠道费用与折扣",
            })
    if {"gross_sales", "discount", "returns", "product_cost", "freight", "tariff", "platform_fee", "marketing_spend"}.issubset(frame.columns):
        by_channel = commercial_segments(frame, ["channel"])
        date = pd.Timestamp(frame["date"].max()).strftime("%Y-%m")
        for _, item in by_channel.iterrows():
            channel = str(item["channel"])
            if float(item["contribution_profit"]) < 0:
                rows.append({
                    "id": _id("negative_cp", channel, date), "audience": "Sales",
                    "severity": "High", "signal": "Negative channel contribution / 渠道贡献利润为负",
                    "metric": "Contribution Profit $",
                    "observed": round(float(item["contribution_profit"]), 2), "baseline": 0.0,
                    "delta": round(float(item["contribution_profit"]), 2),
                    "evidence": "Channel net revenue less product, logistics, platform and marketing costs",
                    "suggested_review": "Review pricing, fees and promotion economics / 复核定价及促销经济性",
                })
            if pd.notna(item["return_rate"]) and item["return_rate"] > 10:
                rows.append({
                    "id": _id("return", channel, date), "audience": "Sales",
                    "severity": "Medium", "signal": "Elevated channel returns / 渠道退货率偏高",
                    "metric": "Return Rate %",
                    "observed": round(float(item["return_rate"]), 2), "baseline": 10.0,
                    "delta": round(float(item["return_rate"] - 10), 2),
                    "evidence": "Channel returns / (gross sales - discounts); 10% is a demo triage threshold",
                    "suggested_review": "Review return reasons and SKU cohorts / 检查退货原因及 SKU",
                })
    return pd.DataFrame(rows)


def evidence_packet(frame: pd.DataFrame, signals: pd.DataFrame, audience: str) -> dict:
    """Only a small aggregated numeric packet can leave the app with consent."""
    summary = commercial_summary(frame)
    limited = signals.loc[
        signals["audience"].isin([audience, "CFO"]) if audience == "CFO"
        else signals["audience"].isin([audience])
    ].head(6)
    return {
        "audience": audience,
        "period_months": int(frame["date"].nunique()),
        "summary": {key: (round(float(value), 2) if value is not None else None)
                    for key, value in summary.items()},
        "signals": [
            {
                "signal": str(row["signal"]), "metric": str(row["metric"]),
                "observed": float(row["observed"]), "baseline": float(row["baseline"]),
                "delta": float(row["delta"]), "evidence": str(row["evidence"]),
            }
            for _, row in limited.iterrows()
        ],
        "data_scope": "Aggregated summary only; no raw rows, names, files, SKU identifiers or account numbers.",
    }


def proposal_from_signal(row: pd.Series) -> dict:
    return {
        "id": str(row["id"]),
        "audience": str(row["audience"]),
        "signal": str(row["signal"]),
        "evidence": str(row["evidence"]),
        "recommendation": str(row["suggested_review"]),
        "status": "Proposed",
        "owner": "",
        "expected_impact": "",
        "actual_impact": "",
        "notes": "",
    }
