"""Can every document the interview claims to open actually be produced?

This file exists because one could not. The business return letter registered
`EntityType`, `ScheduleK1Target`, `SignerName` and `SignerTitle` as the
interview's to supply, no question asked any of them, and every business
engagement refused to render. Nothing caught it for two reasons:

1. the templates were proven against `samples/business-engagement.json`, which
   hand-writes all four -- a payload the real pipeline could never produce; and
2. the interview offered 1120-S, 1065 and 1120 in its very first question,
   while a note in the run log justified the gap by saying "the tax interview
   covers individual returns". Both could not be true.

The check below is deliberately end-to-end and deliberately blunt: compose a
record from interview answers ALONE, and ask each document what it still
wants. Anything left is either something a later stage legitimately supplies,
or a hole.
"""

from __future__ import annotations

import json
from datetime import date
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import intake  # noqa: E402
import interview as iv  # noqa: E402
import merge  # noqa: E402

SAMPLES = ROOT / "samples"

# Fields a LATER stage owns. Not exemptions from the interview -- statements
# about which stage supplies them, each of which has to be true.
FIRM = {"FirmName", "FirmLegalName", "FirmAddress1", "FirmCity",
        "FirmState", "FirmZip", "FirmWebsite", "FirmJurisdiction",
        "PreparerName", "PreparerTitle", "PreparerEmail",
        "BillingContactName", "BillingContactEmail",
        "PaymentInstruction", "MaterialsDeadline"}
DELIVERY = {"AmountDue", "InvoiceDate", "InvoiceNumber", "Subtotal",
            "SignatureDeadline", "EstimateDate", "EstimateTotal", "VarianceNote",
            "CreditAmount", "CreditDetail", "CreditLabel", "EstimateReference"}
IN_FLIGHT = {"ExtendedDeadline", "PaymentDeadline", "EstimatedPaymentAmount"}
ENDING = {"EffectiveDate", "RecordsAvailableUntil", "ScopeEnded", "OutstandingBalance"}
ENGAGEMENT = {"EngagementRef", "FeeChangeNote"}
# Bookkeeping is a separate engagement with no interview at all. That is a
# known, deliberate gap -- the PRD defers it -- and it has its own test below
# so it cannot be forgotten rather than being silently swept in here.
LATER = FIRM | DELIVERY | IN_FLIGHT | ENDING | ENGAGEMENT


def _answers(**over):
    a = json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))
    a.update(over)
    return a


ENTITY_ANSWERS = dict(
    federal_form="1120S", client_full_name="Larchmere Holdings LLC",
    entity_structure="llc", entity_state="Ohio",
    signer_name="Daniel Reyes", signer_title="Managing Member",
    k1_target="March 10, 2027", count_owners=3, owner_returns="yes",
)


