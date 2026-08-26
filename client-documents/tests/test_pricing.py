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
import yaml

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

def test_the_firms_schedule_is_fully_priced():
    """The other side of the §9 rule, reached on 26 August 2026.

    This test used to assert the schedule was still UNPRICED, and said in its
    own docstring that the right fix when the firm priced itself was to delete
    it rather than put the placeholders back. The firm has now set every
    amount, so it is replaced by its opposite: a blank that comes back is a
    price somebody dropped, not a decision somebody made.
    """
    assert pricing.open_amounts() == [], (
        "something in registry/fee-schedule.yaml is unpriced again. Every "
        "amount was set by the firm; a [CONFIRM: reappearing is a regression."
    )


def _with_one_unpriced(path=("per_unit", "rental", "form_fee")):
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
    so the line names the package, the gate that selected it, AND everything
    the package covers -- the same promise, carrying more information, and the
    thing that makes a wrong package visible on the page before it reaches
    anyone.

    The covers list is the firm's answer of 25 August 2026, and the reason is
    the shape of the document: an estimate that names a package and a price
    and nothing else asks the client to take the number on faith. Every line
    is written to be read by a client, because this is where they are read.
    """
    base = pricing.line_items({"federal_form": "1040"})[0]
    assert base["Service"] == "Essentials"
    assert base["Detail"] == (
        "No schedules. Includes: Your federal 1040, your first state return "
        "and your first local return; Wages, interest and dividends; "
        "The standard deduction.")


def test_a_package_covers_everything_the_rung_below_it_covers():
    """`includes:` is followed, not printed.

    "Everything in Standard" is a true sentence on a public price page, where
    the reader can see Standard. On an estimate the client sees one package,
    so the phrase says nothing -- and a client who cannot tell what they
    bought is the problem the covers list exists to fix.
    """
    s = pricing.load()
    tiers = s["base"]["1040"]["tiers"]
    lines = pricing.covers("business", tiers, "base.1040")

    # Broadest rung first, so it reads as a ladder rather than a list.
    assert lines[0].startswith("Your federal 1040")
    assert "Itemized deductions" in lines              # from Standard
    assert "One full Schedule C business" in lines
    assert not any("Everything in" in line for line in lines)


def test_a_package_that_includes_itself_is_an_error_not_a_hang():
    s = pricing.load()
    tiers = {"a": {"includes": "b"}, "b": {"includes": "a"}}
    with pytest.raises(pricing.PricingError) as exc:
        pricing.covers("a", tiers, "base.1040")
    assert "loop" in str(exc.value)


def test_a_package_that_includes_a_package_that_is_not_there_is_an_error():
    with pytest.raises(pricing.PricingError) as exc:
        pricing.covers("a", {"a": {"includes": "nope"}}, "base.1040")
    assert "not a package" in str(exc.value)


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
# rental is the Business package without anyone deciding it at the call.

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
    assert line["Service"] == "Self-Employed"
    assert line["Amount"] == "$500.00"


def test_a_rental_is_a_standard_client_with_a_schedule_e():
    """Changed 26 August 2026, when rentals became a form.

    A landlord used to be sent to the package above; now they are a Standard
    client and their Schedule E is priced beside it. This is the change that
    fixed the sentence nobody could defend — the landlord who itemised paying
    less than the landlord who did not.
    """
    assert _pkg({"federal_schedules": ["E1"]})["Service"] == "Standard"


def test_the_cheapest_eligible_package_wins():
    """The selection rule, changed 25 August 2026 on the firm's instruction:

        "that logic must be built into the actual mechanism used to generate
         invoices"

    It used to be "the first gate that holds, reading most specific first",
    with a test watching from outside to check that this also happened to be
    cheapest. It is now the engine's job: among the packages whose gates hold,
    the client gets the one with the lowest TOTAL.

    A gig Schedule C with a rental holds Standard's gate. The Business package
    takes only a FULL Schedule C now, so a gig one plus a rental is a Standard
    client with a Schedule E beside it: $325 + $145 = $470.
    """
    a = {"federal_form": "1040", "federal_schedules": ["C", "E1"],
         "schedule_c_kind": "simple", "count_rentals": 1}
    s = pricing.load()
    items = pricing.line_items(a, s)
    assert items[0]["Service"] == "Standard"
    assert pricing.estimate_total(items, s) == "$470.00"


def test_a_package_the_client_is_not_eligible_for_is_never_chosen_however_cheap():
    """Eligibility is the gates, and the gates are not a pricing device.

    Starter is the cheapest thing on the sheet at $100. A client with a
    Schedule A is not eligible for it, and quoting them $100 would underprice
    the firm rather than save the client money.
    """
    line = _pkg({"federal_schedules": ["A"]})
    assert line["Service"] == "Standard"


def test_the_file_order_still_breaks_a_tie():
    """Two packages at the same total are the same deal to the client, so the
    tie goes to the one that describes them better -- which is what the file's
    most-specific-first order encodes."""
    s = pricing.load()
    # Let the Business package take this client, at exactly Standard's total.
    s["base"]["1040"]["tiers"]["business"]["gate"] = {"schedules_any": ["C"]}
    s["base"]["1040"]["tiers"]["business"]["amount"] = 325
    a = {"federal_form": "1040", "federal_schedules": ["C"],
         "schedule_c_kind": "simple", "count_states": 0, "count_localities": 0}
    key, _ = pricing.derive_tier(s["base"]["1040"], a, "base.1040", schedule=s)
    assert key == "business", "business is written first, so it wins the tie"


def test_a_ticked_schedule_with_no_count_still_lands_in_the_right_package():
    """The trap this design exists to avoid.

    A client ticks "Schedule E page 1 -- rentals" and leaves `count_rentals`
    blank. A gate written as "count_rentals > 0" reads that as no rentals and
    sends a landlord to the CHEAPEST package. Gates key on what is ON the
    return, never on how many, precisely because a count can be blank and a
    ticked box cannot.
    """
    line = _pkg({"federal_schedules": ["E1"]})            # no count at all
    assert line["Service"] == "Standard"


def test_a_ticked_schedule_with_no_count_is_still_charged_for():
    """The same trap, one level down, and it bit when rentals became a line.

    Under the package ladder a ticked Schedule E sent the client to a dearer
    rung, so the work was paid for even when the count was blank. As a counted
    line it simply did not fire: the Schedule E was prepared for nothing. A
    form-priced line now asks what is ON the return, exactly as a gate does.
    """
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["E1"]}, s)   # no count
    assert "Rental schedule" in [i["Service"] for i in items]
    assert pricing.estimate_total(items, s) == "$470.00"


def test_the_package_line_says_which_gate_selected_it():
    """A wrong pick has to be visible on the page before it reaches a client."""
    line = _pkg({"federal_schedules": ["A"]})
    assert line["Detail"], "the package line must explain itself"


# `test_starter_cannot_be_derived_and_says_so` lived here. It asserted that
# Starter's gate was a [CONFIRM:] because the interview could not tell a
# Starter client from an Essentials one -- both answered it identically. The
# interview now asks the two facts that separate them, so the test was
# describing a limitation rather than a rule, and the tests just below it
# assert the behaviour that replaced it.


def _priced_both_branches(priced=None):
    """A SYNTHETIC schedule with an either/or allowance on it.

    No package on the live sheet has one any more. `allows_one_of` was built
    for Property & Business — three rentals OR one full Schedule C — and on
    26 August 2026 rentals became a form, which left one option and no choice.

    The mechanism is kept because "either/or, resolved in the client's favour"
    is a normal thing for a fee schedule to want and the careful part of it
    (compare in money, on what is LEFT after the flat allowances, refuse
    rather than guess when a branch the client uses has no price) is the part
    that took two bugs to get right. These tests are what keep it honest.

    Built here rather than loaded, so that nothing about it can be mistaken
    for a claim about what the firm charges today.
    """
    s = json.loads(json.dumps(pricing.load()))
    tier = s["base"]["1040"]["tiers"]["business"]
    tier.pop("allows_when", None)
    tier["allows_one_of"] = [
        {"label": "up to three rentals", "count_rentals": 3},
        {"label": "one full Schedule C", "count_businesses": 1},
    ]
    tier["gate"] = {"any_of": [{"schedules_any": ["E1", "F"]},
                               {"answer_is": {"schedule_c_kind": "standard"}}]}
    # Rentals go back to being counted per property, which is what an either/or
    # over rentals needs in order to mean anything.
    s["per_unit"]["rental"] = {"count_from": "count_rentals",
                               "label": "Rental property",
                               "detail": "Schedule E, per property",
                               "amount": 45}
    s["per_unit"]["schedule_c"]["tiers"]["standard"]["amount"] = 200
    s["per_unit"]["schedule_c"]["tiers"]["simple"]["amount"] = 65
    # Standard must not be the cheaper answer here, or the engine picks it and
    # the either/or never runs. The mechanism is what is under test.
    s["base"]["1040"]["tiers"]["standard"]["gate"] = {"schedules_any": ["Z"]}
    return s


def test_a_full_schedule_c_is_absorbed_not_billed_on_top():
    """The package says it covers one full Schedule C. It has to actually."""
    s = _priced_both_branches()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C"],
         "schedule_c_kind": "standard", "count_businesses": 1,
         "count_rentals": 0}, s)
    assert [i["Service"] for i in items] == ["Self-Employed"], \
        "the covered Schedule C must not appear as a charged line"
    assert pricing.estimate_total(items, s) == "$500.00"


def test_rentals_are_absorbed_when_that_is_the_better_branch():
    s = _priced_both_branches()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["E1"],
         "count_rentals": 3, "count_businesses": 0}, s)
    assert [i["Service"] for i in items] == ["Self-Employed"]


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


def test_a_gig_c_inside_the_business_package_is_included():
    """The firm's ruling of 25 August 2026, and what became of it.

    The Business package covers "everything in Standard", which includes a gig
    Schedule C, and it used to ALSO carry an either/or over rentals. Those
    collided, and the ruling was that the gig one rides in while the either/or
    is scoped to a FULL Schedule C.

    Rentals left the ladder the next day, so the collision is gone — but the
    ruling still governs the half that remains: a gig Schedule C is never a
    charged line on a package that says it covers one.
    """
    s = pricing.load()
    a = {"federal_form": "1040", "federal_schedules": ["C", "E1"],
         "schedule_c_kind": "simple", "count_businesses": 1,
         "count_rentals": 3}
    items = pricing.line_items(a, s)
    assert "Sole proprietorship" not in [i["Service"] for i in items]
    # Standard, plus the Schedule E as its own form. The rentals are no longer
    # something a package absorbs, so they are priced rather than bundled.
    assert [i["Service"] for i in items] == ["Standard", "Rental schedule"]
    assert pricing.estimate_total(items, s) == "$470.00"

def test_a_full_schedule_c_is_what_the_business_package_is_for():
    """The half of the ruling that costs money, and the only reason the
    package still earns its step: $500 against Standard's $325 plus a $200
    full Schedule C."""
    s = pricing.load()
    a = {"federal_form": "1040", "federal_schedules": ["C", "E1"],
         "schedule_c_kind": "standard", "count_businesses": 1,
         "count_rentals": 3}
    items = pricing.line_items(a, s)
    assert items[0]["Service"] == "Self-Employed"
    assert "Sole proprietorship" not in [i["Service"] for i in items], \
        "the one full C the package covers must not also be billed"
    # 500 for the package, 145 for the Schedule E beside it.
    assert pricing.estimate_total(items, s) == "$645.00"

def test_a_gig_c_does_not_spend_an_either_or_it_no_longer_needs():
    """The bug the ruling exposed, and the reason the comparator changed.

    Branches are compared in money. Scored against the RAW counts, the
    full-Schedule-C branch was worth $65 to a landlord with a side gig — more
    than one rental at $45 — so it won, and the client paid for a rental while
    collecting an allowance for a Schedule C they already had free. Scoring
    what is LEFT after the flat allowances is what makes the two halves of the
    ruling compose.

    Run against the synthetic either/or schedule, since no live package has
    one — the logic is what is under test, not the sheet.
    """
    s = _priced_both_branches()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["C", "E1"],
         "schedule_c_kind": "simple", "count_businesses": 1,
         "count_rentals": 1}, s)
    assert [i["Service"] for i in items] == ["Self-Employed"]

def test_the_package_says_which_allowance_the_client_got():
    s = _priced_both_branches()
    base = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["E1"],
         "count_rentals": 2}, s)[0]
    assert "with up to three rentals" in base["Detail"]


def test_a_package_does_not_claim_an_allowance_the_client_cannot_use():
    """A client with none of the things on offer is told about neither.

    Applying a branch nobody can spend is harmless arithmetic and a
    misleading sentence: it prints "with up to three rentals" to somebody who
    owns no rentals.
    """
    s = _priced_both_branches()
    base = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["F"]}, s)[0]
    assert base["Service"] == "Self-Employed"
    assert "with up to" not in base["Detail"]


def test_a_counted_line_says_the_first_one_was_free():
    """Otherwise the covers list above it reads as a lie.

    The package promises a first state return; the estimate then carries a
    "State return" line. Without the word "after", a client reasonably
    concludes they were charged for the one they were told was included.
    """
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "count_states": 2, "count_localities": 3}, s)
    by_service = {i["Service"]: i["Detail"] for i in items}
    assert "after the first" in by_service["State return"]
    assert "after the first" in by_service["Local return"]


def test_a_counted_line_says_how_many_the_package_swallowed():
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["B"], "count_k1s": 3}, s)
    k1 = [i for i in items if i["Service"] == "Schedule K-1 received"][0]
    assert "after the 2 included" in k1["Detail"]


# ── Starter, once the interview can see it ────────────────────────────────

def test_the_simple_filer_rung_selects_for_a_w2_only_client():
    s = pricing.load()
    line = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": [],
         "other_income_documents": "no"}, s)[0]
    assert line["Service"] == "Simple Filer", (
        "renamed 26 Aug 2026 — 'Starter' read as the bottom of a ladder when "
        "the firm wants it to read as an exception below the minimum"
    )
    assert line["Amount"] == "$100.00"


def test_a_dependent_no_longer_takes_a_client_out_of_the_cheapest_rung():
    """Changed 26 August 2026, after the firm asked how the market charges for
    dependents and the answer turned out to be that it doesn't.

    A dependent by itself is a name, a taxpayer ID and a checkbox. What costs
    time is the due diligence on the credit it unlocks, and that is priced
    separately at $65. A W-2 parent claiming the child tax credit is a Simple
    Filer.
    """
    s = pricing.load()
    line = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": [],
         "other_income_documents": "no", "has_dependents": "yes"}, s)[0]
    assert line["Service"] == "Simple Filer"


def test_another_income_document_is_what_still_takes_them_out():
    """The test that DOES predict work, and the only thing now separating the
    two cheapest rungs."""
    s = pricing.load()
    line = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": [],
         "other_income_documents": "yes"}, s)[0]
    assert line["Service"] == "Essentials"

def test_any_other_income_document_takes_a_client_out_of_starter():
    s = pricing.load()
    line = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": [],
         "other_income_documents": "yes", "has_dependents": "no"}, s)[0]
    assert line["Service"] == "Essentials"


def test_an_unanswered_starter_question_falls_to_essentials():
    """The safe direction, and it has to be deliberate.

    A record made before these questions existed answers neither. Falling to
    Starter would quote $100 for a return nobody has established is a Starter
    return; falling to Essentials quotes what the firm quotes today. Silence
    is not evidence of simplicity.
    """
    s = pricing.load()
    line = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": []}, s)[0]
    assert line["Service"] == "Essentials"


def test_starter_is_no_longer_an_open_decision():
    assert not [p for p, _ in pricing.open_amounts() if p.endswith("starter.gate")]


# ── the per-form rule ─────────────────────────────────────────────────────

def test_a_named_form_costs_the_one_per_form_price():
    """One amount, a handful of named situations. Signed 25 Aug 2026 at $50,
    against a recommendation of $75."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["home_sale"]}, s)
    assert [i["Service"] for i in items] == ["Essentials", "Sale of a home"]
    assert items[1]["Amount"] == "$50.00"


