"""Interview-safe thin vertical slice: source -> SQLite -> controls -> evidence."""
from __future__ import annotations

import json
from io import StringIO

import pandas as pd
import streamlit as st

from ai_client import available, generate_explanation
from thin_slice import AMAZON, B2B, GL_CONTROL, connect, deterministic_explanation, evaluate, evidence_packet, ingest
from evaluate_slice import run_gold_set


def thin_slice_page() -> None:
    st.title("Live Pipeline Demo / 财务数据闭环演示")
    st.caption("Synthetic evidence only · No merchant API connection · No accounting entries posted")
    st.info(
        "Daily operating figures remain PROVISIONAL. The independent GL control below is a "
        "synthetic monthly demonstration, not an actual ERP reconciliation."
    )

    a, b = st.columns(2)
    with a:
        st.subheader("Amazon sample")
        amazon_upload = st.file_uploader("Optional Amazon CSV", type=["csv"], key="thin_amazon")
        amazon_csv = amazon_upload.getvalue().decode("utf-8-sig") if amazon_upload else AMAZON
        st.dataframe(pd.read_csv(StringIO(amazon_csv)), use_container_width=True, hide_index=True)
    with b:
        st.subheader("B2B sample")
        b2b_upload = st.file_uploader("Optional B2B CSV", type=["csv"], key="thin_b2b")
        b2b_csv = b2b_upload.getvalue().decode("utf-8-sig") if b2b_upload else B2B
        st.dataframe(pd.read_csv(StringIO(b2b_csv)), use_container_width=True, hide_index=True)

    supply_gl = st.checkbox("Use independent synthetic GL control totals / 使用模拟总账控制数", value=True)
    backfill = st.checkbox("Simulate late Amazon fee adjustment / 模拟迟到费用更正", value=False)
    if backfill:
        amazon_csv = amazon_csv.replace(
            "24.00,96.00,2026-10-21T10:00:00Z",
            "20.00,100.00,2026-10-23T10:00:00Z",
        )
    try:
        with connect() as db:
            seed_amazon = amazon_csv if not backfill else AMAZON
            first = {
                "Amazon": ingest(db, "Amazon", seed_amazon,
                                 amazon_upload.name if amazon_upload else None),
                "B2B": ingest(db, "B2B", b2b_csv,
                              b2b_upload.name if b2b_upload else None),
            }
            # A second identical run proves no duplicate source rows/events.
            replay = {
                "Amazon": ingest(db, "Amazon", seed_amazon,
                                 amazon_upload.name if amazon_upload else None),
                "B2B": ingest(db, "B2B", b2b_csv,
                              b2b_upload.name if b2b_upload else None),
            }
            if backfill:
                ingest(db, "Amazon", amazon_csv,
                       amazon_upload.name if amazon_upload else None)
            # The GL snapshot remains the original control, and will show FAIL after a change.
            result = evaluate(db, GL_CONTROL if supply_gl else None)
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        st.error(f"Pipeline blocked: {exc}")
        return

    st.subheader("1. SQLite and idempotent ingestion / 入库与幂等")
    x, y, z = st.columns(3)
    x.metric("Canonical business rows", len(result["rows"]))
    y.metric("Load event history", result["event_count"])
    z.metric("Identical replay new rows", sum(item["changed"] for item in replay.values()))
    st.caption("Composite key (channel, record_id); source updated_at controls backfill order. "
               "Replay uses SQL UPSERT without duplicating rows.")

    st.subheader("2. Finance validation / 财务勾稽")
    c1, c2, c3 = st.columns(3)
    c1.metric("Daily status", result["operational_status"])
    c2.metric("Synthetic GL controls", result["gl_status"])
    c3.metric("Month-end demo status", result["monthly_finance_status"])
    control = pd.DataFrame([
        {"control": "Net sales", "actual_usd": result["totals"]["net_sales_cents"] / 100,
         "gl_usd": GL_CONTROL["net_sales_cents"] / 100 if supply_gl else None},
        {"control": "Platform fees", "actual_usd": result["totals"]["fee_actual_cents"] / 100,
         "gl_usd": GL_CONTROL["fee_actual_cents"] / 100 if supply_gl else None},
        {"control": "Cash due", "actual_usd": result["totals"]["settlement_net_cents"] / 100,
         "gl_usd": GL_CONTROL["cash_due_cents"] / 100 if supply_gl else None},
    ])
    control["difference_usd"] = control["actual_usd"] - control["gl_usd"]
    st.dataframe(control, use_container_width=True, hide_index=True)
    if result["settlement_issues"]:
        st.error("Settlement arithmetic differences need investigation.")

    st.subheader("3. Fee exception and evidence / 异常与证据")
    if result["fee_signals"]:
        signals = pd.DataFrame(result["fee_signals"])
        st.dataframe(signals[["evidence_id", "channel", "record_id", "source_file", "source_row", "category", "status",
                              "expected_fee_cents", "actual_fee_cents", "difference_cents"]].rename(
            columns={"expected_fee_cents": "expected_cents",
                     "actual_fee_cents": "actual_cents", "difference_cents": "variance_cents"}
        ), use_container_width=True, hide_index=True)
        chosen = st.selectbox("Trace one exception to source / 下钻异常", signals["record_id"].tolist())
        source = next(row for row in result["rows"] if row["record_id"] == chosen)
        st.write("Source evidence / 来源记录")
        st.dataframe(pd.DataFrame([{
            "file": source["source_file"], "csv_row": source["source_row"],
            "order_id": source["order_id"], "sku": source["sku"],
            "net_sales_usd": source["net_sales_cents"] / 100,
            "expected_fee_usd": source["fee_expected_cents"] / 100,
            "actual_fee_usd": source["fee_actual_cents"] / 100,
            "settlement_usd": source["settlement_net_cents"] / 100,
            "source_updated_at": source["updated_at"]
        }]), use_container_width=True, hide_index=True)
    else:
        st.success("No fee deviations in this sample.")
    st.markdown(deterministic_explanation(result))

    packet = evidence_packet(result)
    with st.expander("Synthetic detection gold set / 模拟规则评估"):
        scores = run_gold_set()
        st.write(f"{scores['case_count']} hand-constructed cases · "
                 f"Precision {scores['precision']:.0%} · Recall {scores['recall']:.0%}")
        st.dataframe(pd.DataFrame(scores["cases"]), use_container_width=True, hide_index=True)
        st.warning("These are in-sample synthetic rule checks. LLM accuracy is NOT MEASURED. "
                   "Production use requires a separate human-labeled external gold set.")
    with st.expander("Exact permitted AI evidence packet / 可发送的聚合证据"):
        st.json(packet)
    st.caption("No raw uploaded rows, order IDs, customer names, or SKU identifiers are sent to AI.")
    if not packet["signals"]:
        return
    if "thin_review_state" not in st.session_state:
        st.session_state["thin_review_state"] = "Proposed"
    if st.button("Mark investigated / 标记人工已调查", key="thin_review"):
        st.session_state["thin_review_state"] = "Investigated (session only)"
    st.write("Finance review:", st.session_state["thin_review_state"])
    if available():
        consent = st.checkbox("I approve sending this synthetic aggregate packet to the configured LLM.",
                              key="thin_ai_consent")
        if st.button("Generate optional AI explanation", disabled=not consent):
            try:
                st.write(generate_explanation(packet, audience="CFO"))
            except RuntimeError as exc:
                st.error(str(exc))
    else:
        st.caption("Optional LLM explanation disabled: no OPENAI_API_KEY. "
                   "The deterministic evidence and review flow remains fully usable.")
