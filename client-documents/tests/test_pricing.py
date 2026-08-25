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


def _with_one_unpriced(path=("per_unit", "rental", "amount")):
    """The real schedule with one amount blanked.

    This used to just be `pricing.load()`, because every amount in the real
    file was open. They are set now, which is the point of the work -- so the
    refusal path needs a schedule that is deliberately incomplete rather than
    one that happens to be.
    """
    s = json.loads(json.dumps(pricing.load()))
    node = s
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = "[CONFIRM: deliberately unset, for the refusal tests]"
    return s


def test_an_unpriced_schedule_refuses_to_total(answers):
    s = _with_one_unpriced()
    out = pricing.price(answers, s)
    assert "[CONFIRM:" in out["EstimateTotal"]
    assert any("[CONFIRM:" in i["Amount"] for i in out["LineItems"])


def test_the_refusal_names_what_is_unpriced(answers):
    """A total that just said "cannot compute" would send you hunting.

    Asserted against the lines themselves rather than against two fixed
    strings: the base line used to read "Federal Form 1040" and now reads
    whichever package the client's answers select, and the promise being kept
    is that the total names every line it could not price -- not that it
    names any particular one.
    """
    out = pricing.price(answers, _with_one_unpriced())
    total = out["EstimateTotal"]
    unpriced = [i["Service"] for i in out["LineItems"] if "[CONFIRM:" in i["Amount"]]
    assert unpriced, "this fixture is meant to exercise the unpriced path"
    for name in unpriced:
        assert name in total, f"the refusal does not say {name!r} is the problem"


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


def test_an_undecided_base_covers_is_carried_not_guessed(priced):
    """The structure itself can be a [CONFIRM]. When it is, the base line
    cannot honestly describe what it covers, so it carries the question.

    The firm answered this on 25 August -- the default package is a 1040, the
    first state and the first locality -- so the real schedule no longer
    exercises the path. The behaviour still has to hold for the next schedule
    that leaves it open, which is what this builds."""
    schedule = json.loads(json.dumps(priced))
    schedule["base_covers"] = "[CONFIRM: federal_only or one_included?]"
    base = pricing.line_items({"federal_form": "1040"}, schedule)[0]
    assert "[CONFIRM:" in base["Detail"]


def test_the_firms_base_says_what_the_package_includes():
    """The client should read what they are getting on the line rather than
    infer it from an absence.

    This used to assert the words "Includes the first state and locality",
    which was the flat base fee describing itself. The base is a ladder now,
    so the line names the package and the gate that selected it -- the same
    promise, carrying more information, and the thing that makes a wrong
    package visible on the page before it reaches anyone.
    """
    base = pricing.line_items({"federal_form": "1040"})[0]
    assert base["Service"] == "Essentials"
    assert base["Detail"] == "No schedules"


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


# ── tiers ─────────────────────────────────────────────────────────────────
#
# One price for "a Schedule C" is wrong at both ends. A driver on standard
# mileage who kept a trip log is data entry on a return already being prepared;
# a shop with inventory and payroll is not. Tiers split that, and they split it
# on FACTS the client can answer — which is what makes them different from the
# brokerage and cleanup bands that were deleted.

def test_a_tier_supplies_the_whole_line(priced):
    items = pricing.line_items(
        {"federal_form": "1040", "count_businesses": 1,
         "schedule_c_kind": "simple"}, priced)
    c = next(i for i in items if "Gig" in i["Service"])
    assert c["Service"] == "Gig or contract work"
    assert "standard mileage" in c["Detail"]
    assert c["_raw"] == 60


def test_the_tier_changes_the_price_and_the_words(priced):
    def one(kind):
        return next(i for i in pricing.line_items(
            {"federal_form": "1040", "count_businesses": 1,
             "schedule_c_kind": kind}, priced) if i["_raw"] in (60, 225))
    assert one("simple")["_raw"] == 60
    assert one("standard")["_raw"] == 225
    assert one("simple")["Service"] != one("standard")["Service"]


def test_an_unanswered_tier_is_carried_not_defaulted(priced):
    """The cheapest tier is the tempting default and the wrong one: it would
    quote a business with inventory at a gig-worker's fee, and nothing
    downstream would notice."""
    items = pricing.line_items(
        {"federal_form": "1040", "count_businesses": 1}, priced)
    c = items[-1]
    assert "[CONFIRM:" in c["Amount"]
    assert "schedule_c_kind" in c["Amount"]
    assert "[CONFIRM:" in pricing.estimate_total(items, priced)


def test_a_tier_that_is_not_a_tier_raises(priced):
    with pytest.raises(pricing.PricingError, match="not a tier"):
        pricing.line_items({"federal_form": "1040", "count_businesses": 1,
                            "schedule_c_kind": "medium"}, priced)