def test_forms_print_in_the_schedules_order_not_the_clients():
    """Two clients with the same forms get the same estimate, which matters
    the first time two of them compare notes."""
    s = pricing.load()
    order = ["hsa", "home_sale", "digital_assets"]
    a = [i["Service"] for i in pricing.line_items(
        {"federal_form": "1040", "extra_forms": order}, s)]
    b = [i["Service"] for i in pricing.line_items(
        {"federal_form": "1040", "extra_forms": list(reversed(order))}, s)]
    assert a == b
    assert a == ["Essentials", "Sale of a home", "Digital assets",
                 "Health savings account"]


def test_every_ticked_form_carries_its_own_assumption():
    """The per-form rule IS its assumption -- hold it and pay the flat price,
    break it and the meter runs -- so a $50 line without its sentence is half
    a price."""
    s = pricing.load()
    said = pricing.assumptions(
        {"federal_form": "1040", "extra_forms": ["home_sale"]}, s)
    assert any(t.startswith("Sale of a home \u2014") for t in said)
    assert any("basis has to be reconstructed" in t for t in said)


def test_an_assumption_is_not_printed_for_a_form_nobody_is_filing():
    """Noise is how a client learns to skip the assumptions block."""
    s = pricing.load()
    said = pricing.assumptions({"federal_form": "1040"}, s)
    assert not any(t.startswith("Sale of a home") for t in said)


