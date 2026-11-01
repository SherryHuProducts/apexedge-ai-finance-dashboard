from pathlib import Path

"""End-to-end Streamlit navigation smoke checks (no external API calls)."""
from streamlit.testing.v1 import AppTest


def test_cfo_landing_renders():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=90).run()
    assert not app.exception


def test_sales_mode_renders():
    app = AppTest.from_file("app.py", default_timeout=90).run()
    app.radio(key="audience_role").set_value("Sales Mode / 销售团队").run()
    assert not app.exception


def test_decision_intelligence_renders_without_api_key():
    app = AppTest.from_file("app.py", default_timeout=90).run()
    app.radio(key="navigation_cfo").set_value("Decision Intelligence / 决策智能").run()
    assert not app.exception