def test_tiers_without_a_tier_from_raise(priced):
    schedule = json.loads(json.dumps(priced))
    del schedule["per_unit"]["schedule_c"]["tier_from"]
    with pytest.raises(pricing.PricingError, match="tier_from"):
        pricing.line_items({"federal_form": "1040", "count_businesses": 1,
                            "schedule_c_kind": "simple"}, schedule)


def test_a_tier_missing_a_field_raises_rather_than_printing_blank(priced):
    schedule = json.loads(json.dumps(priced))
    del schedule["per_unit"]["schedule_c"]["tiers"]["simple"]["detail"]
    with pytest.raises(pricing.PricingError, match="detail"):
        pricing.line_items({"federal_form": "1040", "count_businesses": 1,
                            "schedule_c_kind": "simple"}, schedule)


def test_a_tier_priced_at_zero_still_prints_its_line(priced):
    """"Included" is a thing the client should SEE. A zero-priced tier that
    silently vanished would look like work nobody did."""
    schedule = json.loads(json.dumps(priced))
    schedule["per_unit"]["schedule_c"]["tiers"]["simple"]["amount"] = 0
    items = pricing.line_items({"federal_form": "1040", "count_businesses": 1,
                                "schedule_c_kind": "simple"}, schedule)
    c = next(i for i in items if "Gig" in i["Service"])
    assert c["Amount"] == "$0.00"


def test_a_tier_is_still_counted(priced):
    """Two gig businesses are two of them, and the line shows its working."""
    c = next(i for i in pricing.line_items(
        {"federal_form": "1040", "count_businesses": 2,
         "schedule_c_kind": "simple"}, priced) if "Gig" in i["Service"])
    assert c["_raw"] == 120 and "2 × $60.00" in c["Detail"]


def test_an_untiered_item_is_untouched(priced):
    """The mechanism is opt-in. Every other per-unit line still prices flat."""
    k1 = next(i for i in pricing.line_items(
        {"federal_form": "1040", "count_k1s": 1}, priced)
        if i["Service"] == "Schedule K-1 received")
    assert k1["_raw"] == 75


def test_there_is_no_tier_that_only_repeats_its_neighbour():
    """A third Schedule C tier -- inventory, employees, its own books -- was
    drafted and removed. Every engagement already assumes records arrive
    reconciled; hold that and a bookkeeping-heavy Schedule C is the same work
    on a longer trial balance. What makes it expensive is the assumption
    failing, which is priced hourly somewhere else entirely.

    A tier carrying its neighbour's price is a question the client must answer
    that changes nothing, so this refuses to let one back in by accident."""
    tiers = pricing.load()["per_unit"]["schedule_c"]["tiers"]
    assert set(tiers) == {"simple", "standard"}


def test_every_tier_has_a_question_option_and_every_option_has_a_tier():
    """The interview asks which tier; the fee schedule prices it. Nothing keeps
    those two lists in step, and they fell out of step the moment Schedule C
    went from three tiers to two: the question kept a third answer -- inventory,
    employees, or its own set of books -- that no longer named a price.

    That failure is quiet in the worst way. `_resolve_tier` raises on an unknown
    tier, so a client who picks the orphaned answer does not get a wrong number;
    they get an estimate that will not build, at the point the firm is trying to
    send it. This test is the thing that should have caught it.
    """
    import interview as iv

    schedule = pricing.load()
    questions = {q["id"]: q for _, q in iv.all_questions(iv.load_schema())}

    tiered = {name: unit for name, unit in schedule["per_unit"].items()
              if unit.get("tiers")}
    assert tiered, "no tiered items -- this test has stopped testing anything"

    for name, unit in tiered.items():
        key = unit["tier_from"]
        assert key in questions, f"{name}.tier_from names {key!r}, which the interview never asks"
        offered = {o["value"] for o in questions[key]["options"]}
        priced = set(unit["tiers"])
        assert offered == priced, (
            f"{name}: the interview offers {sorted(offered)} but the schedule "
            f"prices {sorted(priced)}. An answer with no tier stops the estimate; "
            f"a tier with no answer is unreachable."
        )


# ── counting is not a place to be generous ────────────────────────────────
#
# Three probes against the real engine found the same shape of bug three
# times: an answer that is not a count being treated as one. None of them
# raised; each produced a confident, wrong number. That is the worst failure
# available here, because a total nobody questions is a total that gets sent.

def test_a_record_with_no_federal_form_is_refused_not_priced(priced):
    """The one that would have shipped a bill for nothing.

    `line_items` guarded the base fee with `if form:` and then went on to
    price the per-unit lines regardless, so a record that had lost its
    `federal_form` produced an estimate for the ADD-ONS ALONE -- three K-1s,
    a confident total, and no return anywhere in it. An unknown form already
    raised; a missing one has to raise for the same reason.
    """
    with pytest.raises(pricing.PricingError, match="federal form"):
        pricing.line_items({"count_k1s": 3}, priced)


