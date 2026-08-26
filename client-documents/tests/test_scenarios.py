"""Whole clients, end to end: the answers a preparer gives -> what the client holds.

The suites either side of this one test PARTS. `test_pricing` proves a line is
the right number, `test_merge` proves a template fills, `test_registry` proves
the names agree. All of them can be green while the thing a client actually
receives is wrong, because the failures this repository keeps producing are not
wrong numbers. They are:

  * software saying something is fine when it isn't -- `doctor` reporting a
    document "Ready now" while `render` refused it; a sample estimate quoting
    prices the firm has never charged; a test that went on passing after the
    field it poked was retired;
  * two documents in one package contradicting each other -- an onboarding
    letter promising an enclosure the pack does not contain;
  * a document stating something that cannot be true -- an estimate listing
    both "The standard deduction" and "Itemized deductions";
  * a question, a gate or a price that can never fire.

So every test in this file drives the real registries -- `registry/*.yaml`, the
firm's own prices -- from a full set of interview answers, and asserts on the
RENDERED documents. Nothing here asserts on an intermediate dict where a unit
test would do the job better.

Every client below is invented. The firm's real prospect workbook is never read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import consistency  # noqa: E402
import engagements  # noqa: E402
import intake  # noqa: E402
import interview as iv  # noqa: E402
import invoicing  # noqa: E402
import leads  # noqa: E402
import merge  # noqa: E402
import packaging  # noqa: E402
import schedules as sched  # noqa: E402
import settings as firm  # noqa: E402

# The day every scenario is "run", so a letter date never moves under the
# suite. Deliberately inside the 2026 filing season.
TODAY = date(2027, 2, 3)


# ── the clients ───────────────────────────────────────────────────────────
#
# Two skeletons, both fictional, both COMPLETE: every required question is
# answered, so a scenario that leaves one out is leaving it out on purpose.

def sitting(**over) -> dict:
    """A finished consultation for an individual. Override what matters."""
    answers = {
        "federal_form": "1040", "return_basis": "original", "tax_year": "2026",
        "client_full_name": "Ms. Wren Alcott",
        "client_address1": "12 Larch Way", "client_city": "Solon",
        "client_state": "OH", "client_zip": "44139",
        "client_email": "wren.alcott@example.com",
        "joint_return": "no", "taxpayer_name": "Wren Alcott",
        "return_features": [],
        "states": ["Ohio — resident"], "localities": ["None"],
        "additional_forms": ["None"],
        "other_income_documents": "no", "has_dependents": "no",
        "count_states": 1, "count_localities": 0,
        "first_deliverable_target": "April 1, 2027",
        "prior_firm": "no", "prior_return_available": "no",
        "decision": "yes",
    }
    answers.update(over)
    return sched.apply(answers)


def entity_sitting(**over) -> dict:
    """A finished consultation for an entity."""
    answers = {
        "federal_form": "1120S", "return_basis": "original", "tax_year": "2026",
        "client_full_name": "Marlow Fabrication LLC",
        "client_address1": "9 Foundry Row", "client_city": "Solon",
        "client_state": "OH", "client_zip": "44139",
        "client_email": "office@marlowfab.example",
        "entity_structure": "llc", "entity_state": "Ohio",
        "signer_name": "Priya Marlow", "signer_title": "member",
        "k1_target": "March 15, 2027", "count_owners": 2,
        "owner_returns": "no",
        "states": ["Ohio — resident"], "localities": ["None"],
        "additional_forms": ["None"],
        "count_states": 1, "count_localities": 0,
        "first_deliverable_target": "March 15, 2027",
        "prior_firm": "no", "prior_return_available": "no",
        "decision": "yes",
    }
    answers.update(over)
    return sched.apply(answers)


PREDECESSOR = {"prior_firm": "yes", "prior_firm_name": "Halloran & Reeve CPAs",
               "prior_return_available": "yes"}


# ── running one ───────────────────────────────────────────────────────────

def engage(answers: dict, store: Path):
    """The interview's own front door. Returns the outcome; asserts nothing."""
    return intake.finish(answers, store=store, today=TODAY)


def created(answers: dict, store: Path):
    out = engage(answers, store)
    assert out.created, f"the engagement was not created: {out.reason}"
    return out


