from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from inventory_metrics import inventory_kpis, inventory_snapshot


COLORS = {
    "ink": "#132238", "muted": "#66758A", "blue": "#2563EB", "cyan": "#0EA5E9",
    "green": "#10B981", "amber": "#F59E0B", "red": "#EF4444", "purple": "#8B5CF6",
    "paper": "#FFFFFF", "canvas": "#F3F6FA", "line": "#E5EAF1",
}

CHANNEL_COLORS = {"Amazon": "#2563EB", "DTC": "#10B981", "Retail": "#8B5CF6", "TikTok": "#F59E0B", "Unspecified": "#94A3B8"}

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: Inter, "Noto Sans SC", "PingFang SC", sans-serif; }
  .stApp { background:#F3F6FA; color:#132238; }
  [data-testid="stSidebar"] { background:#0D1B2A; min-width:282px; }
  [data-testid="stSidebar"] > div { padding-top:1.15rem; }
  [data-testid="stSidebar"] * { color:#E8EEF7; }
  [data-testid="stSidebar"] [data-baseweb="select"] *, [data-testid="stSidebar"] input { color:#132238 !important; }
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * { color:#536277 !important; }
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button { color:#1D4ED8 !important; background:#fff; border:1px solid #CBD5E1; }
  [data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.12); }
  [data-testid="stSidebar"] [role="radiogroup"] label { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:7px 9px; margin-bottom:5px; }
  .block-container { max-width:1500px; padding:1.8rem 2.25rem 3.2rem; }
  #MainMenu, footer, header { visibility:hidden; }
  .sidebar-brand { display:flex; align-items:center; gap:10px; font-size:19px; font-weight:800; margin:4px 0 2px; }
  .brand-mark { width:31px; height:31px; border-radius:10px; display:inline-flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#2563EB,#0EA5E9); color:white; box-shadow:0 8px 18px rgba(14,165,233,.25); }
  .sidebar-caption { color:#91A4BD !important; font-size:11px; margin:0 0 20px 41px; }
  .hero { background:linear-gradient(125deg,#102541 0%,#173B66 56%,#12657A 100%); border-radius:20px; padding:27px 30px; color:white; margin-bottom:19px; box-shadow:0 16px 36px rgba(19,34,56,.12); position:relative; overflow:hidden; }
  .hero:after { content:""; position:absolute; width:260px; height:260px; border-radius:50%; right:-75px; top:-135px; background:rgba(56,189,248,.16); }
  .hero-kicker { font-size:11px; letter-spacing:.13em; text-transform:uppercase; opacity:.75; font-weight:700; }
  .hero h1 { font-size:28px; line-height:1.25; margin:7px 0 7px; font-weight:750; max-width:960px; }
  .hero p { font-size:13px; line-height:1.55; margin:0; opacity:.78; max-width:980px; }
  .metric-card { background:#fff; border:1px solid #E5EAF1; border-radius:16px; padding:17px 18px 15px; box-shadow:0 7px 22px rgba(19,34,56,.045); min-height:128px; }
  .metric-head { display:flex; justify-content:space-between; gap:8px; align-items:flex-start; color:#66758A; font-size:12px; font-weight:650; }
  .metric-head small { display:block; font-size:10px; font-weight:500; color:#94A3B8; margin-top:2px; }
  .metric-icon { width:30px; height:30px; display:flex; align-items:center; justify-content:center; background:#EEF4FF; color:#2563EB; border-radius:9px; font-size:14px; flex:0 0 auto; }
  .metric-value { color:#132238; font-size:26px; font-weight:750; margin-top:9px; line-height:1; }
  .metric-foot { color:#7A8798; font-size:10px; margin-top:9px; }
  .delta-up { color:#059669; font-weight:700; } .delta-down { color:#DC2626; font-weight:700; }
  .section-head { margin:18px 0 8px; }
  .section-title { color:#132238; font-size:17px; font-weight:750; line-height:1.25; }
  .section-title span { color:#64748B; font-weight:600; }
  .section-sub { color:#7A8798; font-size:11px; margin-top:4px; }
  [data-testid="stPlotlyChart"] { background:white; border:1px solid #E5EAF1; border-radius:16px; box-shadow:0 7px 22px rgba(19,34,56,.04); padding:6px 7px 0; }
  [data-testid="stDataFrame"] { border:1px solid #E5EAF1; border-radius:14px; overflow:hidden; }
  .signal-card { background:#fff; border:1px solid #E5EAF1; border-radius:14px; padding:14px 16px; margin-bottom:9px; }
  .signal-label { font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:#64748B; font-weight:750; }
  .signal-value { font-size:13px; color:#132238; font-weight:700; margin:5px 0 3px; }
  .signal-note { font-size:10px; color:#7A8798; line-height:1.45; }
  .alert-card { background:#FFF7ED; border:1px solid #FED7AA; border-radius:14px; padding:14px 16px; }
  .summary-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:4px 0 8px; }
  .summary-card { background:#fff; border:1px solid #E5EAF1; border-radius:15px; padding:17px; min-height:135px; }
  .summary-num { width:25px; height:25px; border-radius:8px; background:#EEF4FF; color:#2563EB; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800; margin-bottom:9px; }
  .summary-card b { display:block; font-size:13px; color:#132238; margin-bottom:6px; }
  .summary-card p { font-size:11px; color:#64748B; line-height:1.55; margin:0; }
  .scenario-panel { background:#fff; border:1px solid #E5EAF1; border-radius:16px; padding:18px 19px 9px; }
  .scenario-panel h4 { margin:0 0 3px; font-size:14px; color:#132238; }
  .scenario-panel p { margin:0 0 12px; font-size:10px; color:#7A8798; }
  .decision { background:linear-gradient(135deg,#ECFDF5,#F0FDFA); border:1px solid #A7F3D0; border-radius:15px; padding:16px 18px; margin-bottom:8px; }
  .decision b { color:#065F46; font-size:12px; } .decision p { color:#477569; font-size:10px; line-height:1.45; margin:5px 0 0; }
  div[data-testid="stDownloadButton"] > button { border-radius:10px; border:0; background:#2563EB; color:white; font-weight:650; }
  div[data-testid="stDownloadButton"] > button:hover { background:#1D4ED8; color:white; border:0; }
  div[data-testid="stExpander"] { background:#fff; border:1px solid #E5EAF1; border-radius:13px; }
  @media(max-width:900px) { .block-container{padding:1.2rem 1rem 2rem}.hero{padding:22px}.hero h1{font-size:23px}.summary-grid{grid-template-columns:1fr}.metric-value{font-size:22px} }
</style>
"""


def money(value: float, compact: bool = True) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if compact and value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}M"
    if compact and value >= 1_000:
        return f"{sign}${value / 1_000:.1f}K"
    return f"{sign}${value:,.0f}"


def pct_change(current: float, previous: float) -> float:
    return (current - previous) / abs(previous) * 100 if previous else 0.0


def section_title(en: str, zh: str, sub_en: str = "", sub_zh: str = "") -> None:
    subtitle = f'<div class="section-sub">{sub_en}{" · " if sub_en and sub_zh else ""}{sub_zh}</div>' if sub_en or sub_zh else ""
    st.markdown(f'<div class="section-head"><div class="section-title">{en} <span>/ {zh}</span></div>{subtitle}</div>', unsafe_allow_html=True)


def metric_card(en: str, zh: str, value: str, delta: float | None, note: str, icon: str, pp: bool = False, invert: bool = False) -> None:
    favorable = (delta <= 0 if invert else delta >= 0) if delta is not None else True
    css = "delta-up" if favorable else "delta-down"
    arrow = "↑" if delta is not None and delta >= 0 else "↓"
    delta_label = f"{arrow} {abs(delta):.1f}{' pp' if pp else '%'}" if delta is not None else ""
    st.markdown(
        f'<div class="metric-card"><div class="metric-head"><span>{en}<small>{zh}</small></span><span class="metric-icon">{icon}</span></div>'
        f'<div class="metric-value">{value}</div><div class="metric-foot"><span class="{css}">{delta_label}</span>&nbsp; {note}</div></div>',
        unsafe_allow_html=True,
    )


def style_chart(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=18, r=18, t=48, b=72), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter, "PingFang SC", sans-serif', color=COLORS["muted"], size=11),
        title_font=dict(color=COLORS["ink"], size=14), legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="#132238", font_color="white", bordercolor="#132238"),
    )
    fig.update_xaxes(showgrid=False, linecolor=COLORS["line"], tickfont=dict(color=COLORS["muted"]))
    fig.update_yaxes(gridcolor="#EDF1F6", zeroline=False, tickfont=dict(color=COLORS["muted"]))
    return fig


def weighted_margin(frame: pd.DataFrame) -> float:
    revenue = frame["net_revenue"].sum()
    return frame["gross_profit"].sum() / revenue * 100 if revenue else 0.0


def inventory_metrics(frame: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    metrics = inventory_kpis(frame)
    return metrics["inventory_value"], metrics["turnover"], metrics["inventory_days"]


def hero(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><div class="hero-kicker">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def executive_page(df: pd.DataFrame) -> None:
    hero(
        "CFO DECISION SUPPORT · CFO 决策支持",
        "Revenue is growing—but gross margin is falling. Why, and what should we do?<br>收入持续增长，但毛利率正在下滑：原因是什么，CFO 应该如何行动？",
        "ApexEdge consumer electronics case · 12 months · 100 SKUs · Amazon, DTC, Retail & TikTok",
    )
    monthly = df.groupby("date", as_index=False).agg(
        net_revenue=("net_revenue", "sum"), gross_profit=("gross_profit", "sum"),
        contribution_profit=("contribution_profit", "sum"), inventory_value=("inventory_value", "sum"),
    )
    monthly["gross_margin"] = monthly["gross_profit"] / monthly["net_revenue"] * 100
    current = monthly.iloc[-1]
    previous = monthly.iloc[-2] if len(monthly) > 1 else current
    inventory_value, _, inventory_days = inventory_metrics(df)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("Net Revenue", "净收入", money(current["net_revenue"]), pct_change(current["net_revenue"], previous["net_revenue"]), "MoM / 环比", "↗")
    with k2:
        metric_card("Gross Margin", "毛利率", f"{current['gross_margin']:.1f}%", current["gross_margin"] - previous["gross_margin"], "MoM / 环比", "◎", pp=True)
    with k3:
        metric_card("Contribution Profit", "贡献利润", money(current["contribution_profit"]), pct_change(current["contribution_profit"], previous["contribution_profit"]), "MoM / 环比", "◇")
    with k4:
        metric_card("Inventory Days", "库存天数", f"{inventory_days:.0f} days" if inventory_days is not None else "N/A", None, "month-end snapshot / 月末快照", "◫", invert=True)

    section_title("Performance Pulse", "经营脉搏", "Revenue growth vs. margin quality", "收入增长与利润质量")
    left, right = st.columns([1.58, 0.82])
    with left:
        trend = go.Figure()
        trend.add_bar(x=monthly["date"], y=monthly["net_revenue"], name="Net Revenue / 净收入", marker_color="#BFDBFE", hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra></extra>")
        trend.add_scatter(x=monthly["date"], y=monthly["gross_margin"], name="Gross Margin / 毛利率", mode="lines+markers", line=dict(color=COLORS["blue"], width=3), marker=dict(size=6), yaxis="y2", hovertemplate="%{x|%b %Y}<br>%{y:.1f}%<extra></extra>")
        trend.update_layout(
            title="Revenue & Gross Margin Trend / 收入与毛利率趋势",
            yaxis=dict(title="Revenue / 收入", tickprefix="$", tickformat="~s", gridcolor="#EDF1F6"),
            yaxis2=dict(title="Margin / 毛利率", overlaying="y", side="right", ticksuffix="%", showgrid=False, range=[min(monthly["gross_margin"].min() - 3, 20), max(monthly["gross_margin"].max() + 3, 45)]),
            bargap=.35,
        )
        st.plotly_chart(style_chart(trend, 356), use_container_width=True, config={"displayModeBar": False})
    with right:
        first_q, last_q = monthly.head(3), monthly.tail(3)
        rev_growth = pct_change(last_q["net_revenue"].sum(), first_q["net_revenue"].sum())
        margin_delta = (last_q["gross_profit"].sum() / last_q["net_revenue"].sum() - first_q["gross_profit"].sum() / first_q["net_revenue"].sum()) * 100
        channel_margin = df.groupby("channel").agg(revenue=("net_revenue", "sum"), profit=("gross_profit", "sum"))
        channel_margin["margin"] = channel_margin["profit"] / channel_margin["revenue"] * 100
        weakest_channel = channel_margin["margin"].idxmin()
        st.markdown(
            f'<div class="signal-card"><div class="signal-label">Growth / 增长</div><div class="signal-value">Revenue {rev_growth:+.1f}%</div><div class="signal-note">Latest quarter vs. first quarter<br>最近季度对比首季度</div></div>'
            f'<div class="alert-card"><div class="signal-label">Margin alert / 毛利预警</div><div class="signal-value">{margin_delta:+.1f} pp</div><div class="signal-note">Growth is not converting into margin.<br>收入增长未转化为毛利改善。</div></div>'
            f'<div class="signal-card" style="margin-top:9px"><div class="signal-label">Primary drag / 主要拖累</div><div class="signal-value">{weakest_channel} channel</div><div class="signal-note">Lowest blended gross margin<br>综合毛利率最低的渠道</div></div>',
            unsafe_allow_html=True,
        )

    section_title("Profitability Bridge", "利润桥", "Reconcile every dollar from gross sales to contribution profit", "从销售总额逐项核对至贡献利润")
    left, right = st.columns([1.45, 1])
    with left:
        sums = df[["gross_sales", "discount", "returns", "net_revenue", "product_cost", "freight", "tariff", "gross_profit", "platform_fee", "marketing_spend", "contribution_profit"]].sum()
        bridge = go.Figure(go.Waterfall(
            orientation="v", measure=["relative", "relative", "relative", "total", "relative", "relative", "relative", "total", "relative", "relative", "total"],
            x=["Gross Sales<br>销售总额", "Discounts<br>折扣", "Returns<br>退货", "Net Revenue<br>净收入", "Product Cost<br>产品成本", "Freight<br>运费", "Tariffs<br>关税", "Gross Profit<br>毛利", "Platform Fees<br>平台费", "Marketing<br>营销", "Contribution<br>贡献利润"],
            y=[sums["gross_sales"], -sums["discount"], -sums["returns"], 0, -sums["product_cost"], -sums["freight"], -sums["tariff"], 0, -sums["platform_fee"], -sums["marketing_spend"], 0],
            connector={"line": {"color": "#CBD5E1"}}, increasing={"marker": {"color": COLORS["blue"]}},
            decreasing={"marker": {"color": COLORS["red"]}}, totals={"marker": {"color": COLORS["ink"]}},
            hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
        ))
        bridge.update_layout(title="P&L Waterfall / 损益瀑布图")
        bridge.update_yaxes(tickprefix="$", tickformat="~s")
        st.plotly_chart(style_chart(bridge, 365), use_container_width=True, config={"displayModeBar": False})
    with right:
        channel = df.groupby("channel", as_index=False).agg(net_revenue=("net_revenue", "sum"), gross_profit=("gross_profit", "sum"), contribution_profit=("contribution_profit", "sum"))
        channel["gross_margin"] = channel["gross_profit"] / channel["net_revenue"] * 100
        channel = channel.sort_values("gross_margin")
        bars = px.bar(channel, x="gross_margin", y="channel", orientation="h", color="channel", color_discrete_map=CHANNEL_COLORS, text="gross_margin")
        bars.update_traces(texttemplate="%{text:.1f}%", textposition="outside", hovertemplate="%{y}<br>Gross margin %{x:.1f}%<extra></extra>")
        bars.update_layout(title="Gross Margin by Channel / 渠道毛利率", showlegend=False)
        bars.update_xaxes(ticksuffix="%", range=[0, max(channel["gross_margin"].max() * 1.2, 10)])
        st.plotly_chart(style_chart(bars, 365), use_container_width=True, config={"displayModeBar": False})

    section_title("CFO Executive Summary", "CFO 管理层摘要", "Decision-ready, reusable and presentation-friendly", "可决策、可复用、可直接汇报")
    st.markdown(
        f'<div class="summary-grid">'
        f'<div class="summary-card"><div class="summary-num">01</div><b>What changed / 发生了什么</b><p>Revenue grew {rev_growth:.1f}% from the first to latest quarter, while gross margin moved {margin_delta:+.1f} pp. Growth quality is deteriorating.<br>首季至最近季度收入增长 {rev_growth:.1f}%，但毛利率变化 {margin_delta:+.1f} 个百分点，增长质量下降。</p></div>'
        f'<div class="summary-card"><div class="summary-num">02</div><b>Why it happened / 原因判断</b><p>Channel mix shifted toward higher-fee channels while freight, tariffs, discounts and returns increased. {weakest_channel} is the largest margin pressure point.<br>渠道组合向高费率渠道倾斜，同时运费、关税、折扣及退货上升；{weakest_channel} 是主要利润压力点。</p></div>'
        f'<div class="summary-card"><div class="summary-num">03</div><b>CFO action / CFO 行动建议</b><p>Run a controlled price test, renegotiate platform fees, reduce high-return SKUs and rebalance slow inventory. Track contribution profit—not revenue alone.<br>开展小范围提价测试、重谈平台费、治理高退货 SKU 并优化滞销库存；核心考核贡献利润，而非只看收入。</p></div></div>',
        unsafe_allow_html=True,
    )
    brief = f"""# CFO Executive Summary / CFO 管理层摘要
## What changed / 发生了什么
- Latest-quarter revenue vs. first quarter: {rev_growth:+.1f}%
- Gross-margin movement: {margin_delta:+.1f} percentage points
## Why / 原因
- Mix shifted toward higher-fee and higher-return channels.
- Freight and tariffs increased while discounting deepened.
- Weakest gross-margin channel: {weakest_channel}.
## Recommendation / 建议
1. Pilot a targeted 3% price increase on resilient SKUs.
2. Renegotiate platform fees and cap inefficient paid acquisition.
3. Reduce high-return SKUs and rebalance slow-moving inventory.
4. Manage the business to contribution profit and inventory turns.
"""
    st.download_button("Download CFO Brief / 下载管理层摘要", brief.encode("utf-8"), "cfo_executive_summary.md", "text/markdown")
    with st.expander("Data Controls & Reconciliation / 数据控制与勾稽关系"):
        rev_check = (df["gross_sales"] - df["discount"] - df["returns"] - df["net_revenue"]).abs().max()
        gp_check = (df["net_revenue"] - df["product_cost"] - df["freight"] - df["tariff"] - df["gross_profit"]).abs().max()
        st.markdown(f"**Rows / 数据行：** {len(df):,} &nbsp;&nbsp; **SKUs：** {df['sku'].nunique():,} &nbsp;&nbsp; **Months / 月份：** {df['date'].nunique()}  \n**Revenue reconciliation / 收入勾稽差异：** ${rev_check:,.2f} &nbsp;&nbsp; **Gross-profit reconciliation / 毛利勾稽差异：** ${gp_check:,.2f}")


def margin_inventory_page(df: pd.DataFrame) -> None:
    hero(
        "UNIT ECONOMICS · 单位经济模型",
        "Margin & Inventory Analysis / 毛利与库存分析",
        "Drill from category to SKU, connect price and cost to inventory velocity · 从品类下钻至 SKU，联动价格、成本与库存周转",
    )
    latest_month = df["date"].max()
    latest_snapshot = df[df["date"] == latest_month]
    inventory_value, turns, days = inventory_metrics(df)
    revenue, margin = df["net_revenue"].sum(), weighted_margin(df)
    prior_dates = sorted(df["date"].unique())
    prev_month = df[df["date"] == prior_dates[-2]] if len(prior_dates) > 1 else latest_snapshot
    prev_margin = weighted_margin(prev_month)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("Selected Revenue", "筛选后收入", money(revenue), 0, "selected period / 所选期间", "↗")
    with k2:
        metric_card("Gross Margin", "毛利率", f"{margin:.1f}%", margin - prev_margin, "vs prior month / 对比上月", "◎", pp=True)
    with k3:
        metric_card("Inventory Value", "库存金额", money(inventory_value) if inventory_value is not None else "N/A", None, f"as of {latest_month:%b %Y}", "◫", invert=True)
    with k4:
        metric_card("Inventory Turnover", "库存周转", f"{turns:.2f}x" if turns is not None else "N/A", None, f"{days:.0f} days / 天" if days is not None else "insufficient data / 数据不足", "↻")

    aggregates = df.groupby(["sku", "product", "category"], as_index=False).agg(
        net_revenue=("net_revenue", "sum"), gross_profit=("gross_profit", "sum"),
        contribution_profit=("contribution_profit", "sum"), units=("units", "sum"), cogs=("product_cost", "sum"),
    )
    inventory = inventory_snapshot(latest_snapshot).groupby("sku", as_index=False).agg(inventory_value=("inventory_value", "sum"), inventory_units=("inventory_units", "sum"))
    sku = aggregates.merge(inventory, on="sku", how="left")
    sku["gross_margin"] = sku["gross_profit"] / sku["net_revenue"].replace(0, float("nan")) * 100
    months = max(df["date"].nunique(), 1)
    sku["turnover"] = (sku["cogs"] * 12 / months) / sku["inventory_value"].where(sku["inventory_value"] > 0)
    sku["inventory_days"] = 365 / sku["turnover"].where(sku["turnover"] > 0)

    section_title("SKU Profitability Map", "SKU 盈利地图", "Bubble size represents ending inventory value", "气泡大小代表期末库存金额")
    scatter = px.scatter(
        sku.assign(bubble_size=sku["inventory_value"].fillna(0).clip(lower=0)), x="net_revenue", y="gross_margin", size="bubble_size", color="category", hover_name="sku",
        hover_data={"product": True, "net_revenue": ":$,.0f", "gross_margin": ":.1f", "inventory_value": ":$,.0f", "turnover": ":.2f"},
        labels={"net_revenue": "Net Revenue / 净收入", "gross_margin": "Gross Margin / 毛利率", "category": "Category / 品类"},
        size_max=38, color_discrete_sequence=["#2563EB", "#10B981", "#8B5CF6", "#F59E0B", "#0EA5E9", "#EF4444"],
    )
    scatter.add_hline(y=sku["gross_margin"].median(), line_dash="dot", line_color="#94A3B8")
    scatter.add_vline(x=sku["net_revenue"].median(), line_dash="dot", line_color="#94A3B8")
    scatter.update_layout(title="Revenue vs. Margin by SKU / SKU 收入与毛利率")
    scatter.update_xaxes(tickprefix="$", tickformat="~s")
    scatter.update_yaxes(ticksuffix="%")
    st.plotly_chart(style_chart(scatter, 410), use_container_width=True, config={"displayModeBar": False})

    section_title("Margin Drivers", "毛利驱动因素", "Compare channel-category margin and the cost stack behind it", "对比渠道与品类毛利，并拆解成本结构")
    left, right = st.columns([1.15, 1])
    with left:
        heat = df.groupby(["category", "channel"], as_index=False).agg(revenue=("net_revenue", "sum"), profit=("gross_profit", "sum"))
        heat["margin"] = heat["profit"] / heat["revenue"] * 100
        pivot = heat.pivot(index="category", columns="channel", values="margin")
        heatmap = px.imshow(pivot, text_auto=".1f", aspect="auto", color_continuous_scale=["#FEE2E2", "#FEF3C7", "#DCFCE7"], labels=dict(x="Channel / 渠道", y="Category / 品类", color="GM%"))
        heatmap.update_layout(title="Gross Margin Heatmap / 毛利率热力图", coloraxis_showscale=False)
        st.plotly_chart(style_chart(heatmap, 365), use_container_width=True, config={"displayModeBar": False})
    with right:
        cost = df.groupby("channel", as_index=False)[["net_revenue", "product_cost", "freight", "tariff", "platform_fee", "marketing_spend"]].sum()
        cost_long = []
        labels = {"product_cost": "Product Cost / 产品成本", "freight": "Freight / 运费", "tariff": "Tariff / 关税", "platform_fee": "Platform Fee / 平台费", "marketing_spend": "Marketing / 营销"}
        for _, row in cost.iterrows():
            for col, label in labels.items():
                cost_long.append({"channel": row["channel"], "cost": label, "pct_revenue": row[col] / row["net_revenue"] * 100})
        cost_chart = px.bar(
            pd.DataFrame(cost_long), x="channel", y="pct_revenue", color="cost", barmode="stack",
            color_discrete_sequence=["#334155", "#0EA5E9", "#F59E0B", "#8B5CF6", "#10B981"],
            labels={"channel": "Channel / 渠道", "pct_revenue": "% of Revenue / 收入占比", "cost": "Cost / 成本"},
        )
        cost_chart.update_layout(title="Cost per $100 Revenue / 每百美元收入成本", legend_title="")
        cost_chart.update_yaxes(ticksuffix="%")
        st.plotly_chart(style_chart(cost_chart, 365), use_container_width=True, config={"displayModeBar": False})

    section_title("Inventory Risk Worklist", "库存风险清单", "Prioritize low-turn, low-margin SKUs for action", "优先治理低周转、低毛利 SKU")
    sku["risk_score"] = sku["inventory_days"].clip(upper=365) / 365 * 60 + (40 - sku["gross_margin"]).clip(lower=0) / 40 * 40
    risk = sku.sort_values("risk_score", ascending=False).head(20).copy()
    risk["Action / 建议"] = risk.apply(
        lambda r: "Markdown & reduce PO / 降价并减少采购" if r["inventory_days"] > 180 else ("Review pricing / 复核定价" if r["gross_margin"] < 25 else "Monitor / 持续观察"), axis=1
    )
    risk_display = risk[["sku", "product", "category", "net_revenue", "gross_margin", "inventory_value", "inventory_days", "turnover", "Action / 建议"]].rename(
        columns={"sku": "SKU", "product": "Product / 产品", "category": "Category / 品类", "net_revenue": "Revenue / 收入", "gross_margin": "GM% / 毛利率", "inventory_value": "Inventory / 库存金额", "inventory_days": "Days / 库存天数", "turnover": "Turns / 周转"}
    )
    st.dataframe(
        risk_display, use_container_width=True, hide_index=True, height=405,
        column_config={
            "Revenue / 收入": st.column_config.NumberColumn(format="$%,.0f"), "GM% / 毛利率": st.column_config.NumberColumn(format="%.1f%%"),
            "Inventory / 库存金额": st.column_config.NumberColumn(format="$%,.0f"), "Days / 库存天数": st.column_config.NumberColumn(format="%.0f"),
            "Turns / 周转": st.column_config.NumberColumn(format="%.2fx"),
        },
    )
    st.download_button("Download Risk Worklist / 下载风险清单", risk_display.to_csv(index=False).encode("utf-8-sig"), "inventory_risk_worklist.csv", "text/csv")


def scenario_page(df: pd.DataFrame) -> None:
    hero(
        "WHAT-IF MODEL · 情景模型",
        "Turn analysis into a CFO decision / 将分析转化为 CFO 决策",
        "Simulate price, fees, returns, freight, tariffs and marketing—then quantify the profit bridge · 模拟价格、平台费、退货、运费、关税及营销变化，并量化利润影响",
    )
    section_title("Scenario Assumptions", "情景假设", "Adjust the levers to test management actions", "调整关键变量，检验管理行动")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="scenario-panel"><h4>Commercial / 商业</h4><p>Pricing and demand response / 定价及需求反应</p>', unsafe_allow_html=True)
        price_change = st.slider("Price change / 售价变化", -5.0, 10.0, 3.0, 0.5, format="%.1f%%")
        elasticity = st.slider("Price elasticity / 价格弹性", -2.0, -0.2, -1.2, 0.1)
        return_change = st.slider("Return-rate change / 退货率变化", -5.0, 3.0, -1.0, 0.5, format="%.1f pp")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="scenario-panel"><h4>Channel / 渠道</h4><p>Fees and demand generation / 费率及获客投入</p>', unsafe_allow_html=True)
        fee_change = st.slider("Platform-fee change / 平台费率变化", -5.0, 3.0, -2.0, 0.5, format="%.1f pp")
        marketing_change = st.slider("Marketing spend / 营销费用变化", -25.0, 25.0, 0.0, 5.0, format="%.0f%%")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="scenario-panel"><h4>Supply Chain / 供应链</h4><p>Landed-cost sensitivity / 到岸成本敏感性</p>', unsafe_allow_html=True)
        freight_change = st.slider("Freight cost / 运费变化", -25.0, 25.0, -10.0, 5.0, format="%.0f%%")
        tariff_change = st.slider("Tariff cost / 关税变化", -25.0, 25.0, 0.0, 5.0, format="%.0f%%")
        st.markdown("</div>", unsafe_allow_html=True)

    base = df[["gross_sales", "discount", "returns", "net_revenue", "product_cost", "freight", "tariff", "platform_fee", "marketing_spend", "gross_profit", "contribution_profit", "units"]].sum()
    price_multiplier = 1 + price_change / 100
    volume_multiplier = max(0.65, 1 + elasticity * price_change / 100)
    base_pre_return = base["gross_sales"] - base["discount"]
    base_return_rate = base["returns"] / base_pre_return if base_pre_return else 0
    scenario_pre_return = base_pre_return * price_multiplier * volume_multiplier
    net_revenue_before_return_action = scenario_pre_return * (1 - base_return_rate)
    scenario_return_rate = max(0, base_return_rate + return_change / 100)
    scenario_returns = scenario_pre_return * scenario_return_rate
    scenario_revenue = scenario_pre_return - scenario_returns
    scenario_product_cost = base["product_cost"] * volume_multiplier
    scenario_freight = base["freight"] * volume_multiplier * (1 + freight_change / 100)
    scenario_tariff = base["tariff"] * volume_multiplier * (1 + tariff_change / 100)
    base_fee_rate = base["platform_fee"] / base["net_revenue"] if base["net_revenue"] else 0
    scenario_fee = scenario_revenue * max(0, base_fee_rate + fee_change / 100)
    scenario_marketing = base["marketing_spend"] * (1 + marketing_change / 100)
    scenario_gp = scenario_revenue - scenario_product_cost - scenario_freight - scenario_tariff
    scenario_cp = scenario_gp - scenario_fee - scenario_marketing
    base_gm = base["gross_profit"] / base["net_revenue"] * 100 if base["net_revenue"] else 0
    scenario_gm = scenario_gp / scenario_revenue * 100 if scenario_revenue else 0

    section_title("Scenario Impact", "情景影响", "Compared with the selected-period baseline", "对比所选期间基准")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("Net Revenue", "净收入", money(scenario_revenue), pct_change(scenario_revenue, base["net_revenue"]), "vs baseline / 对比基准", "↗")
    with k2:
        metric_card("Gross Margin", "毛利率", f"{scenario_gm:.1f}%", scenario_gm - base_gm, "vs baseline / 对比基准", "◎", pp=True)
    with k3:
        metric_card("Contribution Profit", "贡献利润", money(scenario_cp), pct_change(scenario_cp, base["contribution_profit"]), "vs baseline / 对比基准", "◇")
    with k4:
        metric_card("Volume", "销量", f"{volume_multiplier * 100:.1f}%", (volume_multiplier - 1) * 100, "of baseline / 相对基准", "◉")

    price_volume_impact = net_revenue_before_return_action - base["net_revenue"]
    return_impact = scenario_revenue - net_revenue_before_return_action
    cost_impact = base["product_cost"] - scenario_product_cost
    freight_impact = base["freight"] - scenario_freight
    tariff_impact = base["tariff"] - scenario_tariff
    fee_impact = base["platform_fee"] - scenario_fee
    marketing_impact = base["marketing_spend"] - scenario_marketing

    section_title("Profit Bridge & P&L", "利润桥与损益表", "Explain exactly how the scenario creates or destroys value", "清晰解释情景如何创造或损耗价值")
    left, right = st.columns([1.45, 1])
    with left:
        scenario_bridge = go.Figure(go.Waterfall(
            measure=["absolute", "relative", "relative", "relative", "relative", "relative", "relative", "relative", "total"],
            x=["Base Profit<br>基准利润", "Price & Volume<br>价格及销量", "Returns<br>退货", "Product Cost<br>产品成本", "Freight<br>运费", "Tariffs<br>关税", "Platform Fees<br>平台费", "Marketing<br>营销", "Scenario Profit<br>情景利润"],
            y=[base["contribution_profit"], price_volume_impact, return_impact, cost_impact, freight_impact, tariff_impact, fee_impact, marketing_impact, 0],
            connector={"line": {"color": "#CBD5E1"}}, increasing={"marker": {"color": COLORS["green"]}},
            decreasing={"marker": {"color": COLORS["red"]}}, totals={"marker": {"color": COLORS["ink"]}}, hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
        ))
        scenario_bridge.update_layout(title="Contribution Profit Bridge / 贡献利润桥")
        scenario_bridge.update_yaxes(tickprefix="$", tickformat="~s")
        st.plotly_chart(style_chart(scenario_bridge, 390), use_container_width=True, config={"displayModeBar": False})
    with right:
        pnl = pd.DataFrame({
            "P&L / 损益项目": ["Net Revenue / 净收入", "Product Cost / 产品成本", "Freight / 运费", "Tariffs / 关税", "Gross Profit / 毛利", "Platform Fees / 平台费", "Marketing / 营销", "Contribution Profit / 贡献利润"],
            "Baseline / 基准": [base["net_revenue"], -base["product_cost"], -base["freight"], -base["tariff"], base["gross_profit"], -base["platform_fee"], -base["marketing_spend"], base["contribution_profit"]],
            "Scenario / 情景": [scenario_revenue, -scenario_product_cost, -scenario_freight, -scenario_tariff, scenario_gp, -scenario_fee, -scenario_marketing, scenario_cp],
        })
        pnl["Variance / 差异"] = pnl["Scenario / 情景"] - pnl["Baseline / 基准"]
        st.dataframe(
            pnl, use_container_width=True, hide_index=True, height=390,
            column_config={
                "Baseline / 基准": st.column_config.NumberColumn(format="$%,.0f"), "Scenario / 情景": st.column_config.NumberColumn(format="$%,.0f"),
                "Variance / 差异": st.column_config.NumberColumn(format="$%,.0f"),
            },
        )

    section_title("Decision Recommendation", "决策建议", "Translate model output into management action", "将模型结果转化为管理行动")
    profit_change = scenario_cp - base["contribution_profit"]
    recommendation = "Proceed with a controlled pilot / 建议开展小范围试点" if profit_change > 0 else "Revise assumptions before rollout / 建议调整假设后再推进"
    action_1 = f"A {price_change:+.1f}% price move with elasticity {elasticity:.1f} changes modeled volume by {(volume_multiplier - 1) * 100:+.1f}%. / 售价变化 {price_change:+.1f}%，在弹性 {elasticity:.1f} 下，模拟销量变化 {(volume_multiplier - 1) * 100:+.1f}%。"
    action_2 = f"Fee and return actions contribute {money(fee_impact + return_impact)} to the profit bridge. / 平台费与退货改善对利润桥贡献 {money(fee_impact + return_impact)}。"
    action_3 = f"Scenario contribution profit changes by {money(profit_change)}; monitor weekly by SKU and channel. / 情景贡献利润变化 {money(profit_change)}；建议按 SKU 与渠道每周跟踪。"
    st.markdown(
        f'<div class="decision"><b>{recommendation}</b><p>{action_1}</p></div><div class="summary-grid">'
        f'<div class="summary-card"><div class="summary-num">A</div><b>Channel economics / 渠道经济性</b><p>{action_2}</p></div>'
        f'<div class="summary-card"><div class="summary-num">B</div><b>Profit guardrail / 利润护栏</b><p>{action_3}</p></div>'
        f'<div class="summary-card"><div class="summary-num">C</div><b>Test design / 测试设计</b><p>Run a 4-week SKU-level pilot with a control group; stop if volume loss exceeds the modeled guardrail.<br>开展四周 SKU 级对照试验；若销量损失超过模型护栏，则停止推广。</p></div></div>',
        unsafe_allow_html=True,
    )


def data_quality_page(result: dict) -> None:
    stats = result.get("stats", {})
    sources = result.get("sources", pd.DataFrame())
    issues = result.get("issues", pd.DataFrame())
    coverage = result.get("coverage", pd.DataFrame())
    canonical = result.get("canonical", pd.DataFrame())
    staging = result.get("staging", pd.DataFrame())
    hero(
        "DATA INTAKE & CONTROL · 数据接入与控制",
        "Multi-file Data Intake & Quality / 多文件数据接入与质量",
        "CSV and Excel files from different teams and periods are mapped, cleaned, reconciled and traced before financial analysis · 对不同部门和期间的 CSV 与 Excel 报表先完成映射、清洗、勾稽和血缘记录，再进入财务分析",
    )

    section_title("Independent GL Reconciliation", "独立总账对账",
                  "Not supplied is not a pass", "未提供总账数据不等于对账通过")
    gl_status = result.get("gl_status", "NOT SUPPLIED / 尚未提供")
    st.write(f"**GL Status / 对账状态: {gl_status}**")
    gl_recon = result.get("gl_recon")
    if isinstance(gl_recon, pd.DataFrame):
        st.dataframe(gl_recon, use_container_width=True, hide_index=True)
    else:
        st.caption("Upload an independent monthly GL control file in the sidebar to compare revenue, COGS and ending inventory. / 在侧边栏上传独立月度总账控制数，核对收入、成本与期末库存。")

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        metric_card("Files", "文件数", f"{stats.get('files', 0):,}", 0, "uploaded / 已上传", "▤")
    with k2:
        metric_card("Tables", "工作表数", f"{stats.get('tables', 0):,}", 0, "sheets detected / 已识别", "▦")
    with k3:
        metric_card("Raw Rows", "原始行数", f"{stats.get('raw_rows', 0):,}", 0, "before cleaning / 清洗前", "≣")
    with k4:
        metric_card("Clean Rows", "清洗后行数", f"{stats.get('clean_rows', 0):,}", 0, "standardized / 已标准化", "✓")
    with k5:
        metric_card("Analysis-ready", "可分析行数", f"{stats.get('analysis_rows', 0):,}", 0, f"{stats.get('issues', 0)} issues / 个问题", "◎")

    section_title("Processing Steps", "处理步骤", "The source layer remains separate from the analytical output", "原始来源层与分析输出层保持分离")
    p1, p2, p3, p4 = st.columns(4)
    steps = [
        (p1, "01", "Read files / 读取文件", "CSV encodings, delimiters and every Excel worksheet are detected.<br>识别 CSV 编码和分隔符，并读取 Excel 全部工作表。"),
        (p2, "02", "Map fields / 字段映射", "Chinese and English aliases map to one finance schema.<br>中英文字段别名映射至统一财务口径。"),
        (p3, "03", "Clean & reshape / 清洗与重塑", "Headers, dates, currency, totals, duplicates and wide monthly reports are standardized.<br>标准化表头、日期、金额、合计行、重复行和月度宽表。"),
        (p4, "04", "Join & control / 整合与控制", "Exact period, SKU and channel keys combine sources; missing prerequisites remain unavailable.<br>按期间、SKU 和渠道精确整合；缺少前提的数据保持不可用。"),
    ]
    for column, number, title, note in steps:
        with column:
            st.markdown(f'<div class="summary-card"><div class="summary-num">{number}</div><b>{title}</b><p>{note}</p></div>', unsafe_allow_html=True)

    section_title("Source Lineage", "数据血缘", "One row per uploaded file and worksheet", "每个上传文件及工作表保留一条来源记录")
    if sources.empty:
        st.info("Upload CSV or Excel files to build source lineage. / 请上传 CSV 或 Excel 文件以生成数据血缘。")
    else:
        st.dataframe(sources, use_container_width=True, hide_index=True, height=min(430, 72 + len(sources) * 35))

    section_title("Field Coverage", "字段覆盖", "Required fields must be present before profit metrics are calculated", "利润指标计算前必须具备所需字段")
    if coverage.empty:
        st.warning("No recognized fields are available. / 暂无已识别字段。")
    else:
        required = ["date", "sku", "channel", "gross_sales", "discount", "returns", "net_revenue", "product_cost", "freight", "tariff", "platform_fee", "marketing_spend", "inventory_value"]
        coverage_view = coverage[coverage["Field / 字段"].isin(required)].copy()
        coverage_view["Coverage % / 覆盖率"] = coverage_view["Row Coverage / 行覆盖率"] * 100
        coverage_view = coverage_view.sort_values("Coverage % / 覆盖率")
        coverage_chart = px.bar(
            coverage_view, x="Coverage % / 覆盖率", y="Field / 字段", orientation="h", color="Coverage % / 覆盖率",
            color_continuous_scale=["#FEE2E2", "#FEF3C7", "#DCFCE7"], text="Coverage % / 覆盖率",
        )
        coverage_chart.update_traces(texttemplate="%{text:.0f}%", textposition="outside", hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>")
        coverage_chart.update_layout(title="Canonical Field Coverage / 标准字段覆盖率", coloraxis_showscale=False)
        coverage_chart.update_xaxes(ticksuffix="%", range=[0, 108])
        st.plotly_chart(style_chart(coverage_chart, 410), use_container_width=True, config={"displayModeBar": False})

    section_title("Issues & Required Actions", "问题与必需操作", "Critical issues block affected rows from financial analysis", "严重问题会阻止受影响记录进入财务分析")
    if issues.empty:
        st.success("No data-quality issues detected. / 未发现数据质量问题。")
    else:
        severity_order = {"Critical / 严重": 0, "Warning / 警告": 1, "Info / 信息": 2}
        issue_view = issues.copy()
        issue_view["_order"] = issue_view["Severity / 严重性"].map(severity_order).fillna(9)
        issue_view = issue_view.sort_values(["_order", "Source / 来源"]).drop(columns="_order")
        st.dataframe(issue_view, use_container_width=True, hide_index=True, height=min(450, 72 + len(issue_view) * 35))
        st.download_button("Download Issue Log / 下载问题清单", issue_view.to_csv(index=False).encode("utf-8-sig"), "data_quality_issues.csv", "text/csv")

    section_title("Canonical Data Preview", "标准数据预览", "Cleaned values with source metadata and analysis status", "清洗后数据包含来源信息和可分析状态")
    if canonical.empty:
        st.warning("No canonical records were produced. Resolve the critical issues above. / 尚未生成标准数据，请先解决以上严重问题。")
    else:
        display_columns = [column for column in ["date", "sku", "product", "category", "channel", "source_department", "net_revenue", "product_cost", "freight", "tariff", "platform_fee", "marketing_spend", "inventory_value", "analysis_ready", "source_file"] if column in canonical]
        preview = canonical[display_columns].copy().sort_values("date", ascending=False).head(500)
        st.dataframe(
            preview,
            use_container_width=True,
            hide_index=True,
            height=410,
            column_config={
                "date": st.column_config.DateColumn("Period / 期间", format="MMM YYYY"),
                "analysis_ready": st.column_config.CheckboxColumn("Ready / 可分析"),
                "net_revenue": st.column_config.NumberColumn("Net Revenue / 净收入", format="$%,.0f"),
                "product_cost": st.column_config.NumberColumn("Product Cost / 产品成本", format="$%,.0f"),
                "inventory_value": st.column_config.NumberColumn("Inventory / 库存金额", format="$%,.0f"),
            },
        )
        st.download_button("Download Cleaned Data / 下载清洗后数据", canonical.to_csv(index=False).encode("utf-8-sig"), "cleaned_finance_data.csv", "text/csv")

    section_title("Data Governance Rules", "数据治理规则", "Controls applied before management reporting", "进入管理报表前执行的控制")
    st.markdown(
        '<div class="summary-grid">'
        '<div class="summary-card"><div class="summary-num">A</div><b>No silent zeroes / 缺失值不默认为零</b><p>Missing cost or period fields remain unavailable and are listed as issues.<br>缺少成本或期间字段时保持不可用，并列入问题清单。</p></div>'
        '<div class="summary-card"><div class="summary-num">B</div><b>Exact join keys / 精确连接键</b><p>Department reports combine only on matching period, SKU and channel keys. No allocation is applied without an approved rule.<br>部门报表仅按相同期间、SKU 和渠道整合；未经批准不自动分摊。</p></div>'
        '<div class="summary-card"><div class="summary-num">C</div><b>Traceable outputs / 输出可追溯</b><p>Every standardized record retains its source file, worksheet and department.<br>每条标准记录保留来源文件、工作表和部门信息。</p></div>'
        '</div>',
        unsafe_allow_html=True,
    )




