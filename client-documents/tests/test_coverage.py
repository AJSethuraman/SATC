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
        "ReturnInstruction", "PaymentInstruction", "MaterialsDeadline"}
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


@pytest.mark.parametrize("form", ["1040", "1120S", "1065", "1120"])
def test_every_return_type_the_interview_offers_can_open_an_engagement(form):
    """The guard on the whole thing.

    `federal_form` offers four returns. Offering one the pipeline cannot
    produce documents for is the bug this file was written after.
    """
    over = dict(ENTITY_ANSWERS) if form != "1040" else {}
    over["federal_form"] = form
    record = _record(**over)
    doc = "business-letter" if form != "1040" else "tax-letter"
    missing = sorted(f for f in _wants(doc) if f not in record and f not in LATER)
    assert not missing, (
        f"a {form} engagement cannot produce {doc}: {missing} are unasked"
    )


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
