"""Three-page OLX executive dashboard; no built-in case data or fictional KPIs."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from business_performance import financial_period, previous_period, period_rows


def value(frame: pd.DataFrame, metric: str) -> float | None:
    if frame.empty or metric not in frame or frame[metric].isna().any():
        return None
    return float(pd.to_numeric(frame[metric], errors="coerce").sum())


def ratio(numer: float | None, denom: float | None) -> float | None:
    return None if numer is None or denom in (None,0) else numer/denom


def money(amount: float | None) -> str:
    symbol=st.session_state.get("olx_currency_symbol","¤")
    return "N/A" if amount is None else f"{symbol}{amount:,.0f}"


def percent(fraction: float | None) -> str:
    return "N/A" if fraction is None else f"{fraction*100:.1f}%"


def change(cur: float | None, prior: float | None, pp: bool=False) -> str | None:
    if cur is None or prior is None: return None
    return f"{(cur-prior)*100:+.1f} pp" if pp else f"{(cur/prior-1)*100:+.1f}%" if prior else None


def scope(frame: pd.DataFrame, prefix: str):
    months=sorted(pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp().dropna().unique(),reverse=True)
    if not months:return frame.iloc[:0],frame.iloc[:0],None
    a,b,c=st.columns([1,1,1])
    gran=a.selectbox("Period / 周期",["Month","Quarter","Year"],key=prefix+"gran")
    comp=b.selectbox("Compare / 对比",["Previous Period","Prior Year"],key=prefix+"comp")
    last=pd.Timestamp(c.selectbox("As of / 截至",months,key=prefix+"month",
                                  format_func=lambda x:pd.Timestamp(x).strftime("%b %Y")))
    start,end=financial_period(last,gran)
    ps,pe=previous_period(start,min(end,last),comp)
    st.caption(f"Current {start:%Y-%m}–{min(end,last):%Y-%m} · Comparison {ps:%Y-%m}–{pe:%Y-%m} · Provisional until independently reconciled")
    return period_rows(frame,start,min(end,last)),period_rows(frame,ps,pe),gran


def _no_data(data):
    if data is None or data.empty:
        st.info("No validated source data. Open Data & System Tools → ERP Integration to upload an approved P&L or sales summary / 请先上传数据。")
        return True
    return False


def _margin(frame):
    return ratio(value(frame,"gross_profit"),value(frame,"net_revenue"))


def _available_rows(frame,dimension):
    if dimension not in frame:return pd.DataFrame()
    subset=frame.loc[~frame[dimension].astype(str).isin(["Unspecified","UNSPECIFIED","nan",""])].copy()
    return subset


def overview(data: pd.DataFrame | None,role: str):
    st.title("Executive Overview / 经营总览")
    st.caption("What happened, what changed, and where to act / 经营结果、变化趋势、核心驱动")
    if _no_data(data):return
    cur,prior,_=scope(data,"ov3_")
    if cur.empty:return st.warning("No records in selected period / 所选期间无数据")
    rev=value(cur,"net_revenue")
    margin=_margin(cur)
    net=value(cur,"net_income")
    ebitda=value(cur,"ebitda")
    st.subheader("01 · Executive Scorecard / 核心经营指标")
    if role=="CFO":
        items=[("Net Revenue / 净收入",money(rev),change(rev,value(prior,"net_revenue"))),
               ("Gross Margin / 毛利率",percent(margin),change(margin,_margin(prior),True)),
               ("EBITDA",money(ebitda),change(ebitda,value(prior,"ebitda"))),
               ("Net Income / 净利润",money(net),change(net,value(prior,"net_income")))]
    else:
        units=value(cur,"units")
        aov=ratio(rev,value(cur,"orders"))
        return_rate=ratio(value(cur,"returns"),value(cur,"gross_sales"))
        items=[("Net Revenue / 净收入",money(rev),change(rev,value(prior,"net_revenue"))),
               ("Gross Margin / 毛利率",percent(margin),change(margin,_margin(prior),True)),
               ("Units / 销售件数",f"{units:,.0f}" if units is not None else "N/A",change(units,value(prior,"units"))),
               ("Return Rate / 退货率",percent(return_rate),change(return_rate,ratio(value(prior,"returns"),value(prior,"gross_sales")),True))]
    for col,(title,metric,delta) in zip(st.columns(4),items):
        col.metric(title,metric,delta=delta)
    if role=="CFO" and net is None:
        st.caption("Net income and EBITDA are displayed only when supplied by an approved P&L; contribution profit is not net income / 未提供时不估算净利润或 EBITDA。")
    st.subheader("02 · Trend & Margin / 收入和毛利趋势")
    monthly=data.copy()
    monthly["month"]=pd.to_datetime(monthly["date"]).dt.to_period("M").dt.to_timestamp()
    trend=monthly.groupby("month").agg(net_revenue=("net_revenue",lambda x:x.sum() if x.notna().all() else float("nan")),
                                        gross_profit=("gross_profit",lambda x:x.sum() if x.notna().all() else float("nan")))
    left,right=st.columns(2)
    with left:
        st.caption("Net Revenue by Month / 月度净收入")
        st.line_chart(trend["net_revenue"])
    with right:
        st.caption("Gross Margin by Month / 月度毛利率")
        margins=trend["gross_profit"]/trend["net_revenue"].where(trend["net_revenue"]!=0)*100
        if margins.notna().any():st.line_chart(margins)
        else:st.info("Gross-profit information not available / 缺少毛利数据")
    st.subheader("03 · Channel Economics & Executive Exceptions / 渠道贡献与重点关注")
    a,b=st.columns([1.25,1])
    with a:
        sub=_available_rows(cur,"channel")
        if not sub.empty:
            channels=sub.groupby("channel")["net_revenue"].sum(min_count=1).sort_values(ascending=False)
            st.bar_chart(channels.head(12))
            top=channels.index[0]
            st.caption(f"Leading revenue channel: {top} / 收入最大渠道")
        else:st.info("No channel breakdown in the selected summary / 汇总文件未提供渠道维度。")
    with b:
        if margin is not None and _margin(prior) is not None and margin<_margin(prior):
            st.warning(f"Gross margin declined {(_margin(prior)-margin)*100:.1f} pp / 毛利率下滑")
        elif margin is not None:
            st.success("No gross-margin decline against the selected comparison / 毛利率未下降")
        else:st.info("Margin variance cannot be verified / 毛利差异不可用")
        if role=="CFO":
            costs=[("Product",value(cur,"product_cost")),("Freight",value(cur,"freight")),
                   ("Tariff",value(cur,"tariff")),("Platform",value(cur,"platform_fee")),
                   ("Advertising",value(cur,"marketing_spend"))]
            known=[{"Cost":k,"% Revenue":round(v/rev*100,1)} for k,v in costs if v is not None and rev]
            if known:st.dataframe(pd.DataFrame(known),hide_index=True,use_container_width=True)
            else:st.caption("Cost mix unavailable / 缺少成本分类")
        else:
            aov=ratio(rev,value(cur,"orders"))
            st.metric("Average Order Value / 客单价",money(aov))
            st.caption("Sales focus: growth, channel mix, returns, pricing / 销售重点：增长、渠道、退货、定价")
    st.caption(f"Independent GL status: {st.session_state.get('olx_gl','NOT SUPPLIED')} · Operational reporting is not a certified financial statement.")


def margin_inventory(data: pd.DataFrame | None,role: str):
    st.title("Margin & Inventory Analysis / 毛利与库存分析")
    st.caption("Find profitable products and inventory risks / 定位高利润产品与库存风险")
    if _no_data(data):return
    cur,_,_=scope(data,"mi3_")
    if cur.empty:return st.warning("No matching records / 所选期间无数据")
    a,b,c=st.columns(3)
    dim=a.selectbox("Analyze by / 分析维度",["channel","category","sku"],key="mi3_dim",
                     format_func=lambda x:{"channel":"Channel / 渠道","category":"Category / 品类","sku":"SKU / 产品"}[x])
    metric_choices={"net_revenue":"Revenue / 收入","gross_profit":"Gross Profit / 毛利",
                    "contribution_profit":"Contribution Profit / 贡献利润"}
    metric=b.selectbox("Ranking metric / 排序指标",list(metric_choices),format_func=lambda x:metric_choices[x])
    floor=c.number_input("Min gross margin alert % / 毛利警戒线",min_value=-100.0,max_value=100.0,value=20.0,step=1.0)
    sub=_available_rows(cur,dim)
    if sub.empty:return st.info("Selected source has no channel/category/SKU detail / 所选来源未提供该分析维度。")
    cols={k:(k,lambda v:v.sum() if v.notna().all() else float("nan"))
          for k in ("net_revenue","gross_profit","contribution_profit","units","product_cost","freight","tariff") if k in sub}
    grouped=sub.groupby(dim,dropna=False).agg(**cols).reset_index()
    grouped["Gross Margin % / 毛利率"]=grouped["gross_profit"]/grouped["net_revenue"].where(grouped["net_revenue"]!=0)*100
    if metric not in grouped or grouped[metric].isna().all():
        st.warning("Selected profitability metric is incomplete; switch to a supported KPI / 当前指标缺少成本数据。")
    else:
        grouped=grouped.sort_values(metric,ascending=False)
        st.subheader("01 · Margin Comparison / 盈利能力对比")
        st.bar_chart(grouped.set_index(dim)[metric].head(20))
        st.dataframe(grouped,hide_index=True,use_container_width=True)
        if metric!="net_revenue":
            left,right=st.columns(2)
            with left:
                st.caption("Top 5 profitable / 盈利前五")
                st.dataframe(grouped.head(5)[[dim,metric]],hide_index=True,use_container_width=True)
            with right:
                st.caption("Bottom 5 / 盈利后五")
                st.dataframe(grouped.tail(5).sort_values(metric)[[dim,metric]],hide_index=True,use_container_width=True)
    st.subheader("02 · Inventory & Pricing Signals / 库存及定价信号")
    x,y=st.columns(2)
    with x:
        months=cur["date"].max()
        snap=cur.loc[cur["date"]==months]
        if "inventory_units" in snap and snap["inventory_units"].notna().any():
            threshold=st.number_input("Minimum stock / 库存安全量",min_value=0.0,value=10.0,step=1.0)
            stock=snap.groupby(dim)["inventory_units"].sum(min_count=1)
            low=stock[stock<threshold]
            st.metric("Low-stock groups / 库存不足对象",len(low))
            if len(low):st.dataframe(low.rename("Inventory Units").reset_index(),hide_index=True,use_container_width=True)
        elif "inventory_days" in snap and snap["inventory_days"].notna().any():
            dio=float(snap["inventory_days"].iloc[0]) if len(snap)==1 else None
            st.metric("Inventory Days (source) / 存货周转天数",f"{dio:.1f}" if dio is not None else "N/A")
        else:st.info("No inventory snapshot or DIO supplied / 缺少库存快照或周转数据")
    with y:
        below=grouped.loc[grouped["Gross Margin % / 毛利率"]<floor,[dim,"Gross Margin % / 毛利率"]].dropna()
        st.metric("Below gross-margin threshold / 低毛利对象",len(below))
        if len(below):st.dataframe(below,hide_index=True,use_container_width=True)
        if role=="Sales VP":
            st.caption("Review discount, returns and price competitiveness before changing prices / 调价前核对促销、退款与竞争力")
        else:
            st.caption("Confirm cost attribution, tariff/freight cutoffs and source controls before approval / 审批前复核成本分摊和截止")
    st.caption("Inventory uses the latest-period snapshot, not a multi-month sum. Without SKU/channel facts, segment comparisons remain unavailable.")


def scenario(data: pd.DataFrame | None,role: str):
    st.title("What-if Scenario / 定价与利润情景模拟")
    st.caption("Price × volume elasticity × fees × returns × tariffs / 定价、销量、费用、退货及关税的联合影响")
    if _no_data(data):return
    cur,_,_=scope(data,"sc3_")
    if cur.empty:return st.warning("No records / 无有效记录")
    rev=value(cur,"net_revenue")
    if rev is None:return st.warning("Net revenue required / 缺少净收入")
    st.subheader("01 · Baseline / 当前基准")
    gp=value(cur,"gross_profit")
    cp=value(cur,"contribution_profit")
    a,b,c=st.columns(3)
    a.metric("Revenue / 净收入",money(rev))
    b.metric("Gross Profit / 毛利",money(gp))
    c.metric("Contribution Profit / 贡献利润",money(cp))
    st.subheader("02 · Assumptions / 假设条件")
    a,b,c=st.columns(3)
    price=a.slider("Price change / 调价 (%)",-20.0,30.0,3.0,0.5)/100
    elasticity=b.slider("Price elasticity / 价格弹性",-3.0,0.0,-1.2,0.1)
    return_delta=c.slider("Extra return rate / 退货率额外变化 (pp)",-5.0,10.0,0.0,0.5)/100
    d,e,f=st.columns(3)
    platform_delta=d.slider("Platform fee rate change / 平台费率变化 (pp)",-5.0,10.0,-2.0,0.5)/100
    tariff_new=e.number_input("New tariff rate on product cost / 新关税率 (%)",
                              min_value=0.0,max_value=100.0,value=15.0,step=1.0)/100
    ad_mode=f.radio("Advertising assumption / 广告假设",["Keep spend / 金额不变","Keep rate / 费率不变"],horizontal=False)
    st.caption("Elasticity and tariff default values are illustrative assumptions, NOT inferred from uploaded records. / 弹性与关税初始值只是情景假设。")
    volume_factor=(1+price)**elasticity
    new_revenue=rev*(1+price)*volume_factor*(1-return_delta)
    st.subheader("03 · Financial Impact / 情景结果")
    left,right,third=st.columns(3)
    left.metric("Scenario Revenue / 情景收入",money(new_revenue),
                f"{(new_revenue/rev-1)*100:+.1f}% vs baseline")
    costs=[value(cur,k) for k in ("product_cost","freight","tariff","platform_fee","marketing_spend")]
    if any(v is None for v in costs):
        right.metric("Scenario Contribution / 情景贡献利润","N/A")
        third.metric("Change in Profit / 利润变化","N/A")
        st.warning("Cost, freight, tariff, platform fee and advertising sources are required for a full profit scenario / 缺少必要成本时不模拟利润。")
        return
    product,freight,tariff,platform,marketing=costs
    new_product=product*volume_factor
    new_freight=freight*volume_factor
    new_tariff=new_product*tariff_new
    new_platform=new_revenue*max(0,platform/rev+platform_delta)
    new_ad=marketing if ad_mode.startswith("Keep spend") else marketing*new_revenue/rev
    scenario_contribution=new_revenue-new_product-new_freight-new_tariff-new_platform-new_ad
    derived_baseline=rev-product-freight-tariff-platform-marketing
    right.metric("Scenario Contribution / 情景贡献利润",money(scenario_contribution))
    third.metric("Incremental Profit / 贡献利润变化",money(scenario_contribution-derived_baseline))
    bridge=pd.DataFrame({
        "Component / 项目":["Revenue / 收入","Product Cost / 商品成本","Freight / 运费",
            "Tariff / 关税","Platform Fee / 平台费","Advertising / 广告费","Contribution / 贡献利润"],
        "Baseline / 基准":[rev,-product,-freight,-tariff,-platform,-marketing,derived_baseline],
        "Scenario / 情景":[new_revenue,-new_product,-new_freight,-new_tariff,-new_platform,-new_ad,scenario_contribution]})
    st.dataframe(bridge,hide_index=True,use_container_width=True)
    st.caption("This is a sensitivity calculation, not a demand forecast. Fixed overhead, tax, inventory constraints and second-order effects are excluded / 这是敏感性分析，不代表需求预测或净利润。")
    st.info("Sales VP: test promotion and pricing decisions. CFO: confirm margin, tariff and fee exposure before approving a change. / 商务决策须经过财务复核。")
