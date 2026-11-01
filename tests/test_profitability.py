import pandas as pd
import pytest

from profitability import margin_driver_bridge
from cost_attribution import channel_unit_economics, validate_cost_bridge


def example():
    return pd.DataFrame([
        dict(date="2026-01-01", sku="A", channel="DTC", units=10, gross_sales=110,
             discount=10, returns=0, net_revenue=100, product_cost=50, freight=5,
             tariff=5, gross_profit=40, platform_fee=4, marketing_spend=5,
             contribution_profit=31),
        dict(date="2026-01-01", sku="B", channel="DTC", units=5, gross_sales=100,
             discount=0, returns=0, net_revenue=100, product_cost=40, freight=5,
             tariff=5, gross_profit=50, platform_fee=3, marketing_spend=8,
             contribution_profit=39),
        dict(date="2026-02-01", sku="A", channel="DTC", units=12, gross_sales=144,
             discount=12, returns=0, net_revenue=132, product_cost=62, freight=7,
             tariff=6, gross_profit=57, platform_fee=5, marketing_spend=7,
             contribution_profit=45),
        dict(date="2026-02-01", sku="B", channel="DTC", units=4, gross_sales=84,
             discount=0, returns=0, net_revenue=84, product_cost=34, freight=4,
             tariff=4, gross_profit=42, platform_fee=3, marketing_spend=7,
             contribution_profit=32),
    ])


def test_bridge_reconciles_exact_change():
    result = margin_driver_bridge(example())
    delta = result["current_profit"] - result["prior_profit"]
    assert delta == pytest.approx(9)
    assert sum(result["effects"].values()) == pytest.approx(delta, abs=.01)
    assert abs(result["residual"]) < .01


def test_bridge_rejects_bad_gross_profit():
    bad = example()
    bad.loc[0, "gross_profit"] = 50
    with pytest.raises(ValueError, match="does not reconcile"):
        margin_driver_bridge(bad)


def test_cost_attribution_reconciles_contribution_profit():
    data = example()
    validate_cost_bridge(data)
    totals = channel_unit_economics(data)
    assert totals.iloc[0]["gross_profit"] == pytest.approx(data["gross_profit"].sum())
    assert totals.iloc[0]["contribution_profit"] == pytest.approx(data["contribution_profit"].sum())


def test_cost_attribution_flags_double_counting():
    bad = example()
    bad.loc[0, "contribution_profit"] += 5
    with pytest.raises(ValueError, match="Contribution profit"):
        validate_cost_bridge(bad)


def test_bridge_handles_new_sku_as_volume_mix_not_invented_price():
    data = example()
    new_sku = dict(data.iloc[-1])
    new_sku["sku"] = "NEW"
    new_sku["gross_profit"] = new_sku["net_revenue"] - new_sku["product_cost"] - new_sku["freight"] - new_sku["tariff"]
    data = pd.concat([data, pd.DataFrame([new_sku])], ignore_index=True)
    result = margin_driver_bridge(data)
    assert sum(result["effects"].values()) == pytest.approx(result["current_profit"] - result["prior_profit"], abs=.01)