def test_foreign_accounts_are_counted_rather_than_charged_once():
    """The firm already bills these per account: "i have been doing this stuff
    with a client for awhile and just charge per account".

    Priced against a schedule whose cap IS set, because the real one's is not
    yet and the thing under test here is the counting, not the cap.
    """
    s = pricing.load()
    s["per_unit"]["foreign_account"]["cap_units"] = 6
    items = pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 3}, s)
    assert [i["Service"] for i in items] == ["Essentials",
                                             "Foreign account reporting"]
    assert items[1]["Amount"] == "$150.00"


# ── the cap ───────────────────────────────────────────────────────────────

def test_a_capped_line_stops_climbing():
    """Asked for by the firm, 25 Aug 2026. Every other line on the sheet has
    an allowance or a package around it; this one had neither."""
    s = pricing.load()
    s["per_unit"]["foreign_account"]["cap_units"] = 4
    items = pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 12}, s)
    line = [i for i in items if i["Service"] == "Foreign account reporting"][0]
    assert line["Amount"] == "$200.00"          # 4 x 50, not 12 x 50
    assert "capped at 4" in line["Detail"]
    assert "4 ×" in line["Detail"], "the multiplier shows what was charged"


def test_a_cap_that_is_a_decision_but_not_yet_a_number_refuses():
    """Not the same as uncapped, and must not price as though it were.

    The firm has ruled that this line stops somewhere. Quoting the uncapped
    total in the meantime is the answer they rejected, delivered silently.
    """
    s = pricing.load()
    s["per_unit"]["foreign_account"]["cap_units"] = (
        "[CONFIRM: how many before this stops climbing]")
    items = pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 5}, s)
    total = pricing.estimate_total(items, s)
    assert total.startswith("[CONFIRM:")
    assert "stops climbing" in total, "the total carries the actual question"


