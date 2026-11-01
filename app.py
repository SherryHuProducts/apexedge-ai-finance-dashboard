"""OLX — Finance Intelligence. Blank-by-default ERP, reporting and analysis workspace."""
import pandas as pd
import streamlit as st
from data_pipeline import ingest_finance_files
from business_performance import financial_period, previous_period, period_rows, kpis, aggregate_dimension
from gl_reconciliation import parse_gl_control_file, reconcile_gl

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
[data-testid="stAppViewContainer"] {background:#fbfaf7;color:#292620}
[data-testid="stSidebar"] {background:#f3eee6;border-right:1px solid #e5ded4}
html,body,h1,h2,h3,p,div {font-family:'DM Sans',sans-serif}
h1,h2,h3 {color:#27231f!important;letter-spacing:-.025em}
[data-testid="stMetric"] {border:1px solid #e7e1d8;background:#fffefa;border-radius:12px;padding:16px}
.stButton button[kind="primary"] {background:#393631;color:white;border-color:#393631}
</style>
"""

def ready():
    data=st.session_state.get("olx_data")
    return data if isinstance(data,pd.DataFrame) and not data.empty else None

def money(value):
    return "N/A" if value is None or pd.isna(value) else "$"+f"{value:,.0f}"

def empty(message):
    st.info("◇ "+message+" / 等待有效数据。请先进入 ERP Integration 上传文件。")

def selected_data(data, key):
    options=[("channel","Channel / 渠道"),("category","Category / 品类"),
             ("sku","SKU / 产品"),("region","Region / 地区")]
    result=data.copy()
    for col,(field,label) in zip(st.columns(4),options):
        if field in data and data[field].notna().any():
            choices=sorted(data[field].dropna().astype(str).unique())
            selected=col.multiselect(label,choices,key=key+field,placeholder="All / 全部")
            if selected: result=result.loc[result[field].astype(str).isin(selected)]
        else: col.caption(label+" — unavailable")
    return result

def select_period(data,key):
    months=sorted(pd.to_datetime(data["date"]).dt.to_period("M").dt.to_timestamp().dropna().unique(),reverse=True)
    if not months: return None
    a,b,c=st.columns(3)
    interval=a.selectbox("Period / 期间",["Month","Quarter","Year"],key=key+"interval")
    compare=b.selectbox("Comparison / 同比环比",["Previous Period","Prior Year"],key=key+"compare")
    ending=c.selectbox("As of / 截至月份",months,key=key+"end",
                       format_func=lambda v:pd.Timestamp(v).strftime("%b %Y"))
    start,end=financial_period(pd.Timestamp(ending),interval)
    end=min(end,pd.Timestamp(ending))
    prior_start,prior_end=previous_period(start,end,compare)
    st.caption(f"Current {start:%Y-%m} to {end:%Y-%m} · Comparison {prior_start:%Y-%m} to {prior_end:%Y-%m}. Partial periods explicitly shown.")
    return start,end,prior_start,prior_end

def integration():
    st.title("ERP Integration & Data Foundation / ERP 集成与数据基础")
    st.write("Secure extraction → quality validation → canonical mapping → storage → reconciliation → monitored refresh.")
    with st.expander("Integration design & accuracy controls / 如何实现与保证准确性",expanded=True):
        st.markdown("""
**1. Data acquisition / 数据获取:** authorized ERP, OMS, WMS, marketplace,
website, social-commerce and advertising APIs; vendor EDI; controlled file extracts.

**2. Validation / 数据合理性:** required columns, unique keys, date/currency checks,
source totals, missing cost and cutoff validation. Exceptions must block unsafe reporting.

**3. Standardization / 数据标准化:** approved product/SKU/customer/account mappings;
source IDs and original files retained for auditability.

**4. Database / 数据库:** raw and validated staging records; canonical finance facts;
idempotent upserts, record fingerprints, audit events and lineage.

**5. Daily refresh / 每日更新:** a production scheduler would execute authorized
incremental pulls, retries, alerting and backfills. Daily figures remain
**PROVISIONAL**; only controlled month-end numbers may be marked reconciled.

**Delivery status:** This workspace currently implements **uploaded-file validation
and reporting**. Live API/EDI credentials, hosted database and cron automation are
architecture only, not deployed OLX integrations.
""")
    files=st.file_uploader("Source reports / 上传来源文件",type=["csv","tsv","txt","xlsx","xls","xlsm"],
                           accept_multiple_files=True,key="olx_files")
    if st.button("Validate & Load / 验证并加载",type="primary",disabled=not files):
        result=ingest_finance_files(tuple((f.name,f.getvalue()) for f in files))
        frame=result["canonical"]
        valid=frame.loc[frame["analysis_ready"]].copy() if not frame.empty else frame
        st.session_state["olx_data"]=valid
        st.session_state["olx_pipeline"]=result
        st.session_state["olx_gl"]="NOT SUPPLIED"
        st.session_state["olx_gl_table"]=None
        st.success(f"Loaded {len(valid):,} validated records. Review validation findings below.")
    if st.button("Clear workspace / 清空数据"):
        for key in ("olx_data","olx_pipeline","olx_gl","olx_gl_table"):st.session_state.pop(key,None)
        st.rerun()
    result=st.session_state.get("olx_pipeline")
    if result is None:
        empty("No data loaded. Charts and KPIs will not appear until source validation.")
        return
    a,b,c=st.columns(3)
    a.metric("Source Files",result["stats"]["files"])
    b.metric("Analysis-ready Rows",result["stats"]["analysis_rows"])
    c.metric("Validation Issues",result["stats"]["issues"])
    st.subheader("Data Validation / 数据校验")
    if not result["issues"].empty:st.dataframe(result["issues"],hide_index=True,use_container_width=True)
    else:st.success("No ingestion exceptions detected.")
    with st.expander("Source inventory & lineage / 数据来源"):
        st.dataframe(result["sources"],hide_index=True,use_container_width=True)
    data=ready()
    if data is None:return
    st.subheader("GL Reconciliation / 总账勾稽")
    gl_file=st.file_uploader("Independent monthly GL control / 独立月度总账控制数",
                              type=["csv","xlsx"],key="olx_gl_file")
    if st.button("Reconcile / 执行勾稽",disabled=gl_file is None):
        try:
            gl=parse_gl_control_file(gl_file.name,gl_file.getvalue())
            recon=reconcile_gl(data,gl)
            statuses=recon[[c for c in recon if c.endswith(" status")]]
            st.session_state["olx_gl"]="PASS" if statuses.eq("PASS").all().all() else "FAIL"
            st.session_state["olx_gl_table"]=recon
        except (ValueError,KeyError) as exc:
            st.session_state["olx_gl"]="ERROR: "+str(exc)
    st.write("GL control status:",st.session_state.get("olx_gl","NOT SUPPLIED"))
    if st.session_state.get("olx_gl_table") is not None:
        st.dataframe(st.session_state["olx_gl_table"],hide_index=True,use_container_width=True)

def report(role):
    st.title("Financial Reporting / 财务报告")
    st.caption("CFO: P&L controls and completeness. Sales VP: channel and product economics.")
    data=ready()
    if data is None:return empty("No reporting data. Open ERP Integration to load validated files.")
    data=selected_data(data,"rep_")
    periods=select_period(data,"rep_")
    if periods is None:return
    start,end,pstart,pend=periods
    cur=period_rows(data,start,end)
    prior=period_rows(data,pstart,pend)
    if cur.empty:return st.warning("No records for this selection.")
    a,b=kpis(cur),kpis(prior)
    for col,(name,key,is_rate) in zip(st.columns(3),[
        ("Net Revenue","net_revenue",False),("Gross Margin","gross_margin",True),
        ("Contribution Profit","contribution_profit",False)]):
        value=a[key]
        col.metric(name, f"{value*100:.1f}%" if is_rate and value is not None else money(value))
    st.subheader("Current vs Previous / 本期与对比期间")
    stats=[]
    for name,key,rate in [("Net Revenue","net_revenue",False),("Gross Margin","gross_margin",True),
                          ("Contribution Profit","contribution_profit",False),("Units","units",False),
                          ("Return Rate","return_rate",True)]:
        x,y=a[key],b[key]
        fmt=lambda z: "N/A" if z is None else (f"{z*100:.1f}%" if rate else money(z))
        stats.append({"Metric":name,"Current":fmt(x),"Comparison":fmt(y),
                      "Variance":"N/A" if x is None or y is None else (f"{(x-y)*100:+.1f} pp" if rate else money(x-y))})
    st.dataframe(pd.DataFrame(stats),hide_index=True,use_container_width=True)
    st.subheader("Profit & Loss Statement / 利润表")
    lines=[("gross_sales","Gross Sales"),("discount","Discount"),("returns","Returns"),
           ("net_revenue","Net Revenue"),("product_cost","Product COGS"),
           ("freight","Freight"),("tariff","Tariff"),("gross_profit","Gross Profit"),
           ("platform_fee","Platform Fees"),("marketing_spend","Advertising"),
           ("contribution_profit","Contribution Profit")]
    st.dataframe(pd.DataFrame([{"Line Item":label,"Amount":money(float(cur[key].sum()))
        if key in cur and cur[key].notna().all() else "UNAVAILABLE"} for key,label in lines]),
        hide_index=True,use_container_width=True)
    st.warning("Estimates and unallocated shared costs are not inferred. This is operational reporting, "
               "not a GAAP-certified full P&L. Source and GL scope must match.")
    st.write("Independent GL control:",st.session_state.get("olx_gl","NOT SUPPLIED"))
    st.caption("A global GL PASS does NOT certify the selected channel, SKU or period.")
    st.subheader("Performance by Channel / 渠道业绩" if role=="Sales VP" else "Source Detail / 来源追溯")
    grouped=aggregate_dimension(cur,"channel")
    if role=="Sales VP" and not grouped.empty:
        st.bar_chart(grouped.set_index("channel")["net_revenue"])
        st.dataframe(grouped,hide_index=True,use_container_width=True)
    with st.expander("Source records & export / 原始记录与导出",expanded=role=="CFO"):
        fields=[f for f in ["date","channel","sku","region","city","net_revenue","product_cost",
                           "freight","platform_fee","marketing_spend","source_file","source_sheet"] if f in cur]
        st.dataframe(cur[fields].head(1000),hide_index=True,use_container_width=True)
        st.download_button("Export selection / 导出筛选结果",cur[fields].to_csv(index=False),
                           "olx_financial_records.csv",mime="text/csv")

def analyze(role):
    st.title("Analysis & Planning / 分析与规划")
    st.caption("KPI drivers · Monthly variance · Forecasting · Pricing · Scenario analysis")
    data=ready()
    if data is None:return empty("No analytical data. Load sources before selecting KPIs.")
    data=selected_data(data,"ana_")
    periods=select_period(data,"ana_")
    if periods is None:return
    start,end,pstart,pend=periods
    cur=period_rows(data,start,end)
    prior=period_rows(data,pstart,pend)
    if cur.empty:return st.warning("No analysis-ready records for this period.")
    available={"Net Revenue":"net_revenue","Gross Profit":"gross_profit",
               "Contribution Profit":"contribution_profit","Freight":"freight",
               "Platform Fees":"platform_fee","Advertising":"marketing_spend","Returns":"returns"}
    available={label:key for label,key in available.items() if key in cur and cur[key].notna().all()}
    if not available:return st.warning("Missing KPI inputs. No figures inferred.")
    choice=st.selectbox("Analysis KPI / 分析指标",list(available))
    metric=available[choice]
    st.subheader("KPI Trend & Monthly Variance / 趋势与月度差异")
    trend=data.assign(month=pd.to_datetime(data["date"]).dt.to_period("M").dt.to_timestamp()).groupby("month")[metric].sum(min_count=1)
    st.line_chart(trend)
    if not prior.empty and metric in prior and prior[metric].notna().all():
        c,p=float(cur[metric].sum()),float(prior[metric].sum())
        st.metric(choice,money(c),f"{c-p:+,.2f} versus comparison")
    else:st.info("No comparable prior-period data / 缺少可比期间数据")
    st.subheader("Driver Analysis / 驱动因素分析")
    dimensions=[x for x in ("channel","category","sku","region","city","customer_id")
                if x in cur and cur[x].notna().any()]
    if dimensions:
        dimension=st.selectbox("Break down by / 按维度分析",dimensions)
        st.bar_chart(cur.groupby(dimension)[metric].sum(min_count=1).sort_values(ascending=False).head(20))
    st.subheader("Pricing & Scenario / 定价与情景模拟")
    delta=st.slider("Hypothetical price change / 假设价格变动 (%)",-20,20,0)
    if all(x in cur and cur[x].notna().all() for x in ("net_revenue","contribution_profit")):
        base=float(cur["net_revenue"].sum())
        cp=float(cur["contribution_profit"].sum())
        a,b=st.columns(2)
        a.metric("Scenario Revenue",money(base*(1+delta/100)))
        b.metric("Scenario Contribution",money(cp+base*delta/100))
        st.caption("Illustrative only: constant volume, costs, returns and fees. "
                   "No elasticity or causal forecast has been estimated.")
    st.info("AI explanations and causal attributions require verified evidence and human approval. "
            "This page uses deterministic calculations, not unverified LLM conclusions.")
    st.caption("CFO focus: margin, cash and variance controls." if role=="CFO" else
               "Sales VP focus: channel mix, SKU pricing and customer opportunities.")

def cases():
    st.title("Case Studies & Code Lab / 案例与代码演示")
    st.warning("Synthetic cases are isolated from live OLX workspace data.")
    selection=st.selectbox("Demo / 演示",["Multi-Channel Connectors","Master Data Mapping",
                                         "Channel P&L Bridge","Live Pipeline"])
    if selection=="Multi-Channel Connectors":
        from multi_channel_dashboard import multi_channel_page
        multi_channel_page()
    elif selection=="Master Data Mapping":
        from master_data_dashboard import master_data_page
        master_data_page()
    elif selection=="Channel P&L Bridge":
        from channel_pl_dashboard import channel_pl_page
        channel_pl_page()
    else:
        from thin_slice_dashboard import thin_slice_page
        thin_slice_page()

def main():
    st.set_page_config(page_title="OLX · Finance Intelligence",page_icon="◈",layout="wide")
    st.markdown(CSS,unsafe_allow_html=True)
    with st.sidebar:
        st.header("OLX")
        st.caption("Finance Intelligence / 财务智能系统")
        role=st.radio("View As / 角色",["CFO","Sales VP"],horizontal=True)
        page=st.radio("Workspace / 工作模块",["ERP Integration / ERP 集成",
                        "Financial Reporting / 财务报告","Analysis & Planning / 分析与规划"])
        st.divider()
        show_cases=st.toggle("Case Studies & Code / 案例与代码",value=False)
        st.caption("NO DATA / 尚无数据" if ready() is None else f"Validated records: {len(ready()):,}")
    if show_cases:cases()
    elif page.startswith("ERP"):integration()
    elif page.startswith("Financial"):report(role)
    else:analyze(role)

if __name__=="__main__":
    main()
