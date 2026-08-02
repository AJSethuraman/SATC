"""THE ENGAGEMENT PLAN screen — answer the interview once, see what falls out.

The engines behind this page are guarded elsewhere: the fan-out in
``test_intake_fanout.py``, the money in ``test_quote.py``, the calendar in
``test_obligations_calendar.py``, the promises in ``test_sla.py``. This file
guards the SCREEN, and specifically the ways a screen like this goes wrong even
when everything behind it is right:

* it lists a document request but cannot say which answer caused it, so nobody
  can defend the ask to the client who asks why;
* it adds the lines up itself, so the page and the engine hold two different
  opinions about a client's fee;
* it reads like a bill;
* it hides the work the catalogue could not price — which is exactly the work
  that turns up on an invoice nobody agreed to;
* it renders a statute, a firm cutoff and a promise in the same typeface, so a
  preference the owner changes over coffee reads like law (principle 4);
* it invents a promised date rather than naming the fact nobody records;
* it flattens the three-way blocking split, so a K-1 that cannot exist until
  September reads like a missing W-2.

Everything goes through the real ``create_app()`` and, except where a known
shape is needed, through the real ``satc.intake.fanout``. A fixture that
hand-registered the blueprint would keep passing after the wiring was dropped.
"""

from __future__ import annotations

import ast
import dataclasses
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from satc.app import intake_views
from satc.app.server import create_app
from satc.app.state import STATE
from satc.models.filing import Filing
from satc.models.identity import PublicClient

CLIENT = "SATC-PLAN-1"
WORKFLOW = "personal_1040_core"
YEAR = 2025


# --- wiring -------------------------------------------------------------------

@pytest.fixture()
def client():
    app = create_app()
    assert "intake.engagement_plan" in app.view_functions, (
        "create_app() does not reach the engagement plan route — it lives on the "
        "intake blueprint, which server.py already registers.")
    return app.test_client()


@pytest.fixture()
def practice(monkeypatch):
    """A known client, and nothing else on file.

    Patches the mart and the store rather than the view's own helpers, so the
    screen resolves the client, the rate plan and the filing history exactly the
    way it does in the running app.
    """
    def install(*, entity_type="INDIVIDUAL", engagements=(), filings=()):
        pc = PublicClient(client_id=CLIENT, entity_type=entity_type,
                          display_label=f"Client {CLIENT} ({entity_type})",
                          tin_last4="1234", tin_masked="***-**-1234",
                          default_return_type="1040", home_state="MA")
        monkeypatch.setattr(STATE.mart, "public_clients", [pc])
        monkeypatch.setattr(STATE.mart, "engagements", list(engagements))
        monkeypatch.setattr(STATE, "names", {CLIENT: "Maplewood Household"})
        monkeypatch.setattr(STATE, "filings", lambda return_key="": list(filings))
    return install


def plan_url(workflow=WORKFLOW, tax_year=YEAR, **answers) -> str:
    parts = [f"client={CLIENT}", f"workflow={workflow}", "mode=new"]
    if tax_year is not None:
        parts.append(f"tax_year={tax_year}")
    parts += [f"q_{qid}={value}" for qid, value in answers.items()]
    return "/intake/plan?" + "&".join(parts)


def body_of(resp) -> str:
    assert resp.status_code == 200, resp.status_code
    return resp.data.decode("utf-8")


def a_real_plan(**answers):
    """The plan the real fan-out produces for these answers."""
    from satc.intake.fanout import fan_out
    from satc.intake.workflows import load_workflow

    answers = {"newSatcClient": "yes", **answers}
    return fan_out(load_workflow(WORKFLOW), answers, client_id=CLIENT,
                   tax_year=YEAR, today=date.today())


@pytest.fixture()
def instead_of_the_quote(monkeypatch):
    """Swap the plan's quote for one of a known shape, keeping everything else real."""
    def install(quote, **answers):
        plan = dataclasses.replace(a_real_plan(**answers), quote=quote)
        monkeypatch.setattr(intake_views, "_fan_out", lambda *a, **kw: plan)
        return plan
    return install


