"""Synthetic two-channel finance pipeline for an interview-safe vertical slice.

Only Python stdlib. This module is intentionally separate from production APIs.
The accounting controls are illustrative and must not be mistaken for a live GL.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

AMAZON = """record_id,order_date,source_order_id,sku,customer_id,net_sales,units,fee_expected,fee_actual,settlement_net,updated_at
A-1,2026-10-20,AMZ-1008,SKU-RED,MARKETPLACE,120.00,2,18.00,24.00,96.00,2026-10-21T10:00:00Z
"""
B2B = """record_id,order_date,source_order_id,sku,customer_id,net_sales,units,fee_expected,fee_actual,settlement_net,updated_at
B-1,2026-10-20,INV-0042,SKU-BLUE,B2B-CUSTOMER-1,200.00,4,0.00,0.00,200.00,2026-10-21T10:00:00Z
"""
GL_CONTROL = {"net_sales_cents": 32000, "fee_actual_cents": 2400, "cash_due_cents": 29600}
FIELDS = ["record_id", "order_date", "source_order_id", "sku", "customer_id", "net_sales", "units",
          "fee_expected", "fee_actual", "settlement_net", "updated_at"]


def cents(value: str) -> int:
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError(f"Invalid money amount: {value!r}") from exc
    if not number.is_finite() or number != number.quantize(Decimal("0.01")):
        raise ValueError("Money requires finite values with at most two decimals")
    return int(number * 100)


def connect(db_path: str = ":memory:") -> sqlite3.Connection:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS source_rows(
            channel TEXT NOT NULL,
            record_id TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_row INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            order_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            net_sales_cents INTEGER NOT NULL,
            units INTEGER NOT NULL,
            fee_expected_cents INTEGER NOT NULL,
            fee_actual_cents INTEGER NOT NULL,
            settlement_net_cents INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            PRIMARY KEY(channel, record_id)
        );
        CREATE TABLE IF NOT EXISTS load_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loaded_at TEXT NOT NULL,
            channel TEXT NOT NULL,
            record_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            prior_fingerprint TEXT,
            new_fingerprint TEXT NOT NULL
        );
    """)
    return db


