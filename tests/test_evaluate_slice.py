from evaluate_slice import run_gold_set


def test_synthetic_gold_set_rules_all_match():
    result = run_gold_set()
    assert result["case_count"] == 4
    assert result["all_cases_match"] is True
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["llm_accuracy"] == "NOT MEASURED"