# --- a quote whose totals are NOT derivable from its own lines ---------------
#
# Built to the real ``satc.billing.quote.Quote`` shape but with arithmetic the
# page cannot reproduce: the lines come to 635.00, standard minus discount comes
# to 800.00, and the total is neither. The real engine's total IS derivable,
# which is exactly why it could not prove this.

@dataclass(frozen=True)
class AQuoteLine:
    service_code: str
    label: str
    quantity: Decimal
    standard_amount: Decimal
    because: str


@dataclass(frozen=True)
class APlan:
    key: str = "household"
    name: str = "Household rate"
    discount_pct: Decimal = Decimal("20")
    client_label: str = "Household rate"


@dataclass(frozen=True)
class SomethingUnpriced:
    service_code: str
    label: str
    because: str
    reason: str


@dataclass(frozen=True)
class AQuote:
    lines: tuple = ()
    unpriced: tuple = ()
    plan: APlan = field(default_factory=APlan)
    plan_is_fallback: bool = False
    plan_why: str = "'household' agreed on the 2025 engagement."
    standard_total: Decimal = Decimal("1000.00")
    discount_total: Decimal = Decimal("200.00")
    total: Decimal = Decimal("471.35")
    shows_a_discount: bool = True
    is_estimate: bool = True


def a_quote(**over) -> AQuote:
    return AQuote(lines=(
        AQuoteLine("return_1040", "Your federal individual tax return", Decimal(1),
                   Decimal("450.00"), "this is your federal individual return"),
        AQuoteLine("schedule_e_rental", "Rental property", Decimal(1),
                   Decimal("185.00"), "you told us about a rental")), **over)


# --- it renders at all, through the real engines ------------------------------

def test_the_plan_renders_for_a_real_workflow_and_real_answers(client, practice):
    """No doubles anywhere: the real fan-out, the real catalogue, the real
    calendar, the real promises."""
    practice()

    page = body_of(client.get(plan_url(expectedK1s="yes", marketplaceInsurance="yes")))
    assert "Personal 1040 core" in page
    assert "Maplewood Household" in page
    # All four sections, on one screen, out of one set of answers.
    assert "What we need from" in page
    assert "What it will cost" in page
    assert "When it is due" in page
    assert "What we promised" in page
    # And nothing has happened.
    assert "Nothing above has happened yet" in page


# --- what we need -------------------------------------------------------------

def test_a_document_request_names_the_answer_that_caused_it(client, practice):
    """The payoff of the whole screen. A request whose cause cannot be named is
    a request nobody can defend to the client who asks why we want it."""
    practice()

    page = body_of(client.get(plan_url(marketplaceInsurance="yes")))
    assert "1095-A" in page
    assert "you answered “yes” to “Marketplace health insurance coverage?”" in page
    # An answer nobody gave asks for nothing.
    assert "1098-T" not in page


def test_an_unconditional_request_says_so_rather_than_naming_a_random_answer(
        client, practice):
    practice()

    page = body_of(client.get(plan_url()))
    assert "Asked on every Personal 1040 core engagement." in page


def test_the_three_way_blocking_split_puts_a_late_k1_apart_from_the_rest(
        client, practice):
    """A K-1 that cannot exist until September does not stop prep; a screen that
    files it with the ordinary asks throws away the distinction the split buys."""
    practice()

    page = body_of(client.get(plan_url(expectedK1s="yes", marketplaceInsurance="yes")))
    filing_half = page.split("Blocks filing, not prep", 1)[1]
    late, rest = filing_half.split("Useful, not load-bearing", 1)
    assert "K-1" in late
    assert "1095-A" in rest
    assert "K-1" not in rest


def test_a_request_the_rule_says_blocks_prep_renders_in_the_blocking_half(
        client, practice, monkeypatch):
    """The class comes off the cited rule via the plan's own RequestedItem. The
    screen's job is to render the three apart — so give it a blocking one."""
    practice()
    plan = a_real_plan(marketplaceInsurance="yes")
    for item in plan.requests:
        if item.doc_type == "1095-A":
            item.blocking = "blocking"
    monkeypatch.setattr(intake_views, "_fan_out", lambda *a, **kw: plan)

    page = body_of(client.get(plan_url(marketplaceInsurance="yes")))
    prep_half = page.split("Blocks starting prep", 1)[1].split(
        "Useful, not load-bearing", 1)[0]
    assert "1095-A" in prep_half