def test_the_real_cap_is_set_and_applies():
    """Set by the firm at four, 26 August 2026."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 12}, s)
    line = [i for i in items if i["Service"] == "Foreign account reporting"][0]
    assert line["Amount"] == "$200.00"          # 4 x 50, not 12 x 50
    assert "capped at 4" in line["Detail"]


def test_one_unit_prices_normally_under_an_open_cap():
    """One account cannot be over any cap worth setting, so the open value
    cannot change that client's price and is not worth refusing over."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 1}, s)
    assert pricing.estimate_total(items, s) == "$250.00"


def test_a_line_under_its_cap_says_nothing_about_one():
    s = pricing.load()
    s["per_unit"]["foreign_account"]["cap_units"] = 6
    line = [i for i in pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 2}, s)
        if i["Service"] == "Foreign account reporting"][0]
    assert "capped" not in line["Detail"]


def test_ticking_foreign_accounts_does_not_also_charge_a_flat_form():
    """`priced_by` exists so the two lines cannot both fire and bill the
    first account twice."""
    s = pricing.load()
    total = pricing.estimate_total(pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 1}, s), s)
    assert total == "$250.00"      # 200 + one account at 50, not 50 + 50


def test_a_form_the_interview_offers_and_the_schedule_ignores_is_an_error():
    """A situation the client ticks and the estimate skips is billed at
    nothing, silently."""
    s = pricing.load()
    with pytest.raises(pricing.PricingError) as exc:
        pricing.line_items(
            {"federal_form": "1040", "extra_forms": ["a_thing_we_never_priced"]}, s)
    assert "billed" in str(exc.value)


def test_every_option_the_interview_offers_has_a_price():
    """The guard that keeps the two registries in step.

    The interview and the fee schedule are separate files edited by separate
    hands. Adding an option to one and forgetting the other is the easiest
    mistake available here, and it fails silently in the direction that costs
    money.
    """
    import interview as iv
    s = pricing.load()
    forms = (s.get("per_form") or {}).get("forms") or {}
    offered = [q for _, q in iv.all_questions(iv.load_schema())
               if q["id"] == (s["per_form"]["select_from"])]
    assert offered, "the schedule selects from a question the interview does not ask"
    for opt in offered[0]["options"]:
        assert opt["value"] in forms, (
            f"the interview offers {opt['value']!r} and nothing prices it"
        )


# ── brokerage, off the hourly list ────────────────────────────────────────

def test_the_first_brokerage_statement_is_inside_the_package():
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["D"],
         "count_brokerages": 1}, s)
    assert [i["Service"] for i in items] == ["Standard"]


def test_a_second_brokerage_statement_is_counted():
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["D"],
         "count_brokerages": 2}, s)
    assert pricing.estimate_total(items, s) == "$370.00"      # 325 + 45
    assert "after the first" in [i for i in items
                                 if i["Service"] == "Brokerage statement"][0]["Detail"]


