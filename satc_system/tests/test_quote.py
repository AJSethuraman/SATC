"""The interview says what the work will cost, before any of it is done.

Money is correctness-critical, so every total below is hand-checked against
``configs/billing/services.yaml`` rather than round-tripped through the code
that produced it.

The three things these tests exist to hold down:

  * a quote is auditable — every line names the answer that put it there;
  * a quote is not an invoice, structurally rather than by convention;
  * work the catalogue cannot price is VISIBLE, never dropped and never guessed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from satc.billing import next_invoice_number
from satc.billing.invoice import Invoice
from satc.billing.quote import (
    Quote,
    QuoteError,
    load_service_map,
    quote_for,
)
from satc.config import ConfigError
from satc.intake.workflows import list_workflows, load_workflow
from satc.models.work import Engagement

CLIENT = "client-quote-test"
YEAR = 2025

# Hand-checked from configs/billing/services.yaml.
RETURN_1040 = Decimal("450.00")
SCHEDULE_D = Decimal("145.00")
SCHEDULE_E = Decimal("185.00")
STATE_RETURN = Decimal("95.00")


def core(**answers):
    """A 1040 quote. Every question answered "no" unless the test says otherwise."""
    wf = load_workflow("personal_1040_core")
    said = {q.id: "no" for q in wf.questions}
    said.update(answers)
    return wf, said


def quote(plan_key="", basis="", **answers):
    wf, said = core(**answers)
    engagements = ([Engagement(client_id=CLIENT, tax_year=YEAR,
                               rate_plan_key=plan_key, rate_plan_basis=basis)]
                   if plan_key else [])
    return quote_for(wf, said, client_id=CLIENT, tax_year=YEAR,
                     engagements=engagements)


def codes(q):
    return [line.service_code for line in q.lines]


# --- an answer puts a line on the quote ---------------------------------------

def test_an_answer_adds_its_service():
    """The origin fact. Say you sold investments; the quote grows a Schedule D."""
    assert "schedule_d" in codes(quote(brokerageActivity="yes"))


def test_an_explicit_no_adds_nothing():
    assert "schedule_d" not in codes(quote())


def test_an_unanswered_question_adds_nothing_either():
    """Principle 2 in the direction that costs money: a question nobody answered
    is not a yes, so it cannot quietly add $145 to what a client is told."""
    wf = load_workflow("personal_1040_core")
    empty = quote_for(wf, {}, client_id=CLIENT, tax_year=YEAR)
    assert "schedule_d" not in codes(empty)


def test_two_answers_meaning_the_same_work_bill_it_once():
    """Brokerage sales and crypto sales are one Schedule D. Two lines here would
    be a client charged twice for one schedule."""
    both = quote(brokerageActivity="yes", digitalAssets="yes")
    assert codes(both).count("schedule_d") == 1


# --- every line says which answer put it there --------------------------------

def test_a_line_names_the_answer_that_put_it_there():
    line = next(l for l in quote(brokerageActivity="yes").lines
                if l.service_code == "schedule_d")
    assert line.because == "you told us about investment sales or digital asset activity"
    assert "brokerageActivity" in line.from_questions


def test_every_conditional_line_is_traceable_to_a_real_question():
    """The prose can drift; the question ids cannot. A quote the owner cannot
    check against the interview is a number they will not defend to a client."""
    for wf in list_workflows():
        said = {q.id: "yes" for q in wf.questions}
        priced = quote_for(wf, said, client_id=CLIENT, tax_year=YEAR)
        known = {q.id for q in wf.questions}
        for item in list(priced.lines) + list(priced.unpriced):
            assert item.because, f"{wf.key}/{item.service_code} says nothing"
            for qid in item.from_questions:
                assert qid in known, f"{wf.key} prices on unknown question {qid}"


def test_an_unconditional_line_says_so_rather_than_naming_an_answer():
    line = next(l for l in quote().lines if l.service_code == "return_1040")
    assert line.from_questions == ()
    assert line.because == "this is your federal individual return"


def test_a_mapping_with_no_words_falls_back_to_the_question_label(tmp_path):
    """The config author may leave `because` out; the engine must never leave the
    line unexplained. The derived sentence is read off the condition that just
    fired, so it cannot describe a different branch."""
    _write_workflow(tmp_path, """
services:
  - service: schedule_d
    condition: {question_id: soldShares, equals: "yes"}
