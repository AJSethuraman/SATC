"""Deriving the fee schedule from hours × a rate.

The firm has never priced itself and has no past invoices to read prices off,
so "what do you charge for a K-1?" has no answer. "How long does a K-1 take
you?" does. This module does that multiplication.

What the tests defend is the same claim `test_pricing.py` defends from the
other side: **nothing here may invent a number.** A blank hour count must stay
a `[CONFIRM:`, a missing rate must refuse rather than default, and rounding —
which is a pricing policy — must stay off until asked for.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fees  # noqa: E402
import pricing  # noqa: E402

EXAMPLE_HOURS = ROOT / "samples" / "fee-hours-example.yaml"


@pytest.fixture(scope="module")
def blank():
    """The firm's real schedule: every amount still open."""
    return pricing.load()


@pytest.fixture(scope="module")
def hours():
    raw = yaml.safe_load(EXAMPLE_HOURS.read_text(encoding="utf-8"))
    raw.pop("rate"), raw.pop("base_covers")
    return raw


# ── the multiplication ────────────────────────────────────────────────────

def test_a_fee_is_hours_times_the_rate(blank):
    out = fees.derive(175, {"base.1040": 2.5}, schedule=blank)
    assert out["base"]["1040"] == 437.5


def test_a_full_sitting_prices_everything(hours, blank):
    out = fees.derive(175, hours, base_covers="federal_only", schedule=blank)
    assert fees.still_open(out) == []


def test_the_result_actually_prices_an_interview(hours, blank):
    """The point of the exercise: a schedule the estimate can render from."""
    out = fees.derive(175, hours, base_covers="federal_only", schedule=blank)
    priced = pricing.price({"federal_form": "1040", "count_states": 1,
                            "count_k1s": 2}, out)
    # 2.5h + 1h + (2 x 0.4h) = 4.3h at $175. Written as the arithmetic rather
    # than as a total, because a bare "$752.50" is unfalsifiable by eye.
    assert priced["EstimateTotal"] == "$752.50" == \
        f"${(2.5 + 1 + 0.4 * 2) * 175:,.2f}"
    assert "[CONFIRM:" not in priced["EstimateTotal"]


# ── what it refuses to invent ─────────────────────────────────────────────

def test_an_item_left_blank_stays_unpriced(blank):
    """The whole failure mode. A preparer who knows what a 1040 takes and
    genuinely does not know what heavy cleanup takes must be able to say so."""
    out = fees.derive(175, {"base.1040": 2.5}, schedule=blank)
    still = dict(fees.still_open(out))
    assert "bands.cleanup.values.heavy.amount" in still
    assert "base.1040" not in still


def test_a_partial_sitting_still_refuses_to_total(blank):
    out = fees.derive(175, {"base.1040": 2.5}, schedule=blank)
    assert "[CONFIRM:" in pricing.price(
        {"federal_form": "1040", "count_states": 1}, out)["EstimateTotal"]


def test_hours_with_no_rate_refuse_rather_than_default(blank):
    with pytest.raises(fees.FeeBasisError):
        fees.derive(None, {"base.1040": 2.5}, schedule=blank)


def test_a_rate_of_zero_is_refused(blank):
    with pytest.raises(fees.FeeBasisError):
        fees.derive(0, {"base.1040": 2.5}, schedule=blank)


def test_negative_hours_are_refused(blank):
    with pytest.raises(fees.FeeBasisError):
        fees.derive(175, {"base.1040": -1}, schedule=blank)


def test_an_hours_key_that_prices_nothing_is_refused(blank):
    """A typo'd path that silently priced nothing would look like a blank."""
    with pytest.raises(fees.FeeBasisError):
        fees.derive(175, {"base.1041": 2}, schedule=blank)


def test_base_covers_is_not_guessed(blank):
    """It changes every number under it, so it is answered or left open."""
    out = fees.derive(175, {"base.1040": 2.5}, schedule=blank)
    assert pricing.is_open(out["base_covers"])
    with pytest.raises(fees.FeeBasisError):
        fees.derive(175, {}, base_covers="whatever", schedule=blank)


# ── rounding is a policy, not a default ───────────────────────────────────

def test_rounding_is_off_unless_asked_for(blank):
    assert fees.derive(175, {"base.1040": 2.5}, schedule=blank)["base"]["1040"] == 437.5


def test_rounding_goes_up_to_the_firms_increment(blank):
    out = fees.derive(175, {"base.1040": 2.5}, increment=25, schedule=blank)
    assert out["base"]["1040"] == 450


def test_an_amount_already_on_the_increment_does_not_jump(blank):
    out = fees.derive(100, {"base.1040": 4.5}, increment=25, schedule=blank)
    assert out["base"]["1040"] == 450


# ── writing back ──────────────────────────────────────────────────────────

def test_the_write_keeps_every_comment(blank):
    """The file is two thirds comment and the comments are what make it
    fillable by hand. A YAML dump would produce a valid file that had lost
    all of them."""
    src = fees.SCHEDULE.read_text(encoding="utf-8")
    out = fees.derive(175, {"base.1040": 2.5}, schedule=blank)
    written = fees.apply_to_text(src, blank, out)
    assert written.count("#") == src.count("#")
    assert "TO PRICE THE FIRM" in written


def test_the_write_changes_only_what_was_priced(blank):
    src = fees.SCHEDULE.read_text(encoding="utf-8")
    out = fees.derive(175, {"base.1040": 2.5}, schedule=blank)
    written = fees.apply_to_text(src, blank, out)
    diff = [(a, b) for a, b in zip(src.splitlines(), written.splitlines()) if a != b]
    assert len(diff) == 1 and "1040" in diff[0][1]


