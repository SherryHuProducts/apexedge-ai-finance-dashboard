"""Streamlit presentation page for simulated multi-channel data connectors."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from multi_channel_connectors import COSTCO_EDI_LIKE, WALMART_RESPONSE, run_demo


SCENARIOS = {
    "Standard / 正常数据": "standard",
    "Repeat upload / 重复上传": "duplicate_upload",
    "Late fee correction / 晚到费用调整": "late_fee_adjustment",
    "Missing SKU / 缺失 SKU": "missing_sku",
    "Settlement mismatch / 结算不一致": "settlement_mismatch",
}


def multi_channel_page() -> None:
    st.title("Multi-Channel Data Connector Demo / 多渠道数据连接器")
    st.info("**SIMULATED CONNECTORS ONLY / 仅模拟连接器** — Walmart-style API JSON and a simplified Costco EDI-like file. No real retailer access, credentials, or production data. / 未连接真实账户。")
    st.caption("Story / 演示主线: Extract → Standardize → Validate → SQLite → Reconcile → Evidence")
    choice = st.selectbox("Test a data condition / 选择场景", list(SCENARIOS))
    if st.button("Run connector pipeline / 执行模拟接入", type="primary"):
        st.session_state["multi_connector_result"] = run_demo(SCENARIOS[choice])
    demo = st.session_state.get("multi_connector_result")
    if demo is None:
        st.caption("Click Run to execute the entire simulated pipeline; results below are not pre-calculated dashboard images.")
        return

    if demo["scenario"] != SCENARIOS[choice]:
        st.warning("The displayed results are from the previous run. Click Run to apply the selected scenario.")
    result = demo["result"]
    left, mid, right = st.columns(3)
    left.metric("Records in database / 入库记录", len(result["rows"]))
    mid.metric("Audit events / 审计事件", result["event_count"])
    right.metric("GL comparison / 总账对比", result["gl_status"])
    st.warning("Finance status: PROVISIONAL / SYNTHETIC. The supplied GL totals are fictional controls, not a closed accounting period.")

    st.subheader("1 · Data Sources / 数据来源与接入状态")
    sources = pd.DataFrame(demo["sources"])
    st.dataframe(sources.rename(columns={
        "channel": "Channel", "source": "Source File", "method": "Transport",
        "records_received": "Received", "last_sync": "Last Run (UTC)",
        "validation": "Validation", "loaded": "Rows Changed",
        "unchanged": "Unchanged", "reconciliation": "GL Status",
    }), hide_index=True, use_container_width=True)

    with st.expander("Inspect raw source formats / 查看原始模拟输入"):
        st.write("Walmart-style response / 模拟 API JSON")
        st.json(WALMART_RESPONSE)
        st.write("Costco EDI-inspired sample (not real X12) / 简化格式")
        st.code(COSTCO_EDI_LIKE, language="text")

    st.subheader("2 · Canonical Records / 统一数据结构")
    fields = ["channel", "record_id", "sku", "net_sales_cents", "fee_actual_cents", "settlement_net_cents", "source_file", "source_row"]
    st.dataframe(pd.DataFrame(result["rows"])[fields] if result["rows"] else pd.DataFrame(columns=fields),
                 hide_index=True, use_container_width=True)

    st.subheader("3 · Finance Controls / 财务控制")
    issues = []
    for signal in result["fee_signals"]:
        issues.append({"type": "Fee policy", "source": signal["source_file"],
                       "row": signal["source_row"], "difference_usd": signal["difference_cents"] / 100,
                       "status": signal["status"]})
    for signal in result["settlement_issues"]:
        issues.append({"type": "Settlement mismatch", "source": signal["source_file"],
                       "row": signal["source_row"], "difference_usd": signal["difference_cents"] / 100,
                       "status": signal["status"]})
    st.dataframe(pd.DataFrame(issues, columns=["type", "source", "row", "difference_usd", "status"]),
                 hide_index=True, use_container_width=True)
    if result["gl_variances"]:
        st.caption("GL variances (USD): " + ", ".join(
            f"{key} = ${value / 100:,.2f}" for key, value in result["gl_variances"].items()))

    st.subheader("4 · AI-ready Evidence / AI 证据包")
    st.json(demo["ai_evidence"])
    st.caption("This is a deterministic evidence packet for optional LLM explanation. No live LLM request is performed here; causes remain unverified.")
    with st.expander("Database changes / 数据变更日志"):
        st.dataframe(pd.DataFrame(demo["audit_events"]), hide_index=True, use_container_width=True)
