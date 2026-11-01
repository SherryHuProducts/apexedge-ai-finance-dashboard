import pandas as pd
import pytest

from sales_metrics import commercial_summary, commercial_segments, commercial_worklist
from cost_attribution import channel_unit_economics


def sample():
    return pd.DataFrame([
        dict(date="2026-01-01", sku="A", channel="DTC", units=10,
             gross_sales=110, discount=10, returns=0, net_revenue=100,
             product_cost=50, freight=5, tariff=5, platform_fee=4,
             marketing_spend=5, gross_profit=40, contribution_profit=31),
        dict(date="2026-01-01", sku="B", channel="TikTok", units=20,
             gross_sales=240, discount=20, returns=20, net_revenue=200,
             product_cost=100, freight=10, tariff=10, platform_fee=30,
             marketing_spend=20, gross_profit=80, contribution_profit=30),
    ])


def test_shared_sales_and_finance_totals_reconcile():
    frame = sample()
    summary = commercial_summary(frame)
    sales_channels = commercial_segments(frame, ["channel"])
    finance_channels = channel_unit_economics(frame)
    assert summary["net_revenue"] == pytest.approx(300)
    assert summary["contribution_profit"] == pytest.approx(61)
    assert sales_channels["net_revenue"].sum() == pytest.approx(finance_channels["net_revenue"].sum())
    assert sales_channels["contribution_profit"].sum() == pytest.approx(finance_channels["contribution_profit"].sum())


def test_sales_worklist_is_deterministic_and_review_only():
    worklist = commercial_worklist(sample())
    assert len(worklist) == 2
    assert "recommended_review" in worklist
    assert worklist["recommended_review"].str.len().gt(0).all()


def test_sales_missing_units_is_reported_not_zero():
    frame = sample().drop(columns="units")
    assert commercial_summary(frame)["units"] is None
    assert "units" not in commercial_segments(frame, ["channel"])


def test_sales_return_rate_uses_net_of_discount_base():
    summary = commercial_summary(sample())
    assert summary["return_rate"] == pytest.approx(20 / 320 * 100)