def test_a_statement_that_must_be_keyed_is_its_own_line():
    """Signed 25 Aug 2026 at $95, keying on what cannot be summarised."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "federal_schedules": ["D"],
         "count_brokerages": 1, "count_brokerages_keyed": 1}, s)
    assert pricing.estimate_total(items, s) == "$420.00"      # 325 + 95


def test_the_old_brokerage_assumption_is_gone_not_reworded():
    """`assumed.brokerage` said brokerage sat inside the base fee at any
    volume and billed the overrun hourly. All three claims are now wrong."""
    s = pricing.load()
    assert "brokerage" not in (s.get("assumed") or {})
    said = pricing.assumptions({"federal_form": "1040"}, s)
    assert not any("imports cleanly" in t for t in said)
    assert not any("more than one broker" in t for t in said)


# ── beyond: priced ────────────────────────────────────────────────────────

def test_a_priced_boundary_names_the_number_not_the_rate():
    """The firm, 25 Aug 2026, asked for exactly this:

        "this should be more like - we will tell you it's going to be $95 more
         and we agree now that we know?"

    A third consequence, and the best of the three. Hourly gives a client a
    rate and leaves them unable to work out the total; a re-quote stops the
    job; this gives them the number before the work and agrees it at the
    moment it is found.
    """
    s = pricing.load()
    said = [t for t in pricing.assumptions({"federal_form": "1040"}, s)
            if t.startswith("Brokerage keying")]
    assert len(said) == 1
    t = said[0]
    assert "$95.00" in t
    assert "an hour" not in t
    assert "agree it with you then" in t


def test_a_priced_boundary_reads_its_number_off_the_line_that_charges_it():
    """Two places holding the same number is how an estimate ends up
    promising $95 while the invoice bills $110."""
    s = pricing.load()
    s["per_unit"]["brokerage_keyed"]["amount"] = 110
    said = [t for t in pricing.assumptions({"federal_form": "1040"}, s)
            if t.startswith("Brokerage keying")][0]
    assert "$110.00" in said


def test_a_priced_boundary_that_names_no_line_refuses():
    s = pricing.load()
    del s["assumed"]["brokerage_keying"]["beyond_price_from"]
    with pytest.raises(pricing.PricingError) as exc:
        pricing.assumptions({"federal_form": "1040"}, s)
    assert "invent a number" in str(exc.value)


def test_a_priced_boundary_pointing_at_nothing_refuses():
    s = pricing.load()
    s["assumed"]["brokerage_keying"]["beyond_price_from"] = "not_a_line"
    with pytest.raises(pricing.PricingError) as exc:
        pricing.assumptions({"federal_form": "1040"}, s)
    assert "the invoice cannot keep" in str(exc.value)


def test_a_priced_boundary_whose_line_has_no_amount_carries_the_question():
    """Promising a client a number requires having one — but an unset price is
    a gap, not a broken schedule.

    The file's rule for a gap is to carry the question, so the sentence keeps
    its `[CONFIRM:` and the merge engine refuses on it. Raising instead would
    kill the whole estimate over one line and hide everything else missing.
    """
    s = pricing.load()
    s["per_unit"]["brokerage_keyed"]["amount"] = "[CONFIRM: what keying costs]"
    said = [t for t in pricing.assumptions({"federal_form": "1040"}, s)
            if t.startswith("Brokerage keying")][0]
    assert "[CONFIRM:" in said
    assert "brokerage_keyed" in said


def test_requote_is_still_refused():
    """The vocabulary got wider by exactly one word, and not that one. A
    re-quote stops the job and opens a negotiation the firm did not want."""
    s = pricing.load()
    s["assumed"]["cleanup"]["beyond"] = "requote"
    with pytest.raises(pricing.PricingError) as exc:
        pricing.assumptions({"federal_form": "1040"}, s)
    assert "ruled out re-quoting" in str(exc.value)


# ── the wording is data ───────────────────────────────────────────────────

def test_every_phrase_the_estimate_can_say_is_in_the_registry():
    """The firm, 25 Aug 2026: "templates should be easily customizable to the
    degree possible - in the sense that i can easily manually update how they
    read". A sentence assembled in Python is one they cannot reach."""
    s = pricing.load()
    phrases = s.get("phrases") or {}
    missing = sorted(set(pricing._SLOTS) - set(phrases))
    assert not missing, f"assembled in code, not editable: {missing}"


def test_every_phrase_renders_with_exactly_the_slots_it_declares():
    """The guard that makes editing them safe.

    A phrase that gains a slot nobody fills would print a literal brace on a
    client's estimate, or raise mid-render. This fails first, by name.
    """
    s = pricing.load()
    for key, slots in pricing._SLOTS.items():
        out = pricing.say(s, key, **{name: f"<{name}>" for name in slots})
        assert "{" not in out and "}" not in out, f"{key} left a brace: {out}"
        for name in slots:
            assert f"<{name}>" in out, f"{key} dropped its {name} slot"


def test_a_phrase_that_invents_a_slot_says_which_one():
    s = pricing.load()
    s["phrases"]["after_first_only"] = "After the first {colour} one"
    with pytest.raises(pricing.PricingError) as exc:
        pricing.say(s, "after_first_only")
    assert "after_first_only" in str(exc.value)
    assert "colour" in str(exc.value)


def test_changing_a_phrase_changes_what_the_estimate_says():
    """The whole point: edit the file, the document changes."""
    s = pricing.load()
    s["phrases"]["after_first_only"] = "(the first one is on us)"
    items = pricing.line_items({"federal_form": "1040", "count_states": 2}, s)
    state = [i for i in items if i["Service"] == "State return"][0]
    assert state["Detail"] == "Per state, after the first", (
        "this line has a detail, so it uses the paired phrase"
    )
    s["phrases"]["after_first"] = "{detail} (the first one is on us)"
    items = pricing.line_items({"federal_form": "1040", "count_states": 2}, s)
    state = [i for i in items if i["Service"] == "State return"][0]
    assert state["Detail"] == "Per state (the first one is on us)"


def test_a_schedule_without_phrases_uses_the_firms_one_copy():
    """A sample schedule, a test fixture and a future second schedule should
    all say the same thing to a client, and only one file should have to be
    edited to change it."""
    sample = pricing.load(ROOT / "samples" / "fee-schedule-example.yaml")
    assert "phrases" not in sample
    said = pricing.assumptions({"federal_form": "1040"}, sample)
    assert said and all("this estimate assumes" in t for t in said)


# ── the mechanism gives the cheapest answer ───────────────────────────────

