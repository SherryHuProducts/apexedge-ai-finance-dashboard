"""CFO/Sales channel margin bridge with explicit exceptions and source trace."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from channel_pl import build_pl


def _usd(value: int) -> str:
    return f"${value / 100:,.2f}"


def channel_pl_page() -> None:
    st.title("Reconciled Channel P&L / 渠道利润桥表")
    st.info("SYNTHETIC FINANCIAL CONTROLS — Walmart, Costco, ERP and Website are mock sources. Not a published GAAP statement or live ledger.")
    st.caption("Source → Approved SKU/Customer/Account → Revenue → COGS → Channel costs → GL control")
    c1, c2 = st.columns(2)
    approved = c1.checkbox("Approve Website SKU / 批准网站 SKU 映射", value=False)
    missing = c2.checkbox("Remove Costco cost evidence / 模拟 Costco 成本缺失", value=False)
    result = build_pl(approve_website=approved, missing_cost=missing)
    total = result["totals"]

    st.subheader("1 · Data Readiness / 数据准备状态")
    a, b, c, d = st.columns(4)
    a.metric("Blocked by mapping", _usd(result["blocked_mapping_cents"]))
    b.metric("Blocked by missing cost", _usd(result["blocked_cost_cents"]))
    c.metric("GL control", result["gl_status"])
    d.metric("Shared cost unallocated", _usd(result["unallocated_shared_cents"]))
    if not result["profit_complete"]:
        st.error("INCOMPLETE PROFITABILITY / 利润数据不完整。Below are calculated-only *partial* totals; do not treat them as company P&L.")
    else:
        st.success("Complete synthetic source coverage and demo net revenue/COGS controls passed. Still not a real month-end close.")

    st.subheader("2 · Profit Bridge / 利润计算桥表")
    bridge = [
        ("Gross Sales", total["revenue_cents"]),
        ("Less: Returns", -total["returns_cents"]),
        ("Net Revenue", total["net_revenue_cents"]),
        ("Less: Product COGS", -total["cogs_cents"]),
        ("Less: Freight", -total["freight_cents"]),
        ("Less: Tariff", -total["tariff_cents"]),
        ("Gross Profit (case policy)", total["gross_profit_cents"]),
        ("Less: Marketplace Fees", -total["platform_fee_cents"]),
        ("Less: Advertising", -total["advertising_cents"]),
        ("Less: Wholesale Rebates", -total["rebate_cents"]),
        ("Contribution Profit (before shared costs)", total["contribution_profit_cents"]),
    ]
    st.dataframe(pd.DataFrame([{"Metric": k, "Amount (USD)": _usd(v)} for k, v in bridge]),
                 use_container_width=True, hide_index=True)
    st.caption("Shared costs are explicitly **UNALLOCATED** and not subtracted from contribution profit. "
               "Accounting policy differs by entity; here freight and tariff are placed above gross profit by illustrative case policy.")

    st.subheader("3 · Channel Comparison / 渠道对比")
    channels = pd.DataFrame(result["channels"])
    if not channels.empty:
        for key in ("net_revenue_cents", "gross_profit_cents", "contribution_profit_cents"):
            channels[key.replace("_cents", "_usd")] = channels[key] / 100
        channels["contribution_margin_pct"] = (channels["contribution_profit_cents"] /
                                                channels["net_revenue_cents"].where(channels["net_revenue_cents"] != 0) * 100)
        st.bar_chart(channels.set_index("channel")[["net_revenue_usd", "contribution_profit_usd"]])
        st.dataframe(channels[["channel", "orders", "net_revenue_usd", "gross_profit_usd",
                               "contribution_profit_usd", "contribution_margin_pct"]], hide_index=True, use_container_width=True)

    st.subheader("4 · GL Reconciliation & Exceptions / 总账差异与异常")
    st.dataframe(pd.DataFrame([{"Control": key, "Source minus demo GL (USD)": _usd(value)}
                               for key, value in result["gl_variance"].items()]), hide_index=True, use_container_width=True)
    if result["exceptions"]:
        st.dataframe(pd.DataFrame(result["exceptions"]), hide_index=True, use_container_width=True)
    else:
        st.success("No mapping or missing-cost exceptions in this synthetic sample.")

    st.subheader("5 · Source Evidence / 溯源")
    st.dataframe(pd.DataFrame(result["details"]), hide_index=True, use_container_width=True)
    st.caption("One row per source order in this small synthetic case, with source_system/order_id, canonical keys and cost breakdown. "
               "Unapproved or missing-cost records are preserved, not priced at zero.")