def test_a_boolean_is_not_a_count(priced):
    """`int(True)` is 1, so a yes/no answer wired to a count question would
    quietly bill for exactly one of whatever it was counting. Nothing in the
    interview does that today; the packages about to be built key on facts,
    which makes it a question of when rather than whether.
    """
    with pytest.raises(pricing.PricingError, match="not a count"):
        pricing.line_items({"federal_form": "1040", "count_k1s": True}, priced)


def test_a_fractional_count_is_refused_rather_than_truncated(priced):
    """2.7 K-1s was silently 2. Nobody has 2.7 K-1s, so the answer is wrong
    rather than imprecise, and rounding it hides that.
    """
    with pytest.raises(pricing.PricingError, match="not a count"):
        pricing.line_items({"federal_form": "1040", "count_k1s": 2.7}, priced)


def test_text_where_a_count_belongs_is_still_nothing(priced):
    """The forgiving case, kept deliberately: an empty or unanswered count is
    absence, not an error. Only a value that LOOKS like a count and is not one
    is refused.
    """
    for blank in (None, "", "   "):
        items = pricing.line_items(
            {"federal_form": "1040", "count_k1s": blank}, priced)
        assert [i["Service"] for i in items] == ["Federal Form 1040"]


# ── the individual ladder ─────────────────────────────────────────────────
#
# "The highest package whose gate is met." The tiers are read top to bottom
# and the last matching one wins, so a client with a gig Schedule C and a
# rental is Property & Business without anyone deciding it at the call.

def _pkg(answers, schedule=None):
    """The package line, which is always the first line on the estimate."""
    return pricing.line_items({"federal_form": "1040", **answers},
                              schedule if schedule is not None else pricing.load())[0]


def test_no_schedules_is_essentials():
    assert _pkg({"federal_schedules": []})["Amount"] == "$200.00"


def test_itemising_is_standard():
    assert _pkg({"federal_schedules": ["A"]})["Amount"] == "$325.00"


def test_a_gig_schedule_c_stays_in_standard():
    line = _pkg({"federal_schedules": ["C", "SE"], "schedule_c_kind": "simple"})
    assert line["Service"] == "Standard"


def test_a_full_schedule_c_is_property_and_business():
    line = _pkg({"federal_schedules": ["C", "SE"], "schedule_c_kind": "standard"})
    assert line["Service"] == "Property & Business"
    assert line["Amount"] == "$500.00"


def test_a_rental_is_property_and_business():
    assert _pkg({"federal_schedules": ["E1"]})["Service"] == "Property & Business"


def test_the_highest_gate_wins_not_the_first():
    """A gig Schedule C alone is Standard. Add a rental and the same client is
    Property & Business -- the ladder is walked to the end, not short-circuited
    at the first match."""
    both = _pkg({"federal_schedules": ["C", "E1"], "schedule_c_kind": "simple"})
    assert both["Service"] == "Property & Business"


def test_a_ticked_schedule_with_no_count_still_lands_in_the_right_package():
    """The trap this design exists to avoid.

    A client ticks "Schedule E page 1 -- rentals" and leaves `count_rentals`
    blank. A gate written as "count_rentals > 0" reads that as no rentals and
    sends a landlord to the CHEAPEST package. Gates key on what is ON the
    return, never on how many, precisely because a count can be blank and a
    ticked box cannot.
    """
    line = _pkg({"federal_schedules": ["E1"]})            # no count at all
    assert line["Service"] == "Property & Business"


def test_the_package_line_says_which_gate_selected_it():
    """A wrong pick has to be visible on the page before it reaches a client."""
    line = _pkg({"federal_schedules": ["A"]})
    assert line["Detail"], "the package line must explain itself"


def test_starter_cannot_be_derived_and_says_so():
    """Starter's gate is a [CONFIRM:] because the interview cannot distinguish
    it from Essentials -- a Starter client and an Essentials client answer
    identically. It must never select silently, and `doctor` must report it.
    """
    opens = dict(pricing.open_amounts())
    gate_keys = [k for k in opens if k.endswith("starter.gate")]
    assert gate_keys, "Starter's underivable gate must be reported as open"
    # and a would-be Starter client is quoted Essentials rather than nothing
    assert _pkg({"federal_schedules": []})["Service"] == "Essentials"


# ── the either/or, and the way it lies quietly ────────────────────────────
#
# Property & Business covers up to three rentals OR one full Schedule C, and
# the branch that saves the CLIENT most is the one applied. Both branches are
# scored in money, which is right -- and which fails silently the moment a
# price behind one of them is not set yet. Both branches then save $0, `max`
# keeps the first, and a client with a full Schedule C and no rentals has
# their Schedule C billed on top of a package that was supposed to include
# it. With the price still open a [CONFIRM:] happens to mask it. Set the
# price and the same client is silently overcharged by it.