def test_what_was_written_parses_back_to_what_was_derived(blank):
    src = fees.SCHEDULE.read_text(encoding="utf-8")
    out = fees.derive(175, dict.fromkeys((p for p, _ in fees.ITEMS), 2),
                      base_covers="one_included", schedule=blank)
    assert yaml.safe_load(fees.apply_to_text(src, blank, out)) == out


def test_a_whole_number_writes_without_a_trailing_point_zero(blank):
    """`450.0` in a fee schedule reads like a rounding error."""
    src = fees.SCHEDULE.read_text(encoding="utf-8")
    out = fees.derive(180, {"base.1040": 2.5}, schedule=blank)
    written = fees.apply_to_text(src, blank, out)
    assert '"1040":  450\n' in written


def test_an_ambiguous_rewrite_refuses_rather_than_editing_the_wrong_line(blank):
    """Once amounts are plain numbers, `450` may occur twice and there is no
    safe way to tell which line was meant."""
    src = 'base:\n  "1040": 450\n  "1065": 450\n'
    before = {"base": {"1040": 450, "1065": 450}}
    after = {"base": {"1040": 500, "1065": 450}}
    with pytest.raises(fees.FeeBasisError):
        fees._sub_once(src, "450", "500", "base.1040")


# ── the prompts ───────────────────────────────────────────────────────────

def test_every_priceable_amount_has_a_prompt(blank):
    """If the schedule grows an amount and ITEMS does not, that amount can
    never be derived and nothing would say so."""
    derivable = {p for p, _ in fees.ITEMS}
    for path, _ in pricing.open_amounts(blank):
        if path in fees.NOT_DERIVED:
            continue
        assert path in derivable, f"{path} has no prompt in fees.ITEMS"


def test_every_prompt_points_at_something_real(blank):
    for path, meaning in fees.ITEMS:
        fees._dig(blank, path)
        assert meaning and meaning[0].islower(), path


def test_the_example_hours_are_labelled_fictional():
    """Same guard the example schedule carries. A file of plausible hours is
    one copy-paste from becoming the firm's prices."""
    head = EXAMPLE_HOURS.read_text(encoding="utf-8")[:200].upper()
    assert "EXAMPLE ONLY" in head and "FICTIONAL" in head


# ── what a price buys, in hours ───────────────────────────────────────────
#
# The inverse of derivation, and the half that gets used daily: `price` is run
# once when the firm sets its fees; `hours` is run whenever someone wants to
# know how long a job has before it stops earning its rate.

def test_the_rate_comes_from_the_schedule_not_the_caller():
    """A budget that depended on what the caller typed would not be an
    expectation. It would be an opinion held once."""
    rate, step, floor = fees.basis_of(pricing.load())
    assert rate > 0 and step > 0
    assert floor > 0, "with no floor, nothing can ever be flagged as under it"


def test_a_schedule_with_no_rate_yields_no_budgets_and_says_so():
    with pytest.raises(fees.FeeBasisError, match="basis.rate"):
        fees.basis_of({"base": {"1040": 170}})


def test_hours_are_rounded_to_the_unit_time_is_booked_in():
    """1.133 h cannot be entered on a timesheet; 1.25 can."""
    b = fees.hours_for(170, 150, step=0.25)
    assert b.raw == pytest.approx(170 / 150)
    assert b.hours == 0.25 * round((170 / 150) / 0.25) == 1.25


def test_rounding_is_to_nearest_not_up():
    """Rounding a budget up hands back time the price never paid for.
    $800 / $150 is 5.33 h, which is nearer 5.25 than 5.50."""
    assert fees.hours_for(800, 150).hours == 5.25


def test_the_floor_is_reported_and_never_applied():
    """A $30 line does not become a $37.50 line because the firm has a
    fifteen-minute minimum. It becomes a line worth asking about."""
    b = fees.hours_for(30, 150, floor=0.25)
    assert b.under_floor is True
    assert b.raw == pytest.approx(0.2), "the honest number survives the flag"
    assert fees.hours_for(60, 150, floor=0.25).under_floor is False


def test_a_half_priced_schedule_yields_half_a_budget():
    """Absent, not zero. A schedule that is partly priced is partly budgeted,
    which is the truth about it."""
    schedule = copy.deepcopy(pricing.load())
    fees._plant(schedule, "base.1040", 170)
    budgets = fees.expected_hours(schedule)
    assert set(budgets) == {"base.1040"}
    assert budgets["base.1040"].hours == 1.25


def test_every_priceable_item_can_carry_a_budget():
    """Whatever `price` can set, `hours` can read back. If ITEMS grows and the
    budget side is not taught about it, the new line would silently have no
    expectation attached."""
    schedule = copy.deepcopy(pricing.load())
    for path, _ in fees.ITEMS:
        fees._plant(schedule, path, 300)
    assert set(fees.expected_hours(schedule)) == {p for p, _ in fees.ITEMS}


def test_a_price_and_its_budget_agree_at_the_rate():
    """The round trip that does hold: hours -> price -> hours, when the hours
    were already a multiple of the booking unit."""
    rate, _, _ = fees.basis_of(pricing.load())
    priced = fees.derive(rate, {"base.1040": 2.5}, schedule=copy.deepcopy(pricing.load()))
    assert fees._dig(priced, "base.1040") == 2.5 * rate
    assert fees.expected_hours(priced)["base.1040"].hours == 2.5