def _forced(schedule, key):
    """The schedule with one package, gated open, so any client gets it.

    Lets a test ask "what would this client have paid on THAT rung?", which
    is the only way to check that the rung they were put on was the cheap one.
    """
    tiers = schedule["base"]["1040"]["tiers"]
    # Every rung stays: `includes:` walks the chain, so a ladder with one rung
    # on it cannot price the rung that inherits from the one below.
    forced = {}
    for name, tier in tiers.items():
        gate = {} if name == key else {"answer_is": {"__never__": "x"}}
        forced[name] = {**tier, "gate": gate}
    out = dict(schedule)
    out["base"] = {**schedule["base"],
                   "1040": {"tier_from": "derived", "tiers": forced}}
    return out


def _total_on(schedule, key, answers):
    try:
        items = pricing.line_items(answers, _forced(schedule, key))
    except pricing.PricingError:
        return None
    if any(pricing.is_open(i["_raw"]) for i in items):
        return None
    return sum(i["_raw"] for i in items)


def _client_shapes():
    """A sweep of the return shapes the ladder is meant to describe."""
    import itertools
    schedules = ["A", "B", "C", "D", "E1", "E2", "SE", "F"]
    combos = [list(c) for r in range(4)
              for c in itertools.combinations(schedules, r)]
    for scheds in combos:
        kinds = ["simple", "standard"] if "C" in scheds else [None]
        for kind in kinds:
            for states, rentals, k1s, biz in itertools.product(
                    [0, 2], [0, 1, 4], [0, 3], [0, 2]):
                a = {"federal_form": "1040", "federal_schedules": scheds,
                     "count_states": states, "count_localities": 1,
                     "count_rentals": rentals, "count_k1s": k1s,
                     "count_businesses": biz,
                     "other_income_documents": "no", "has_dependents": "no"}
                if kind:
                    a["schedule_c_kind"] = kind
                yield a


def test_the_ladder_always_puts_a_client_on_their_cheapest_package():
    """The property the firm asked for, 25 August 2026:

        "something should be able to pretty simply determine its cheaper tier
         or combination of pricing to get them to the cheapest thing they
         need to do"

    The mechanism does NOT search for the cheapest — it takes the first gate
    that holds, reading most-specific first. This test is what makes that
    simple rule trustworthy: it prices every client shape on every rung the
    client is ELIGIBLE for, and fails if one of those would have been cheaper
    than the rung they were given.

    Eligibility is the gates, and the gates are a firm decision rather than a
    pricing accident: Starter is $100 and W-2-only, so a client with a
    Schedule A is not eligible for it, and quoting them $100 would underprice
    the firm rather than save the client money. "The cheapest thing they need
    to do" means the cheapest package that actually covers their return.

    If this ever fails, do not relax it — a price moved and the ladder stopped
    being a ladder. The fix is the price.
        """
    s = pricing.load()
    tiers = s["base"]["1040"]["tiers"]
    losses = []
    checked = 0
    for a in _client_shapes():
        chosen, _ = pricing.derive_tier(s["base"]["1040"], a, "base.1040",
                                        schedule=s)
        if chosen is None:
            continue
        eligible = [k for k, t in tiers.items()
                    if pricing._gate_holds(t.get("gate") or {}, a, k)]
        prices = {k: _total_on(s, k, a) for k in eligible}
        prices = {k: v for k, v in prices.items() if v is not None}
        if prices.get(chosen) is None:
            continue
        checked += 1
        best = min(prices, key=lambda k: prices[k])
        if prices[chosen] > prices[best]:
            losses.append(
                f"{a['federal_schedules']} c={a.get('schedule_c_kind')} "
                f"rentals={a['count_rentals']} k1s={a['count_k1s']} "
                f"biz={a['count_businesses']}: got {chosen} at "
                f"${prices[chosen]:.0f}, {best} was ${prices[best]:.0f}")
    assert checked > 500, "the sweep stopped covering the ladder"
    assert not losses, (
        f"{len(losses)} client shape(s) were quoted more than they had to "
        f"pay. First few:\n  " + "\n  ".join(losses[:5]))


def test_a_price_that_breaks_the_ladder_is_caught():
    """The test above is only worth having if it can fail. Make Standard
    dearer than Property and a Standard client is overpaying."""
    s = pricing.load()
    s["base"]["1040"]["tiers"]["standard"]["amount"] = 900
    a = {"federal_form": "1040", "federal_schedules": ["A"],
         "count_states": 0, "count_localities": 0}
    chosen, _ = pricing.derive_tier(s["base"]["1040"], a, "base.1040")
    assert chosen == "standard"
    assert _total_on(s, "standard", a) > _total_on(s, "essentials", a), (
        "a price change can make the chosen rung the dearest one, which is "
        "exactly what the sweep above is watching for"
    )


# ── is the ladder sensible? ───────────────────────────────────────────────

def test_every_package_is_reachable_and_is_somebody_s_best_deal():
    """The firm, 25 Aug 2026: "we should ensure that our tiers are sensical
    with our pricing altogether".

    The engine picks the cheapest eligible package, which turns a pricing
    mistake into a SILENCE rather than an overcharge: a package priced above
    what its allowances are worth simply stops being selected and nothing
    complains. This listens for that silence.
    """
    rows = pricing.ladder_report()
    assert rows, "the 1040 base is meant to be a ladder"
    for r in rows:
        assert r["eligible"], (
            f"{r['label']} has a gate no client can hold — it is invisible")
        assert r["chosen"], (
            f"{r['label']} is eligible for {r['eligible']} client shapes and "
            f"chosen for none. Every client who qualifies does better on "
            f"{sorted(r['beaten_by'])}, so it is priced above what it covers.")


