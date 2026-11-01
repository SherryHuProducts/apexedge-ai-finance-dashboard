"""Synthetic Walmart API-shaped + Costco EDI-inspired connector demonstration.

No live network calls or credentials. Costco's example is a deliberately simplified
EDI-like transport, NOT an ANSI X12 EDI parser. Uses existing finance controls.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from decimal import Decimal

from thin_slice import FIELDS, cents, connect, evaluate, evidence_packet, ingest


WALMART_RESPONSE = {
    "orders": [{
        "purchaseOrderId": "WM-801", "purchaseDate": "2026-10-20",
        "item": {"sku": "SKU-RED", "quantity": 2},
        "grossSales": "100.00", "expectedCommission": "12.00",
        "chargedCommission": "16.00", "netSettlement": "84.00",
        "lastModified": "2026-10-21T10:00:00Z",
    }]
}

# The actual wholesale order would arrive through a supported EDI provider;
# this compact pipe-delimited fixture is for demonstrating a distinct adapter.
COSTCO_EDI_LIKE = """850|CT-902|2026-10-20|SKU-BLUE|4|200.00|5.00|195.00|2026-10-21T10:00:00Z"""

# Independent synthetic accounting control. NOT an actual ERP or posted GL.
DEMO_GL = {"net_sales_cents": 30000, "fee_actual_cents": 2100, "cash_due_cents": 27900}


def _money(value: str) -> str:
    value_cents = cents(value)
    return f"{Decimal(value_cents) / 100:.2f}"


def walmart_adapter(payload: dict) -> list[dict]:
    """Map an API-shaped JSON response into the same canonical finance schema."""
    records = payload.get("orders")
    if not isinstance(records, list):
        raise ValueError("Walmart: orders must be a list")
    mapped = []
    for record in records:
        item = record["item"]
        mapped.append({
            "record_id": record["purchaseOrderId"],
            "order_date": record["purchaseDate"],
            "source_order_id": record["purchaseOrderId"],
            "sku": item["sku"], "customer_id": "WALMART-MARKETPLACE",
            "net_sales": _money(record["grossSales"]),
            "units": item["quantity"],
            "fee_expected": _money(record["expectedCommission"]),
            "fee_actual": _money(record["chargedCommission"]),
            "settlement_net": _money(record["netSettlement"]),
            "updated_at": record["lastModified"],
        })
    return mapped


def costco_adapter(text: str) -> list[dict]:
    """Parse a simplified EDI-like PO feed; treat allowance as a separate deduction.

    Full X12 850/810/856 handling, invoice matching, and terms are out of scope.
    The canonical 'fee' columns represent retailer deductions in this *demo* only.
    """
    mapped = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) != 9 or parts[0] != "850":
            raise ValueError("Costco: expected simplified 850 record with nine fields")
        _, po, date, sku, units, invoice, allowance, receivable, timestamp = parts
        mapped.append({
            "record_id": po, "order_date": date, "source_order_id": po,
            "sku": sku, "customer_id": "COSTCO-WHOLESALE",
            "net_sales": _money(invoice), "units": units,
            "fee_expected": _money(allowance), "fee_actual": _money(allowance),
            "settlement_net": _money(receivable), "updated_at": timestamp,
        })
    return mapped


def to_canonical_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def run_demo(scenario: str = "standard") -> dict:
    """End-to-end extract → adapter → validate → SQLite → controls.

    Scenarios: standard, duplicate_upload, late_fee_adjustment, missing_sku,
    settlement_mismatch. A failed validation keeps the entire batch out.
    """
    allowed = {"standard", "duplicate_upload", "late_fee_adjustment", "missing_sku", "settlement_mismatch"}
    if scenario not in allowed:
        raise ValueError(f"Unknown scenario: {scenario}")
    walmart_raw = json.loads(json.dumps(WALMART_RESPONSE))
    if scenario == "missing_sku":
        walmart_raw["orders"][0]["item"]["sku"] = ""
    if scenario == "settlement_mismatch":
        walmart_raw["orders"][0]["netSettlement"] = "83.00"

    sources = [
        ("Walmart", walmart_adapter(walmart_raw), "walmart_api_mock.json", "Simulated REST JSON"),
        ("Costco", costco_adapter(COSTCO_EDI_LIKE), "costco_edi_mock.txt", "Simplified EDI-like 850"),
    ]
    reports = []
    with connect() as db:
        for channel, rows, source, method in sources:
            report = {
                "channel": channel, "source": source, "method": method,
                "records_received": len(rows), "last_sync": datetime.now(timezone.utc).isoformat(),
                "validation": "PASS", "loaded": 0, "unchanged": 0,
            }
            try:
                stats = ingest(db, channel, to_canonical_csv(rows), source_name=source)
                report["loaded"] = stats["changed"]
                report["unchanged"] = stats["unchanged"]
            except (ValueError, KeyError) as exc:
                report["validation"] = f"FAIL: {exc}"
            reports.append(report)

        if scenario == "duplicate_upload":
            stats = ingest(db, "Walmart", to_canonical_csv(sources[0][1]), source_name=sources[0][2])
            reports[0]["unchanged"] += stats["unchanged"]

        if scenario == "late_fee_adjustment":
            revised = json.loads(json.dumps(WALMART_RESPONSE))
            revised["orders"][0]["chargedCommission"] = "13.00"
            revised["orders"][0]["netSettlement"] = "87.00"
            revised["orders"][0]["lastModified"] = "2026-10-23T10:00:00Z"
            revision_stats = ingest(db, "Walmart", to_canonical_csv(walmart_adapter(revised)),
                                    source_name=sources[0][2])
            reports[0]["loaded"] += revision_stats["changed"]

        result = evaluate(db, DEMO_GL)
        for report in reports:
            report["reconciliation"] = result["gl_status"] if report["validation"] == "PASS" else "BLOCKED"
        events = [dict(item) for item in db.execute(
            "SELECT channel,record_id,event_type FROM load_events ORDER BY id")]
    return {
        "scenario": scenario, "sources": reports, "result": result,
        "audit_events": events, "ai_evidence": evidence_packet(result),
        "financial_status": "PROVISIONAL / SYNTHETIC",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ApexEdge mock Walmart + Costco connector demo")
    parser.add_argument("--scenario", default="standard", choices=[
        "standard", "duplicate_upload", "late_fee_adjustment", "missing_sku", "settlement_mismatch"])
    args = parser.parse_args()
    demo = run_demo(args.scenario)
    print(json.dumps({
        "scenario": demo["scenario"], "sources": demo["sources"],
        "gl_status": demo["result"]["gl_status"],
        "exceptions": demo["result"]["fee_signals"],
        "settlement_issues": demo["result"]["settlement_issues"],
        "audit_events": demo["audit_events"],
    }, indent=2))
