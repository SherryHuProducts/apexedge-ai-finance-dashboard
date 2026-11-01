"""Human decision-state validation. No automatic business-system mutations."""
from __future__ import annotations

from datetime import datetime, timezone


TRANSITIONS = {
    "Proposed": ("Proposed", "Approved", "Rejected"),
    "Approved": ("Approved", "In progress", "Rejected"),
    "In progress": ("In progress", "Completed", "Rejected"),
    "Completed": ("Completed",),
    "Rejected": ("Rejected",),
}


def update_decision(
    record: dict,
    *,
    status: str,
    owner: str,
    expected_impact: str = "",
    actual_impact: str = "",
    notes: str = "",
) -> tuple[dict, dict]:
    current = str(record.get("status", ""))
    if current not in TRANSITIONS or status not in TRANSITIONS[current]:
        raise ValueError(f"Invalid decision transition: {current} -> {status}")
    if status in ("Approved", "In progress", "Completed") and not owner.strip():
        raise ValueError("A named owner is required for approval or execution")
    if status == "Completed" and not actual_impact.strip():
        raise ValueError("Completion requires a measured impact or documented outcome")
    updated = dict(record)
    updated.update(status=status, owner=owner.strip(), expected_impact=expected_impact,
                   actual_impact=actual_impact, notes=notes)
    event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "id": str(record["id"]), "from_status": current, "to_status": status,
        "actor": owner.strip() or "Demo user", "note": notes[:240],
    }
    return updated, event