def test_the_report_notices_a_package_priced_out_of_existence():
    """The check is only worth having if it can fail.

    Raising a price alone is not enough to prove it, and that is worth
    knowing: every package on the real ladder has clients no other package is
    eligible for, so it stays chosen at any price. The check fires when a
    package's clients ALL have somewhere better to go — which is what it is
    for, and why it is a weak signal on a ladder of specialists. Read the
    counts, not just the warning.
    """
    s = pricing.load()
    tiers = s["base"]["1040"]["tiers"]
    # Give the Business package exactly Essentials' clients, then price it above.
    tiers["business"]["gate"] = dict(tiers["essentials"]["gate"])
    tiers["business"]["amount"] = 5000
    rows = {r["key"]: r for r in pricing.ladder_report(s)}
    assert rows["business"]["eligible"] > 0
    assert rows["business"]["chosen"] == 0
    assert "essentials" in rows["business"]["beaten_by"] or \
           "starter" in rows["business"]["beaten_by"]


def test_every_package_is_a_discount_on_its_parts():
    """A package dearer than buying the same things one at a time is a package
    nobody who does the arithmetic will want.

    That is exactly the shape T-15 found on the old rental allowance: $175 of
    price step buying $135 of rentals. It never crossed, and the client who
    noticed was the client who lost money by taking it.
    """
    for r in pricing.ladder_value():
        if r["step"] is None:
            continue
        assert r["delta"] >= 0, (
            f"{r['label']} costs ${-r['delta']} more than buying its parts: "
            f"a ${r['step']} step absorbing ${r['absorbs']} of line items")


def test_a_package_is_not_a_giveaway_either():
    """The other end of the same question. A rung that absorbs far more than
    it charges is not a package, it is a discount nobody decided on."""
    for r in pricing.ladder_value():
        if r["step"] is None or not r["step"]:
            continue
        assert r["delta"] <= r["step"], (
            f"{r['label']} absorbs ${r['absorbs']} for a ${r['step']} step — "
            f"more than double what it charges. Deliberate, or a mistake?")


def test_the_value_check_reads_allowances_not_prose():
    """`covers:` is prose and can drift; `allows` is the arithmetic.

    Widening an allowance must move the number, or the check is decorative.
    """
    s = pricing.load()
    s["base"]["1040"]["tiers"]["standard"]["allows"]["count_k1s"] = 6
    row = {r["key"]: r for r in pricing.ladder_value(s)}["standard"]
    assert row["absorbs"] == 45 + 6 * 15 + 65


def test_a_soft_cap_says_that_time_is_billed_past_it():
    """The firm, answering round eleven on 26 Aug 2026:

        4 is a soft cap. Then we add dollars for time

    A bare `cap_units` is a HARD cap: past four, the client is charged nothing
    further, ever. That is not what was meant and it is the expensive
    direction to be wrong in — a dozen accounts would have been four accounts'
    money for a dozen accounts' work.

    So the cap keeps the PER-ACCOUNT charge from running away, and the time
    past it is billed. The sentence on the estimate has to say both, because
    "capped at four" on its own is now a promise the firm is not making.
    """
    s = pricing.load()
    line = [i for i in pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 12}, s)
        if i["Service"] == "Foreign account reporting"][0]

    assert line["Amount"] == "$200.00", "the per-account charge still stops at four"
    assert "capped at 4" in line["Detail"]
    assert "150" in line["Detail"], "the rate past the cap has to be on the line"


def test_a_hard_cap_still_reads_as_a_hard_cap():
    """The soft wording must come from the schedule saying so, not from every
    cap suddenly claiming time is billed past it."""
    s = pricing.load()
    s["per_unit"]["foreign_account"].pop("cap_beyond", None)
    line = [i for i in pricing.line_items(
        {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
         "count_foreign_accounts": 12}, s)
        if i["Service"] == "Foreign account reporting"][0]
    assert "capped at 4" in line["Detail"]
    assert "150" not in line["Detail"]


def test_a_cap_beyond_nobody_recognises_refuses():
    """Same rule as `beyond:` on an assumption. A consequence the code does
    not know would print as though it were not there at all."""
    s = pricing.load()
    s["per_unit"]["foreign_account"]["cap_beyond"] = "requote"
    with pytest.raises(pricing.PricingError, match="requote"):
        pricing.line_items(
            {"federal_form": "1040", "extra_forms": ["foreign_accounts"],
             "count_foreign_accounts": 12}, s)


# ── amended returns (T-16) ────────────────────────────────────────────────

def test_an_amended_return_is_its_own_engagement_not_a_package():
    """Round eleven, 26 Aug 2026: "Its own engagement, at $250".

    Not an add-on to a package. An amendment is the whole job — the package
    ladder describes an original return being prepared from scratch, and none
    of its rungs describes redoing one.
    """
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "return_basis": "amended",
         "other_income_documents": "no"}, s)
    assert items[0]["Service"] == "Amended return"
    assert items[0]["Amount"] == "$250.00"
    assert not any(i["Service"] in ("Simple Filer", "Essentials", "Standard",
                                    "Business") for i in items), \
        "an amendment must not also be sold a package"


def test_an_amended_return_still_pays_for_what_is_on_it():
    """The amendment is the base, not a flat fee for everything. Redoing a
    return with three rentals on it is still three rentals of work."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "return_basis": "amended",
         "count_rentals": 1, "schedules": ["E1"]}, s)
    assert items[0]["Amount"] == "$250.00"
    assert any(i["Service"] == "Rental schedule" for i in items)


def test_an_original_return_still_gets_the_package_ladder():
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "return_basis": "original",
         "other_income_documents": "no"}, s)
    assert items[0]["Service"] in ("Simple Filer", "Essentials")
    assert items[0]["Service"] != "Amended return"


def test_an_absent_return_basis_prices_as_an_original_return():
    """`line_items` defaults to `original`, and that default is deliberate.

    Refusing instead would break every engagement recorded before this
    question existed, for a question whose answer is "original" in almost
    every case. The guarantee that a REAL engagement has answered it lives
    where engagements are made — the interview requires it — which is the
    same rule as every other gate: it belongs in `intake.finish`, not here.
    See `test_interview.py` for the half that does the work.
    """
    s = pricing.load()
    items = pricing.line_items({"federal_form": "1040",
                                "other_income_documents": "no"}, s)
    assert items[0]["Service"] != "Amended return"


# ── extensions (T-17) ─────────────────────────────────────────────────────

def test_filing_an_extension_with_nothing_to_compute_is_free():
    """Round eleven: "$75, as its own named line — filing-only extensions
    free". The priced thing is the payment estimate, not the filing."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "return_basis": "original",
         "other_income_documents": "no"}, s)
    assert not any(i["Service"].startswith("Extension") for i in items)


