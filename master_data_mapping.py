"""Synthetic cross-system master data mapping with review/audit controls.

Only approved mappings allow records into a comparable analytical dataset.
Neither raw IDs nor unmapped financial amounts are silently discarded or zeroed.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


SOURCE_RECORDS = [
    {"system": "Walmart", "order_id": "WM-1", "sku": "WM-RED-001", "customer": "WM-MKT", "account": "400-WM", "revenue_cents": 12000},
    {"system": "Costco", "order_id": "CT-1", "sku": "CT-1001", "customer": "COSTCO-W", "account": "REV-WHS", "revenue_cents": 20000},
    {"system": "ERP", "order_id": "ERP-1", "sku": "SKU-RED", "customer": "C-001", "account": "4000", "revenue_cents": 8000},
    {"system": "Website", "order_id": "WEB-1", "sku": "RED-V2", "customer": "WEB-DTC", "account": "DTC-REV", "revenue_cents": 6000},
]

STARTER_MAPPINGS = [
    ("Walmart", "sku", "WM-RED-001", "SKU-RED"),
    ("Costco", "sku", "CT-1001", "SKU-RED"),
    ("ERP", "sku", "SKU-RED", "SKU-RED"),
    ("Walmart", "customer", "WM-MKT", "C-MARKETPLACE"),
    ("Costco", "customer", "COSTCO-W", "C-COSTCO"),
    ("ERP", "customer", "C-001", "C-001"),
    ("Website", "customer", "WEB-DTC", "C-DTC"),
    ("Walmart", "account", "400-WM", "4000"),
    ("Costco", "account", "REV-WHS", "4000"),
    ("ERP", "account", "4000", "4000"),
    ("Website", "account", "DTC-REV", "4000"),
]


def create_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE mappings (
            system TEXT NOT NULL,
            entity TEXT NOT NULL CHECK(entity IN ('sku', 'customer', 'account')),
            source_value TEXT NOT NULL,
            canonical_value TEXT NOT NULL,
            approved_by TEXT NOT NULL,
            approved_at TEXT NOT NULL,
            PRIMARY KEY(system, entity, source_value)
        );
        CREATE TABLE mapping_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system TEXT NOT NULL, entity TEXT NOT NULL,
            source_value TEXT NOT NULL,
            old_value TEXT, new_value TEXT NOT NULL,
            reviewer TEXT NOT NULL, changed_at TEXT NOT NULL
        );
    """)
    return db


def approve(db: sqlite3.Connection, system: str, entity: str, source: str,
            canonical: str, reviewer: str) -> None:
    if entity not in ("sku", "customer", "account") or not all((system, source, canonical, reviewer)):
        raise ValueError("A reviewer and nonempty source/canonical keys are required")
    timestamp = datetime.now(timezone.utc).isoformat()
    with db:
        old = db.execute("SELECT canonical_value FROM mappings WHERE system=? AND entity=? AND source_value=?",
                         (system, entity, source)).fetchone()
        if old and old["canonical_value"] == canonical:
            return  # approval is idempotent
        db.execute("""INSERT INTO mappings(system,entity,source_value,canonical_value,approved_by,approved_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(system,entity,source_value) DO UPDATE SET
            canonical_value=excluded.canonical_value, approved_by=excluded.approved_by,
            approved_at=excluded.approved_at""", (system, entity, source, canonical, reviewer, timestamp))
        db.execute("""INSERT INTO mapping_events(system,entity,source_value,old_value,new_value,reviewer,changed_at)
            VALUES(?,?,?,?,?,?,?)""", (system, entity, source, old["canonical_value"] if old else None,
                                         canonical, reviewer, timestamp))


def map_records(db: sqlite3.Connection, records: list[dict]) -> dict:
    lookup = {(r["system"], r["entity"], r["source_value"]): r["canonical_value"]
              for r in db.execute("SELECT * FROM mappings")}
    ready, blocked, issues = [], [], []
    for record in records:
        mapped = dict(record)
        missing = []
        for entity in ("sku", "customer", "account"):
            resolved = lookup.get((record["system"], entity, record[entity]))
            mapped["canonical_" + entity] = resolved
            if not resolved:
                missing.append(entity)
                issues.append({"system": record["system"], "order_id": record["order_id"],
                               "entity": entity, "source_value": record[entity],
                               "revenue_cents": record["revenue_cents"], "status": "OPEN"})
        if missing:
            mapped["mapping_status"] = "BLOCKED"
            blocked.append(mapped)
        else:
            mapped["mapping_status"] = "APPROVED"
            ready.append(mapped)
    return {
        "ready": ready, "blocked": blocked, "issues": issues,
        "total_revenue_cents": sum(r["revenue_cents"] for r in records),
        "approved_revenue_cents": sum(r["revenue_cents"] for r in ready),
        "blocked_revenue_cents": sum(r["revenue_cents"] for r in blocked),
        "events": [dict(row) for row in db.execute("SELECT * FROM mapping_events ORDER BY id")],
    }


def run_demo(resolve_website: bool = False) -> dict:
    with create_db() as db:
        for system, entity, source, canonical in STARTER_MAPPINGS:
            approve(db, system, entity, source, canonical, "Demo Finance Owner")
        before = map_records(db, SOURCE_RECORDS)
        if resolve_website:
            approve(db, "Website", "sku", "RED-V2", "SKU-RED", "Demo Finance Reviewer")
        after = map_records(db, SOURCE_RECORDS)
    return {"before": before, "after": after, "resolved": resolve_website}


if __name__ == "__main__":
    import json
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--approve-website", action="store_true")
    args = parser.parse_args()
    result = run_demo(args.approve_website)
    print(json.dumps({
        "before_blocked": result["before"]["blocked_revenue_cents"] / 100,
        "after_blocked": result["after"]["blocked_revenue_cents"] / 100,
        "issues": result["after"]["issues"],
        "approved_rows": len(result["after"]["ready"]),
        "audit_events": len(result["after"]["events"]),
    }, indent=2))
