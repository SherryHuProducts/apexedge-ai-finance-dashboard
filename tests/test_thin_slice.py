import pytest
from pathlib import Path

from thin_slice import (
    AMAZON, B2B, GL_CONTROL, cents, connect, demo_run,
    deterministic_explanation, evaluate, evidence_packet, ingest,
)


def test_two_channel_controls_and_one_fee_exception():
    result, loads = demo_run()
    assert len(result["rows"]) == 2
    assert result["gl_status"] == "PASS"
    assert result["monthly_finance_status"] == "RECONCILED DEMO CONTROLS"
    assert result["operational_status"] == "PROVISIONAL"
    assert result["settlement_issues"] == []
    assert result["fee_signals"][0]["difference_cents"] == 600
    assert "does not establish its cause" in deterministic_explanation(result)
    assert loads["Amazon"]["changed"] == 1


def test_idempotent_replay_adds_no_event_or_business_row():
    with connect() as db:
        ingest(db, "Amazon", AMAZON)
        ingest(db, "B2B", B2B)
        replay = ingest(db, "Amazon", AMAZON)
        assert replay == {"changed": 0, "unchanged": 1, "stale": 0}
        result = evaluate(db, GL_CONTROL)
        assert result["event_count"] == 2
        assert len(result["rows"]) == 2


def test_backfill_changes_prior_month_and_reconciliation_fails_until_control_updated():
    updated = AMAZON.replace(
        "24.00,96.00,2026-10-21T10:00:00Z",
        "20.00,100.00,2026-10-23T10:00:00Z",
    )
    with connect() as db:
        ingest(db, "Amazon", AMAZON)
        ingest(db, "B2B", B2B)
        assert ingest(db, "Amazon", updated)["changed"] == 1
        result = evaluate(db, GL_CONTROL)
        assert result["gl_status"] == "FAIL"
        assert result["monthly_finance_status"] == "NOT RECONCILED"
        assert result["fee_signals"][0]["difference_cents"] == 200
        assert result["event_count"] == 3
        assert ingest(db, "Amazon", AMAZON)["stale"] == 1
        assert evaluate(db, GL_CONTROL)["event_count"] == 3


def test_bad_settlement_arithmetic_detected_even_if_gl_matches():
    bad = AMAZON.replace("24.00,96.00", "24.00,100.00")
    with connect() as db:
        ingest(db, "Amazon", bad)
        ingest(db, "B2B", B2B)
        result = evaluate(db, None)
        assert result["settlement_issues"][0]["difference_cents"] == -400
        assert result["monthly_finance_status"] == "NOT RECONCILED"


def test_conflicting_same_timestamp_is_blocked():
    with connect() as db:
        ingest(db, "Amazon", AMAZON)
        with pytest.raises(ValueError, match="conflicting revision"):
            ingest(db, "Amazon", AMAZON.replace("24.00,96.00", "20.00,100.00"))


def test_money_rejects_excess_precision_and_nan():
    for value in ["1.001", "NaN", "oops"]:
        with pytest.raises(ValueError):
            cents(value)


def test_ai_packet_is_aggregated_no_ids():
    result, _ = demo_run()
    packet = evidence_packet(result)
    text = str(packet)
    for sensitive in ("AMZ-1008", "SKU-RED", "B2B-CUSTOMER-1", "A-1"):
        assert sensitive not in text
    assert packet["signals"][0]["difference"] == 6.0


def test_optional_gl_absence_is_not_pass():
    result, _ = demo_run(gl_control=None)
    assert result["gl_status"] == "NOT SUPPLIED"
    assert result["monthly_finance_status"] == "NOT RECONCILED"


def test_intentionally_broken_duplicate_file_is_rejected():
    path = Path(__file__).parent / "fixtures/broken_amazon.csv"
    with connect() as db:
        with pytest.raises(ValueError, match="duplicate"):
            ingest(db, "Amazon", path.read_text())
        assert evaluate(db)["event_count"] == 0


def test_intentionally_broken_settlement_is_detected_with_provenance():
    path = Path(__file__).parent / "fixtures/settlement_mismatch.csv"
    with connect() as db:
        ingest(db, "Amazon", path.read_text(), path.name)
        issue = evaluate(db)["settlement_issues"][0]
        assert issue["difference_cents"] == -400
        assert issue["category"] == "settlement_mismatch"
        assert issue["source_row"] == 2
        assert issue["source_file"] == path.name