def record_for(ref: str, store: Path) -> dict:
    return cli.build_record(engagements.load(ref, store))


def write_pack(ref: str, store: Path, out: Path, **kw) -> int:
    args = argparse.Namespace(engagement=ref, store=str(store), out=str(out),
                              with_invoice=False, no_pdf=True)
    for k, v in kw.items():
        setattr(args, k, v)
    return cli.cmd_package(args)


def render_all(record: dict, docs) -> dict[str, str]:
    """{document -> its HTML}, refusing exactly as `render` would."""
    out = {}
    for doc in docs:
        template = (cli.TEMPLATE_DIR / cli.DOCUMENTS[doc][0]).read_text(encoding="utf-8")
        out[doc] = merge.render(template, record,
                                required_lists=cli._required_lists().get(doc, ())).html
    return out


def readable(html: str) -> str:
    """What a person reads off the page, whitespace collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


HOLES = ("&lt;&lt;", "<<", "[[", "[CONFIRM:")


def assert_no_holes(name: str, html: str) -> None:
    for hole in HOLES:
        assert hole not in html, f"{name}: {hole!r} survived into a client document"


# ══ 1 · every federal form, all the way to the folder ═════════════════════

@pytest.mark.parametrize("form,letter", [
    ("1040", "Engagement Letter"),
    ("1120S", "Business Engagement Letter"),
    ("1065", "Business Engagement Letter"),
])
def test_every_federal_form_reaches_a_folder_the_client_can_be_sent(
        form, letter, tmp_path):
    """One client, one command, four returns -- and the RIGHT letter each time.

    FOUND HERE, 26 August 2026. `cli.opening_package()` was the literal list
    `["tax-letter", "fee-estimate", "onboarding-letter"]` while
    `packaging.PACKS` keyed the letter on `_return_type`. So `render
    --engagement` on an S corporation reached for the INDIVIDUAL engagement
    letter -- which refused on `<<TaxpayerName>>`, a field the entity
    interview never asks -- and the business letter its own signing pack would
    have sent was never rendered at all. Nothing caught it because every
    end-to-end test in the suite drove a 1040.

    The two lists are one list now. This drives each form through the front
    door a person actually uses and reads the folder afterwards.
    """
    answers = sitting() if form == "1040" else entity_sitting(federal_form=form)
    store, out = tmp_path / "store", tmp_path / "pack"
    ref = created(answers, store).ref

    assert write_pack(ref, store, out) == 0, "the pack refused"

    names = [p.name for p in out.iterdir() if p.suffix == ".html"]
    assert any(letter in n for n in names), \
        f"a {form} engagement was sent {names}, which does not include {letter!r}"
    if form != "1040":
        assert not any(n.startswith("SAT-C Engagement Letter -") for n in names), \
            "an entity was sent the individual engagement letter"

    for path in out.glob("*.html"):
        assert_no_holes(path.name, path.read_text(encoding="utf-8"))

    book = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    on_disk = sorted(n for n in names)
    listed = sorted(f for d in book["Documents"] for f in d["files"])
    assert on_disk == listed, "the manifest and the folder disagree"


def test_a_c_corporation_pack_arrives_whole_or_not_at_all(tmp_path):
    """A GAP FOUND HERE, and the invariant that survives whichever way it goes.

    A C corporation answering the interview cannot produce its own engagement
    letter. `k1_target` is asked only of a 1120-S or a 1065 -- correctly, a C
    corporation issues no K-1s -- and the business engagement letter merges
    `<<ScheduleK1Target>>` unconditionally, in a section 02 headed "Schedules
    K-1, and your personal return" that does not describe a C corporation at
    all. So the pack refuses, every time, on a field the interview is right
    not to ask for.

    That is the firm's decision to make: section 02 needs a conditional, and
    the templates and their FIELDS specs are the authoring contract's
    territory, not this suite's. It is reported rather than papered over.

    WHAT THIS TEST HOLDS is the part that must be true either way, and it is
    the reason the pack exists: it arrives whole or it does not arrive. A
    half-written folder is worse than none, because the client signs what
    turned up. Note the shape of the near miss --
    `test_packaging.test_every_entity_type_produces_a_pack[1120]` is green,
    because its fixture hands the 1120 a `k1_target` the interview would never
    have collected. A fixture that answers a question the software does not
    ask is a test passing for the wrong reason.
    """
    store, out = tmp_path / "store", tmp_path / "pack"
    answers = entity_sitting(federal_form="1120", entity_structure="corporation")
    answers.pop("k1_target", None)              # the interview would not ask
    ref = created(sched.apply(answers), store).ref

    rc = write_pack(ref, store, out)
    if rc == 0:
        names = [p.name for p in out.glob("*.html")]
        assert any("Business Engagement" in n for n in names)
        for path in out.glob("*.html"):
            assert_no_holes(path.name, path.read_text(encoding="utf-8"))
    else:
        assert not out.exists() or not list(out.iterdir()), (
            "a refused pack left documents on disk, which is the one failure "
            "the atomic write exists to prevent")


def test_both_front_doors_send_the_same_documents(tmp_path):
    """`render` and `package` must not have their own idea of the package.

    They did, and each was right about the half the other got wrong: `render`
    knew about the records release and sent the individual letter to
    corporations; `package` knew about the business letter and never sent the
    release. A control that lives in one front door is a control the other
    silently skips -- the rule `intake.py` was written for, applied to which
    documents come out rather than to which gates run.
    """
    store = tmp_path / "store"
    for label, answers in [
        ("individual", sitting()),
        ("individual with a predecessor", sitting(**PREDECESSOR)),
        ("s corporation", entity_sitting()),
        ("s corporation with a predecessor", entity_sitting(**PREDECESSOR)),
    ]:
        record = record_for(created(answers, store).ref, store)
        assert cli.opening_package(record) == packaging.documents_for(record), \
            f"{label}: the two front doors disagree about the package"


def test_a_client_with_no_predecessor_is_not_told_a_document_is_blocking_them(
        tmp_path, capsys):
    """`doctor --engagement` on a healthy engagement, reading clean.

    It did not. The records release goes only to a client who had a previous
    accountant -- `opening_package` has always known that -- and this report
    listed it under "Blocked, and due now" for everybody, then exited 1. A
    readiness tool that overstates what is broken teaches whoever reads it to
    stop believing the parts that are true; that is the firm's own argument
    for putting `hard_no` in `settings.POLICY_ONLY`, and it applies here.
    """
    store = tmp_path / "store"
    ref = created(sitting(), store).ref
    cli._engagement_readiness(ref, store)
    out = capsys.readouterr().out
    due = out.split("Not due yet")[0]
    assert "records-release" not in due, (
        "a client with nobody to ask was told the authorization they will "
        "never be sent is blocking them:\n" + out)


def test_the_demo_command_runs_the_whole_chain(tmp_path):
    """`make demo` is the first thing anybody runs, and it was dead.

    `cmd_demo` passed the record's PATH to `opening_package()`, which asks the
    record for `.get(flag)` -- so the command died with `AttributeError: 'str'
    object has no attribute 'get'` the moment the records release became
    conditional. Nothing tested it, so the one command a newcomer runs first
    had been broken since that landed.
    """
    rc = cli.main(["demo", "--out", str(tmp_path), "--no-pdf"])
    assert rc == 0, "the demo chain did not complete"
    written = sorted(p.name for p in tmp_path.glob("*.html"))
    assert written, "the demo wrote no documents"
    for path in tmp_path.glob("*.html"):
        assert_no_holes(path.name, path.read_text(encoding="utf-8"))


# ══ 2 · what the client is asked for, and what they are charged ═══════════

# Each row: what the client ticked, the document the onboarding letter must
# ask for, and the line the estimate must carry. Deliberately only things that
# sit OUTSIDE every package -- a K-1 or a first brokerage statement is inside
# Standard, so "no line" is the right answer for those and would make this a
# weaker test rather than a stronger one.
TICKED = [
    ("a rental", {"return_features": ["rentals"]},
     "Rental income and expenses", "Rental schedule"),
    ("a farm", {"return_features": ["farm"]},
     "Farm income and expenses", "Farm schedule"),
    ("a foreign account", {"extra_forms": ["foreign_accounts"]},
     "Your foreign account statements", "Foreign account reporting"),
    ("a home sale", {"extra_forms": ["home_sale"]},
     "The closing statement from the sale of your home", "Sale of a home"),
    ("marketplace health insurance", {"extra_forms": ["marketplace"]},
     "Form 1095-A", "Marketplace health insurance"),
]


@pytest.mark.parametrize("label,ticked,document,line",
                         TICKED, ids=[t[0] for t in TICKED])
def test_anything_ticked_is_both_asked_for_and_charged_for(
        label, ticked, document, line, tmp_path):
    """WITH THE COUNT LEFT BLANK, which is the whole point.

    THE BUG THIS FOUND. A client ticked "Held a foreign bank or investment
    account" and left the number for later. The onboarding letter duly asked
    them for "the bank, the account number, and the highest balance at any
    point in the year" -- and the estimate charged nothing at all, because
    `per_unit.foreign_account` priced per account and read the blank count as
    zero. The firm asked for the records and billed nobody for the work.

    It is the same trap `per_unit.rental.form_when` was invented for a day
    earlier, one line further down the sheet: "A client ticks 'Schedule E
    page 1 -- rentals' and leaves the number blank; the count reads zero, the
    line never fires, and the Schedule E is prepared for nothing."

    Asking and billing are two halves of one decision, so they are tested as
    one. A row here that asks and does not bill is work given away; one that
    bills and does not ask is a client who cannot send us what we are
    charging them for.
    """
    store = tmp_path / "store"
    record = record_for(created(sitting(**ticked), store).ref, store)

    asked = [r["Document"] for r in record["RequestList"]]
    assert any(document in a for a in asked), \
        f"{label}: the onboarding letter never asks for {document!r}. Asked: {asked}"

    services = [i["Service"] for i in record["LineItems"]]
    assert line in services, \
        f"{label}: the estimate has no {line!r} line. Billed: {services}"

    # And the client can read both, on the page, in the same package.
    pages = render_all(record, ["onboarding-letter", "fee-estimate"])
    assert document.split(",")[0] in readable(pages["onboarding-letter"])
    assert line in readable(pages["fee-estimate"])


def test_the_request_list_grows_and_shrinks_with_the_answers(tmp_path):
    """The list a client reads is derived, not typed.

    It was typed once, and "it asked for five things where the answers call
    for nine -- no signed engagement letter, no ID, and nothing about the
    Schedule C business the estimate was pricing a package around"
    (`cli.cmd_sample`). The failure mode is not one wrong bullet; it is a list
    that stops tracking the sitting at all. So: two clients, one plain and one
    with everything, and the difference has to be the answers.
    """
    store = tmp_path / "store"
    plain = record_for(created(sitting(), store).ref, store)
    loaded = record_for(created(sitting(
        return_features=["itemizing", "self_employment", "rentals", "k1",
                         "investments"],
        schedule_c_kind="simple", count_businesses=1,
        other_income_documents="yes",
        extra_forms=["home_sale"], **PREDECESSOR), store).ref, store)

    plain_docs = [r["Document"] for r in plain["RequestList"]]
    loaded_docs = [r["Document"] for r in loaded["RequestList"]]

    # Everybody is asked for the same ungated ones, and they come first --
    # registry order, not answer order, so the engagement letter and the ID
    # sit at the top rather than wherever a gate happened to fire.
    assert loaded_docs[:len(plain_docs)] == plain_docs
    assert len(loaded_docs) > len(plain_docs) + 4, (
        "a client with five schedules, a home sale and a predecessor was "
        f"asked for {len(loaded_docs)} things against a plain client's "
        f"{len(plain_docs)}")
    assert len(set(loaded_docs)) == len(loaded_docs), "a document is asked for twice"

    # The mileage log is the case worth pinning: it is asked of a gig
    # Schedule C and NOT of a full one, off `schedule_c_kind` alone.
    full = record_for(created(sitting(
        return_features=["self_employment"], schedule_c_kind="standard",
        count_businesses=1, other_income_documents="yes"), store).ref, store)
    assert any("mileage log" in d for d in loaded_docs)
    assert not any("mileage log" in r["Document"] for r in full["RequestList"])


# ══ 3 · the interview's derivations ═══════════════════════════════════════

def test_a_derived_schedule_names_the_fact_behind_it(tmp_path):
    """The preparer sees WHY, or the derivation is an oracle.

    `schedules.derive` returns a proposal and the reason for each line, and
    both front doors show them before an engagement is created. A schedule
    with no reason is exactly the "software decided, trust it" the firm ruled
    out: "the interview needs to ask questions that then mean we definitely
    need a schedule".
    """
    answers = sitting(return_features=["self_employment", "rentals", "k1"])
    derived = sched.derive(answers)

    assert set(derived.schedules) == {"C", "SE", "E1", "E2"}
    reasons = dict(derived.because)
    for schedule in derived.schedules:
        assert reasons.get(schedule, "").strip(), \
            f"Schedule {schedule} was derived with no fact behind it"
    assert "rent" in reasons["E1"].lower()
    # Two answers, one schedule, named once -- "Schedules C, SE" not "C, SE, C".
    assert reasons["C"] and reasons["SE"]


def test_changing_one_answer_moves_the_scope_the_package_and_the_price(tmp_path):
    """The derivation is load-bearing in three places at once.

    A schedule that fell out of `federal_schedules` without moving the scope
    sentence, the package gate and the price would be a derivation that only
    LOOKS wired. This drives the difference a single tick makes, end to end,
    and reads it off the rendered letter and the rendered estimate.
    """
    store = tmp_path / "store"
    bare = record_for(created(sitting(other_income_documents="yes"), store).ref, store)
    itemising = record_for(created(sitting(
        return_features=["itemizing"], other_income_documents="yes"), store).ref, store)

    assert bare["FederalReturns"] == "Form 1040"
    assert itemising["FederalReturns"] == "Form 1040 with Schedule A"

    assert [i["Service"] for i in bare["LineItems"]] == ["Essentials"]
    assert [i["Service"] for i in itemising["LineItems"]] == ["Standard"]

    for record, expected in ((bare, "Form 1040"),
                             (itemising, "Form 1040 with Schedule A")):
        letter = readable(render_all(record, ["tax-letter"])["tax-letter"])
        assert f"Federal: {expected}" in letter


def test_two_answers_that_mean_one_schedule_name_it_once(tmp_path):
    """"Form 1040 with Schedules E and E" is how a letter reads as a mistake.

    Rentals and a received K-1 are Schedule E page 1 and page 2. The client
    ticked two facts; the return has one Schedule E.
    """
    store = tmp_path / "store"
    record = record_for(created(sitting(
        return_features=["rentals", "k1"], other_income_documents="yes"),
        store).ref, store)
    assert record["FederalReturns"] == "Form 1040 with Schedule E"


# ══ 4 · the money, as the client reads it ═════════════════════════════════

def test_a_capped_line_tells_the_client_what_happens_past_the_cap(tmp_path):
    """Four accounts, then five: the boundary, and one past it.

    A soft cap that prints only "capped at 4" is a promise the firm is not
    making -- the firm's own words, 26 August 2026: "4 is a soft cap. Then we
    add dollars for time." The client finds out otherwise on the invoice.
    Read off the rendered estimate, because the sentence is the deliverable.
    """
    store = tmp_path / "store"
    at_cap = record_for(created(sitting(
        extra_forms=["foreign_accounts"], count_foreign_accounts=4,
        other_income_documents="yes"), store).ref, store)
    past = record_for(created(sitting(
        extra_forms=["foreign_accounts"], count_foreign_accounts=5,
        other_income_documents="yes"), store).ref, store)

    assert at_cap["EstimateTotal"] == past["EstimateTotal"], (
        "the fifth account is charged past a cap the firm set at four")

    page = readable(render_all(past, ["fee-estimate"])["fee-estimate"])
    assert "capped at 4" in page
    assert "billed at $150 an hour" in page, (
        "a soft cap that does not say the time is billed reads as a hard one")

    inside = readable(render_all(at_cap, ["fee-estimate"])["fee-estimate"])
    assert "capped at 4" not in inside, (
        "a client whose count is inside the cap was told about a cap that "
        "never applied to them")


def test_a_form_fee_says_what_it_covers_and_what_is_extra(tmp_path):
    """Three rentals, then four. One form, then rows past it.

    The Schedule E is priced as a FORM covering up to three properties, at the
    firm's own instruction. A client with four sees the form fee and the
    fourth property separately, or the covers list above the line reads as a
    lie.
    """
    store = tmp_path / "store"
    three = record_for(created(sitting(
        return_features=["rentals"], count_rentals=3,
        other_income_documents="yes"), store).ref, store)
    four = record_for(created(sitting(
        return_features=["rentals"], count_rentals=4,
        other_income_documents="yes"), store).ref, store)

    page3 = readable(render_all(three, ["fee-estimate"])["fee-estimate"])
    page4 = readable(render_all(four, ["fee-estimate"])["fee-estimate"])
    assert "covering up to 3" in page3
    assert "plus 1 ×" not in page3, "a third property was charged as an extra"
    assert "covering up to 3" in page4 and "plus 1 × $45.00" in page4, \
        "the fourth property is not shown as an extra at the marginal rate"

    only = [i for i in four["LineItems"] if i["Service"] == "Rental schedule"]
    assert len(only) == 1, "one Schedule E is one line, however many properties"


def test_a_zero_of_something_produces_no_line_and_no_sentence(tmp_path):
    """The empty case. Nothing ticked, nothing counted.

    An estimate that lists a $0.00 rental line, or an assumptions block that
    warns a W-2 filer about foreign companies, is a document stating something
    that cannot be true. `assumed.officer_compensation` was doing exactly that
    on individual estimates until 26 August 2026 -- "caught by reading a
    rendered one rather than by any test", which is what this is.
    """
    store = tmp_path / "store"
    record = record_for(created(sitting(), store).ref, store)
    page = readable(render_all(record, ["fee-estimate"])["fee-estimate"])

    assert [i["Service"] for i in record["LineItems"]] == ["Simple Filer"]
    for absent in ("Rental schedule", "Farm schedule", "Schedule K-1",
                   "Brokerage statement", "Foreign account reporting",
                   "Records sorting", "Officer compensation", "$0.00"):
        assert absent not in page, \
            f"a W-2-only client's estimate mentions {absent!r}"


def test_an_amendment_of_our_own_return_is_the_whole_estimate(tmp_path):
    """The case that REPLACES the estimate rather than adding to it.

    "if we legit made a mistake i wouldn't even charge to fix it for $50" --
    and billing the package again would bill twice for one piece of work. The
    client's estimate has to show that, on the page, with a total.
    """
    store = tmp_path / "store"
    ours = record_for(created(sitting(
        return_basis="amended", amendment_reason="our_error",
        return_features=["itemizing"], other_income_documents="yes"),
        store).ref, store)
    theirs = record_for(created(sitting(
        return_basis="amended", amendment_reason="other_preparer",
        return_features=["itemizing"], other_income_documents="yes"),
        store).ref, store)

    assert [i["Service"] for i in ours["LineItems"]] == ["Amendment"]
    assert ours["EstimateTotal"] == "$0.00"
    assert [i["Service"] for i in theirs["LineItems"]] == ["Standard", "Amendment"]

    page = readable(render_all(ours, ["fee-estimate"])["fee-estimate"])
    assert "Total estimate $0.00" in page
    assert "Standard" not in page, "an amendment we caused re-charged the return"


# ══ 5 · the deadline the documents print ══════════════════════════════════

# The statutory dates for the 2026 tax year, from firm-settings.yaml's own
# note: "Individual and calendar-year C corporation returns are due 15 April
# 2027; partnerships and S corporations are due 15 March 2027. Neither falls
# on a weekend or a holiday in 2027." Not invented here -- quoted.
FILING_DUE = {"individual": date(2027, 4, 15), "c_corp": date(2027, 4, 15),
              "partnership": date(2027, 3, 15), "s_corp": date(2027, 3, 15)}


@pytest.mark.parametrize("return_type", sorted(FILING_DUE))
def test_the_deadline_on_the_letter_obeys_the_firms_own_three_week_rule(return_type):
    """The firm set a RULE, not four dates, so next season is arithmetic.

    "SET 26 August 2026: THREE WEEKS BEFORE EACH FILING DEADLINE ... The rule,
    not four unrelated dates -- so next season is arithmetic rather than
    another decision." Nothing checked that the dates in the file are what the
    rule produces, and rolling the season forward is exactly when a
    weekend-shifted filing deadline moves one of them and nobody notices. The
    two samples got this wrong once already -- March 15 and February 15
    against the rule's March 25 and February 22.
    """
    printed = firm.firm_fields("2026", return_type)["MaterialsDeadline"]
    got = datetime.strptime(printed, "%B %d, %Y").date()
    assert got == FILING_DUE[return_type] - timedelta(days=21), (
        f"{return_type}: the documents print {printed}, which is not three "
        f"weeks before the {FILING_DUE[return_type]} filing deadline the "
        f"settings file names")


# ══ 6 · the lead, and the claim it makes ══════════════════════════════════

def test_a_sitting_driven_from_a_website_lead_reaches_the_letter(tmp_path):
    """Lead -> prefill -> accepted -> the address block on the page.

    The prefill mechanism is the one place where something the CLIENT typed
    can land in a document with one keystroke, and it has produced two real
    bugs: "Solon, OH, Solon, OH 44139" on a letter when city and state both
    offered the whole location string, and five dead `prefill_map` keys that
    meant a prospect ticking "Rental property" prefilled nothing.

    So this accepts every claim the interview says is answerable -- the way a
    preparer pressing enter would -- and reads the result off the rendered
    letter rather than off the answers dict.
    """
    lead = json.loads((ROOT / "samples" / "website-lead.json").read_text(encoding="utf-8"))
    session = iv.Interview(lead=lead)

    typed = dict(sitting())
    accepted, refused_claims = {}, {}
    while (nxt := session.next_question()) is not None:
        _, q = nxt
        claim = iv.prefill_for(q, lead)
        if claim is not None and iv.prefill_is_answerable(q, claim):
            session.answer(q["id"], claim)
            accepted[q["id"]] = claim
            continue
        if claim is not None:
            refused_claims[q["id"]] = claim
        value = typed.get(q["id"])
        if value in (None, "", []) and q.get("required"):
            value = "Ohio — resident" if q["type"] == "list" else "not stated"
        session.answer(q["id"], value if value is not None else "")

    assert accepted.get("client_city") == "Solon"
    assert accepted.get("client_state") == "OH"
    assert set(accepted.get("return_features", [])) == {"k1", "rentals"}, (
        "the website's own complexity vocabulary did not reach the interview")
    # Both services this prospect asked for mean the same return, so the claim
    # collapses to one answer and is offerable. The ambiguous case is below.
    assert accepted.get("federal_form") == "1040"
    assert iv.prefill_for(session.question("federal_form"),
                          {"services": ["individual_tax", "business_tax"]}) is None, (
        "a prospect who asked for an individual AND a business return was "
        "offered the individual one as though that were the whole job")
    assert refused_claims.get("prior_return_available") == "unsure", (
        "'unsure' is not one of yes/partial/no, so it must be shown and NOT "
        "be one keystroke from an answer")

    session.answers["decision"] = "yes"
    session.answers.setdefault("count_rentals", 1)
    session.answers.setdefault("count_k1s", 1)
    store = tmp_path / "store"
    ref = created(session.answers, store).ref
    letter = readable(render_all(record_for(ref, store), ["tax-letter"])["tax-letter"])
    assert "12 Larch Way Solon, OH 44139" in letter, (
        "the address block did not come out as street, city, state and ZIP")
    assert "Solon, OH, Solon" not in letter, (
        "the location string was accepted whole into two address lines")


def test_a_lead_that_is_only_a_phone_number_still_opens_an_engagement(tmp_path):
    """"they may just give us contact info" -- the firm, 26 August 2026.

    A hand-typed lead is a REAL lead, not a lesser one: it carries the same
    keys with the website's answers simply absent. Absent is not "none", and
    the interview asks everything either way. The failure this guards is the
    opposite one -- a manual lead that quietly prefills a claim nobody made.
    """
    lead = leads.by_hand(name="Tobias Renn", phone="216-555-0182",
                         notes="Called about last year's return.")
    for _, q in iv.all_questions(iv.load_schema()):
        claim = iv.prefill_for(q, lead)
        assert not claim, (
            f"{q['id']} was offered the claim {claim!r} from a lead that only "
            f"gave us a name and a phone number")
        assert not iv.prefill_is_answerable(q, claim), (
            f"{q['id']} could be answered with a keystroke from a lead that "
            f"said nothing about it")

    store = tmp_path / "store"
    ref = created(sitting(client_full_name="Mr. Tobias Renn",
                          client_email="tobias.renn@example.com"), store).ref
    assert write_pack(ref, store, tmp_path / "pack") == 0


# ══ 7 · work the firm does not take ═══════════════════════════════════════

def test_refusing_work_leaves_nothing_behind_anywhere(tmp_path):
    """A refusal that left a file on disk would be worse than none.

    Three ways not to take work, and none of them may produce an engagement,
    a document or a folder: a HARD NO, a decision that is not yes, and an
    override that IS taken but has to say so.
    """
    store, out = tmp_path / "store", tmp_path / "pack"

    refused = engage(sitting(red_flags=["assurance_needed"]), store)
    assert refused.status == "refused" and refused.ref is None
    assert refused.blockers == ["Needs assurance work"]

    declined = engage(sitting(decision="thinking"), store)
    assert declined.status == "declined" and declined.ref is None
    assert declined.exit_code == 0, "deciding not to take work is not a failure"

    assert not store.exists() or not list(store.iterdir()), \
        "work the firm refused left an engagement in the store"
    assert not out.exists()

    override = intake.finish(sitting(red_flags=["assurance_needed"]),
                             store=store, today=TODAY, override_hard_no=True)
    assert override.created and override.overridden and override.blockers


def test_a_preparer_flag_is_raised_and_never_printed(tmp_path):
    """A flag is for a human, and it is not a price and not a blocker.

    Four rentals and one local return is the firm's own example: it "may
    genuinely owe one local return -- Ohio townships have no income tax" -- so
    the software asks a person rather than billing for returns nobody has to
    file. What it must never do is put that reasoning in front of the client.
    """
    store = tmp_path / "store"
    flagged = sitting(return_features=["rentals"], count_rentals=4,
                      count_localities=1, localities=["Solon municipal"],
                      other_income_documents="yes")
    out = created(flagged, store)
    assert out.flags and "rental" in out.flags[0]

    quiet = created(sitting(return_features=["rentals"], count_rentals=1,
                            count_localities=1, localities=["Solon municipal"],
                            other_income_documents="yes"), store)
    assert not quiet.flags

    record = record_for(out.ref, store)
    for name, html in render_all(record, cli.opening_package(record)).items():
        page = readable(html)
        for phrase in ("townships", "do not assume either way", "Check whether"):
            assert phrase not in page, f"{name} prints a preparer's flag"


# ══ 8 · the bill ══════════════════════════════════════════════════════════

def test_the_next_command_the_invoice_prints_actually_works(tmp_path, capsys):
    """A tool that hands you the next command has to hand you one that works.

    `cli.py invoice` ended with "Next: python cli.py render --engagement REF
    --docs invoice --out out", and that command refused every time on
    `<<AmountDue>>, <<InvoiceDate>>, <<InvoiceNumber>>, <<Subtotal>>`. One
    engagement has many invoices, so each is written beside the record rather
    than into it -- and the render only ever read the record. The instruction
    had presumably never been followed.
    """
    store, out = tmp_path / "store", tmp_path / "out"
    ref = created(sitting(other_income_documents="yes"), store).ref

    assert cli.main(["invoice", "--engagement", ref, "--store", str(store),
                     "--billed", "March 2027"]) == 0
    printed = capsys.readouterr().out
    assert "render --engagement" in printed

    assert cli.main(["render", "--engagement", ref, "--store", str(store),
                     "--docs", "invoice", "--out", str(out), "--no-pdf"]) == 0
    page = next(out.glob("*.html"))
    assert_no_holes(page.name, page.read_text(encoding="utf-8"))

    text = readable(page.read_text(encoding="utf-8"))
    assert "$200.00" in text
    # The one value the estimate and the invoice must NOT share.
    assert "March 2027" in text and "2026 tax year" not in text


def test_an_engagement_with_no_invoice_says_so_rather_than_refusing_blankly(tmp_path):
    """The other half: rendering an invoice nobody raised.

    "no invoice yet, raise one" is an answer. Four unresolved field names is a
    puzzle.
    """
    store, out = tmp_path / "store", tmp_path / "out"
    ref = created(sitting(), store).ref
    assert invoicing.find(store, ref) is None
    assert cli.main(["render", "--engagement", ref, "--store", str(store),
                     "--docs", "invoice", "--out", str(out), "--no-pdf"]) == 1
    assert not out.exists() or not list(out.glob("*.html"))
