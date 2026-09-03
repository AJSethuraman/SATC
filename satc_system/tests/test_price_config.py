"""Prices live in YAML and the owner edits them by hand — so an edit has to
take effect, and a bad edit has to be loud.

The failure this guards against is the quiet one: change a rate, see the old
rate on the next invoice, and never find out why.
"""

from decimal import Decimal

import pytest

from satc.billing import catalogue
from satc.config import ConfigError

SERVICES = """
services:
  - code: return_1040
    name: "Individual return"
    client_label: "Your federal individual tax return"
    category: "Tax returns"
    unit: fixed
    standard_rate: {rate}
"""

PLANS = """
meta:
  default_plan: standard
plans:
  - key: standard
    name: "Standard"
    discount_pct: 0
"""


@pytest.fixture
def prices(tmp_path, monkeypatch):
    """A billing config the test owns, wired in where the app reads from."""
    folder = tmp_path / "billing"
    folder.mkdir()
    (folder / "rate_plans.yaml").write_text(PLANS, encoding="utf-8")
    monkeypatch.setattr(catalogue, "billing_dir", lambda *a, **k: folder)
    catalogue.forget_prices()
    yield folder
    catalogue.forget_prices()


def write_rate(folder, rate):
    (folder / "services.yaml").write_text(SERVICES.format(rate=rate), encoding="utf-8")


def test_changing_a_rate_takes_effect_without_a_restart(prices):
    write_rate(prices, 450)
    assert catalogue.service("return_1040").standard_rate == Decimal(450)

    write_rate(prices, 495)
    assert catalogue.service("return_1040").standard_rate == Decimal(495), (
        "A price edit that needs an app restart is a price edit that silently "
        "did not happen — the owner would invoice at the old rate.")


def test_adding_a_service_makes_it_pickable_immediately(prices):
    write_rate(prices, 450)
    assert "planning_session" not in catalogue.services()

    (prices / "services.yaml").write_text(SERVICES.format(rate=450) + """
  - code: planning_session
    name: "Planning conversation"
    client_label: "Tax planning conversation"
    category: "Advice"
    unit: per_hour
    standard_rate: 200
""", encoding="utf-8")
    assert catalogue.service("planning_session").standard_rate == Decimal(200)


def test_an_unchanged_file_is_not_re_read(prices):
    """Cheap enough to check on every page load, because it usually does nothing."""
    write_rate(prices, 450)
    assert catalogue.services() is catalogue.services()


def test_a_broken_edit_refuses_rather_than_serving_the_old_prices(prices):
    """Principle 5. Falling back to the last good version would mean billing at
    a rate that is no longer in the file the owner is looking at."""
    write_rate(prices, 450)
    assert catalogue.service("return_1040")

    (prices / "services.yaml").write_text(SERVICES.format(rate="four hundred"),
                                          encoding="utf-8")
    with pytest.raises(ConfigError) as refusal:
        catalogue.services()
    assert "return_1040" in str(refusal.value)


def test_a_contingent_fee_cannot_be_added_by_editing_the_file(prices):
    """The config is the easy way in, so the Circular 230 §10.27 guard has to
    live at load, not at invoice time."""
    (prices / "services.yaml").write_text("""
services:
  - code: refund_share
    name: "Refund share"
    client_label: "Our fee — 10% of refund"
    category: "Tax returns"
    unit: fixed
    standard_rate: 0
""", encoding="utf-8")
    with pytest.raises(ConfigError) as refusal:
        catalogue.services()
    assert "10.27" in str(refusal.value)
