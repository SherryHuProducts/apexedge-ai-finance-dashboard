"""Salesforce-inspired operating dashboard with finance evidence and period controls."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from business_performance import (
    aggregate_dimension, financial_period, kpis, period_rows, previous_period, source_gl_bridge,
)


def _money(value: float | None) -> str:
    return "N/A" if value is None else f"${value:,.0f}"


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def _delta(current: float | None, prior: float | None, percent_points: bool = False) -> str:
    if current is None or prior is None:
        return "N/A — prior or current data unavailable"
    if percent_points:
        return f"{(current - prior) * 100:+.1f} pp"
    if prior == 0:
        return "N/A — zero baseline"
    return f"{(current / abs(prior) - 1) * 100:+.1f}%"


def business_performance_page(data: pd.DataFrame, pipeline_result: dict, is_demo: bool) -> None:
    st.title("Business Performance Overview / 经营业绩看板")
    st.caption("Sales performance → Financial control → Exception drill-down. AI analysis follows the evidence.")
    if is_demo:
        st.info("SYNTHETIC DEMO / 模拟数据。地区、城市、销售与成本均为合成数据；不是 JLA HOME 真实经营信息。")
    else:
        st.warning("Uploaded source reporting / 上传数据。若未提供地区、客户或完整财务控制数，不会推断或补造这些字段。")

    monthly = pd.to_datetime(data["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    if monthly.isna().all():
        st.error("No valid reporting dates / 缺少有效日期")
        return
    latest = monthly.max()
    c1, c2, c3 = st.columns(3)
    kind = c1.selectbox("Reporting period / 分析期间", ["Month", "Quarter", "Year"])
    comparison = c2.selectbox("Compare with / 对比", ["Previous Period", "Prior Year"])
    choices = sorted(monthly.dropna().unique(), reverse=True)
    selected = c3.selectbox("Period ending month / 选择月份", choices, format_func=lambda x: pd.Timestamp(x).strftime("%b %Y"))
    start, end = financial_period(pd.Timestamp(selected), kind)
    # Never present unfinished quarters/years as full-period totals.
    end = min(end, pd.Timestamp(selected))
    prior_start, prior_end = previous_period(start, end, comparison)

    filters = st.columns(4)
    options = [("channel", "Channel / 渠道"), ("category", "Category / 产品类别"),
               ("sku", "SKU / 产品"), ("region", "Region / 地区")]
    filtered = data.copy()
    for col, (field, label) in zip(filters, options):
        if field in filtered and filtered[field].notna().any():
            choices_field = sorted(filtered[field].dropna().astype(str).unique())
            chosen = col.multiselect(label, choices_field, default=[], placeholder="All / 全部")
            if chosen:
                filtered = filtered.loc[filtered[field].astype(str).isin(chosen)]
        else:
            col.caption(f"{label}: unavailable / 无源数据")

    current = period_rows(filtered, start, end)
    previous = period_rows(filtered, prior_start, prior_end)
    if current.empty:
        st.warning("No transactions for the selected period and dimensions.")
        return
    metrics, baseline = kpis(current), kpis(previous)
    st.caption(f"Current: {start:%Y-%m} to {end:%Y-%m} · Comparison: {prior_start:%Y-%m} to {prior_end:%Y-%m} · "
               "Unmatched comparison periods display N/A.")

    kpi_columns = st.columns(5)
    cards = [
        ("Net Revenue", "net_revenue", _money, False),
        ("Gross Margin", "gross_margin", _percent, True),
        ("Contribution Profit", "contribution_profit", _money, False),
        ("Units Sold", "units", lambda v: "N/A" if v is None else f"{v:,.0f}", False),
        ("Return Rate", "return_rate", _percent, True),
    ]
    for col, (label, key, formatter, is_rate) in zip(kpi_columns, cards):
        col.metric(label, formatter(metrics[key]), _delta(metrics[key], baseline[key], is_rate), delta_color="off")

    st.subheader("Revenue & Contribution Trend / 收入与贡献利润趋势")
    trend = filtered.copy()
    trend["month"] = pd.to_datetime(trend["date"]).dt.to_period("M").dt.to_timestamp()
    trend = trend.groupby("month", as_index=False)[["net_revenue", "contribution_profit"]].sum(min_count=1)
    st.line_chart(trend.set_index("month")[["net_revenue", "contribution_profit"]], use_container_width=True)

    st.subheader("Where is performance changing? / 分维度分析")
    available = [f for f in ("channel", "category", "sku", "region", "city", "customer_id")
                 if f in current and current[f].notna().any()]
    if available:
        dimension = st.selectbox("Group by / 分组", available)
        grouped = aggregate_dimension(current, dimension)
        if not grouped.empty:
            st.bar_chart(grouped.set_index(dimension)["net_revenue"].head(20), use_container_width=True)
            st.dataframe(grouped.head(100), use_container_width=True, hide_index=True)
    else:
        st.caption("No grouping dimensions supplied / 未提供可用分组字段")

    st.subheader("Source Sales vs Financial Control / 销售与财务核对")
    bridge = source_gl_bridge(current, pipeline_result.get("gl_status", "NOT SUPPLIED"),
                              pipeline_result.get("gl_recon"))
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Operational Net Revenue", _money(bridge["source_revenue"]))
    cc2.metric("Operational Product Cost", _money(bridge["source_cogs"]))
    cc3.metric("Independent GL Control", bridge["gl_status"])
    if bridge["is_reconciled"]:
        st.success("GL control supplied and passed for its tested scope. Confirm period alignment before financial sign-off.")
        st.dataframe(bridge["gl_recon"], use_container_width=True, hide_index=True)
    else:
        st.warning("NOT RECONCILED for selected period / 当前筛选期间尚未独立勾稽。Operational totals are not GL totals.")

    st.subheader("Transaction Drill-down / 原始记录追溯")
    details = [f for f in ("date", "channel", "region", "city", "customer_id", "sku", "product", "units",
                         "gross_sales", "discount", "returns", "net_revenue", "product_cost", "freight",
                         "tariff", "platform_fee", "marketing_spend", "gross_profit", "contribution_profit",
                         "source_file", "source_sheet", "source_row") if f in current]
    st.dataframe(current[details].sort_values("net_revenue", ascending=False).head(500),
                 use_container_width=True, hide_index=True)
    st.download_button("Download filtered source records / 下载当前记录", current[details].to_csv(index=False),
                       file_name="apexedge_selected_source_records.csv", mime="text/csv")
    st.caption("Record grain follows the uploaded source or synthetic SKU-month-channel fact table. "
               "A monthly aggregated row must not be described as a single order; order-level drill-down requires order IDs and underlying transactions.")