def _priced_both_branches(priced=None):
    """The REAL schedule -- the one with the ladder -- with the two either/or
    prices filled in. `priced` is the flat-base example and cannot exercise a
    package at all; keeping both means the untiered path stays covered too."""
    s = json.loads(json.dumps(pricing.load()))
    s["per_unit"]["rental"]["amount"] = 45
    s["per_unit"]["schedule_c"]["tiers"]["standard"]["amount"] = 200
    s["per_unit"]["schedule_c"]["tiers"]["simple"]["amount"] = 65
    return s


def test_a_full_schedule_c_is_absorbed_not_billed_on_top():
    """The package says it covers one full Schedule C. It has to actually."""
    s = _priced_both_branches()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C"],
         "schedule_c_kind": "standard", "count_businesses": 1,
         "count_rentals": 0}, s)
    assert [i["Service"] for i in items] == ["Property & Business"], \
        "the covered Schedule C must not appear as a charged line"
    assert pricing.estimate_total(items, s) == "$500.00"


def test_rentals_are_absorbed_when_that_is_the_better_branch():
    s = _priced_both_branches()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["E1"],
         "count_rentals": 3, "count_businesses": 0}, s)
    assert [i["Service"] for i in items] == ["Property & Business"]


def test_the_branch_that_saves_the_client_most_wins():
    """Three rentals at $45 is $135; one full Schedule C is $200. A client
    with both gets the Schedule C absorbed, because that is the branch worth
    more to them -- not the one that happens to be written first."""
    s = _priced_both_branches()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C", "E1"],
         "schedule_c_kind": "standard", "count_businesses": 1,
         "count_rentals": 3}, s)
    charged = {i["Service"] for i in items}
    assert "Sole proprietorship" not in charged, "the dearer branch must be absorbed"
    assert "Rental property" in charged, "the cheaper branch is billed"


def test_an_unpriced_branch_the_client_actually_uses_refuses():
    """The honest answer when the comparison cannot be made.

    A branch whose price is still open scores zero, which is indistinguishable
    from a branch worth nothing -- so the choice would be made by file order
    and the client would never know. Refuse instead. A branch the client has
    NO units in cannot change the answer, so it is not grounds to refuse.
    """
    s = _priced_both_branches()
    s["per_unit"]["schedule_c"]["tiers"]["standard"]["amount"] = \
        "[CONFIRM: fee per Schedule C business]"
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C"],
         "schedule_c_kind": "standard", "count_businesses": 1,
         "count_rentals": 2}, s)
    assert "[CONFIRM:" in pricing.estimate_total(items, s)


def test_an_unpriced_branch_the_client_does_not_use_is_not_grounds_to_refuse():
    s = _priced_both_branches()
    s["per_unit"]["rental"]["amount"] = "[CONFIRM: fee per rental]"
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C"],
         "schedule_c_kind": "standard", "count_businesses": 1,
         "count_rentals": 0}, s)
    assert pricing.estimate_total(items, s) == "$500.00"


def test_standard_absorbs_the_gig_schedule_c_it_advertises():
    """Standard's covers list says "a gig Schedule C on standard mileage", so
    it has to actually include one. It was billing $65 on top of the $325."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C", "SE"],
         "schedule_c_kind": "simple", "count_businesses": 1}, s)
    assert [i["Service"] for i in items] == ["Standard"]
    assert pricing.estimate_total(items, s) == "$325.00"


def test_a_second_gig_business_is_charged():
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C", "SE"],
         "schedule_c_kind": "simple", "count_businesses": 2}, s)
    assert pricing.estimate_total(items, s) == "$390.00"      # 325 + one at 65


def test_a_gig_c_inside_property_and_business_is_currently_charged():
    """PINS AN OPEN QUESTION rather than asserting an answer.

    Property & Business covers "everything in Standard" -- which includes a
    gig Schedule C -- PLUS either three rentals or one full Schedule C. Those
    two clauses collide for a client with a gig C and rentals, and the signed
    sheet does not say which wins.

    Give the package a flat one-business allowance and a full-Schedule-C
    client gets their C free AND three rentals free, which is the "not both"
    the sheet rules out. Leave it off, as here, and a landlord with a side gig
    pays $65 for a Schedule C that Standard would have included.

    $565 is what it does today. Whether that is right is the firm's call, so
    this test records the behaviour and the reason rather than blessing it.
    """
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C", "E1"],
         "schedule_c_kind": "simple", "count_businesses": 1,
         "count_rentals": 3}, s)
    assert pricing.estimate_total(items, s) == "$565.00"
