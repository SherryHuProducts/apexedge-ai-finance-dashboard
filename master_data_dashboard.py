"""CFO-readable interactive master data mapping review simulation."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from master_data_mapping import SOURCE_RECORDS, run_demo


def master_data_page() -> None:
    st.title("Master Data Mapping & Validation / 主数据映射")
    st.info("SYNTHETIC DEMO / 模拟业务数据。Approval represents a local, auditable demo decision, not an ERP master-data update.")
    st.caption("Walmart + Costco + ERP + Website → Canonical SKU / Customer / Account → Approved or Blocked")
    st.subheader("1 · Raw Cross-System Records / 原始跨系统记录")
    st.dataframe(pd.DataFrame(SOURCE_RECORDS), use_container_width=True, hide_index=True)

    approve = st.checkbox("Approve Website RED-V2 → SKU-RED / 模拟财务审核并批准映射", value=False)
    result = run_demo(resolve_website=approve)
    mapped = result["after"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Mapped records / 已映射记录", len(mapped["ready"]))
    c2.metric("Blocked records / 拦截记录", len(mapped["blocked"]))
    c3.metric("Revenue held from analysis / 暂停分析金额", f"${mapped['blocked_revenue_cents'] / 100:,.2f}")
    st.caption("Amounts held are excluded from approved profitability analysis and reported separately—not treated as zero sales.")

    st.subheader("2 · Data Quality Exceptions / 待审核异常")
    if mapped["issues"]:
        st.dataframe(pd.DataFrame(mapped["issues"]), use_container_width=True, hide_index=True)
    else:
        st.success("All source SKU, customer and account identifiers have approved mappings.")

    st.subheader("3 · Normalized Analytical Records / 统一主数据")
    if mapped["ready"]:
        st.dataframe(pd.DataFrame(mapped["ready"]), hide_index=True, use_container_width=True)
    if mapped["blocked"]:
        with st.expander("Blocked raw records (preserved) / 保留的原始异常记录"):
            st.dataframe(pd.DataFrame(mapped["blocked"]), hide_index=True, use_container_width=True)

    st.subheader("4 · Approval History / 审批记录")
    events = pd.DataFrame(mapped["events"])
    st.dataframe(events.tail(15), hide_index=True, use_container_width=True)
    st.caption("This demo uses a local SQLite mapping registry and human reviewer labels. "
               "Real approval would require authenticated roles, segregation of duties, governed deployment and ERP change control.")