""")
    wf = load_workflow("tiny", tmp_path)
    priced = quote_for(wf, {"soldShares": "yes"}, client_id=CLIENT, tax_year=YEAR,
                       config_root=tmp_path)
    assert priced.lines[0].because == 'you answered "yes" to "Did you sell shares?"'


# --- the arithmetic -----------------------------------------------------------

def test_the_total_matches_the_catalogue_by_hand():
    """450.00 federal + 145.00 Schedule D = 595.00, at full rate."""
    priced = quote(brokerageActivity="yes")
    assert priced.standard_total == Decimal("595.00")
    assert priced.discount_total == Decimal("0.00")
    assert priced.total == Decimal("595.00")
    assert priced.standard_total == RETURN_1040 + SCHEDULE_D


def test_a_reduced_plan_shows_the_full_value_and_the_reduction():
    """595.00 at the household rate: 112.50 off the federal, 36.25 off the
    Schedule D, so 148.75 off 595.00 leaves 446.25."""
    priced = quote(plan_key="household", basis="Working household, two W-2s",
                   brokerageActivity="yes")
    assert priced.standard_total == Decimal("595.00")
    assert priced.discount_total == Decimal("148.75")
    assert priced.total == Decimal("446.25")

    block = priced.summary_block()
    assert "Full value of work" in block and "595.00" in block
    assert "Household rate applied" in block and "25%" in block
    assert "446.25" in block


def test_a_quantity_multiplies_the_catalogue_rate():
    """One rental, one out-of-state return: 185.00 + 95.00 = 280.00."""
    wf = load_workflow("personal_rental_schedule_e")
    said = {q.id: "no" for q in wf.questions} | {"outOfStateProperty": "yes"}
    priced = quote_for(wf, said, client_id=CLIENT, tax_year=YEAR)
    assert codes(priced) == ["schedule_e_rental", "return_state"]
    assert priced.standard_total == SCHEDULE_E + STATE_RETURN == Decimal("280.00")


# --- the plan is an agreement, or it is not -----------------------------------

def test_a_fallback_plan_is_labelled_a_fallback_not_an_agreement():
    """Nobody has priced this client. Standard applies — but saying "standard was
    agreed" invents a conversation that never happened."""
    priced = quote()
    assert priced.plan.key == "standard"
    assert priced.plan_is_fallback is True
    assert "No rate plan agreed" in priced.plan_why
    assert priced.plan_why in priced.summary_block()


def test_an_agreed_standard_plan_is_not_a_fallback():
    """The pair that matters: same plan key, different fact."""
    priced = quote(plan_key="standard")
    assert priced.plan.key == "standard"
    assert priced.plan_is_fallback is False
    assert "No rate plan agreed" not in priced.summary_block()


def test_a_rate_plan_the_catalogue_no_longer_has_refuses_to_price():
    """Principle 5. Falling back to the default would invent an agreement.

    The refusal has to name the ENGAGEMENT, not just the catalogue: the record
    to fix is the one that still points at a plan nobody offers any more, and
    "no rate plan called X" sends the owner to the wrong file (principle 10)."""
    engagement = Engagement(client_id=CLIENT, tax_year=YEAR,
                            rate_plan_key="retired_2019")
    wf, said = core()
    with pytest.raises(ConfigError) as refusal:
        quote_for(wf, said, client_id=CLIENT, tax_year=YEAR,
                  engagements=[engagement])
    assert "retired_2019" in str(refusal.value)
    assert f"The {YEAR} engagement records" in str(refusal.value)
    assert "Agree a current plan" in str(refusal.value)


def test_a_reduced_plan_with_no_recorded_basis_is_not_quoted():
    """The refusal Invoice.issue already makes, moved to where the client first
    reads a number. Quoting a 60% discount the invoice engine will then refuse
    to bill leaves the practice withdrawing it in front of the client — worse
    than never offering it, and the exact shape of a guard put on one path while
    the exploit walks in through the other."""
    engagement = Engagement(client_id=CLIENT, tax_year=YEAR,
                            rate_plan_key="hardship", rate_plan_basis="")
    wf, said = core()
    with pytest.raises(ConfigError) as refusal:
        quote_for(wf, said, client_id=CLIENT, tax_year=YEAR,
                  engagements=[engagement])

    words = str(refusal.value)
    assert "hardship" in words
    assert "no basis is recorded" in words
    # Principle 10: both ways out, named. A refusal that only says no ends a run.
    assert f"Record why on the {YEAR} engagement" in words
    assert "plan that needs no basis" in words


