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
  September reads like a missing W-2;
* it supplies a deadline the ENGINE refused to compute, by answering "which
  return is this" from a fact that was not asked about — so a bookkeeping
  engagement gets a statute and a mis-clicked workflow gets a confident wrong
  one (principle 5);
* it attributes the blocking split to the deadline's citation, which is not
  where any of its three classes comes from (principle 4);
* it renders a promise the engine has already judged as a bare date, throwing
  the judgement away — or, worse, never asks the engine for a judgement at all,
  so met/missed/on-track are all structurally unreachable and every row says
  "nobody looked";
* it carries rows that are byte-identical on every plan for every client
  forever, which is what teaches somebody to scroll past the row that mattered
  (principle 13);
* it shows a row the practice cannot clear by doing the work;
* it answers about this engagement with a fact from another year and another
  return;
* it hands the owner — a tax preparer — a refusal written for a developer;
* it 500s where it should refuse;
* it posts something other than the plan the owner just read.

Everything goes through the real ``create_app()`` and, except where a known
shape is needed, through the real ``satc.intake.fanout``. A fixture that
hand-registered the blueprint would keep passing after the wiring was dropped.
"""

from __future__ import annotations

import ast
import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime
from html import unescape
from decimal import Decimal
from pathlib import Path

import pytest

from satc.app import intake_views
from satc.app.server import create_app
from satc.app.state import STATE
from satc.ids import return_key
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


def flat(html: str) -> str:
    """One-line the markup, so a sentence can be asserted across a line wrap.

    Only for prose. Anything asserting about STRUCTURE — which half of the page a
    row landed in, which ``data-kind`` wraps it — reads the raw markup, because
    that is the thing under test.
    """
    return " ".join(html.split())


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
    # ...and the "nothing ever lands here" warning goes away when something does.
    # A warning that cannot clear is the row the owner learns to scroll past.
    assert "the classifier failing to fire" not in page


def test_each_blocking_class_is_attributed_to_where_it_actually_comes_from(
        client, practice):
    """Principle 4, upside down and put back. The page asserted that all three
    classes "come from the same cited rule the deadline does". None of them does.

    ``blocking`` comes from the rule's own ``blocking_docs``, cited by its
    ``blocking_source`` (Pub 1345) — a DIFFERENT rule from the one that says when
    the return is due (IRC §6072(a)). ``expected_late`` comes from a hardcoded
    Python literal that nobody sourced. ``non_blocking`` is the default. A screen
    that dresses the uncited one as law is the exact failure principle 4 names.
    """
    practice()
    expected = a_real_plan()

    page = body_of(client.get(plan_url(expectedK1s="yes")))
    assert "it comes from" not in page, "the false attribution must be gone"

    # The blocking list, cited to its OWN source and visibly not the deadline's.
    cited = flat(page.split('data-kind="cited_rule"', 1)[1].split("</div>", 1)[0])
    assert "IRS Pub 1345" in cited
    assert "W-2" in cited and "1099-R" in cited
    assert expected.citation in cited          # named, precisely to be told apart
    assert "two rules answering two questions" in cited

    # The judgement, marked as a judgement — in the markup, not only in prose.
    judgement = flat(page.split('data-kind="uncited_judgement"', 1)[1].split("</div>", 1)[0])
    assert "No citation" in judgement
    assert "satc.models.readiness.blocking_class_for" in judgement
    # Pub 1345 belongs to the class above it and must not bleed onto this one.
    assert "Pub 1345" not in judgement


def test_a_blocking_class_nothing_can_ever_reach_says_so_rather_than_reading_empty(
        client, practice):
    """The W-2 ask renders under "Useful, not load-bearing" on every 1040 plan
    there has ever been, and the page said a cited rule put it there.

    Root cause is not on this screen: ``configs/workflows/personal_1040_core.yaml``
    types the ask that collects W-2s as ``doc_type: Core income documents``, a
    bucket, while the rule's ``blocking_docs`` are form numbers, and
    ``blocking_class_for`` matches the whole string. So the class is unreachable
    for every plan. The screen cannot honestly reclassify — what blocks is the
    cited rule's business, not a literal in a view — but it must not present an
    empty top bucket as though the file were clean (principles 1 and 13).
    """
    practice()

    page = body_of(client.get(plan_url(marketplaceInsurance="yes")))
    assert "Blocks starting prep" not in page          # still genuinely unreachable
    assert "the classifier failing to fire, not a clean file" in page
    # It names the rule's documents, the bucket that failed to match them, and
    # both places the fix could go (principle 10).
    assert "W-2, W-2G, 1099-R" in page
    assert "Core income documents" in page
    assert "configs/workflows/personal_1040_core.yaml" in page
    assert "satc.models.readiness.blocking_class_for" in page
    assert "treat the split below as unanswered" in page


def test_a_rule_that_names_no_blocking_documents_says_that_instead_of_warning(
        client, practice):
    """The 1120-S rule lists none — that is the rule's answer, not a classifier
    that failed. Warning about it would be noise on every S-corp plan forever."""
    practice(entity_type="SCORP")

    page = body_of(client.get(plan_url(workflow="business_scorp_tax")))
    assert "names no such documents at all" in page
    assert "the classifier failing to fire" not in page


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
    """A bookkeeping engagement discharges no filing duty — AND THAT IS TRUE OF A
    REAL S-CORP, which is the only version of this that matters.

    The engine refuses a workflow that names no return. The screen used to defeat
    that refusal by supplying the client's recorded entity type, which answers a
    question nobody asked — "what would this taxpayer file if they were filing" —
    so a monthly-bookkeeping plan for an S corporation came back with a STATUTE
    badge, March 16 and a citation to IRC §6072(b). The engagement files nothing;
    the client is an S corporation; both are true and only one of them is about
    this engagement.

    The refusal has to be THE RIGHT ONE, not merely some refusal. "SATC does not
    know how it knows this client is an S-corp" invites the owner to record the
    basis, after which bookkeeping would get a filing deadline again. The true
    answer does not depend on the client at all.
    """
    practice(entity_type="SCORP")

    page = body_of(client.get(plan_url(workflow="business_monthly_bookkeeping")))

    # It PLANS — refusing outright made two of the four business workflows
    # unreachable, which is worse than the deadline it was preventing.
    assert "SATC will not plan this engagement" not in page

    # ...but carries no statutory anything. The absence IS the answer.
    assert 'data-kind="statute"' not in page
    assert "NO STATUTORY DEADLINE" in page
    assert "1120S" not in page
    assert "no date has been guessed at" in page
    assert "files nothing" in page


def test_a_workflow_and_a_client_record_that_disagree_reach_the_screen_as_a_refusal(
        client, practice):
    """Principle 5. Two recorded facts claim to say what this engagement files:
    the workflow the owner clicked declares an S-corp return, the client record
    says INDIVIDUAL. The screen printed "STATUTE April 15, 2026 — Form 1040" with
    a citation over a mis-clicked S-corp workflow, and never said a second fact
    disagreed.

    ``duty_rule_for`` now refuses the disagreement itself, and the screen's job
    is to let that refusal through instead of a date — which is what this guards.
    A view holding its own opinion about which duty applies would be a second
    place for the answer to be wrong."""
    practice(entity_type="INDIVIDUAL")

    page = body_of(client.get(plan_url(workflow="business_scorp_tax")))
    assert "SATC will not plan this engagement" in page
    # BOTH facts named, because the fix is to correct one of them and the owner
    # cannot do that without knowing which two are in conflict (principle 10).
    assert "INDIVIDUAL" in page and "SCORP" in page
    assert "will not pick between" in page
    # ...and not one date, from either of them.
    assert 'data-kind="statute"' not in page
    assert "April 15" not in page and "March 16" not in page


def test_a_workflow_that_does_prepare_a_return_still_gets_its_deadline(
        client, practice):
    """The other half of the two rules above — otherwise they are checks that can
    only ever refuse, which is not evidence of anything (principle 12). An S-corp
    client on the S-corp workflow is one engagement, one duty, one cited date."""
    practice(entity_type="SCORP")

    page = body_of(client.get(plan_url(workflow="business_scorp_tax")))
    assert "SATC will not plan this engagement" not in page
    statute = page.split('data-kind="statute"', 1)[1].split(
        'data-kind="firm_policy"', 1)[0]
    assert "Form 1120S" in statute
    assert "IRC" in statute


def test_no_tax_year_is_refused_rather_than_guessed(client, practice):
    """A deadline is a rule landed on a PERIOD. Without the year there is none."""
    practice()

    page = body_of(client.get(plan_url(tax_year=None)))
    assert "Set the tax year." in page
    assert 'data-kind="statute"' not in page


def test_a_year_the_calendar_has_no_period_for_is_refused_and_not_a_stack_trace(
        client, practice):
    """``_int_or_none`` returns the integer 0 for ``tax_year=0``, and 0 is falsy
    but not ``None`` — a year somebody typed, not a year nobody gave. It reached
    ``obligations.due_dates.tax_year``, which rightly refuses to invent a period
    for it, and the ValueError came out of the browser as a stack trace. A 500 is
    not a refusal; it is the absence of one (principles 5 and 10)."""
    practice()

    resp = client.get(plan_url(tax_year=0))
    assert resp.status_code == 200, "a nonsense year must refuse, not crash"
    page = resp.data.decode("utf-8")
    assert "SATC will not plan this engagement" in page
    assert "tax year 0" in page                       # the refusal names it back
    assert "Set the tax year to the year the return is for." in page
    assert 'data-kind="statute"' not in page


# --- what we promised ---------------------------------------------------------
#
# The panel had stopped answering the question it exists for. It resolved the
# START of every clock and never the STOP, so `compliance` correctly withheld a
# verdict on all of them — a compliance screen where met, missed and on-track
# were all structurally unreachable, and every row said "nobody looked". These
# tests go through the REAL app, the REAL policy file and REAL Filing records,
# because that is the only way a screen can be caught not asking.

RK_2025 = return_key(CLIENT, 2025, "1040", "US")
RK_2025_OH = return_key(CLIENT, 2025, "1040", "OH")
RK_2023 = return_key(CLIENT, 2023, "1065", "US")


def _filing(rk, *, ack="", attempt=1, ack_date=None, sent=None):
    return Filing(filing_id=f"F-{rk}-{attempt}", return_key=rk, client_id=CLIENT,
                  transmitted_at=sent, ack_code=ack, ack_date=ack_date, attempt=attempt)


def promise_panel(page: str) -> str:
    """Just the promise panel, so an assertion cannot be satisfied elsewhere."""
    assert 'data-kind="promise"' in page, "the promise panel lost its kind marking"
    return page.split('data-kind="promise"', 1)[1].split("</div></div>", 1)[0]


def promise_rows(page: str) -> list[str]:
    return [chunk.split("</tr>", 1)[0]
            for chunk in page.split('<tr class="dateline promise"')[1:]]


def test_the_screen_reports_a_verdict_and_not_only_a_date(client, practice):
    """The defect this panel had: it could not report ANY verdict.

    ``compliance`` returns a status and a sentence. The screen resolved only the
    start of the clock, so every row came back ``unresolved`` — and a test that
    read the status back off the engine passed anyway, because both sides had
    degraded to the same non-answer. So this one names MISSED literally. A
    rejection five years old that nothing ever retransmitted is a promise this
    practice broke, and the screen has to say so.
    """
    rejected_on = date(2020, 3, 10)
    practice(filings=[_filing(RK_2025, ack="R", ack_date=rejected_on,
                              sent=datetime(2020, 3, 9, 16, 0))])

    row, = promise_rows(body_of(client.get(plan_url())))
    assert "MISSED" in row, (
        "the engine judged this promise broken and the screen did not say so")
    assert '<span class="badge' in row
    assert f"we promised 2 business days from {rejected_on}" in row
    # An apology, never a penalty — and never dressed as a statute (principle 4).
    assert "apology to make, not a penalty to pay" in row
    assert 'data-kind="statute"' not in row


def test_every_verdict_the_engine_can_reach_is_reachable_from_this_screen(
        client, practice):
    """Principle 12, said as a range rather than as one case.

    MISSED alone proves a badge renders. It does not prove the screen can tell
    the three answers APART — which is what it could not do, and what a panel
    stuck on one verdict would still fail at silently.
    """
    seen = {}
    for label, filings in {
        "missed": [_filing(RK_2025, ack="R", ack_date=date(2020, 3, 10),
                           sent=datetime(2020, 3, 9, 16, 0))],
        "met": [_filing(RK_2025, ack="R", ack_date=date(2026, 3, 10),
                        sent=datetime(2026, 3, 9, 16, 0)),
                _filing(RK_2025, ack="A", attempt=2, ack_date=date(2026, 3, 13),
                        sent=datetime(2026, 3, 11, 9, 0))],
        "open": [_filing(RK_2025, ack="R", ack_date=date.today(),
                         sent=datetime.now())],
    }.items():
        practice(filings=filings)
        row, = promise_rows(body_of(client.get(plan_url())))
        seen[label] = row.split('data-status="', 1)[1].split('"', 1)[0]

    assert seen == {"missed": "missed", "met": "met", "open": "open"}


def test_recording_the_retransmission_clears_a_row_nothing_could_clear(
        client, practice):
    """The row the practice could not clear by doing the work.

    Any rejection older than two business days made the plan say so forever, and
    keying the retransmission changed nothing — the stop was never read. It went
    from "missed forever" to "unresolved forever", which is the same row wearing
    a different word. A queue whose rows cannot be cleared by working is a queue
    people stop reading (principle 13).
    """
    reject = _filing(RK_2025, ack="R", ack_date=date(2026, 3, 10),
                     sent=datetime(2026, 3, 9, 16, 0))
    practice(filings=[reject])
    still_owed, = promise_rows(body_of(client.get(plan_url())))
    assert "MISSED" in still_owed

    # Now the owner keys the retransmission that actually went out next morning.
    practice(filings=[reject, _filing(RK_2025, ack="A", attempt=2,
                                      ack_date=date(2026, 3, 13),
                                      sent=datetime(2026, 3, 11, 9, 30))])
    cleared, = promise_rows(body_of(client.get(plan_url())))
    assert "KEPT" in cleared and "MISSED" not in cleared, (
        "recording the work did not clear the row that said we had not done it")
    assert "2026-03-11" in cleared          # the day it actually went back out


def test_a_rejection_in_another_year_on_another_return_is_not_this_promise(
        client, practice):
    """The cross-year, cross-return leak, seen from the screen.

    The lookup scanned every filing the client had ever had, with no year and no
    return filter, and took the maximum ack_date. So a 2023 partnership
    rejection — fixed at the time, on a job that closed two years ago — became a
    broken promise on the 2025 1040 plan.
    """
    practice(filings=[_filing(RK_2023, ack="R", ack_date=date(2024, 4, 2),
                              sent=datetime(2024, 4, 1, 10, 0))])

    panel = promise_panel(body_of(client.get(plan_url())))
    assert promise_rows(panel) == [], (
        "a 2023 1065 rejection was reported as a promise broken on the 2025 1040")
    assert "Nothing on this engagement has started one of our promise clocks" in panel
    assert "1065" not in panel


def test_two_returns_in_one_year_get_two_rows_that_say_which(client, practice):
    """Principle 13: two rows must never say the same thing.

    A client with a federal and a state rejection in the same year owes two
    different retransmissions. Rendered without the return they are the same row
    printed twice — and the key itself is not something to print at somebody, so
    the row says "2025 Form 1040 · OH".
    """
    practice(filings=[
        _filing(RK_2025, ack="R", ack_date=date(2026, 3, 2),
                sent=datetime(2026, 3, 1, 10, 0)),
        _filing(RK_2025, ack="A", attempt=2, ack_date=date(2026, 3, 5),
                sent=datetime(2026, 3, 3, 10, 0)),
        _filing(RK_2025_OH, ack="R", ack_date=date(2026, 4, 20),
                sent=datetime(2026, 4, 19, 10, 0))])

    rows = promise_rows(body_of(client.get(plan_url())))
    assert len(rows) == 2
    assert len({flat(r) for r in rows}) == 2, "two rows said the same thing"
    assert any("2025 Form 1040 · US" in r and "KEPT" in r for r in rows)
    assert any("2025 Form 1040 · OH" in r and "MISSED" in r for r in rows)
    assert not any(RK_2025_OH in r for r in rows), "the raw return key reached the screen"


def test_the_structural_refusals_are_gone_from_the_plan_and_said_once_elsewhere(
        client, practice):
    """Principle 13. Five byte-identical rows on every plan, for every client.

    They were RIGHT — SATC genuinely cannot measure a promise whose start fact
    nobody records — and they must not be deleted. But they are statements about
    the BUILD, identical whoever is on screen, so they belong on the capability
    screen and are pointed at from here in one line.
    """
    practice(filings=[])
    panel = promise_panel(body_of(client.get(plan_url())))

    assert "SATC cannot tell you whether this was met" not in panel
    assert "nothing records when the documents went complete" not in panel
    # ...and the pointer, once, with the count.
    assert "cannot be checked here at all" in flat(panel)
    assert "what SATC can and cannot check" in panel
    assert panel.count("/practice/promises") == 1

    # Said in full, once, where a missing capability belongs.
    capability = unescape(body_of(client.get("/practice/promises")))
    for label in ("First reply to a client's message",
                  "Substantive response to an IRS or state notice",
                  "Return out once the documents are complete",
                  "Acknowledging a signed 8879"):
        assert capability.count(label) == 1, f"{label} is missing or said twice"
    assert capability.count("SATC cannot tell you whether this was met") == 4
    # And the promise the build CAN check is on the same page, so the list reads
    # as a capability rather than as a list of complaints.
    assert "Fixing and retransmitting a rejected return" in capability


def test_the_plan_is_not_wallpaper_two_clients_do_not_render_the_same_panel(
        client, practice):
    """The measurable check for the defect: the panel used to hash identically
    across every client on file, because nothing in it came from the client."""
    import hashlib

    def digest(filings) -> str:
        practice(filings=filings)
        panel = promise_panel(body_of(client.get(plan_url())))
        return hashlib.sha1(flat(panel).encode("utf-8")).hexdigest()

    quiet = digest([])
    rejected = digest([_filing(RK_2025, ack="R", ack_date=date(2026, 3, 10),
                               sent=datetime(2026, 3, 9, 16, 0))])
    fixed = digest([_filing(RK_2025, ack="R", ack_date=date(2026, 3, 10),
                            sent=datetime(2026, 3, 9, 16, 0)),
                    _filing(RK_2025, ack="A", attempt=2, ack_date=date(2026, 3, 13),
                            sent=datetime(2026, 3, 11, 9, 30))])

    assert len({quiet, rejected, fixed}) == 3, (
        "the promise panel rendered identically whatever the practice recorded")


def test_a_promise_this_build_cannot_read_refuses_in_the_owners_language(
        client, practice, monkeypatch):
    """The OTHER path a refusal reaches this panel by, and it was left open.

    ``clocks_for`` refuses a promise whose clock nothing knows how to read out
    of the records — right, and loud rather than an empty table. But its message
    tells you to add a resolver in a Python module, and the person reading the
    engagement plan is a tax preparer. The panel is empty either way; what they
    need to know is that it is not a clean board and not their data.
    """
    from satc.config import ConfigError
    from satc.work import sla as sla_mod

    def refuse(kind, **kw):
        raise ConfigError("Add a resolver in satc.work.sla beside _reject_clocks.")

    monkeypatch.setattr(sla_mod, "clocks_for", refuse)
    practice(filings=[])

    panel = promise_panel(body_of(client.get(plan_url())))
    assert "cannot read its clock out of the records" in flat(panel)
    assert "nothing below is a clean bill of health" in flat(panel)
    assert "satc.work.sla" not in panel and "_reject_clocks" not in panel


def test_the_owner_is_never_handed_an_instruction_written_for_a_developer(
        client, practice):
    """Principle 10 is about the RIGHT next step, and right depends on the reader.

    The refusals were rendered verbatim on the owner's plan and named Python
    modules and function calls at somebody who is a tax preparer. A refusal the
    reader cannot act on is a refusal that only says no.
    """
    practice(filings=[])
    developer_words = ("satc.work", "satc.models", "clocks_for", "closed_on",
                       "unmeasurable_promises()", "principle", "docstring")

    for where, text in (("the plan", promise_panel(body_of(client.get(plan_url())))),
                        ("the capability screen",
                         body_of(client.get("/practice/promises")))):
        for word in developer_words:
            assert word not in text, f"{where} tells the owner about {word!r}"


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
    "_promise_rows", "_about_return", "practice_promise_gaps", "promise_capability",
    "_fee_slot", "_entity_type_for", "_blocking_basis",
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


def test_the_button_does_not_invent_a_new_client_the_owner_never_claimed(
        client, practice, monkeypatch):
    """Whether this is a new SAT-C client is a RECORDED FACT, and it is the gate
    the whole interview branches on.

    ``value="{{ mode or 'new' }}"`` invented it: an owner who never touched the
    new/returning switch posted ``mode=new``, which /intake/new takes as the
    owner having SAID so — overriding the record for a returning client and
    generating a different engagement from the plan just read. Absent, the route
    now reads it off the record, which is where this screen's own plan came from.
    """
    practice()
    monkeypatch.setattr(STATE, "is_returning", lambda cid: True)

    # No mode in the URL: nobody said which this is.
    page = body_of(client.get(f"/intake/plan?client={CLIENT}&workflow={WORKFLOW}"
                              f"&tax_year={YEAR}"))
    assert 'name="mode"' not in page, (
        "posting a mode nobody chose hands /intake/new an answer as if the owner "
        "had given it")
    # ...and the plan itself resolved the gate the same way the route will, so the
    # two are one derivation. A returning client is not asked for prior-year
    # returns, which is the task that answer gates.
    assert "Request prior-year returns" not in page

    # An explicit choice still travels — the owner may know better than the record.
    chosen = body_of(client.get(f"/intake/plan?client={CLIENT}&workflow={WORKFLOW}"
                                f"&tax_year={YEAR}&mode=new"))
    assert 'name="mode" value="new"' in chosen
    assert "Request prior-year returns" in chosen


# --- the button and the plan must be the same derivation --------------------
#
# The plan screen called fan_out; the Generate button called the legacy door.
# So the engagement the owner READ and the engagement they GENERATED came from
# two different derivations, and could disagree. These walk the real route.

def _post_engagement(web, *, year=2025, **extra):
    """Each test uses its OWN tax year: creating the same engagement twice is a
    no-op by design, so shared years would make these order-dependent."""
    data = {"client": "SATC-001000", "workflow_key": "personal_1040_core",
            "tax_year": str(year)}
    data.update(extra)
    return web.post("/intake/new", data=data)


def test_a_typed_due_date_no_longer_drives_the_engagement(client):
    """A date in a form box is not a statutory deadline (principles 3 and 4)."""
    from satc.app.state import STATE

    before = {j.job_id for j in STATE.store.load_jobs()}
    _post_engagement(client, year=2031, due_date="2031-12-25")
    STATE.reload()
    made = [j for j in STATE.store.load_jobs() if j.job_id not in before]

    assert made, "the route must still create an engagement"
    for job in made:
        assert str(job.due_date) != "2031-12-25", (
            "the deadline must come from the cited rule, not the form")


def test_generating_an_engagement_sets_the_obligation_key(client):
    """Nothing wrote this, which is why the work queue's deadline ranking could
    never fire on a real job."""
    from satc.app.state import STATE

    before = {j.job_id for j in STATE.store.load_jobs()}
    _post_engagement(client, year=2032)
    STATE.reload()
    made = [j for j in STATE.store.load_jobs() if j.job_id not in before]

    assert made
    assert all(j.obligation_key for j in made), "obligation_key is still empty"


def test_pressing_generate_twice_does_not_make_two_engagements(client):
    """Principle 8. The screen told the owner this was safe; it was not."""
    from satc.app.state import STATE

    _post_engagement(client, year=2033)
    STATE.reload()
    after_first = {j.job_id for j in STATE.store.load_jobs()}

    _post_engagement(client, year=2033)
    STATE.reload()
    assert {j.job_id for j in STATE.store.load_jobs()} == after_first


def test_a_returning_client_is_not_recorded_as_new_when_the_form_omits_it(client):
    """Whether this is a new client is a RECORDED FACT. Defaulting an absent
    field to "new" invented the answer the whole interview branches on."""
    from satc.app.intake_views import NEW_CLIENT_GATE
    from satc.app.state import STATE

    cid = "SATC-001000"
    if not STATE.is_returning(cid):
        return                      # nothing to assert on this fixture
    before = {j.job_id for j in STATE.store.load_jobs()}
    _post_engagement(client, year=2034)   # no "mode" field at all
    STATE.reload()
    made = [j for j in STATE.store.load_jobs() if j.job_id not in before]
    for job in made:
        assert (job.intake_answers or {}).get(NEW_CLIENT_GATE) != "yes"
