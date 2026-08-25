"""Pricing: interview counts -> line items -> a total.

The claim under test is narrow and it is the whole reason this module exists:
**an unpriced item does not become zero.** Every amount in the real
`fee-schedule.yaml` is a `[CONFIRM:` until the firm sets one, and the wrong
behaviour — skipping the line, or defaulting it to 0 — would quote a client
nothing for a service and produce a total the firm cannot stand behind.

Money formatting is checked against the "Correct" column of
`SATC Figures and Tables.html`, the same worked example
`invoice-generator/tests/test_money_format.py` uses. Two implementations of one
convention is what that document warns about; testing both against the same
source is how they are kept honest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import money as m  # noqa: E402
import pricing  # noqa: E402

SAMPLES = ROOT / "samples"
EXAMPLE = SAMPLES / "fee-schedule-example.yaml"


@pytest.fixture(scope="module")
def priced():
    return pricing.load(EXAMPLE)


@pytest.fixture(scope="module")
def answers():
    return json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


# ── money ─────────────────────────────────────────────────────────────────

def test_two_decimals_always():
    assert m.money(450) == "$450.00"
    assert m.money(0) == "$0.00"


def test_thousands_separated():
    assert m.money(1225) == "$1,225.00"


def test_negatives_take_parentheses_never_a_minus():
    assert m.money(-1500) == "($1,500.00)"
    assert "-" not in m.money(-1500) and "−" not in m.money(-1500)


def test_credits_drop_the_symbol():
    assert m.money(-1500, symbol=False) == "(1,500.00)"


def test_nil_and_a_computed_zero_are_different():
    assert m.money(None) == "—"
    assert m.money(0) == "$0.00"


def test_an_unset_amount_passes_through_rather_than_becoming_zero():
    """The single most important line in money.py.

    A `[CONFIRM:` turned into $0.00 quotes a client nothing for a service, and
    nothing downstream would ever notice.
    """
    placeholder = "[CONFIRM: fee per state return]"
    assert m.money(placeholder) == placeholder


def test_the_reference_table_renders_exactly():
    """The 'Correct' column of SATC Figures and Tables, line for line."""
    assert m.money(2450) == "$2,450.00"
    assert m.money(1137.5) == "$1,137.50"
    assert m.money(300) == "$300.00"
    assert m.money(-1500, symbol=False) == "(1,500.00)"
    assert m.money(-116.63, symbol=False) == "(116.63)"


# ── the real schedule is unpriced, on purpose ─────────────────────────────

def test_the_firms_schedule_is_still_unpriced():
    """Guards the §9 rule: fee figures are a human's to set.

    When Arjun prices the firm this test starts failing, and the right fix is
    to delete it — not to put the placeholders back.
    """
    assert pricing.open_amounts(), (
        "registry/fee-schedule.yaml now has prices. If they are the firm's "
        "real ones, delete this test."
    )


def test_an_unpriced_schedule_refuses_to_total(answers):
    out = pricing.price(answers)          # the real, unpriced schedule
    assert "[CONFIRM:" in out["EstimateTotal"]
    assert any("[CONFIRM:" in i["Amount"] for i in out["LineItems"])


def test_the_refusal_names_what_is_unpriced(answers):
    """A total that just said "cannot compute" would send you hunting."""
    total = pricing.price(answers)["EstimateTotal"]
    assert "Federal Form 1040" in total and "State return" in total


def test_one_unpriced_line_poisons_the_whole_total(priced):
    """Not just the unpriced line. A total that silently omits one is a quote
    the firm cannot stand behind."""
    schedule = json.loads(json.dumps(priced))       # deep copy
    schedule["per_unit"]["state_return"]["amount"] = "[CONFIRM: not set]"
    out = pricing.price({"federal_form": "1040", "count_states": 1}, schedule)
    assert "[CONFIRM:" in out["EstimateTotal"]


# ── pricing, with numbers ─────────────────────────────────────────────────

def test_the_sample_interview_prices_and_totals(answers, priced):
    out = pricing.price(answers, priced)
    assert out["EstimateTotal"] == "$1,225.00", \
        "$175 lower than it was: the sample's cleanup band was a priced line "\
        "and cleanup is no longer priced at all"
    assert [i["Service"] for i in out["LineItems"]] == [
        "Federal Form 1040", "State return", "Local return", "Rental property",
        "Schedule K-1 received", "Sole proprietorship",
    ], "cleanup is an assumption now, so it appears in words, not as a line"


def test_the_total_is_the_sum_of_the_lines(answers, priced):
    """Computed, never typed -- and a client will add the column up."""
    items = pricing.line_items(answers, priced)
    assert m.money(sum(i["_raw"] for i in items)) == \
        pricing.estimate_total(items, priced)


def test_a_count_above_one_shows_its_working(answers, priced):
    """2 K-1s at $75 must read as "2 x $75.00", not an unexplained $150."""
    k1 = next(i for i in pricing.line_items(answers, priced)
              if i["Service"] == "Schedule K-1 received")
    assert k1["Amount"] == "$150.00"
    assert "2 × $75.00" in k1["Detail"]


def test_a_zero_count_produces_no_line(priced):
    services = [i["Service"] for i in
                pricing.line_items({"federal_form": "1040", "count_rentals": 0}, priced)]
    assert "Rental property" not in services


def test_an_assumed_item_never_becomes_a_line(priced):
    """Brokerage and cleanup carry no price, so they carry no line. A row
    reading "Records cleanup - hourly" is a term of business wearing a line
    item's clothes; terms belong in the assumptions block, in words."""
    services = [i["Service"] for i in
                pricing.line_items({"federal_form": "1040",
                                    "brokerage_band": "heavy",
                                    "cleanup_band": "heavy"}, priced)]
    assert "Brokerage activity" not in services
    assert "Records cleanup" not in services