def test_the_quote_refuses_exactly_what_the_invoice_refuses():
    """The pair, asserted together. Two engines that disagree about whether a
    plan is billable is how a client is told one number and sent another."""
    from satc.billing.invoice import BillingError

    engagement = Engagement(client_id=CLIENT, tax_year=YEAR,
                            rate_plan_key="hardship", rate_plan_basis="")
    wf, said = core()

    with pytest.raises(ConfigError):
        quote_for(wf, said, client_id=CLIENT, tax_year=YEAR,
                  engagements=[engagement])
    invoice = Invoice(invoice_id="2025-0001", client_id=CLIENT, tax_year=YEAR,
                      plan_key="hardship", plan_basis="")
    invoice.add("return_1040")
    with pytest.raises(BillingError, match="needs a recorded reason"):
        invoice.issue(on=None)


def test_a_reduced_plan_with_a_basis_quotes_normally():
    """The other half of the mutation: the refusal is on the MISSING BASIS, not
    on the discount. 450.00 less 60% is 180.00, hand-checked."""
    priced = quote(plan_key="hardship", basis="Job loss in March, agreed by phone")
    assert priced.total == Decimal("180.00")
    assert priced.shows_a_discount


# --- work the catalogue cannot price ------------------------------------------

def test_hourly_work_is_listed_rather_than_dropped_or_guessed():
    """Principle 1. Nobody knows the hours before the work, and a "typical"
    number would be a guess wearing a dollar sign."""
    wf = load_workflow("personal_schedule_c")
    said = {q.id: "no" for q in wf.questions} | {"newBusiness": "yes"}
    priced = quote_for(wf, said, client_id=CLIENT, tax_year=YEAR)

    assert "bookkeeping_cleanup" not in codes(priced)
    listed = next(u for u in priced.unpriced if u.service_code == "bookkeeping_cleanup")
    assert "hours are not known" in listed.reason
    assert "125.00 an hour" in listed.reason
    assert listed.because == "you started the business this year, so the books need setting up"
    # It is real work, so it is on the page — and it is not in the total.
    assert listed.label in priced.summary_block()
    assert priced.total == Decimal("275.00")


def test_an_unknown_quantity_is_shown_rather_than_assumed_to_be_one():
    """Filing in more than one state: no yes/no question can say how many, so
    no line claims to know."""
    priced = quote(stateReturnNeeded="yes", multipleStateReturns="yes")
    assert "return_state" not in codes(priced)
    listed = next(u for u in priced.unpriced if u.service_code == "return_state")
    assert "does not record how many" in listed.reason
    assert priced.total == RETURN_1040


def test_the_client_sentence_says_what_the_number_leaves_out():
    said = quote(stateReturnNeeded="yes",
                 multipleStateReturns="yes").client_sentence()
    assert "estimate" in said and "not a bill" in said
    assert "state tax return" in said.lower()


# --- a warning every client gets is a warning nobody reads (principle 13) ------

def test_the_state_return_warning_can_be_cleared_by_an_answer():
    """It used to be on every 1040 quote ever produced, because the interview
    recorded nothing about states — so it taught the owner to scroll past the
    one place the quote says "this number is not the whole number"."""
    one_state = quote(stateReturnNeeded="yes", multipleStateReturns="no")
    assert one_state.unpriced == (), "one state is a priced state, not a warning"

    no_state = quote(stateReturnNeeded="no", multipleStateReturns="no")
    assert no_state.unpriced == () and "return_state" not in codes(no_state), (
        "somebody in a state with no income tax files no state return, and a "
        "quote that warns about one is warning about work nobody will do")


def test_one_state_return_is_priced_rather_than_warned_about():
    """450.00 federal + 95.00 for the one state = 545.00, hand-checked."""
    priced = quote(stateReturnNeeded="yes", multipleStateReturns="no")
    assert codes(priced) == ["return_1040", "return_state"]
    assert priced.standard_total == RETURN_1040 + STATE_RETURN == Decimal("545.00")
    line = next(l for l in priced.lines if l.service_code == "return_state")
    assert line.quantity == 1
    assert line.because == "you file one state return alongside the federal one"


