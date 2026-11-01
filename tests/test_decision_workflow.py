import pytest

from decision_workflow import update_decision


def proposed():
    return {"id": "case-1", "status": "Proposed", "owner": "", "notes": ""}


def test_proposal_requires_owner_for_approval():
    with pytest.raises(ValueError, match="owner"):
        update_decision(proposed(), status="Approved", owner="")


def test_approved_action_has_audit_event():
    updated, event = update_decision(proposed(), status="Approved", owner="Sales VP", notes="Pilot approved")
    assert updated["status"] == "Approved"
    assert event["from_status"] == "Proposed"
    assert event["to_status"] == "Approved"
    assert event["timestamp_utc"]
    assert proposed()["status"] == "Proposed"


def test_cannot_skip_directly_to_completed():
    with pytest.raises(ValueError, match="Invalid"):
        update_decision(proposed(), status="Completed", owner="CFO", actual_impact="$100")


def test_completion_requires_measured_outcome():
    approved = {**proposed(), "status": "In progress"}
    with pytest.raises(ValueError, match="measured"):
        update_decision(approved, status="Completed", owner="Sales VP", actual_impact="")
    updated, _ = update_decision(approved, status="Completed", owner="Sales VP", actual_impact="No uplift")
    assert updated["status"] == "Completed"