def test_an_extension_with_a_payment_estimate_is_seventy_five():
    s = pricing.load()
    line = [i for i in pricing.line_items(
        {"federal_form": "1040", "return_basis": "original",
         "other_income_documents": "no", "count_extension_estimates": 1}, s)
        if i["Service"].startswith("Extension")]
    assert line and line[0]["Amount"] == "$75.00"


def test_a_second_extension_estimate_is_charged_too():
    """A state that will not honour the federal extension is a second
    computation, not the same one filed twice."""
    s = pricing.load()
    line = [i for i in pricing.line_items(
        {"federal_form": "1040", "return_basis": "original",
         "other_income_documents": "no", "count_extension_estimates": 2}, s)
        if i["Service"].startswith("Extension")][0]
    assert line["Amount"] == "$150.00"


def test_the_extension_notice_still_carries_no_fee():
    """The letter hands the money to the invoice on purpose — "an extension
    notice that also asks for money reads as a bill and gets filed as one".

    The bug was that the invoice had nowhere to put it. This checks the fix
    did not "solve" that by putting a price back on the letter.
    """
    template = (ROOT.parent / "satc-handoff" / "04-TEMPLATES" /
                "SATC Extension Notice.html").read_text(encoding="utf-8")
    assert "$75" not in template
    assert "Extension with a payment estimate" not in template


# ── the earned income credit (round eleven, q1) ───────────────────────────

def test_the_client_is_not_asked_whether_they_claim_the_eic():
    """Round eleven: "We don't, at the estimate — discover it at file review,
    like brokerage keying."

    It sat in `extra_forms`, the multi-select the CLIENT ticks, beside "sold a
    home" and "paid into an HSA". Eligibility turns on earned income under a
    threshold that moves with filing status and number of children,
    investment income under a separate limit, valid SSNs, residency for the
    whole year, and either a qualifying child or being 25 to 64 without one.
    Every one of those is a number off the return. Drake computes it; a
    consultation cannot, and asking invites a wrong answer that prices a
    return.
    """
    schema = yaml.safe_load(
        (ROOT / "registry" / "interview.yaml").read_text(encoding="utf-8"))
    extra = [q for sec in schema["sections"] for q in sec["questions"]
             if q["id"] == "extra_forms"][0]
    values = {o["value"] for o in extra["options"]}
    assert "earned_income_credit" not in values, \
        "a client cannot answer this and must not be asked to"


def test_the_eic_is_priced_from_the_preparer_answer():
    s = pricing.load()
    line = [i for i in pricing.line_items(
        {"federal_form": "1040", "return_basis": "original",
         "other_income_documents": "no", "eic_claimed": "yes"}, s)
        if i["Service"] == "Earned income credit"]
    assert line and line[0]["Amount"] == "$65.00"


def test_no_eic_answer_means_no_eic_line():
    """Blank when the estimate goes out is the normal case, not an error."""
    s = pricing.load()
    items = pricing.line_items(
        {"federal_form": "1040", "return_basis": "original",
         "other_income_documents": "no"}, s)
    assert not any(i["Service"] == "Earned income credit" for i in items)


def test_the_eic_keeps_its_printed_assumption():
    """The reason it stayed in `per_form` rather than becoming a counted line:
    the boundary it prints is worth keeping, and a counted line has none."""
    s = pricing.load()
    said = pricing.assumptions(
        {"federal_form": "1040", "return_basis": "original",
         "other_income_documents": "no", "eic_claimed": "yes"}, s)
    assert any("more than half the year" in a for a in said)


# ── entity bases as published "from" prices (round twelve, q2) ────────────

def test_entity_bases_still_price_the_same_after_becoming_from_prices():
    """The structure changed; not one number did."""
    s = pricing.load()
    for form, expected in (("1065", "$800.00"), ("1120S", "$950.00"),
                           ("1120", "$950.00")):
        items = pricing.line_items({"federal_form": form}, s)
        assert items[0]["Amount"] == expected, form


def test_every_entity_base_says_it_is_a_from_price_and_why():
    """Round twelve: "definitely a from price ... but it should also be fairly
    clear that these are starting points and maybe some very light notes
    indicating what 'starting' means".

    A bare $950 on a page is read as a total. An entity return is a base with
    the balance sheet, the reconciliation and the owner K-1s on top of it, so
    the number needs the sentence that says so travelling with it — in the
    schedule, where the page reads it from, rather than typed onto the page
    where it can drift.
    """
    s = pricing.load()
    for form in ("1065", "1120S", "1120"):
        base = s["base"][form]
        assert isinstance(base, dict), f"{form} is still a bare number"
        assert base.get("publish") == "from", f"{form} is not marked a from price"
        notes = base.get("starting_note") or []
        assert notes, f"{form} says 'from' and does not say from what"
        assert all(isinstance(n, str) and n.strip() for n in notes), form


def test_the_individual_packages_are_not_from_prices():
    """The four packages are gated on what is on the return, so the price a
    visitor reads is the price they get. Marking them 'from' would give away
    the one thing the ladder buys."""
    s = pricing.load()
    for key, tier in s["base"]["1040"]["tiers"].items():
        assert tier.get("publish") != "from", key