def test_the_state_return_is_never_quoted_twice():
    """Two entries name return_state. They are gated to be mutually exclusive,
    and a client billed twice for one state return is what a mistake here looks
    like — so it is asserted over every answer pair, not just the likely one."""
    for needed in ("yes", "no", ""):
        for many in ("yes", "no", ""):
            priced = quote(stateReturnNeeded=needed, multipleStateReturns=many)
            named = ([l.service_code for l in priced.lines]
                     + [u.service_code for u in priced.unpriced])
            assert named.count("return_state") <= 1, (needed, many)


def test_a_1040_quote_can_be_a_whole_number_the_letter_may_state():
    """The engagement letter states a bare fee only when the total is the WHOLE
    price. While every 1040 carried an unpriceable state return, that was never
    true of any of them — so no 1040 letter could ever carry a fee."""
    priced = quote(plan_key="standard", stateReturnNeeded="yes",
                   multipleStateReturns="no")
    assert priced.unpriced == ()
    assert priced.total == Decimal("545.00")


def test_an_entirely_hourly_engagement_is_not_quoted_as_zero():
    """The whole year-end clean-up is hourly. "$0.00" reads as free; what is
    true is "not priced yet", and those are different sentences."""
    wf = load_workflow("business_year_end_cleanup")
    priced = quote_for(wf, {}, client_id=CLIENT, tax_year=YEAR)
    assert priced.lines == () and priced.unpriced
    assert "0.00" not in priced.client_sentence()
    assert "cannot put a number on this" in priced.client_sentence()
    assert "NOTHING HERE HAS A PRICE YET" in priced.summary_block()


# --- a quote is not an invoice ------------------------------------------------

def test_a_quote_cannot_be_issued():
    with pytest.raises(QuoteError, match="cannot be issued"):
        quote().issue(on=None)


def test_a_quote_cannot_be_given_an_invoice_number():
    with pytest.raises(QuoteError, match="invoice number"):
        quote().invoice_id


def test_a_quote_cannot_walk_into_the_invoice_register():
    """The numbering routine reads .invoice_id off everything it is handed —
    which is exactly where a quote mistaken for an invoice would land."""
    with pytest.raises(QuoteError):
        next_invoice_number([quote()], year=YEAR)


def test_a_quote_cannot_have_lines_added_by_hand():
    with pytest.raises(QuoteError, match="derived from the interview"):
        quote().add("return_1040")


def test_a_quote_is_not_an_invoice_and_cannot_be_edited_into_one():
    priced = quote()
    assert not isinstance(priced, Invoice)
    assert priced.is_estimate is True
    with pytest.raises(Exception):
        priced.lines = ()
    with pytest.raises(Exception):
        priced.is_estimate = False


# --- config, not code ---------------------------------------------------------

def test_changing_a_rate_in_the_catalogue_changes_the_quote(tmp_path, monkeypatch):
    """The owner edits a price by hand in March. No code change, no restart."""
    from satc.billing import catalogue

    billing = tmp_path / "billing"
    billing.mkdir()
    (billing / "rate_plans.yaml").write_text(
        "meta:\n  default_plan: standard\n"
        "plans:\n  - key: standard\n    name: Standard\n    discount_pct: 0\n",
        encoding="utf-8")

    def write(rate):
        (billing / "services.yaml").write_text(
            "services:\n"
            "  - code: return_1040\n"
            "    name: 'Individual return'\n"
            "    client_label: 'Your federal individual tax return'\n"
            "    unit: fixed\n"
            f"    standard_rate: {rate}\n", encoding="utf-8")

    monkeypatch.setattr(catalogue, "billing_dir", lambda *a, **k: billing)
    catalogue.forget_prices()
    _write_workflow(tmp_path, "services:\n  - service: return_1040\n"
                              "    because: this is your federal return\n")
    wf = load_workflow("tiny", tmp_path)

    try:
        write(450)
        first = quote_for(wf, {}, client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)
        assert first.total == Decimal("450.00")

        write(495)
        second = quote_for(wf, {}, client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)
        assert second.total == Decimal("495.00"), (
            "A price edit that needs a restart is a price edit that silently did "
            "not happen — the owner would quote at the old rate.")
    finally:
        catalogue.forget_prices()