# --- what it will cost --------------------------------------------------------

def test_the_total_on_the_page_is_the_engines_and_not_the_pages_arithmetic(
        client, practice, instead_of_the_quote):
    """Two opinions about a client's fee is one too many. These totals are
    deliberately not derivable from the lines: a page that summed them would
    print 635.00, and one that took standard less discount would print 800.00."""
    practice()
    instead_of_the_quote(a_quote())

    page = body_of(client.get(plan_url()))
    assert "471.35" in page          # the engine's total, verbatim
    assert "1,000.00" in page        # the engine's standard total
    assert "635.00" not in page      # ...not the sum of the lines
    assert "800.00" not in page      # ...not standard minus discount


def test_the_estimate_cannot_be_mistaken_for_an_invoice(client, practice):
    practice()

    page = body_of(client.get(plan_url()))
    assert 'data-kind="estimate"' in page
    assert "ESTIMATE — NOT AN INVOICE." in page
    assert "Nobody has been billed" in page
    # An estimate that offers to be paid is a bill in everything but name.
    assert "Amount due" not in page
    assert "Pay this" not in page


def test_work_the_catalogue_cannot_price_is_shown_and_not_hidden(client, practice):
    """Work with no price is exactly the work a client should hear about BEFORE
    it appears on an invoice. The real catalogue cannot price a state return,
    because no question records how many states."""
    practice()

    page = body_of(client.get(plan_url()))
    assert "Not in the total — not priced yet" in page
    assert "State tax return" in page
    assert "the interview does not record how many" in page


def test_a_rate_plan_nobody_agreed_is_shown_as_a_gap_not_as_an_agreement(
        client, practice):
    practice()

    page = body_of(client.get(plan_url()))
    assert "No rate plan agreed for 2025" in page
    assert "That is a gap, not an agreement." in page


def test_an_engagement_with_nothing_priceable_never_reads_as_free(
        client, practice, instead_of_the_quote):
    """0.00 and "not priced yet" are opposite statements about a fee."""
    practice()
    instead_of_the_quote(AQuote(lines=(), unpriced=(SomethingUnpriced(
        "bookkeeping_cleanup", "Getting your books ready", "you said the books need work",
        "charged at $125.00 an hour, and the hours are not known"),)))

    page = body_of(client.get(plan_url()))
    assert "which is not the same thing as no charge" in page
    assert "Estimated total" not in page


def test_a_missing_pricing_engine_is_a_sentence_and_never_a_number(
        client, practice, monkeypatch):
    """Refuse rather than default (principle 5). A plausible fee is worse than
    no fee, because nobody would ever notice it was made up.

    ``fan_out`` already answers this way — it names the missing engine rather
    than returning a zero — so the fixture is its own output, and the screen's
    job is to print it and show no figures beside it."""
    practice()
    unpriceable = dataclasses.replace(
        a_real_plan(), quote=None,
        quote_unavailable=("No quote: satc.billing.quote is not installed, so nothing "
                           "can price these answers."))
    monkeypatch.setattr(intake_views, "_fan_out", lambda *a, **kw: unpriceable)

    page = body_of(client.get(plan_url()))
    assert "satc.billing.quote is not installed" in page
    assert 'data-kind="estimate"' not in page, "a refused quote must show no figures"


# --- when it is due -----------------------------------------------------------

def test_the_statutory_date_is_the_one_the_obligation_engine_computed(
        client, practice):
    """Computed, never stored (principle 3), and cited (principle 4)."""
    practice()
    expected = a_real_plan()

    page = body_of(client.get(plan_url()))
    # Inside the statute block, not merely somewhere on the page: a date with no
    # authority next to it is the thing this system must never print.
    statute = page.split('data-kind="statute"', 1)[1].split(
        'data-kind="firm_policy"', 1)[0]
    assert expected.duty.due.strftime("%B %d, %Y") in statute
    assert "IRS Instructions for Form 1040; IRC §6072(a)" in statute
    assert expected.duty.extended_due.strftime("%B %d, %Y") in statute
    assert "never to pay" in statute


