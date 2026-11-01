"""Synthetic channel P&L: approved master keys, exact cents, source evidence, GL controls.

This is an accounting-policy demonstration, not certified GAAP presentation or live ERP data.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from master_data_mapping import SOURCE_RECORDS, STARTER_MAPPINGS, approve, create_db, map_records


def money(value: str) -> int:
    amount = Decimal(value)
    if not amount.is_finite() or amount != amount.quantize(Decimal(".01")):
        raise ValueError("Currency must use exact cents")
    return int(amount * 100)


# Independent simulated accounting evidence, keyed to source system + order ID.
# None = missing source evidence; never silently converted to zero.
ORDER_COSTS = {
    ("Walmart", "WM-1"): {"cogs": "70.00", "freight": "8.00", "tariff": "4.00", "platform_fee": "18.00", "advertising": "6.00", "rebate": "0.00", "returns": "0.00"},
    ("Costco", "CT-1"): {"cogs": "120.00", "freight": "12.00", "tariff": "6.00", "platform_fee": "0.00", "advertising": "0.00", "rebate": "10.00", "returns": "0.00"},
    ("ERP", "ERP-1"): {"cogs": "40.00", "freight": "3.00", "tariff": "2.00", "platform_fee": "0.00", "advertising": "0.00", "rebate": "0.00", "returns": "0.00"},
    ("Website", "WEB-1"): {"cogs": "30.00", "freight": "5.00", "tariff": "1.00", "platform_fee": "3.00", "advertising": "8.00", "rebate": "0.00", "returns": "5.00"},
}
REQUIRED_COSTS = ("cogs", "freight", "tariff", "platform_fee", "advertising", "rebate", "returns")
UNALLOCATED_SHARED_CENTS = money("20.00")
DEMO_GL = {"net_revenue_cents": money("455.00"), "product_cogs_cents": money("260.00")}


def build_pl(approve_website: bool = False, missing_cost: bool = False) -> dict:
    with create_db() as db:
        for system, entity, source, canonical in STARTER_MAPPINGS:
            approve(db, system, entity, source, canonical, "Demo Finance Owner")
        if approve_website:
            approve(db, "Website", "sku", "RED-V2", "SKU-RED", "Demo Finance Reviewer")
        mapped = map_records(db, SOURCE_RECORDS)

    details, exceptions = [], list(mapped["issues"])
    for source in mapped["ready"]:
        key = (source["system"], source["order_id"])
        costs = dict(ORDER_COSTS.get(key, {}))
        if missing_cost and key == ("Costco", "CT-1"):
            costs.pop("cogs", None)
        absent = [name for name in REQUIRED_COSTS if costs.get(name) is None]
        if absent:
            exceptions.append({"system": source["system"], "order_id": source["order_id"],
                               "entity": "cost", "source_value": ",".join(absent),
                               "revenue_cents": source["revenue_cents"], "status": "BLOCKED_COST"})
            details.append({**source, "analysis_status": "COST_UNAVAILABLE", "net_revenue_cents": None,
                            "gross_profit_cents": None, "contribution_profit_cents": None})
            continue

        c = {name + "_cents": money(costs[name]) for name in REQUIRED_COSTS}
        net = source["revenue_cents"] - c["returns_cents"]
        gp = net - c["cogs_cents"] - c["freight_cents"] - c["tariff_cents"]
        cp = gp - c["platform_fee_cents"] - c["advertising_cents"] - c["rebate_cents"]
        details.append({**source, **c, "net_revenue_cents": net,
                        "gross_profit_cents": gp, "contribution_profit_cents": cp,
                        "analysis_status": "CALCULATED"})

    calculated = [r for r in details if r["analysis_status"] == "CALCULATED"]
    totals = {k: sum(r[k] for r in calculated) for k in (
        "revenue_cents", "returns_cents", "net_revenue_cents", "cogs_cents", "freight_cents", "tariff_cents",
        "platform_fee_cents", "advertising_cents", "rebate_cents", "gross_profit_cents", "contribution_profit_cents")}
    grouped = defaultdict(list)
    for row in calculated:
        grouped[row["system"]].append(row)
    channels = []
    for channel, rows in grouped.items():
        channels.append({"channel": channel, "orders": len(rows),
                         "net_revenue_cents": sum(r["net_revenue_cents"] for r in rows),
                         "gross_profit_cents": sum(r["gross_profit_cents"] for r in rows),
                         "contribution_profit_cents": sum(r["contribution_profit_cents"] for r in rows)})

    complete = not mapped["blocked"] and all(r["analysis_status"] == "CALCULATED" for r in details)
    gl_variance = {
        "net_revenue_cents": totals["net_revenue_cents"] - DEMO_GL["net_revenue_cents"],
        "product_cogs_cents": totals["cogs_cents"] - DEMO_GL["product_cogs_cents"],
    }
    gl_status = "DEMO PASS" if complete and all(v == 0 for v in gl_variance.values()) else "NOT RECONCILED"
    return {
        "details": details, "channels": channels, "totals": totals, "exceptions": exceptions,
        "blocked_mapping_cents": mapped["blocked_revenue_cents"],
        "blocked_cost_cents": sum(r["revenue_cents"] for r in details if r["analysis_status"] != "CALCULATED"),
        "unallocated_shared_cents": UNALLOCATED_SHARED_CENTS,
        "gl_variance": gl_variance, "gl_status": gl_status,
        "profit_complete": complete, "mapping_audit": mapped["events"],
    }


if __name__ == "__main__":
    import json
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--approve-website", action="store_true")
    p.add_argument("--missing-cost", action="store_true")
    args = p.parse_args()
    result = build_pl(args.approve_website, args.missing_cost)
    print(json.dumps({key: result[key] for key in (
        "totals", "gl_status", "profit_complete", "blocked_mapping_cents", "blocked_cost_cents", "exceptions")}, indent=2))
