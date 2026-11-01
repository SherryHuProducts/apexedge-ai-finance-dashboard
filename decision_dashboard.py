"""Streamlit decision cockpit: evidence, opt-in AI, human review and session log."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from ai_client import available, generate_explanation
from dashboard_ui import hero, section_title
from decision_engine import detect_signals, evidence_packet, proposal_from_signal


TRANSITIONS = {
    "Proposed": ["Proposed", "Approved", "Rejected"],
    "Approved": ["Approved", "In progress", "Rejected"],
    "In progress": ["In progress", "Completed", "Rejected"],
    "Completed": ["Completed"],
    "Rejected": ["Rejected"],
}


def decision_page(frame: pd.DataFrame, audience: str) -> None:
    hero(
        "EVIDENCE → DECISION → REVIEW · 证据驱动决策",
        f"{audience} Decision Intelligence / 决策智能",
        "Deterministic finance signals first; AI commentary only by explicit opt-in. / 首先验证财务指标，AI 解释需用户主动启用。",
    )
    signals = detect_signals(frame)
    scoped = signals.loc[signals["audience"] == audience].copy() if not signals.empty else signals
    if "decision_records" not in st.session_state:
        st.session_state["decision_records"] = {}
    if "decision_events" not in st.session_state:
        st.session_state["decision_events"] = []

    section_title("Evidence-Based Signals", "基于证据的异常提示",
                  "Signals identify what to inspect, not proven causes", "异常用于确定调查优先级，并不自动证明因果关系")
    if scoped.empty:
        st.success("No signals crossed the configured thresholds / 当前没有指标超过预设异常阈值。")
    else:
        st.dataframe(
            scoped[["severity", "signal", "metric", "observed", "baseline", "delta", "evidence", "suggested_review"]],
            use_container_width=True, hide_index=True,
        )
        chosen_id = st.selectbox("Select a signal / 选择异常", scoped["id"].tolist(),
                                 format_func=lambda i: scoped.loc[scoped["id"] == i, "signal"].iloc[0])
        chosen = scoped.loc[scoped["id"] == chosen_id].iloc[0]
        st.caption(f"Evidence / 计算依据: {chosen['evidence']}")
        if st.button("Create review proposal / 创建待审核建议", key=f"propose_{audience}"):
            if chosen_id not in st.session_state["decision_records"]:
                st.session_state["decision_records"][chosen_id] = proposal_from_signal(chosen)
                st.session_state["decision_events"].append({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "id": chosen_id, "from_status": "", "to_status": "Proposed",
                    "actor": "Demo user", "note": "Evidence-linked review proposal created",
                })
            st.info("Proposal saved in this browser session / 建议已保存到当前会话。")

    section_title("AI Interpretation (Optional)", "AI 解释（可选）",
                  "Aggregated numbers only; no raw reports sent by default",
                  "默认不上传原始财务文件，仅主动确认后发送汇总指标")
    packet = evidence_packet(frame, signals, audience)
    with st.expander("Preview outbound evidence / 查看将发送的汇总数据"):
        st.json(packet)
    if not available():
        st.caption("No OPENAI_API_KEY configured. Rule-based signals remain fully usable. / 未配置 API Key，规则型分析仍可使用。")
    else:
        consent = st.checkbox("I confirm the aggregate evidence may be sent to the OpenAI API / 我确认允许发送以上汇总数据到 OpenAI API", value=False, key=f"ai_consent_{audience}")
        if st.button("Generate AI explanation / 生成 AI 解释", disabled=not consent, key=f"ai_generate_{audience}"):
            try:
                with st.spinner("Generating an evidence-grounded explanation... / 正在生成基于证据的解释..."):
                    result = generate_explanation(packet, audience=audience)
                st.session_state[f"ai_output_{audience}"] = result
            except RuntimeError as exc:
                st.error(f"AI unavailable / AI 服务不可用: {exc}")
        if st.session_state.get(f"ai_output_{audience}"):
            st.markdown(st.session_state[f"ai_output_{audience}"])
            st.warning("AI text is unverified commentary, not an approved decision. / AI 文字并非已验证或获批的财务决策。")

    section_title("Human Decision Review", "人工决策复核",
                  "Review, approve, track and export without changing any ERP or pricing system",
                  "复核、审批、记录和导出；不会修改 ERP 或销售定价")
    records = st.session_state["decision_records"]
    relevant_ids = [key for key, value in records.items() if value["audience"] == audience]
    if not relevant_ids:
        st.info("Create a review proposal from a signal above. / 请先从上方异常创建待审核建议。")
    else:
        selected = st.selectbox("Decision ID / 决策编号", relevant_ids, key=f"decision_select_{audience}")
        record = records[selected]
        st.write(f"**Status / 状态：{record['status']}**")
        with st.form(f"review_form_{audience}_{selected}"):
            status = st.selectbox("Next status / 下一状态", TRANSITIONS[record["status"]])
            owner = st.text_input("Owner / 负责人", value=record["owner"])
            expected = st.text_input("Expected impact (estimate) / 预计影响（估算）", value=record["expected_impact"])
            actual = st.text_input("Actual measured impact / 实际测得影响", value=record["actual_impact"])
            notes = st.text_area("Evidence, test and follow-up notes / 依据、试验及跟进记录", value=record["notes"])
            submitted = st.form_submit_button("Save review / 保存复核")
        if submitted:
            if status in ("Approved", "In progress", "Completed") and not owner.strip():
                st.error("Owner is required for approval or execution. / 审批及执行必须指定负责人。")
            else:
                previous = record["status"]
                record.update(status=status, owner=owner, expected_impact=expected,
                              actual_impact=actual, notes=notes)
                st.session_state["decision_events"].append({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "id": selected, "from_status": previous, "to_status": status,
                    "actor": owner or "Demo user", "note": notes[:240],
                })
                st.success("Review recorded / 复核已记录。")
        st.dataframe(pd.DataFrame([records[i] for i in relevant_ids]), use_container_width=True, hide_index=True)
    events = pd.DataFrame(st.session_state["decision_events"])
    if not events.empty:
        st.download_button("Download audit events / 下载事件日志",
                           events.to_csv(index=False).encode("utf-8-sig"),
                           "decision_events.csv", "text/csv")
    st.caption("MVP scope: records and history are held in Streamlit session state, not durable storage. Export before the session ends. / 当前版本仅会话内保存，结束前请导出日志。")
