import json

import pandas as pd

from ai_client import extract_text
from decision_engine import detect_signals, evidence_packet, proposal_from_signal


def base_frame():
    return pd.DataFrame([
        dict(date=pd.Timestamp("2026-01-01"), sku="A", channel="DTC",
             gross_sales=100, discount=0, returns=0, net_revenue=100,
             product_cost=50, freight=5, tariff=5, platform_fee=5,
             marketing_spend=5, gross_profit=40, contribution_profit=30),
        dict(date=pd.Timestamp("2026-02-01"), sku="A", channel="DTC",
             gross_sales=110, discount=0, returns=0, net_revenue=110,
             product_cost=70, freight=8, tariff=8, platform_fee=6,
             marketing_spend=8, gross_profit=24, contribution_profit=10),
    ])


def test_evidence_signals_have_reconcilable_numbers():
    signals = detect_signals(base_frame())
    assert {"Gross Margin %", "Contribution Profit $"}.issubset(set(signals["metric"]))
    gm = signals.loc[signals["metric"] == "Gross Margin %"].iloc[0]
    assert gm["delta"] < 0
    assert gm["evidence"]


def test_packet_contains_aggregates_not_raw_identifiers():
    frame = base_frame()
    packet = evidence_packet(frame, detect_signals(frame), "CFO")
    serialized = json.dumps(packet)
    assert "A" not in packet.get("summary", {})  # No SKU key
    assert "sku" not in serialized.lower()
    assert "source_file" not in serialized.lower()
    assert packet["summary"]["net_revenue"] == 210


def test_no_signal_retains_schema():
    frame = base_frame()
    frame.loc[1, ["gross_profit", "contribution_profit"]] = [45, 31]
    signals = detect_signals(frame)
    packet = evidence_packet(frame, signals, "Sales")
    assert "signals" in packet


def test_proposal_starts_unapproved():
    row = detect_signals(base_frame()).iloc[0]
    proposal = proposal_from_signal(row)
    assert proposal["status"] == "Proposed"
    assert proposal["owner"] == ""


def test_response_parser_reads_text_only():
    response = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "Check returns."}]}]}
    assert extract_text(response) == "Check returns."