def test_adding_a_service_to_a_branch_is_a_config_edit(tmp_path):
    """The whole point of the shape: a new branch price is a YAML edit."""
    _write_workflow(tmp_path, "services:\n  - service: return_1040\n")
    before = quote_for(load_workflow("tiny", tmp_path), {"soldShares": "yes"},
                       client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)
    assert codes(before) == ["return_1040"]

    _write_workflow(tmp_path, """
services:
  - service: return_1040
  - service: schedule_d
    condition: {question_id: soldShares, equals: "yes"}
    because: you told us you sold shares
""")
    after = quote_for(load_workflow("tiny", tmp_path), {"soldShares": "yes"},
                      client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)
    assert codes(after) == ["return_1040", "schedule_d"]
    assert after.standard_total == Decimal("595.00")


def test_every_service_priced_by_every_workflow_exists_in_the_catalogue():
    """The configs are hand-edited and hot-reloaded, so this is the check that
    stops a typo reaching a client as a 500 on the quote screen."""
    from satc.billing import services

    catalogue = services()
    for wf in list_workflows():
        for rule in load_service_map(wf.key):
            assert rule.service_code in catalogue, (
                f"{wf.key}.yaml prices {rule.service_code!r}, which is not in "
                f"configs/billing/services.yaml")


def test_pricing_a_service_the_catalogue_does_not_have_refuses(tmp_path):
    """Principle 10: the refusal names both files, because the fix is in one."""
    _write_workflow(tmp_path, "services:\n  - service: gold_plated_return\n")
    wf = load_workflow("tiny", tmp_path)
    with pytest.raises(ConfigError) as refusal:
        quote_for(wf, {}, client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)
    assert "tiny.yaml" in str(refusal.value)
    assert "configs/billing/services.yaml" in str(refusal.value)


def test_a_services_entry_with_no_code_refuses(tmp_path):
    _write_workflow(tmp_path, "services:\n  - because: something vague\n")
    with pytest.raises(ConfigError, match="no 'service:' code"):
        load_service_map("tiny", tmp_path)


def test_a_quantity_that_is_not_a_number_refuses(tmp_path):
    """"a few" is not a quantity, and quietly reading it as 1 would understate
    the quote by however many it really was."""
    _write_workflow(tmp_path, "services:\n  - service: return_state\n"
                              "    quantity: a few\n")
    with pytest.raises(ConfigError, match="unknown"):
        load_service_map("tiny", tmp_path)


def test_a_fixed_price_service_cannot_be_quoted_more_than_once(tmp_path):
    """schedule_d is one charge however many trades there were. Quoting two of
    them produces 290.00 — a total the invoice engine structurally refuses, so
    the owner would have to walk the number back with a client who read it."""
    _write_workflow(tmp_path, "services:\n  - service: schedule_d\n"
                              "    quantity: 2\n")
    wf = load_workflow("tiny", tmp_path)
    with pytest.raises(ConfigError) as refusal:
        quote_for(wf, {}, client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)

    words = str(refusal.value)
    assert "tiny.yaml" in words and "configs/billing/services.yaml" in words
    assert "FIXED-price" in words
    assert "per_form" in words, "principle 10: name the way out"


def test_the_invoice_refuses_the_quantity_the_quote_now_refuses():
    """The same pair again. The quote learned this rule from the invoice; if the
    invoice ever stops enforcing it, this says so rather than quietly agreeing."""
    from satc.billing.invoice import BillingError

    invoice = Invoice(invoice_id="2025-0002", client_id=CLIENT, tax_year=YEAR)
    with pytest.raises(BillingError, match="fixed-price service"):
        invoice.add("schedule_d", quantity=2)


def test_a_fixed_price_service_cannot_be_quoted_at_an_unknown_quantity(tmp_path):
    """"unknown" is a legitimate answer for a per-form service and a nonsense
    one here: there is exactly one of a fixed charge, always."""
    _write_workflow(tmp_path, "services:\n  - service: schedule_d\n"
                              "    quantity: unknown\n")
    with pytest.raises(ConfigError, match="FIXED-price"):
        quote_for(load_workflow("tiny", tmp_path), {}, client_id=CLIENT,
                  tax_year=YEAR, config_root=tmp_path)


