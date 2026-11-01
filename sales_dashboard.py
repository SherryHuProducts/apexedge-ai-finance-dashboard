"""Sales-facing views on the shared validated finance model."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_ui import COLORS, hero, money, section_title, style_chart
from sales_metrics import commercial_summary, commercial_segments, commercial_worklist


def _number(value: float | None, suffix: str = "", money_value: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if money_value:
        return money(value)
    return f"{value:,.1f}{suffix}"


def sales_page(frame: pd.DataFrame) -> None:
    hero(
        "COMMERCIAL DECISION SUPPORT · 销售决策支持",
        "Where should Sales grow—and where is growth destroying profit? / 哪些增长真正创造利润？",
        "Shared accounting definitions, commercial actions. Figures reflect the same validated rows as CFO mode. / 与 CFO 使用同一套已验证财务口径。",
    )
    summary = commercial_summary(frame)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Net Revenue / 净收入", _number(summary["net_revenue"], money_value=True))
    k2.metric("Contribution Margin / 贡献利润率", _number(summary["contribution_margin"], "%"))
    k3.metric("Return Rate / 退货率", _number(summary["return_rate"], "%"))
    k4.metric("Units Sold / 销量", f"{summary['units']:,.0f}" if summary["units"] is not None else "N/A")

    overview, pricing, actions = st.tabs([
        "Channel & SKU / 渠道与产品", "Promotion Economics / 促销测算",
        "Action Worklist / 行动清单",
    ])
    with overview:
        section_title("Channel Profitability", "渠道盈利能力",
                      "Compare contribution profit—not revenue alone", "比较贡献利润，而不只看收入")
        channels = commercial_segments(frame, ["channel"])
        left, right = st.columns([1.2, 1])
        with left:
            fig = px.bar(
                channels.sort_values("net_revenue"), y="channel", x="net_revenue",
                orientation="h", color="contribution_margin", text="net_revenue",
                color_continuous_scale="RdYlGn",
                labels={"net_revenue": "Net Revenue / 净收入", "channel": "Channel / 渠道",
                        "contribution_margin": "CM% / 贡献利润率"},
                title="Revenue with Contribution Margin / 收入与贡献利润率",
            )
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            st.plotly_chart(style_chart(fig, 350), use_container_width=True)
        with right:
            display = channels[["channel", "net_revenue", "gross_margin", "contribution_profit", "contribution_margin", "return_rate", "discount_rate"]].rename(columns={
                "channel": "Channel", "net_revenue": "Net Revenue",
                "gross_margin": "GM %", "contribution_profit": "Contribution Profit",
                "contribution_margin": "CM %", "return_rate": "Return %", "discount_rate": "Discount %",
            })
            st.dataframe(display, use_container_width=True, hide_index=True)
        section_title("SKU & Channel Detail", "SKU 与渠道明细",
                      "The same shared metric model", "同一套经营与财务指标")
        sku = commercial_segments(frame, ["sku", "channel"])
        st.dataframe(sku[["sku", "channel", "net_revenue", "contribution_profit", "contribution_margin", "return_rate", "discount_rate"]],
                     use_container_width=True, hide_index=True, height=360)

    with pricing:
        section_title("Incremental Discount Break-even", "额外折扣盈亏平衡",
                      "How much extra volume must a promotion generate to protect contribution profit?",
                      "促销需要带来多少增量销量才能保持贡献利润？")
        st.info("Sensitivity model, not a forecast. Assumes current unit costs and marketing per unit stay unchanged; platform fees vary with net revenue. / 这是敏感度测算，不是销量预测。")
        choices = commercial_segments(frame, ["sku", "channel"])
        if "units" not in choices or choices["units"].isna().all():
            st.warning("Unit quantities are required for break-even pricing. / 缺少销量字段，无法测算。")
        else:
            labels = [f"{row.sku} · {row.channel}" for row in choices.itertuples(index=False)]
            selected = st.selectbox("SKU × Channel / 产品与渠道", options=list(range(len(labels))), format_func=lambda i: labels[i])
            row = choices.iloc[selected]
            extra_discount = st.slider("Additional discount on net selling price / 额外折扣", 0.0, 15.0, 5.0, 0.5)
            units = float(row["units"])
            if units <= 0 or row["net_revenue"] <= 0:
                st.warning("Selected SKU/channel lacks positive units or revenue. / 所选产品缺少有效销量或收入。")
            else:
                price = row["net_revenue"] / units
                fee_rate = row["platform_fee"] / row["net_revenue"]
                fixed_unit_cost = (row["product_cost"] + row["freight"] + row["tariff"] + row["marketing_spend"]) / units
                original_unit_cp = price * (1 - fee_rate) - fixed_unit_cost
                new_unit_cp = price * (1 - extra_discount / 100) * (1 - fee_rate) - fixed_unit_cost
                a, b, c = st.columns(3)
                a.metric("Baseline contribution / 原单位贡献", money(original_unit_cp, False))
                b.metric("Promoted contribution / 促销后单位贡献", money(new_unit_cp, False))
                if original_unit_cp <= 0:
                    c.metric("Break-even growth / 保本增量销量", "N/A")
                    st.warning("Baseline unit contribution is not positive. First review pricing and cost structure. / 当前单位贡献利润不为正，应先检查定价和成本。")
                elif new_unit_cp <= 0:
                    c.metric("Break-even growth / 保本增量销量", "Not feasible")
                    st.error("No positive sales volume can restore baseline contribution profit under these assumptions. / 按当前假设，单纯提高销量无法保住原有贡献利润。")
                else:
                    growth = (original_unit_cp / new_unit_cp - 1) * 100
                    c.metric("Required volume growth / 所需销量增长", f"{growth:.1f}%")
                    st.caption(f"Illustrative minimum additional volume: {units * growth / 100:,.0f} units over the selected-period baseline. / 相比所选期间，约需增加 {units * growth / 100:,.0f} 件。")
                st.caption("This is not causal incrementality or measured price elasticity. Validate using a controlled test. / 不代表真实价格弹性或因果增量，应进行对照试验。")

    with actions:
        section_title("Commercial Review Queue", "商业行动复核清单",
                      "Prioritize investigation; no automatic price or purchase-order changes",
                      "只建议优先调查，不自动修改售价或采购单")
        worklist = commercial_worklist(frame)
        if worklist.empty:
            st.info("No SKU/channel records meet the minimum revenue threshold.")
        else:
            view = worklist[["sku", "channel", "net_revenue", "contribution_margin",
                             "return_rate", "discount_rate", "priority_score", "recommended_review"]].head(30)
            st.dataframe(view, use_container_width=True, hide_index=True, height=480)
            st.download_button("Download Review Queue / 下载行动清单",
                               view.to_csv(index=False).encode("utf-8-sig"),
                               "sales_review_queue.csv", "text/csv")
        st.caption("These are rule-based review priorities, not AI-generated recommendations or approved management actions. / 这是规则型复核优先级，不是已审批的商业决策。")