def test_base_covers_one_included_stops_double_charging(priced):
    """When the base covers the first state, one state must cost nothing more."""
    schedule = json.loads(json.dumps(priced))
    schedule["base_covers"] = "one_included"
    items = pricing.line_items({"federal_form": "1040", "count_states": 1}, schedule)
    assert [i["Service"] for i in items] == ["Federal Form 1040"]

    items = pricing.line_items({"federal_form": "1040", "count_states": 3}, schedule)
    state = next(i for i in items if i["Service"] == "State return")
    assert state["_raw"] == 185 * 2, "only the states beyond the first are charged"


def test_an_undecided_base_covers_is_carried_not_guessed():
    """The structure itself is a [CONFIRM]. The base line cannot honestly
    describe what it covers, so it carries the question."""
    out = pricing.price({"federal_form": "1040"})
    base = out["LineItems"][0]
    assert "[CONFIRM:" in base["Detail"]


def test_an_unknown_federal_form_raises(priced):
    with pytest.raises(pricing.PricingError):
        pricing.line_items({"federal_form": "990"}, priced)


def test_every_assumed_item_produces_a_sentence_every_time(priced):
    """Not only when something looks unusual. An assumption a client hears
    about after it fails is not an assumption, it is a surprise."""
    lines = pricing.assumptions({}, priced)
    assert len(lines) == len(priced["assumed"])
    for spec in priced["assumed"].values():
        assert any(spec["label"] in line for line in lines)


def test_an_assumption_names_the_rate_the_overage_is_billed_at(priced):
    """The sentence is the only place a client is told what happens when the
    assumption fails, so it has to carry the number."""
    rate = priced["basis"]["rate"]
    assert all(f"${rate:,.0f} an hour" in line for line in pricing.assumptions({}, priced))


def test_an_assumed_item_missing_its_trigger_raises(priced):
    """A boundary nobody stated is not a boundary."""
    schedule = json.loads(json.dumps(priced))
    schedule["assumed"]["cleanup"]["trigger"] = ""
    with pytest.raises(pricing.PricingError, match="trigger"):
        pricing.assumptions({}, schedule)


def test_requoting_is_refused_because_the_firm_ruled_it_out(priced):
    """`beyond: requote` would need a workflow that stops the job and waits for
    a second signature. That was ruled out on purpose, so the schedule may not
    quietly ask for it."""
    schedule = json.loads(json.dumps(priced))
    schedule["assumed"]["cleanup"]["beyond"] = "requote"
    with pytest.raises(pricing.PricingError, match="re-quoting"):
        pricing.assumptions({}, schedule)


def test_line_items_carry_exactly_the_fields_the_template_wants(answers, priced):
    """The registry says LineItems has Amount, Detail, Service. A stray key is
    a field the estimate will not print and nobody will miss."""
    for item in pricing.price(answers, priced)["LineItems"]:
        assert set(item) == {"Service", "Detail", "Amount"}


def test_the_price_always_carries_its_assumptions(answers, priced):
    """They are part of the price, not an optional garnish on it: they say
    what it covers and where it stops.

    This test exists because the first wiring left them out of `price()`. The
    estimate rendered clean and simply had no assumptions block -- the merge
    engine treats an [[EACH]] over a missing list as an empty one, so nothing
    anywhere failed. The document just quietly stopped telling the client what
    the fee assumed."""
    out = pricing.price(answers, priced)
    assert out["Assumptions"], "an estimate with no assumptions states no boundary"
    assert len(out["Assumptions"]) == len(priced["assumed"])
    assert all(set(a) == {"Text"} for a in out["Assumptions"])
    assert all(a["Text"].strip().endswith(".") for a in out["Assumptions"])