def test_a_per_form_service_still_multiplies(tmp_path):
    """The mutation in the other direction: the guard is about the UNIT, not
    about quantities. Two state returns are 190.00 and always were."""
    _write_workflow(tmp_path, "services:\n  - service: return_state\n"
                              "    quantity: 2\n")
    priced = quote_for(load_workflow("tiny", tmp_path), {}, client_id=CLIENT,
                       tax_year=YEAR, config_root=tmp_path)
    assert priced.total == STATE_RETURN * 2 == Decimal("190.00")


# --- silence is not an answer -------------------------------------------------

def test_an_unanswered_question_cannot_put_money_on_the_quote(tmp_path):
    """`not_equals` is the hole: an unanswered question is not None-equal to
    "no", so silence satisfied the gate and bought a $145 line — carrying a
    sentence that told the client they had answered "". Principle 2."""
    _write_workflow(tmp_path, """
services:
  - service: schedule_d
    condition: {question_id: soldShares, not_equals: "no"}
""")
    priced = quote_for(load_workflow("tiny", tmp_path), {}, client_id=CLIENT,
                       tax_year=YEAR, config_root=tmp_path)

    assert codes(priced) == [], "silence must not become money"
    assert priced.total == Decimal("0.00")
    assert 'answered ""' not in priced.summary_block()
    assert '""' not in priced.client_sentence()


def test_what_silence_gated_is_shown_rather_than_dropped(tmp_path):
    """And it does not vanish either — a $145 service disappearing from an
    estimate with nothing said is principle 1 in the other direction. It is
    listed as work nobody can price yet, naming the question still to answer."""
    _write_workflow(tmp_path, """
services:
  - service: schedule_d
    condition: {question_id: soldShares, not_equals: "no"}
    because: you told us you sold shares
""")
    priced = quote_for(load_workflow("tiny", tmp_path), {}, client_id=CLIENT,
                       tax_year=YEAR, config_root=tmp_path)

    listed = next(u for u in priced.unpriced if u.service_code == "schedule_d")
    assert "Did you sell shares?" in listed.reason
    assert "cannot tell whether this applies" in listed.reason
    # And it must NOT keep the config's sentence, which says the client told us
    # something they have not told us.
    assert listed.because == "nothing on file yet says whether this applies"


def test_an_answered_question_still_prices_the_line(tmp_path):
    """The mutation: the rule is about SILENCE, not about `not_equals`. An
    explicit "yes" through the same gate is money, exactly as before."""
    _write_workflow(tmp_path, """
services:
  - service: schedule_d
    condition: {question_id: soldShares, not_equals: "no"}
    because: you told us you sold shares
""")
    priced = quote_for(load_workflow("tiny", tmp_path), {"soldShares": "yes"},
                       client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)
    assert codes(priced) == ["schedule_d"]
    assert priced.total == SCHEDULE_D


def test_one_answered_branch_of_an_any_still_prices_and_says_only_what_was_said(tmp_path):
    """Half-answered `any:`: the answer that fired it is real, so the line is
    real — but the sentence must quote only the question that was actually
    answered, never `"" to "Did you sell crypto?"`. An empty pair of quotes on a
    client-facing line reports silence as though the client had said it."""
    folder = tmp_path / "workflows"
    folder.mkdir(exist_ok=True)
    (folder / "tiny.yaml").write_text(
        "key: tiny\nname: Tiny workflow\nengagement_type: tiny\n"
        "questions:\n"
        "  - id: soldShares\n    label: Did you sell shares?\n    type: boolean\n"
        "  - id: soldCrypto\n    label: Did you sell crypto?\n    type: boolean\n"
        "tasks:\n  - template_id: tiny-task\n    title: Do the thing\n"
        "services:\n"
        "  - service: schedule_d\n"
        "    condition:\n"
        "      any:\n"
        "        - {question_id: soldShares, equals: \"yes\"}\n"
        "        - {question_id: soldCrypto, equals: \"yes\"}\n",
        encoding="utf-8")

    priced = quote_for(load_workflow("tiny", tmp_path), {"soldShares": "yes"},
                       client_id=CLIENT, tax_year=YEAR, config_root=tmp_path)
    assert codes(priced) == ["schedule_d"], "a real answer is still real money"
    assert priced.lines[0].because == 'you answered "yes" to "Did you sell shares?"'
    assert '""' not in priced.summary_block()
    assert '""' not in priced.client_sentence()


# --- a hand-edited condition that the engine cannot read ----------------------