def test_a_statute_a_firm_cutoff_and_a_promise_are_marked_apart_in_the_markup(
        client, practice):
    """Principle 4 as a UI obligation. Prose can be rewritten in a template edit;
    the kind has to survive that, so it is carried in the markup."""
    practice()

    page = body_of(client.get(plan_url()))
    assert 'data-kind="statute"' in page
    assert 'data-kind="firm_policy"' in page
    assert 'data-kind="promise"' in page
    # ...and in words too, because the owner reads words.
    assert "FIRM POLICY — NOT LAW" in page
    assert "configs/firm_policy.yaml" in page
    assert "OUR PROMISE — NOT LAW" in page
    # ...and the three phrases are three different things, said once each.
    assert page.count("OUR PROMISE — NOT LAW") == 1
    assert page.count("FIRM POLICY — NOT LAW") == 1


def test_the_firm_cutoff_is_the_one_the_owners_own_config_sets(client, practice):
    practice()
    expected = a_real_plan()

    page = body_of(client.get(plan_url()))
    cutoff = page.split('data-kind="firm_policy"', 1)[1]
    assert expected.duty.documents_due.strftime("%B %d, %Y") in cutoff
    assert "no citation" in cutoff


def test_work_with_no_statutory_duty_gets_no_date_at_all(client, practice):
    """A bookkeeping engagement discharges no filing duty. April 15 shown
    against one would be a confident wrong answer, which is the worst failure
    there is (principle 5). The engine's refusal is rendered, not rewritten."""
    practice()

    practice(entity_type="")

    page = body_of(client.get(plan_url(workflow="business_monthly_bookkeeping")))
    assert "SATC will not plan this engagement" in page
    assert "business_monthly_bookkeeping" in page      # the refusal names it
    assert "cannot compute a deadline for it" in page
    assert 'data-kind="statute"' not in page
    assert "April" not in page
    assert "no date has been guessed at" in page


def test_no_tax_year_is_refused_rather_than_guessed(client, practice):
    """A deadline is a rule landed on a PERIOD. Without the year there is none."""
    practice()

    page = body_of(client.get(plan_url(tax_year=None)))
    assert "Set the tax year." in page
    assert 'data-kind="statute"' not in page


# --- what we promised ---------------------------------------------------------

def test_a_promise_whose_start_fact_is_missing_shows_the_named_refusal(
        client, practice):
    """Principle 1. Four of the five promises on file have a clock end nothing
    in SATC records, so the screen names the missing fact rather than blanking
    the cell or, worse, showing a green tick derived from a guess."""
    practice(filings=[])

    page = body_of(client.get(plan_url()))
    assert "Return out once the documents are complete" in page
    assert "nothing records when the documents went complete" in page
    assert "SATC cannot tell you whether this was met" in page
    # And the one promise SATC COULD measure refuses too, differently: the fact
    # is recordable, it is just not recorded on this client. A screen that
    # substituted a plausible start date would show a promise nobody made.
    assert "Fixing and retransmitting a rejected return" in page
    assert "nothing on this one records when the rejection was keyed off Drake" in page
    assert "2 business days from" not in page


def test_a_promise_with_a_recorded_start_fact_shows_the_date(client, practice):
    """The other half of the same rule — otherwise the refusal above is a panel
    that can only ever refuse, which is not evidence of anything (principle 12).
    The e-file rejection is the one clock both of whose ends SATC records."""
    from satc.work.sla import sla

    rejected_on = date(2026, 3, 10)
    practice(filings=[Filing(filing_id="F-1", return_key="RK-1", client_id=CLIENT,
                             ack_code="R", ack_date=rejected_on)])
    lands = sla("efile_reject_turnaround").landing(rejected_on)

    page = body_of(client.get(plan_url()))
    assert lands.strftime("%B %d, %Y") in page
    assert "2 business days from" in page


# --- the edges ----------------------------------------------------------------

def test_an_unknown_workflow_is_a_404_and_not_a_500(client, practice):
    practice()
    resp = client.get(f"/intake/plan?client={CLIENT}&workflow=not_a_workflow&tax_year={YEAR}")
    assert resp.status_code == 404
    page = resp.data.decode("utf-8")
    assert "not_a_workflow" in page
    assert "Pick one from the interview screen" in page      # principle 10


