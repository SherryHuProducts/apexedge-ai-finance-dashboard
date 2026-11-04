"""Bilingual executive reporting surfaces. All metrics derive from uploaded canonical data."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from business_performance import period_rows, financial_period, previous_period


def _total(frame: pd.DataFrame, key: str) -> float | None:
    if frame.empty or key not in frame or frame[key].isna().any():
        return None
    return float(pd.to_numeric(frame[key], errors="coerce").sum())


def _pct(num: float | None, den: float | None) -> float | None:
    return None if num is None or den is None or den == 0 else num / den * 100


def _money(value: float | None) -> str:
    symbol = st.session_state.get("olx_currency_symbol", "¤")
    return "N/A" if value is None else f"{symbol}{value:,.0f}"


def _rate(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def _select(frame: pd.DataFrame, key: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    months = sorted(pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp().dropna().unique(), reverse=True)
    if not months:
        return frame.iloc[0:0], frame.iloc[0:0], frame.iloc[0:0]
    a, b, c = st.columns(3)
    kind = a.selectbox("Reporting period / 报告周期", ["Month", "Quarter", "Year"], key=key+"kind")
    mode = b.selectbox("Compare with / 对比基准", ["Previous Period", "Prior Year"], key=key+"mode")
    last = pd.Timestamp(c.selectbox("As of / 截至", months, key=key+"last", format_func=lambda d:pd.Timestamp(d).strftime("%b %Y")))
    start, end = financial_period(last,kind)
    end = min(end,last)
    ps, pe = previous_period(start,end,mode)
    st.caption(f"{start:%Y-%m} — {end:%Y-%m} · {mode}: {ps:%Y-%m} — {pe:%Y-%m} · PROVISIONAL unless independently reconciled")
    current = period_rows(frame,start,end)
    previous = period_rows(frame,ps,pe)
    return current, previous, frame


def _margin(frame: pd.DataFrame) -> float | None:
    return _pct(_total(frame,"gross_profit"), _total(frame,"net_revenue"))


def _delta(current: float | None, previous: float | None, percent_points: bool = False) -> str | None:
    if current is None or previous is None:
        return None
    diff = current - previous
    return f"{diff:+.1f} pp" if percent_points else _money(diff)


def _leaders(frame: pd.DataFrame, field: str, metric: str, limit: int = 10) -> pd.DataFrame:
    if field not in frame or metric not in frame:
        return pd.DataFrame()
    available = frame.dropna(subset=[field, metric]).copy()
    if available.empty:
        return pd.DataFrame()
    summary = available.groupby(field,dropna=False).agg(
        revenue=("net_revenue", lambda s:s.sum(min_count=1)),
        value=(metric,lambda s:s.sum(min_count=1)),
    ).reset_index()
    summary["margin_pct"] = summary["value"] / summary["revenue"].where(summary["revenue"] != 0) * 100
    return summary.sort_values("value",ascending=False).head(limit)


def overview(data: pd.DataFrame | None, role: str) -> None:
    st.title("Executive Overview / 经营总览")
    st.caption("Three executive questions: profitability, direction and economic concentration / 盈利、趋势与收入成本结构")
    if data is None or data.empty:
        st.info("No validated reporting records yet / 暂无有效数据，请先在 ERP Integration 导入财务摘要。")
        return
    cur, prior, _ = _select(data,"overview_")
    if cur.empty:
        st.warning("No data in the selected reporting period / 所选期间无数据")
        return
    revenue = _total(cur,"net_revenue")
    contribution = _total(cur,"contribution_profit")
    net_income = _total(cur,"net_income")
    margin = _margin(cur)
    prev_margin = _margin(prior)
    st.subheader("01 · Are we profitable? / 总体盈利还是亏损？")
    a,b,c = st.columns(3)
    a.metric("Revenue / 收入",_money(revenue),_delta(revenue,_total(prior,"net_revenue")))
    b.metric("Gross Margin / 毛利率",_rate(margin),_delta(margin,prev_margin,True))
    c.metric("Net Profit / 净利润",_money(net_income),_delta(net_income,_total(prior,"net_income")))
    if net_income is None:
        st.caption("Net profit is not supplied. Contribution profit is shown separately; shared overhead and taxes are not assumed / 缺少净利润口径，不以贡献利润替代。")
        st.metric("Contribution Profit / 贡献利润（如可计算）",_money(contribution))
    elif net_income < 0:
        st.error("Net loss in the selected period / 本期净亏损。")
    st.subheader("02 · Improving or declining? / 利润率上升还是下降？")
    if margin is None or prev_margin is None:
        st.info("Two comparable periods with complete gross-profit inputs are required / 需要两个期间的完整毛利数据。")
    else:
        change = margin-prev_margin
        st.write(f"Gross margin {'increased' if change > 0 else 'decreased' if change < 0 else 'was unchanged'} by **{abs(change):.1f} percentage points** / 毛利率{'上升' if change>0 else '下降' if change<0 else '持平'} {abs(change):.1f} 个百分点。")
    st.subheader("03 · Where does the money come from and go? / 收入与成本集中在哪里？")
    left,right=st.columns(2)
    with left:
        if "channel" in cur:
            channels=cur.groupby("channel")["net_revenue"].sum(min_count=1).sort_values(ascending=False)
            st.caption("Revenue by channel / 渠道收入")
            st.bar_chart(channels)
        else: st.info("Channel dimension unavailable / 缺少渠道维度")
    with right:
        cost_labels={"product_cost":"COGS / 产品成本","freight":"Freight / 运费",
                     "tariff":"Tariff / 关税","platform_fee":"Platform Fees / 平台费",
                     "marketing_spend":"Advertising / 广告费"}
        rows=[{"Cost / 费用":name,"Amount / 金额":_total(cur,key)}
              for key,name in cost_labels.items() if _total(cur,key) is not None]
        if rows:
            costs=pd.DataFrame(rows).set_index("Cost / 费用")["Amount / 金额"]
            st.caption("Recognized cost composition / 已识别成本构成")
            st.bar_chart(costs)
            st.dataframe(pd.DataFrame({"Cost":costs.index,"Amount":costs.values,
                                       "% of revenue":[_pct(v,revenue) for v in costs.values]}),
                         hide_index=True,use_container_width=True)
        else: st.info("Costs not supplied / 尚未提供成本")
    st.caption("Financial status / 财务状态: " + str(st.session_state.get("olx_gl","NOT SUPPLIED")) +
               ". Without an independent month-end GL control, figures are PROVISIONAL.")


def matrix(data: pd.DataFrame | None, role: str) -> None:
    st.title("Performance Matrix / 渠道、品类与 SKU 经营分析")
    st.caption("Revenue, gross and contribution economics by business dimension / 多维收入、毛利与贡献利润")
    if data is None or data.empty:
        st.info("Load validated data from ERP Integration / 请先导入有效数据")
        return
    cur, _, _ = _select(data,"matrix_")
    if cur.empty:
        return st.info("No records in selected period / 所选期间无记录")
    dim=st.selectbox("Breakdown / 分析维度",["channel","category","sku"],
                     format_func=lambda x:{"channel":"Channel / 渠道","category":"Category / 品类","sku":"SKU / 产品"}[x])
    if dim not in cur or (cur[dim].astype(str).isin(("UNSPECIFIED","Unspecified")).all()):
        return st.warning("Requested dimension unavailable in source data / 来源文件缺少此维度。")
    metrics={"net_revenue":"Revenue / 收入","gross_profit":"Gross Profit / 毛利",
             "contribution_profit":"Contribution Profit / 贡献利润","net_income":"Net Income / 净利润"}
    available=[k for k in metrics if _total(cur,k) is not None]
    if not available:
        return st.info("No complete numeric metrics / 缺少有效财务指标")
    selected=st.selectbox("Rank by / 排序指标",available,format_func=lambda k:metrics[k])
    wide=cur.groupby(dim,dropna=False).agg(**{
        k:(k,lambda s:s.sum(min_count=1)) for k in available
    }).reset_index()
    if "gross_profit" in wide and "net_revenue" in wide:
        wide["Gross Margin % / 毛利率"]=wide["gross_profit"] / wide["net_revenue"].where(wide["net_revenue"]!=0) * 100
    if "contribution_profit" in wide and "net_revenue" in wide:
        wide["Contribution Margin % / 贡献利润率"]=wide["contribution_profit"] / wide["net_revenue"].where(wide["net_revenue"]!=0) * 100
    wide=wide.sort_values(selected,ascending=False)
    st.subheader("Ranking & comparison / 排名与对比")
    st.bar_chart(wide.set_index(dim)[selected].head(20))
    st.dataframe(wide,hide_index=True,use_container_width=True)
    st.subheader("Most and least profitable / 盈利最佳与最差")
    if "contribution_profit" in wide:
        rank="contribution_profit"
    elif "gross_profit" in wide:
        rank="gross_profit"
    else:
        rank=None
    if rank:
        sorted_profit=wide.sort_values(rank,ascending=False)
        a,b=st.columns(2)
        a.caption("Highest / 盈利最佳")
        a.dataframe(sorted_profit.head(5),hide_index=True,use_container_width=True)
        b.caption("Lowest / 盈利最差")
        b.dataframe(sorted_profit.tail(5).sort_values(rank),hide_index=True,use_container_width=True)
    else:
        st.info("Profitability ranking needs cost data; revenue ranking alone is not profitability / 缺少成本，不能用收入排名冒充盈利排名。")
    st.caption("Net income by SKU/channel requires an approved allocation policy; otherwise only gross/contribution economics are comparable.")


def cash_cost(data: pd.DataFrame | None, role: str) -> None:
    st.title("Cash & Cost / 现金流与成本")
    st.caption("Cash evidence, cost structure and allocation gaps / 现金凭证、成本结构与未分配费用")
    if data is None or data.empty:
        return st.info("No source data / 暂无数据")
    cur, prior, _ = _select(data,"cash_")
    if cur.empty:
        return st.info("No records for period / 本期无记录")
    inflow=_total(cur,"cash_inflow")
    outflow=_total(cur,"cash_outflow")
    settled=_total(cur,"settlement_cash")
    a,b,c=st.columns(3)
    a.metric("Cash inflows / 现金流入",_money(inflow))
    b.metric("Cash outflows / 现金流出",_money(outflow))
    c.metric("Net cash movement / 净现金变化",_money(inflow-outflow) if inflow is not None and outflow is not None else "N/A")
    if settled is not None:
        st.metric("Marketplace settled cash / 平台已结算现金（非全部现金流）",_money(settled))
    if inflow is None or outflow is None:
        st.warning("A cash-flow statement cannot be inferred from sales and expense records. Upload bank/AR/AP cash movements or an approved cash-flow summary / 仅凭销售和费用数据无法生成现金流量表。")
    st.subheader("Cost structure / 成本结构")
    rows=[]
    for field,label in [("product_cost","Product COGS"),("freight","Freight"),
                        ("tariff","Tariff"),("platform_fee","Platform Fees"),
                        ("marketing_spend","Advertising")]:
        current=_total(cur,field)
        if current is not None:
            last=_total(prior,field)
            rows.append({"Cost / 成本":label,"Current / 本期":current,
                         "Prior / 上期":last,"Change / 变动":current-last if last is not None else None,
                         "% of revenue / 收入占比":_pct(current,_total(cur,"net_revenue"))})
    if rows:
        costs=pd.DataFrame(rows)
        st.bar_chart(costs.set_index("Cost / 成本")["Current / 本期"])
        st.dataframe(costs,hide_index=True,use_container_width=True)
    else:
        st.info("No cost metrics available / 缺少成本数据")
    st.caption("Shared overhead and allocations not provided remain UNALLOCATED / 未提供的共享费用及分摊保持未分配状态。")


def risk(data: pd.DataFrame | None, role: str) -> None:
    st.title("Risk Monitor / 风险预警")
    st.caption("Editable thresholds, transparent rules and reviewable rows / 可调阈值、确定性规则与明细")
    if data is None or data.empty:
        return st.info("Load records before evaluating thresholds / 请先加载数据")
    a,b=st.columns(2)
    gm_floor=a.number_input("Minimum gross margin % / 毛利率警戒线",min_value=-100.0,max_value=100.0,value=20.0,step=1.0)
    inventory_floor=b.number_input("Minimum inventory units / 库存安全量",min_value=0.0,value=10.0,step=1.0)
    cur,_,_=_select(data,"risk_")
    if cur.empty:
        return st.info("No records in period / 本期无数据")
    dim=st.selectbox("Alert level / 预警对象",["sku","category","channel"],
                     format_func=lambda x:{"sku":"SKU","category":"Category","channel":"Channel"}[x])
    if dim not in cur:
        return st.warning("Alert dimension not supplied / 缺少分组维度")
    columns={k:(k,lambda v:v.sum(min_count=1)) for k in ["net_revenue","gross_profit","inventory_units"] if k in cur}
    grouped=cur.groupby(dim,dropna=False).agg(**columns).reset_index()
    findings=[]
    for _,row in grouped.iterrows():
        key=str(row[dim])
        revenue=row.get("net_revenue")
        profit=row.get("gross_profit")
        inventory=row.get("inventory_units")
        if pd.notna(revenue) and revenue and pd.notna(profit):
            margin=float(profit/revenue*100)
            if margin<gm_floor:
                findings.append({"Entity / 对象":key,"Type / 类型":"Gross margin below threshold / 毛利率过低",
                                 "Observed / 当前":round(margin,2),"Threshold / 阈值":gm_floor,
                                 "Status / 状态":"Open / 待复核"})
        if pd.notna(inventory) and float(inventory)<inventory_floor:
            findings.append({"Entity / 对象":key,"Type / 类型":"Inventory below threshold / 库存不足",
                             "Observed / 当前":float(inventory),"Threshold / 阈值":inventory_floor,
                             "Status / 状态":"Open / 待复核"})
    if findings:
        st.error(f"{len(findings)} alerts / {len(findings)} 项预警")
        st.dataframe(pd.DataFrame(findings),hide_index=True,use_container_width=True)
    else:
        st.success("No triggered alerts on available metrics / 已提供的指标未触发阈值")
    if _total(cur,"gross_profit") is None:
        st.warning("Gross margin alerts unavailable where costs are incomplete / 缺少成本时不能评价毛利率。")
    if _total(cur,"inventory_units") is None:
        st.warning("Inventory alerts unavailable without inventory snapshots / 缺少库存快照时不能评价库存阈值。")
    st.caption("Inventory is a point-in-time balance. Repeated monthly snapshots must not be summed across months. These rules create review alerts, not automatic business actions.")
