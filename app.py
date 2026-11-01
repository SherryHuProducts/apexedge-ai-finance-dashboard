from __future__ import annotations

from datetime import datetime

import streamlit as st

from dashboard_ui import CSS, data_quality_page, executive_page, margin_inventory_page, scenario_page
from data_pipeline import demo_pipeline_result, ingest_finance_files
from finance_data import generate_demo_data
from gl_reconciliation import parse_gl_control_file, reconcile_gl


st.set_page_config(
    page_title="ApexEdge · AI Finance Analyst",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="sidebar-brand"><span class="brand-mark">◈</span>APEXEDGE</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-caption">AI Finance Decision Studio · AI 财务决策平台</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload Reports / 上传报表",
            type=["csv", "tsv", "txt", "xlsx", "xls", "xlsm"],
            accept_multiple_files=True,
            help="Upload multiple files from different teams and periods / 可上传不同部门和期间的多个文件",
        )
        if uploaded_files:
            payloads = tuple((uploaded.name, uploaded.getvalue()) for uploaded in uploaded_files)
            with st.spinner("Reading and cleaning files... / 正在读取并清洗文件..."):
                pipeline_result = ingest_finance_files(payloads)
            canonical = pipeline_result["canonical"]
            data = canonical[canonical["analysis_ready"]].copy() if not canonical.empty else canonical
            stats = pipeline_result["stats"]
            st.caption(f"{stats['files']} files · {stats['tables']} tables · {stats['analysis_rows']:,} analysis-ready rows")
        else:
            demo_data = generate_demo_data()
            pipeline_result = demo_pipeline_result(demo_data)
            data = pipeline_result["canonical"].copy()
            st.caption("Demo case data / 使用演示案例数据")

        gl_file = st.file_uploader(
            "GL Control Totals (optional) / 总账控制数（可选）",
            type=["csv", "xlsx"],
            help="Independent monthly GL totals with date, gl_net_revenue, gl_cogs, gl_inventory_value.",
        )
        pipeline_result["gl_status"] = "NOT SUPPLIED / 尚未提供"
        pipeline_result["gl_recon"] = None
        if gl_file is not None:
            try:
                gl = parse_gl_control_file(gl_file.name, gl_file.getvalue())
                if data.empty:
                    pipeline_result["gl_status"] = "BLOCKED / 无可分析数据"
                else:
                    pipeline_result["gl_recon"] = reconcile_gl(data, gl)
                    statuses = pipeline_result["gl_recon"][[col for col in pipeline_result["gl_recon"].columns if col.endswith(" status")]]
                    pipeline_result["gl_status"] = "PASS / 通过" if statuses.eq("PASS").all().all() else "FAIL / 存在差异"
            except (ValueError, KeyError) as exc:
                pipeline_result["gl_status"] = f"ERROR / 格式错误: {exc}"

        page_options = [
            "Executive Overview / 管理层总览",
            "Margin & Inventory / 毛利与库存",
            "What-if Scenario / 情景模拟",
            "Data Intake & Quality / 数据接入与质量",
        ]
        page = st.radio(
            "Page / 页面",
            page_options,
            index=3 if uploaded_files else 0,
            label_visibility="collapsed",
        )
        st.divider()
        if page != "Data Intake & Quality / 数据接入与质量" and not data.empty:
            min_date = data["date"].min().date()
            max_date = data["date"].max().date()
            selected_dates = st.date_input("Date Range / 日期范围", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                start_date, end_date = selected_dates
            else:
                start_date, end_date = min_date, max_date
            channel_options = sorted(data["channel"].dropna().astype(str).unique())
            category_options = sorted(data["category"].dropna().astype(str).unique())
            department_options = sorted(data["source_department"].dropna().astype(str).unique()) if "source_department" in data else []
            selected_channels = st.multiselect("Channel / 渠道", channel_options, default=channel_options)
            selected_categories = st.multiselect("Category / 品类", category_options, default=category_options)
            selected_departments = st.multiselect("Department / 部门", department_options, default=department_options) if department_options else []
            if page == "Margin & Inventory / 毛利与库存":
                sku_options = sorted(data["sku"].dropna().astype(str).unique())
                selected_skus = st.multiselect("SKU (optional / 可选)", sku_options, default=[])
            else:
                selected_skus = []
        else:
            start_date = end_date = None
            selected_channels = selected_categories = selected_departments = selected_skus = []

        st.divider()
        st.caption("Last refreshed / 最近更新")
        st.markdown(f"**{datetime.now().strftime('%b %d, %Y · %H:%M')}**")

    if page == "Data Intake & Quality / 数据接入与质量":
        data_quality_page(pipeline_result)
        return
    if data.empty:
        st.error("No rows contain all fields required for profit analysis. Open Data Intake & Quality to review missing fields and join keys. / 没有记录同时具备利润分析所需字段，请前往“数据接入与质量”查看缺失字段和连接键。")
        return
    filtered = data[(data["date"].dt.date >= start_date) & (data["date"].dt.date <= end_date) & data["channel"].astype(str).isin(selected_channels) & data["category"].astype(str).isin(selected_categories)].copy()
    if selected_departments:
        filtered = filtered[filtered["source_department"].astype(str).isin(selected_departments)].copy()
    if selected_skus:
        filtered = filtered[filtered["sku"].astype(str).isin(selected_skus)].copy()
    if filtered.empty:
        st.warning("No data matches the filters. / 当前筛选条件下无数据，请调整筛选。")
        return

    if page == "Executive Overview / 管理层总览":
        executive_page(filtered)
    elif page == "Margin & Inventory / 毛利与库存":
        margin_inventory_page(filtered)
    elif page == "What-if Scenario / 情景模拟":
        scenario_page(filtered)


if __name__ == "__main__":
    main()