def test_naming_no_workflow_offers_the_picker_rather_than_refusing(client, practice):
    """"Which workflow" is a question with an answer. 404 is for one that does
    not exist, not for one nobody has named yet."""
    practice()
    page = body_of(client.get(f"/intake/plan?client={CLIENT}&tax_year={YEAR}"))
    assert "Which engagement?" in page
    assert "Personal 1040 core" in page


def test_the_screen_offers_a_letter_draft_and_the_draft_is_all_it_is(
        client, practice):
    """Principle 9. One click, not zero — and the click drafts, it does not send."""
    practice()

    page = body_of(client.get(plan_url()))
    assert "Draft the engagement letter →" in page
    assert "template=engagement_letter" in page
    assert "It drafts; you send it." in page


def test_the_letters_fee_slot_says_which_condition_left_it_empty(client, practice):
    """Principle 1 reaching a document a client signs. The letter omits the fee;
    this screen says WHICH of the two reasons applies, because they are
    different problems with different fixes."""
    practice()

    page = body_of(client.get(plan_url()))
    assert "nobody has agreed a rate plan with this client" in page
    assert "Agree a plan on the engagement first." in page


# --- and it commits nothing ---------------------------------------------------

_PLAN_FUNCTIONS = {
    "engagement_plan", "_plan_answers", "_because", "_needs", "_fan_out",
    "_sla_outcomes", "_recorded_starts", "_fee_slot",
}

_DISPOSING = {
    "create_engagement", "save_job", "save_task", "save_mart", "save_invoices",
    "save_payments", "save_requested_items", "set_task_completed", "close_request",
    "set_filing_status", "commit_client_import", "delete_client", "post_confirmed",
    "run_intake", "upsert_identity", "reload", "write_bytes", "save_workflow_override",
}


def test_the_plan_screen_writes_nothing(client, practice):
    """Nothing on this screen commits anything (principle 9). Generating the
    engagement stays the click the owner makes, and it happens somewhere else."""
    tree = ast.parse(Path(intake_views.__file__).read_text(encoding="utf-8"))
    checked = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in _PLAN_FUNCTIONS:
            continue
        checked.add(node.name)
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call):
                called = getattr(inner.func, "attr", None) or getattr(inner.func, "id", None)
                assert called not in _DISPOSING, \
                    f"{node.name} calls {called} — that is disposing, not proposing"
    assert checked == _PLAN_FUNCTIONS, f"never checked: {sorted(_PLAN_FUNCTIONS - checked)}"


_STORE_WRITES = ("save_mart", "save_job", "save_task", "save_requested_items",
                 "save_invoices", "save_payments", "upsert_identity",
                 "upsert_relationship", "save_workflow_override", "delete_client",
                 "set_filing_status", "delete_intake_line_items")


def test_planning_an_engagement_writes_nothing_to_the_store(client, practice,
                                                            monkeypatch):
    """The plan lists what WOULD be asked for. Nothing reaches the register, or
    anything else durable, until the owner generates it.

    A tripwire on the store rather than a count of an in-memory list: the mart
    the screen reads and the tables it would write are not the same object, so
    counting rows would miss a save entirely."""
    practice()
    for name in _STORE_WRITES:
        if hasattr(STATE.store, name):
            monkeypatch.setattr(STATE.store, name, lambda *a, _n=name, **kw: (_ for _ in ()).throw(
                AssertionError(f"the plan screen called store.{_n} — that is disposing")))

    body_of(client.get(plan_url(expectedK1s="yes", marketplaceInsurance="yes")))


def test_generating_the_engagement_is_a_separate_deliberate_post(client, practice):
    """The plan is a read. The one thing that writes is a form the owner submits
    to the route that has always done it."""
    practice()

    page = body_of(client.get(plan_url(expectedK1s="yes")))
    assert 'action="/intake/new"' in page
    assert "Generate this engagement →" in page
    # The answers travel with it, so what is generated is what was previewed —
    # and so does the COMPUTED deadline, not one anybody typed.
    assert 'name="q_expectedK1s" value="yes"' in page
    assert f'name="due_date" value="{a_real_plan().duty.due.isoformat()}"' in page
