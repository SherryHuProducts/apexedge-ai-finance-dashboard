"""CFO-friendly, executable walkthrough of three real ApexEdge engineering controls.

Uses only the Python standard library and the existing thin_slice module.
All figures, channel files and GL controls are synthetic.
"""
from __future__ import annotations

import argparse
import csv
import io
from decimal import Decimal

from thin_slice import AMAZON, B2B, GL_CONTROL, cents, connect, ingest, evaluate, evidence_packet


def change_amazon_fee(new_fee: str) -> str:
    """Simulate a revised marketplace settlement without changing unrelated columns."""
    reader = csv.DictReader(io.StringIO(AMAZON))
    rows = list(reader)
    cents(new_fee)  # reject imprecise or invalid financial amounts before touching data
    rows[0]["fee_actual"] = new_fee
    original_sales = Decimal(rows[0]["net_sales"])
    rows[0]["settlement_net"] = f"{original_sales - Decimal(new_fee):.2f}"
    rows[0]["updated_at"] = "2026-10-23T10:00:00Z"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def usd(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def run(fee: str, repeat: bool) -> dict:
    with connect() as db:
        print("1. STANDARDIZE: parse two simulated channels into one row schema")
        print("   Channels: Amazon marketplace + B2B wholesale")
        for channel, content in (("Amazon", AMAZON), ("B2B", B2B)):
            stats = ingest(db, channel, content)
            print(f"   {channel}: {stats}")

        if repeat:
            print("2. IDEMPOTENCY: re-import the identical Amazon file")
            print(f"   Duplicate run: {ingest(db, 'Amazon', AMAZON)}")

        original = evaluate(db, GL_CONTROL)
        print("3. RECONCILE: compare platform records against independent demo GL control")
        print(f"   Initial GL: {original['gl_status']}; rows={len(original['rows'])}; "
              f"audit events={original['event_count']}")

        if fee != "24.00":
            print(f"4. BACKFILL: marketplace corrects fee from $24.00 to ${fee}")
            print(f"   Revision: {ingest(db, 'Amazon', change_amazon_fee(fee))}")

        result = evaluate(db, GL_CONTROL)
        print(f"   Final GL: {result['gl_status']}; finance status: {result['monthly_finance_status']}")
        print(f"   GL fee difference: {usd(result['gl_variances']['fee_actual_cents'])}")
        print(f"   Source rows={len(result['rows'])}; audit events={result['event_count']}")
        for exception in result["fee_signals"]:
            print(f"   Exception {exception['evidence_id']}: "
                  f"{exception['category']} {usd(exception['difference_cents'])} "
                  f"at {exception['source_file']} row {exception['source_row']}; "
                  f"status={exception['status']}")
        packet = evidence_packet(result)
        print("   AI evidence packet: " + str(packet["signals"]))
        print("   Human conclusion: fee variance detected; root cause NOT verified.")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ApexEdge CFO code demonstration (synthetic data)")
    parser.add_argument("--fee", default="24.00", help="Revised Amazon fee, e.g. 20.00")
    parser.add_argument("--repeat", action="store_true", help="Prove duplicate imports don't double-count")
    args = parser.parse_args()
    run(args.fee, args.repeat)
