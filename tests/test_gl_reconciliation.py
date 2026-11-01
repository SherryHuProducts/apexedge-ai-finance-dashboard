import pandas as pd
import pytest

from gl_reconciliation import parse_gl_control_file, reconcile_gl


def analytical_data():
    return pd.DataFrame([{
        "date": pd.Timestamp("2026-01-01"), "sku": "A", "channel": "DTC",
        "net_revenue": 100.0, "product_cost": 50.0, "freight": 5.0,
        "tariff": 5.0, "inventory_value": 100.0, "inventory_units": 10.0,
    }])


def test_independent_gl_reconciliation_passes_matching_controls():
    gl = parse_gl_control_file("gl.csv", (
        b"date,gl_net_revenue,gl_cogs,gl_inventory_value\n"
        b"2026-01-31,100,60,100\n"
    ))
    result = reconcile_gl(analytical_data(), gl)
    assert (result[["Revenue status", "COGS status", "Inventory status"]] == "PASS").all().all()


def test_gl_reconciliation_reports_variances():
    gl = parse_gl_control_file("gl.csv", (
        b"date,gl_net_revenue,gl_cogs,gl_inventory_value\n"
        b"2026-01-31,98,60,100\n"
    ))
    result = reconcile_gl(analytical_data(), gl)
    assert result.iloc[0]["Revenue status"] == "FAIL"
    assert result.iloc[0]["Revenue variance"] == pytest.approx(2)


def test_gl_duplicate_month_is_rejected():
    with pytest.raises(ValueError, match="one GL control"):
        parse_gl_control_file("gl.csv", (
            b"date,gl_net_revenue,gl_cogs,gl_inventory_value\n"
            b"2026-01-01,100,60,100\n2026-01-31,100,60,100\n"
        ))