def _wants(doc: str) -> set[str]:
    filename, _ = cli.DOCUMENTS[doc]
    tpl = (cli.TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    return set(merge.tokens_in(tpl)["fields"])


def _record(**over):
    return intake.compose_record(_answers(**over))


# ── the opening package must be producible for every return the interview offers ──

OPENING = ["tax-letter", "fee-estimate", "onboarding-letter", "organizer-letter"]


def _sat_through(form: str) -> dict:
    """Answers from a REAL sitting for this return type.

    Not a hand-written payload. `ENTITY_ANSWERS` wrote `k1_target` and
    `count_owners` for every entity, and a real 1120 sitting PRUNES both --
    their `showIf` is `1120S or 1065`. So the test supplied two fields the
    interview would never produce and asserted the document could be built from
    them, which is the exact shape `registry/interview.yaml`'s own header says
    this registry exists because of: "the tests passed only because the sample
    payload hand-wrote all four".
    """
    session = iv.Interview()
    session.answer("federal_form", form)
    for _ in range(120):
        nxt = session.next_question()
        if nxt is None:
            break
        _, q = nxt
        session.answer(q["id"], _answerable(q))
    return session.answers


def _answerable(q: dict):
    """Any answer this question takes that does not end the sitting."""
    options = [o for o in (q.get("options") or []) if not o.get("hard_no")]
    if options:
        return [options[0]["value"]] if q["type"] == "multi" else options[0]["value"]
    if q.get("options"):
        return [] if q["type"] == "multi" else ""
    if q["type"] == "year":
        return date.today().year
    if q["type"] == "number":
        return max(1, q.get("min") or 1)
    if q["type"] == "list":
        return ["Ohio - resident"]
    if q.get("pattern"):
        for candidate in ("t@example.com", "44139"):
            if re.match(q["pattern"], candidate):
                return candidate
    return "Larchmere Holdings LLC" if "name" in q["id"] else "x"


@pytest.mark.parametrize("form", ["1040", "1120S", "1065", "1120"])
def test_every_return_type_the_interview_offers_can_open_an_engagement(form):
    """The guard on the whole thing.

    `federal_form` offers four returns. Offering one the pipeline cannot
    produce documents for is the bug this file was written after.

    THE DOCUMENT COMES FROM `OPENING_BY_RETURN`, not from a guess. This test
    asserted `business-letter` for every entity, and a C corporation gets
    `ccorp-letter` -- so the one return type with its own opening letter was
    checked against a document it never receives, and `ccorp-letter` was
    checked by nothing at all.
    """
    answers = _sat_through(form)
    record = intake.compose_record(answers)
    doc = cli.OPENING_BY_RETURN[intake.RETURN_TYPE[form]]
    missing = sorted(f for f in _wants(doc) if f not in record and f not in LATER)
    assert not missing, (
        f"a {form} engagement cannot produce {doc}: {missing} are unasked"
    )


def test_every_opening_letter_is_covered_by_the_test_above():
    """`ccorp-letter` was reachable in production and asserted on by nothing.

    Guarding the guard: if a fifth return type or a fifth opening letter is
    added, this fails until the parametrize list above covers it.
    """
    checked = {cli.OPENING_BY_RETURN[intake.RETURN_TYPE[f]]
               for f in ("1040", "1120S", "1065", "1120")}
    assert checked == set(cli.OPENING_BY_RETURN.values())


def test_the_business_letter_gets_its_entity_fields_from_the_interview():
    """Named explicitly, because these four were the actual hole."""
    record = _record(**ENTITY_ANSWERS)
    for field in ("EntityType", "ScheduleK1Target", "SignerName", "SignerTitle"):
        assert record.get(field), f"{field} still unsupplied"


def test_the_entity_phrase_reads_as_a_phrase_not_a_code():
    """It drops into the letter's opening sentence after a comma."""
    record = _record(**ENTITY_ANSWERS)
    assert record["EntityType"] == \
        "an Ohio limited liability company taxed as an S corporation"


@pytest.mark.parametrize("structure,form,expected", [
    ("llc", "1120S", "an Ohio limited liability company taxed as an S corporation"),
    ("llc", "1065", "an Ohio limited liability company taxed as a partnership"),
    ("corporation", "1120", "an Ohio corporation"),
    ("lp", "1065", "an Ohio limited partnership"),
])
def test_the_phrase_does_not_state_the_obvious(structure, form, expected):
    """"a limited partnership taxed as a partnership" reads as though something
    unusual had been elected, which is the opposite of what it means."""
    got = iv._entity_type({"entity_structure": structure, "entity_state": "Ohio",
                           "federal_form": form})
    assert got == expected


def test_the_article_follows_sound_not_spelling():
    """"an S corporation", but "a C corporation". S is pronounced "ess"."""
    s_corp = iv._entity_type({"entity_structure": "llc", "entity_state": "Ohio",
                              "federal_form": "1120S"})
    c_corp = iv._entity_type({"entity_structure": "llc", "entity_state": "Ohio",
                              "federal_form": "1120"})
    assert "taxed as an S corporation" in s_corp
    assert "taxed as a C corporation" in c_corp


def test_the_owner_flags_are_exact_inverses():
    """Two questions could disagree and the letter would contradict itself."""
    for answer, prepared in (("yes", True), ("no", False)):
        record = _record(**dict(ENTITY_ANSWERS, owner_returns=answer))
        assert record["OwnerReturnsPrepared"] is prepared
        assert record["OwnerReturnsElsewhere"] is (not prepared)


def test_the_scorp_election_flag_follows_the_return_not_an_answer():
    """Asking would invite an answer that contradicts the form already chosen."""
    assert _record(**ENTITY_ANSWERS)["SCorpElection"] is True
    assert _record(**dict(ENTITY_ANSWERS, federal_form="1065"))["SCorpElection"] is False


# ── the known gap, held open on purpose ───────────────────────────────────

def test_bookkeeping_has_no_interview_and_that_is_recorded_not_forgotten():
    """A whole engagement type nothing can open.

    The PRD defers it explicitly, so this is not a bug -- but it is exactly the
    shape of the business-letter bug, and the difference between the two is
    only that someone wrote this down. When the bookkeeping interview is built,
    delete this test and add `bookkeeping-letter` to the parametrised check.
    """
    record = _record()
    missing = sorted(f for f in _wants("bookkeeping-letter")
                     if f not in record and f not in LATER)
    assert missing, "bookkeeping now has an interview -- fold it into the check above"
    assert "AccountingSystem" in missing and "Cadence" in missing


# ── the check itself must be capable of failing ───────────────────────────

def test_the_field_scan_actually_finds_fields():
    """The first version of this scan used a plain `<<Field>>` regex and found
    NOTHING, because the templates HTML-escape their delimiters -- so it
    reported every document clean. A check that passes because its pattern
    never matches is worse than no check."""
    fields = _wants("business-letter")
    assert len(fields) > 15, "the scan is not seeing the template's fields"
    assert "EntityType" in fields
