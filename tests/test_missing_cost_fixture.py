from pathlib import Path

from data_pipeline import ingest_finance_files


def test_missing_cost_is_unavailable_not_zero():
    path = Path(__file__).parent / "fixtures/missing_cost.csv"
    result = ingest_finance_files(((path.name, path.read_bytes()),))
    canonical = result["canonical"]
    assert len(canonical) == 1
    assert not bool(canonical.iloc[0]["analysis_ready"])
    assert canonical.iloc[0]["gross_profit"] != 0 or str(canonical.iloc[0]["gross_profit"]) == "nan"
    assert result["stats"]["analysis_rows"] == 0
    assert any("missing fields required" in issue.lower()
               for issue in result["issues"]["Issue / 问题"].tolist())