def parse_csv(content: str, channel: str, source_name: str | None = None) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or set(FIELDS) - set(reader.fieldnames):
        raise ValueError(f"{channel}: missing columns {sorted(set(FIELDS) - set(reader.fieldnames or []))}")
    seen: set[str] = set()
    rows = []
    for source_row, raw in enumerate(reader, start=2):
        rid = (raw["record_id"] or "").strip()
        if not rid or rid in seen:
            raise ValueError(f"{channel}: blank or duplicate source record id {rid!r}")
        seen.add(rid)
        try:
            units = int(raw["units"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{channel}: units must be an integer") from exc
        if units <= 0:
            raise ValueError(f"{channel}: units must be positive")
        row = {"channel": channel, "record_id": rid,
               "source_file": source_name or f"{channel.lower()}_synthetic.csv", "source_row": source_row,
               "order_date": raw["order_date"].strip(),
               "order_id": raw["source_order_id"].strip(),
               "sku": raw["sku"].strip(),
               "customer_id": raw["customer_id"].strip(),
               "net_sales_cents": cents(raw["net_sales"]), "units": units,
               "fee_expected_cents": cents(raw["fee_expected"]),
               "fee_actual_cents": cents(raw["fee_actual"]),
               "settlement_net_cents": cents(raw["settlement_net"]),
               "updated_at": raw["updated_at"].strip()}
        for field in ("order_date", "order_id", "sku", "customer_id", "updated_at"):
            if not row[field]:
                raise ValueError(f"{channel}: missing {field}")
        row["fingerprint"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        rows.append(row)
    return rows


def ingest(db: sqlite3.Connection, channel: str, content: str,
           source_name: str | None = None) -> dict:
    """Transactional upsert. A repeated identical run creates no new business rows/events.

    The same record_id with a newer source updated_at can revise a prior period.
    Out-of-order older snapshots cannot overwrite newer revisions.
    """
    if channel not in {"Amazon", "B2B"}:
        raise ValueError("Only the synthetic Amazon/B2B connectors are supported")
    rows = parse_csv(content, channel, source_name)
    changed = unchanged = stale = 0
    with db:
        for row in rows:
            old = db.execute(
                "SELECT fingerprint, updated_at FROM source_rows WHERE channel=? AND record_id=?",
                (channel, row["record_id"]),
            ).fetchone()
            if old and row["updated_at"] < old["updated_at"]:
                stale += 1
                continue
            if old and row["fingerprint"] == old["fingerprint"]:
                unchanged += 1
                continue
            if old and row["updated_at"] == old["updated_at"]:
                raise ValueError(f"{channel}: conflicting revision at the same updated_at for {row['record_id']}")
            event_type = "INSERT" if old is None else "BACKFILL_UPDATE"
            db.execute("""
                INSERT INTO source_rows(channel,record_id,source_file,source_row,order_date,order_id,sku,customer_id,
                    net_sales_cents,units,fee_expected_cents,fee_actual_cents,settlement_net_cents,
                    updated_at,fingerprint)
                VALUES(:channel,:record_id,:source_file,:source_row,:order_date,:order_id,:sku,:customer_id,
                    :net_sales_cents,:units,:fee_expected_cents,:fee_actual_cents,:settlement_net_cents,
                    :updated_at,:fingerprint)
                ON CONFLICT(channel,record_id) DO UPDATE SET
                    source_file=excluded.source_file,source_row=excluded.source_row,
                    order_date=excluded.order_date, order_id=excluded.order_id,
                    sku=excluded.sku, customer_id=excluded.customer_id,
                    net_sales_cents=excluded.net_sales_cents, units=excluded.units,
                    fee_expected_cents=excluded.fee_expected_cents,
                    fee_actual_cents=excluded.fee_actual_cents,
                    settlement_net_cents=excluded.settlement_net_cents,
                    updated_at=excluded.updated_at, fingerprint=excluded.fingerprint
            """, row)
            db.execute("""INSERT INTO load_events(loaded_at,channel,record_id,event_type,prior_fingerprint,new_fingerprint)
                VALUES(?,?,?,?,?,?)""", (
                datetime.now(timezone.utc).isoformat(), channel, row["record_id"],
                event_type, old["fingerprint"] if old else None, row["fingerprint"],
            ))
            changed += 1
    return {"changed": changed, "unchanged": unchanged, "stale": stale}


def evaluate(db: sqlite3.Connection, gl_control: dict | None = None) -> dict:
    rows = [dict(row) for row in db.execute("SELECT * FROM source_rows ORDER BY channel,record_id")]
    totals = {key: sum(row[key] for row in rows) for key in (
        "net_sales_cents", "fee_actual_cents", "settlement_net_cents")}
    settlement_issues = [
        {"channel": r["channel"], "record_id": r["record_id"],
         "source_file": r["source_file"], "source_row": r["source_row"],
         "category": "settlement_mismatch", "status": "OPEN",
         "difference_cents": r["net_sales_cents"] - r["fee_actual_cents"] - r["settlement_net_cents"]}
        for r in rows
        if r["net_sales_cents"] - r["fee_actual_cents"] != r["settlement_net_cents"]
    ]
    fee_signals = [
        {"channel": r["channel"], "record_id": r["record_id"],
         "source_file": r["source_file"], "source_row": r["source_row"],
         "category": "fee_policy", "status": "OPEN",
         "expected_fee_cents": r["fee_expected_cents"], "actual_fee_cents": r["fee_actual_cents"],
         "difference_cents": r["fee_actual_cents"] - r["fee_expected_cents"],
         "evidence_fields": ["net_sales", "fee_expected", "fee_actual", "source_updated_at"]}
        for r in rows if r["fee_actual_cents"] != r["fee_expected_cents"]
    ]
    gl_variances = {}
    if gl_control is not None:
        for key, actual in (("net_sales_cents", totals["net_sales_cents"]),
                            ("fee_actual_cents", totals["fee_actual_cents"]),
                            ("cash_due_cents", totals["settlement_net_cents"])):
            gl_variances[key] = actual - gl_control[key]
    gl_pass = gl_control is not None and all(v == 0 for v in gl_variances.values())
    return {
        "rows": rows, "totals": totals, "settlement_issues": settlement_issues,
        "fee_signals": fee_signals, "gl_variances": gl_variances,
        "operational_status": "PROVISIONAL",
        "gl_status": "PASS" if gl_pass else ("FAIL" if gl_control is not None else "NOT SUPPLIED"),
        "monthly_finance_status": "RECONCILED DEMO CONTROLS" if gl_pass and not settlement_issues else "NOT RECONCILED",
        "event_count": db.execute("SELECT COUNT(*) FROM load_events").fetchone()[0],
    }


def evidence_packet(result: dict) -> dict:
    """Only aggregate numeric evidence goes to an optional LLM; no IDs or rows."""
    return {
        "summary": {
            "data_scope": "synthetic two-channel example",
            "gl_status": result["gl_status"],
            "operational_status": result["operational_status"],
            "record_count": len(result["rows"]),
        },
        "signals": [
            {"metric": "platform_fee_variance_usd",
             "baseline": round(s["expected_fee_cents"] / 100, 2),
             "observed": round(s["actual_fee_cents"] / 100, 2),
             "difference": round(s["difference_cents"] / 100, 2),
             "evidence": s["evidence_fields"],
             "cause_status": "unverified"}
            for s in result["fee_signals"][:3]
        ],
    }


def deterministic_explanation(result: dict) -> str:
    if not result["fee_signals"]:
        return "No fee variance was detected in the synthetic dataset."
    s = result["fee_signals"][0]
    return (
        f"Observed: actual platform fee is ${s['actual_fee_cents']/100:,.2f}, "
        f"versus expected ${s['expected_fee_cents']/100:,.2f} "
        f"(variance ${s['difference_cents']/100:,.2f}). "
        "The difference requires a settlement adjustment or fee-schedule review. "
        "The source data does not establish its cause. Finance must verify and close the exception."
    )


def demo_run(db_path: str = ":memory:", amazon: str = AMAZON, b2b: str = B2B,
             gl_control: dict | None = GL_CONTROL) -> tuple[dict, dict]:
    with connect(db_path) as db:
        a = ingest(db, "Amazon", amazon)
        b = ingest(db, "B2B", b2b)
        result = evaluate(db, gl_control)
    return result, {"Amazon": a, "B2B": b}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the synthetic finance vertical slice")
    parser.add_argument("--db", default=":memory:")
    args = parser.parse_args()
    result, loads = demo_run(args.db)
    print(json.dumps({"loads": loads, "gl_status": result["gl_status"],
                      "finance_status": result["monthly_finance_status"],
                      "exceptions": result["fee_signals"],
                      "evidence_for_ai": evidence_packet(result)}, indent=2))
