"""Does the package a client actually receives agree with itself?

The firm's ask, 26 August 2026: *"i want you to come back and also show me how
you can tell it all goes together (so i can see consistency)."*

`test_consistency` breaks each of `consistency.py`'s joins on purpose, which
proves the checks can fail. It does all of it against ONE record -- the demo
package -- and that record turned out to be the single client shape that trips
none of them. So the checks were green on the sample and crying wolf on nearly
every real engagement, which is the same class of failure as a check that never
fires: whoever runs it stops reading it.

This file drives REAL client shapes through the real registries and asks the
firm's question of each one. It also covers the joins `consistency.py` does not
make, which is where the remaining bugs live: two documents in one package that
each look right alone.

Every client is invented.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import consistency  # noqa: E402
import merge  # noqa: E402
import settings as firm  # noqa: E402

from tests.test_scenarios import (  # noqa: E402
    PREDECESSOR, created, entity_sitting, readable, record_for, render_all,
    sitting, write_pack,
)


# The client shapes an ordinary week produces. Each is one whole return, and
# between them they cover all four packages, both engagement letters, the
# form-priced schedules, the counted lines and the per-form ones.
CLIENTS = {
    "a W-2 filer on the simplest rung": sitting(),
    "wages, interest and dividends": sitting(other_income_documents="yes"),
    "a couple who itemise": sitting(
        client_full_name="Mr. and Mrs. Ivo Bramley", joint_return="yes",
        taxpayer_name="Ivo Bramley", spouse_name="Nell Bramley",
        return_features=["itemizing"], other_income_documents="yes"),
    "a landlord with three properties": sitting(
        return_features=["rentals"], count_rentals=3, count_localities=1,
        localities=["Solon municipal"], other_income_documents="yes"),
    "self-employed, with a K-1 and a brokerage": sitting(
        return_features=["self_employment", "k1", "investments"],
        schedule_c_kind="standard", count_businesses=1, count_k1s=3,
        count_brokerages=2, other_income_documents="yes"),
    "three states and two localities": sitting(
        return_features=["itemizing"], other_income_documents="yes",
        states=["Ohio — resident", "Michigan — non-resident",
                "Indiana — non-resident"],
        localities=["Solon municipal", "RITA"],
        count_states=3, count_localities=2),
    "a client who came from another firm": sitting(
        return_features=["itemizing"], other_income_documents="yes",
        **PREDECESSOR),
    "an S corporation with two shareholders": entity_sitting(),
    "a partnership": entity_sitting(federal_form="1065",
                                    entity_structure="lp"),
}


def report_for(record: dict) -> dict:
    """Every check `cli.py check` would print, by name."""
    rendered = consistency.render_package(record, cli.DOCUMENTS,
                                          cli.TEMPLATE_DIR, cli._required_lists())
    return {c.name: c for c in consistency.report(record, rendered)}


# ══ 1 · the firm's own question, asked of every client shape ══════════════

@pytest.mark.parametrize("label", sorted(CLIENTS))
def test_an_ordinary_clients_package_agrees_with_itself(label, tmp_path):
    """Nine real returns through `cli.py check`. All of them, not one.

    THE BUG THIS FOUND, 26 August 2026. "nothing is billed outside the scope"
    scanned the whole rendered estimate for schedule names -- including each
    package's `Includes:` list, which is what the package WOULD cover rather
    than what is being charged. Standard's list says "One gig Schedule C on
    standard mileage", so a couple who only itemise were reported as having a
    Schedule C billed outside their scope. So were the landlord, the client
    with a K-1, the brokerage client: every ordinary Standard engagement.
    `cli.py check` exited 1 on all of them.

    The suite was green throughout, because the one record it checked -- the
    demo package -- is a Self-Employed client whose scope happens to name a
    Schedule C. A check exercised against a single fixture is a check tested
    on the case it cannot fail.

    A green run here is also the evidence for the firm's original question.
    """
    store = tmp_path / "store"
    record = record_for(created(CLIENTS[label], store).ref, store)
    checks = report_for(record)

    assert len(checks) >= 5, f"{label}: only {len(checks)} joins were compared"
    broken = {n: c.detail for n, c in checks.items() if not c.ok}
    assert not broken, f"{label}: the package disagrees with itself: {broken}"
    for name, check in checks.items():
        assert check.detail.strip(), f"{label}: {name} states no detail"


def test_the_scope_check_reads_the_bill_not_the_brochure(tmp_path):
    """Both halves of the fix, in one test, so neither can be lost.

    A package's covers list is a promise about what is INCLUDED. Reading it as
    a charge is what produced the false alarm above. Reading the line items is
    what catches the real bug -- the one that started this check: "The
    engagement letter's scope said 'Schedules A, C, and SE' while the estimate
    billed a $145 Rental schedule. Schedule E was on the bill and outside the
    scope the client had signed."
    """
    store = tmp_path / "store"
    itemising = record_for(created(sitting(
        return_features=["itemizing"], other_income_documents="yes"),
        store).ref, store)

    # The brochure half: the estimate really does say "Schedule C" to this
    # client, in the package's includes list, and that is not a charge.
    estimate = readable(render_all(itemising, ["fee-estimate"])["fee-estimate"])
    assert "Schedule C" in estimate
    assert itemising["FederalReturns"] == "Form 1040 with Schedule A"
    assert report_for(itemising)["nothing is billed outside the scope"].ok

    # The bill half: a landlord whose letter forgot the Schedule E.
    landlord = record_for(created(sitting(
        return_features=["rentals", "itemizing"], count_rentals=2,
        other_income_documents="yes"), store).ref, store)
    assert report_for(landlord)["nothing is billed outside the scope"].ok
    narrowed = dict(landlord, FederalReturns="Form 1040 with Schedule A")
    check = report_for(narrowed)["nothing is billed outside the scope"]
    assert not check.ok and "Schedule E" in check.detail

    # And the way out is the way the letter already provides: a preparer who
    # names the form under "Also included" has put it inside the scope.
    listed = dict(narrowed, AdditionalForms="Schedule E — rental properties")
    assert report_for(listed)["nothing is billed outside the scope"].ok


def test_the_check_never_compares_a_document_nobody_can_send(tmp_path):
    """`doctor` and `render` were made to agree. `check` was still on its own.

    `consistency.render_package` called `merge.render` WITHOUT the
    required-lists guard that `render` and `package` both apply, and an
    `[[EACH]]` over an empty list leaves no token behind to object to. So the
    organizer cover letter -- whose `Requested` list nothing builds yet --
    rendered here as a heading with nothing under it, joined the comparison,
    and was counted among the documents that agree. Three tools, one document,
    two answers.
    """
    store = tmp_path / "store"
    record = record_for(created(sitting(), store).ref, store)

    assert "Requested" not in record
    guarded = consistency.render_package(record, cli.DOCUMENTS,
                                         cli.TEMPLATE_DIR, cli._required_lists())
    assert "organizer-letter" not in guarded, (
        "a document `render` refuses was compared as though it could be sent")

    # And it is genuinely only the guard that keeps it out -- proof the test
    # is exercising the mechanism rather than a document that fails anyway.
    loose = consistency.render_package(record, cli.DOCUMENTS, cli.TEMPLATE_DIR)
    assert "organizer-letter" in loose

    for name in guarded:
        with_lists = cli._required_lists().get(name, ())
        merge.render((cli.TEMPLATE_DIR / cli.DOCUMENTS[name][0]).read_text(
            encoding="utf-8"), record, required_lists=with_lists)


# ══ 2 · what the pack promises, and what is in the folder ═════════════════

@pytest.mark.parametrize("who,answers", [
    ("an individual", sitting(**PREDECESSOR)),
    ("an S corporation", entity_sitting(**PREDECESSOR)),
])
def test_a_pack_never_promises_an_enclosure_it_does_not_contain(
        who, answers, tmp_path):
    """THE BUG, found by reading a written pack rather than a record.

    The onboarding letter's section 03 tells any client with a previous
    accountant: "We have included a short authorization for you to sign."
    `cli.opening_package` knew to include it -- the firm asked for exactly
    that, "let's just make an attachment that we send for them to sign by
    default along with the engagement letter" -- and `packaging.PACKS`, which
    is what `cli.py package` actually uses, did not. So the pack a client is
    sent said "included" over a folder of three documents.

    Two documents in one package contradicting each other, each correct on its
    own. The invariant is written so it holds whichever way the entity case is
    resolved: if the letter makes the promise, the folder keeps it -- and if
    the pack could not be completed, nothing was written at all.
    """
    store, out = tmp_path / "store", tmp_path / "pack"
    ref = created(answers, store).ref
    rc = write_pack(ref, store, out)

    if rc != 0:
        assert not out.exists() or not list(out.iterdir()), \
            f"{who}: a refused pack left documents on disk"
        return

    names = [p.name for p in out.glob("*.html")]
    onboarding = next(p for p in out.glob("*.html") if "Onboarding" in p.name)
    if "We have included a short authorization" in readable(
            onboarding.read_text(encoding="utf-8")):
        assert any("Records Release" in n for n in names), (
            f"{who}: the onboarding letter says an authorization is included "
            f"and the folder holds {names}")

    book = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    assert sorted(f for d in book["Documents"] for f in d["files"]) == sorted(names)


def test_every_document_in_a_written_pack_states_the_same_engagement(tmp_path):
    """Read off the FILES, which is what the client has in front of them.

    Every document renders from one record in one pass, which makes agreement
    likely and proves nothing -- both failures that actually happened were
    inside one record. The reference, the date and the materials deadline are
    the three values a client compares without meaning to, because they are
    printed at the top of each page.
    """
    store, out = tmp_path / "store", tmp_path / "pack"
    answers = sitting(return_features=["rentals"], count_rentals=2,
                      other_income_documents="yes", **PREDECESSOR)
    ref = created(answers, store).ref
    assert write_pack(ref, store, out) == 0
    record = record_for(ref, store)

    pages = {p.name: readable(p.read_text(encoding="utf-8"))
             for p in out.glob("*.html")}
    assert len(pages) == 4

    for name, page in pages.items():
        assert record["EngagementRef"] in page, f"{name} carries another reference"
        assert record["LetterDate"] in page, f"{name} carries another date"
        assert record["ClientFullName"] in page, f"{name} names another client"

    prints_deadline = {n: p for n, p in pages.items()
                       if "complete information by" in p or "send everything by" in p}
    assert len(prints_deadline) >= 2
    for name, page in prints_deadline.items():
        assert record["MaterialsDeadline"] in page, \
            f"{name} states a deadline that is not the firm's"

    estimate = next(p for n, p in pages.items() if "Fee Estimate" in n)
    assert record["EstimateTotal"] in estimate


# ══ 3 · joins nothing made ════════════════════════════════════════════════

def test_a_deliverable_is_never_promised_before_the_materials_are_due(tmp_path):
    """A JOIN NOTHING MADE, and it is one sentence on the entity letter.

    Two dates reach a client in one package from two different places: the
    materials deadline comes from `firm-settings.yaml`, the target comes from
    an answer somebody gives on the call. Nothing compared them. Promise the
    earlier one and the package contradicts itself on its face -- the
    onboarding letter says "Please send everything by the 25th" and then "Our
    target for your first deliverable is the 12th"; the business letter says
    it in a single breath: "Our target for delivering the K-1s is X, provided
    the entity's records reach us complete by Y."

    On an entity return that date is what every owner's personal return is
    planned around, so getting it backwards is not a tight promise. It is an
    impossible one.
    """
    store = tmp_path / "store"

    honest = record_for(created(sitting(
        first_deliverable_target="April 1, 2027"), store).ref, store)
    assert honest["MaterialsDeadline"] == "March 25, 2027"
    assert report_for(honest)[
        "the first deliverable is not promised before the materials are due"].ok

    backwards = record_for(created(sitting(
        first_deliverable_target="March 1, 2027"), store).ref, store)
    check = report_for(backwards)[
        "the first deliverable is not promised before the materials are due"]
    assert not check.ok
    assert "March 1, 2027" in check.detail and "March 25, 2027" in check.detail

    entity = record_for(created(entity_sitting(
        k1_target="February 1, 2027"), store).ref, store)
    assert entity["MaterialsDeadline"] == "February 22, 2027"
    assert not report_for(entity)[
        "the K-1s are not promised before the materials are due"].ok


def test_a_target_that_is_a_phrase_is_skipped_rather_than_failed(tmp_path):
    """The interview invites one: "'April 1, 2027', 'two weeks after the file
    is complete'". A phrase cannot be compared to a date, and a check that
    reported it as a disagreement would be the false alarm this file exists to
    stop -- it would push preparers into giving a date they do not mean."""
    store = tmp_path / "store"
    record = record_for(created(sitting(
        first_deliverable_target="two weeks after the file is complete"),
        store).ref, store)
    names = set(report_for(record))
    assert not any("first deliverable" in n for n in names), \
        "an uncomparable target was compared anyway"
    assert "one letter date" in names, "the other joins stopped running"


def test_an_unpriceable_package_is_reported_rather_than_crashed(tmp_path):
    """`cli.py check` died with a traceback on the records that most need it.

    An engagement whose estimate carries a `[CONFIRM:` has a total that is a
    sentence rather than an amount. The total check stripped everything but
    digits and dots, got "..", and `float("..")` raised. So the tool that
    exists to tell you what is wrong with a package fell over on a package
    that was wrong, and its own docstring already promised the other
    behaviour: "an amount that will not parse".

    THE ROUTE HERE CHANGED and the subject did not. This used to reach the
    state through an amendment with no reason, which `intake.finish` now
    refuses -- the schema marks `amendment_reason` required and the back door
    finally reads that. An unpriced line in the fee schedule still produces
    exactly this total, so the placeholder is set on the record directly: what
    is under test is `report`, not the several ways a price can go unset.
    """
    store = tmp_path / "store"
    record = record_for(created(sitting(
        return_basis="amended", amendment_reason="new_information",
        other_income_documents="yes"), store).ref, store)
    record["EstimateTotal"] = "[CONFIRM: the firm has not priced this]"
    assert record["EstimateTotal"].startswith("[CONFIRM:")

    checks = report_for(record)
    total = checks["the total is the sum of the lines"]
    assert not total.ok
    assert "not an amount" in total.detail

    # And the estimate itself never renders, so no client sees the sentence.
    with pytest.raises(merge.MergeError, match="undecided placeholders"):
        render_all(record, ["fee-estimate"])


def test_the_invoice_and_the_estimate_state_one_engagement(tmp_path):
    """Two documents about the same money, written months apart.

    "Two documents that state the same money from two sources will eventually
    disagree, and the one the client keeps is the one that says the larger
    number." Read side by side, off the rendered pages: same reference, same
    figure, and the ONE value they must not share -- `PeriodLabel`, which is
    the engagement's period on the estimate and the period BILLED on the
    invoice.
    """
    store, out = tmp_path / "store", tmp_path / "out"
    ref = created(sitting(return_features=["itemizing"],
                          other_income_documents="yes"), store).ref
    assert cli.main(["invoice", "--engagement", ref, "--store", str(store),
                     "--billed", "March 2027"]) == 0
    assert cli.main(["render", "--engagement", ref, "--store", str(store),
                     "--docs", "invoice", "--out", str(out), "--no-pdf"]) == 0

    record = record_for(ref, store)
    invoice = readable(next(out.glob("*.html")).read_text(encoding="utf-8"))
    estimate = readable(render_all(record, ["fee-estimate"])["fee-estimate"])

    assert record["EngagementRef"] in invoice and record["EngagementRef"] in estimate
    assert record["EstimateTotal"] in invoice, (
        "the invoice does not carry the estimate it came from, so a client "
        "billed a different number has nothing to compare it against")
    assert "March 2027" in invoice and "March 2027" not in estimate
    assert "2026 tax year" in estimate


# ══ 4 · things a document must not be able to say ═════════════════════════

@pytest.mark.parametrize("label,answers,package", [
    ("simple filer", sitting(), "Simple Filer"),
    ("essentials", sitting(other_income_documents="yes"), "Essentials"),
    ("standard", sitting(return_features=["itemizing"],
                         other_income_documents="yes"), "Standard"),
    ("self-employed", sitting(return_features=["self_employment"],
                              schedule_c_kind="standard", count_businesses=1,
                              other_income_documents="yes"), "Self-Employed"),
])
def test_no_client_is_told_their_package_covers_two_deduction_methods(
        label, answers, package, tmp_path):
    """Found by the firm, reading a rendered estimate.

    A Standard estimate listed "The standard deduction" AND "Itemized
    deductions". A client cannot have both, and the second is the whole reason
    the package costs more. `covers:` inherits down the `includes:` chain, so
    the higher rung stated its own choice on top of the lower rung's.

    The firm's rule, and why deleting the shared line was the wrong fix:
    "standard is implied - itemized is not. so on essentials and starter, we
    can keep standard. for the higher ones just say itemized." Read off the
    page, because the page is where it was found.
    """
    store = tmp_path / "store"
    record = record_for(created(answers, store).ref, store)
    page = readable(render_all(record, ["fee-estimate"])["fee-estimate"])

    assert package in page
    standard = "The standard deduction" in page
    itemized = "Itemized deductions" in page
    assert standard != itemized, (
        f"{label}: the estimate offers "
        + ("both deduction methods" if standard else "neither deduction method"))
    assert itemized == (package in ("Standard", "Self-Employed"))


def test_an_open_decision_is_only_caught_where_it_would_print(tmp_path):
    """The asymmetry that let a test pass while checking nothing.

    The `[CONFIRM:` and unresolved-field guards read the RENDERED TEXT. That
    is the right design -- what matters is what reaches the client -- but it
    has a consequence worth stating out loud, because it has already cost one
    test: `test_confirm_placeholder_cannot_reach_a_client` poked
    `ReturnInstruction`, and when the templates stopped merging that field the
    placeholder no longer reached the render, so the test went on passing and
    was checking nothing at all.

    So a guard test has to poison a field the template ACTUALLY MERGES, and
    the way to know which those are is to ask the template. This asserts both
    halves: poisoning a merged field refuses, poisoning an unmerged one cannot
    possibly, and the list of merged fields is read from the template rather
    than remembered.
    """
    store = tmp_path / "store"
    record = record_for(created(sitting(), store).ref, store)
    template = (cli.TEMPLATE_DIR / cli.DOCUMENTS["tax-letter"][0]).read_text(
        encoding="utf-8")
    merged = merge.tokens_in(template)["fields"]

    assert "ClientCity" in merged
    with pytest.raises(merge.MergeError, match="undecided placeholders"):
        merge.render(template, dict(record, ClientCity="[CONFIRM: which address?]"))

    unmerged = "SomethingNoTemplateAsksFor"
    assert unmerged not in merged
    merge.render(template, dict(record, **{unmerged: "[CONFIRM: anything]"}))

    # The half that turns the lesson into a control: every field the firm
    # supplies to THIS document is one the guard can see.
    supplied = firm.firm_fields(record["_season"], record["_return_type"])
    for field in sorted(set(supplied) & merged):
        with pytest.raises(merge.MergeError, match="undecided placeholders"):
            merge.render(template, dict(record, **{field: "[CONFIRM: undecided]"}))