def test_a_condition_naming_a_question_the_workflow_does_not_ask_refuses(tmp_path):
    """A typo'd question id consults nothing forever. Principles 5 and 10: name
    the question, the file, and what this workflow actually asks."""
    _write_workflow(tmp_path, """
services:
  - service: schedule_d
    condition: {question_id: soldShare, equals: "yes"}
""")
    with pytest.raises(ConfigError) as refusal:
        load_service_map("tiny", tmp_path)

    words = str(refusal.value)
    assert "soldShare" in words and "tiny.yaml" in words
    assert "soldShares" in words, "say what the workflow does ask"


def test_a_mistyped_operator_refuses_rather_than_pricing_everybody(tmp_path):
    """The expensive one. `equal:` is not a comparison the engine knows, so it
    falls off the end of the ladder and returns True — the line lands on every
    quote, with a `because` that is not true of the client reading it."""
    _write_workflow(tmp_path, """
services:
  - service: schedule_d
    condition: {question_id: soldShares, equal: "yes"}
    because: you told us you sold shares
""")
    with pytest.raises(ConfigError) as refusal:
        load_service_map("tiny", tmp_path)

    words = str(refusal.value)
    assert "equal" in words and "not_equals" in words
    assert "TRUE for everybody" in words


def test_the_mistyped_operator_would_otherwise_have_priced_everybody(tmp_path):
    """The mutation for the test above: prove the typo really is silent money
    rather than a broken config that would have failed anyway."""
    from satc.intake.workflows import evaluate_condition

    assert evaluate_condition({"question_id": "soldShares", "equal": "yes"},
                              {"soldShares": "no"}) is True


def test_a_condition_with_no_comparison_at_all_refuses(tmp_path):
    _write_workflow(tmp_path, """
services:
  - service: schedule_d
    condition: {question_id: soldShares}
""")
    with pytest.raises(ConfigError, match="no comparison at all"):
        load_service_map("tiny", tmp_path)


def test_every_condition_in_every_shipped_workflow_is_readable():
    """The check that makes the two above worth having: run it over the real
    configs, so a typo in the file the owner edits fails the build."""
    for wf in list_workflows():
        load_service_map(wf.key)


def test_a_workflow_with_no_services_block_prices_nothing(tmp_path):
    """A legitimate state, not an error — a monthly close is a retainer the
    catalogue does not quote in advance."""
    _write_workflow(tmp_path, "")
    priced = quote_for(load_workflow("tiny", tmp_path), {}, client_id=CLIENT,
                       tax_year=YEAR, config_root=tmp_path)
    assert priced.lines == () and priced.unpriced == ()
    assert priced.total == Decimal("0.00")


# --- determinism --------------------------------------------------------------

def test_the_same_answers_give_the_same_quote_in_the_same_order():
    first = quote(brokerageActivity="yes", homeTransaction="yes")
    second = quote(brokerageActivity="yes", homeTransaction="yes")
    assert codes(first) == codes(second) == ["return_1040", "schedule_d"]
    assert [l.because for l in first.lines] == [l.because for l in second.lines]
    assert first.total == second.total


def test_the_line_order_follows_the_config_not_the_answers():
    """Same set of services, answers given in a different order — the quote is
    the config's order either way, so two quotes can be diffed."""
    wf = load_workflow("personal_1040_core")
    one = quote_for(wf, {"digitalAssets": "yes", "brokerageActivity": "no"},
                    client_id=CLIENT, tax_year=YEAR)
    two = quote_for(wf, {"brokerageActivity": "yes", "digitalAssets": "no"},
                    client_id=CLIENT, tax_year=YEAR)
    assert codes(one) == codes(two) == ["return_1040", "schedule_d"]


# --- helpers ------------------------------------------------------------------

def _write_workflow(root, services_block: str) -> None:
    """A one-question workflow the test owns, at <root>/workflows/tiny.yaml."""
    folder = root / "workflows"
    folder.mkdir(exist_ok=True)
    (folder / "tiny.yaml").write_text(
        "key: tiny\n"
        "name: Tiny workflow\n"
        "engagement_type: tiny\n"
        "questions:\n"
        "  - id: soldShares\n"
        "    label: Did you sell shares?\n"
        "    type: boolean\n"
        "tasks:\n"
        "  - template_id: tiny-task\n"
        "    title: Do the thing\n"
        + services_block, encoding="utf-8")
