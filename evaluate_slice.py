"""Repeatable gold-set evaluation of deterministic controls, NOT of the LLM.

This tiny synthetic set validates detection wiring only. It does not estimate
accuracy on unseen company data or factuality of generated explanations.
"""
from __future__ import annotations

import json
from pathlib import Path

from thin_slice import AMAZON, B2B, connect, evaluate, ingest

FIX = Path(__file__).parent / "tests" / "fixtures"


def run_gold_set() -> dict:
    cases = [
        {"name": "normal_b2b", "content": B2B, "expect": set()},
        {"name": "fee_policy_variance", "content": AMAZON, "expect": {"fee_policy"}},
        {"name": "settlement_mismatch", "content": (FIX / "settlement_mismatch.csv").read_text(),
         "expect": {"settlement_mismatch", "fee_policy"}},
        {"name": "duplicate_record", "content": (FIX / "broken_amazon.csv").read_text(),
         "expect": {"duplicate"}},
    ]
    tp = fp = fn = 0
    per_case = []
    for case in cases:
        detected = set()
        try:
            with connect() as db:
                ingest(db, "B2B" if case["name"] == "normal_b2b" else "Amazon", case["content"])
                result = evaluate(db)
                if result["fee_signals"]:
                    detected.add("fee_policy")
                if result["settlement_issues"]:
                    detected.add("settlement_mismatch")
        except ValueError as exc:
            if "duplicate" in str(exc):
                detected.add("duplicate")
            else:
                raise
        tp += len(detected & case["expect"])
        fp += len(detected - case["expect"])
        fn += len(case["expect"] - detected)
        per_case.append({"case": case["name"], "expected": sorted(case["expect"]),
                         "detected": sorted(detected), "pass": detected == case["expect"]})
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "scope": "hand-constructed synthetic rule test, not LLM evaluation",
        "case_count": len(cases), "true_positives": tp, "false_positives": fp,
        "false_negatives": fn, "precision": precision, "recall": recall,
        "all_cases_match": all(case["pass"] for case in per_case),
        "cases": per_case, "llm_accuracy": "NOT MEASURED",
    }


if __name__ == "__main__":
    print(json.dumps(run_gold_set(), indent=2))
