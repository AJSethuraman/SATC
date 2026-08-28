"""The one fact the engagement turns on, which nothing recorded.

Six places in this codebase already speak of a signed engagement letter as a
fact — `packaging.PURPOSE` calls it "the one that is signed", `requote` freezes
`LetterDate` because "the client has signed that letter", and both front doors
say so to a preparer's face. Nothing recorded that anybody signed anything.

Two documents promise a client something that turns on it, and neither could be
honoured. These tests hold the register, and hold the line between what it
knows and what it only looks like it knows.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import engagements  # noqa: E402
import intake  # noqa: E402
import packaging  # noqa: E402
import signing  # noqa: E402

ANSWERS = ROOT / "samples" / "interview-answers.json"


@pytest.fixture
def live(tmp_path):
    answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
    out = intake.finish(answers, store=tmp_path, today=date(2027, 2, 3))
    assert out.created, out.reason
    record = engagements.load(out.ref, tmp_path)
    return out.ref, tmp_path, record, packaging.documents_for(record)


def here(ref, store, record, docs, **kw):
    return signing.standing(ref, record, docs, cli.TEMPLATE_DIR,
                            store=store, **kw)


# ── the census comes from the documents ───────────────────────────────────

def test_who_must_sign_is_read_off_the_templates():
    """A list in `signing.py` would go stale the first time a block moved, and
    go stale SILENTLY — the register would stop waiting for a signature the
    document still asks for."""
    seen = {}
    for doc, (filename, _) in cli.DOCUMENTS.items():
        html = (cli.TEMPLATE_DIR / filename).read_text(encoding="utf-8")
        lines = signing.lines_in(html, doc)
        if lines:
            seen[doc] = [(ln.field, ln.only_if) for ln in lines]

    assert set(seen) == {"tax-letter", "business-letter", "ccorp-letter",
                         "bookkeeping-letter", "records-release"}, (
        "the set of documents carrying a signature block has changed"
    )
    assert seen["tax-letter"] == [("TaxpayerName", ""),
                                  ("SpouseName", "JointReturn")]
    assert seen["business-letter"] == [("SignerName", "")]


def test_a_date_line_is_not_a_second_person():
    """Every block pairs a signature line with a Date line."""
    html = (cli.TEMPLATE_DIR / cli.DOCUMENTS["tax-letter"][0]).read_text(
        encoding="utf-8")
    assert html.count('class="siglab">Date') == 2
    assert len(signing.lines_in(html, "tax-letter")) == 2


def test_the_spouse_signs_only_on_a_joint_return(live):
    """The template puts that line inside `[[IF JointReturn]]`, and the
    delivery letter says why: "On a joint return, both spouses sign, and one
    signature is not enough to file." """
    ref, store, record, docs = live
    assert record["JointReturn"] is True
    joint = here(ref, store, record, docs)
    assert any(ln.field == "SpouseName" for ln in joint.expected)

    alone = dict(record, JointReturn=False)
    single = signing.standing(ref, alone, docs, cli.TEMPLATE_DIR, store=store)
    assert not any(ln.field == "SpouseName" for ln in single.expected)
    assert single.examined < joint.examined


def test_only_documents_this_client_was_actually_sent(live):
    """The records release goes only to a client with a predecessor. Waiting
    on a signature for a document nobody was given is how a register stops
    being believed."""
    ref, store, record, _ = live
    assert record["PriorFirm"] is True
    with_release = here(ref, store, record, packaging.documents_for(record))
    assert any(ln.document == "records-release"
               for ln in with_release.expected)

    fresh = dict(record, PriorFirm=False)
    without = signing.standing(ref, fresh, packaging.documents_for(fresh),
                               cli.TEMPLATE_DIR, store=store)
    assert not any(ln.document == "records-release"
                   for ln in without.expected)


def test_a_signer_is_named_the_way_a_person_would_name_them(live):
    """It read "SignerName has not signed" — the software's word for a person.
    `fields.yaml` labels all three."""
    ref, store, record, docs = live
    who = {ln.who for ln in here(ref, store, record, docs).expected}
    assert who == {"Taxpayer", "Spouse"}
    assert not any(w.endswith("Name") for w in who)


# ── the register ──────────────────────────────────────────────────────────

def test_nothing_is_signed_until_it_is_recorded(live):
    ref, store, record, docs = live
    where = here(ref, store, record, docs)
    assert where.examined == 4
    assert len(where.missing) == 4
    assert not where.complete


def test_recording_one_closes_exactly_one(live):
    ref, store, record, docs = live
    where = here(ref, store, record, docs)
    line = next(ln for ln in where.expected if ln.document == "tax-letter")
    signing.record_signature(ref, line, when="February 9, 2027",
                             how="in-person", store=store)
    after = here(ref, store, record, docs)
    assert len(after.missing) == len(where.missing) - 1
    assert after.have[0].how == "in-person"


def test_the_means_is_the_evidence_and_cannot_be_invented(live):
    """"He signed it in front of me" and "the portal said it completed" are
    different kinds of knowing. "yes" is not a means."""
    ref, store, record, docs = live
    line = here(ref, store, record, docs).expected[0]
    with pytest.raises(signing.SigningError, match="not a way"):
        signing.record_signature(ref, line, when="February 9, 2027",
                                 how="yes", store=store)
    assert not signing.signatures(ref, store)


def test_a_service_signature_without_its_audit_trail_is_refused(live):
    """The record is worth having only if it points at one."""
    ref, store, record, docs = live
    line = here(ref, store, record, docs).expected[0]
    with pytest.raises(signing.SigningError, match="audit trail"):
        signing.record_signature(ref, line, when="February 9, 2027",
                                 how="e-signed", reference="", store=store)
    signing.record_signature(ref, line, when="February 9, 2027",
                             how="e-signed", reference="env_9f2c11",
                             store=store)
    assert signing.signatures(ref, store)[0].reference == "env_9f2c11"


def test_the_day_they_signed_is_not_the_day_you_heard(live):
    """A letter that arrives on Monday was signed on Friday, and the date on
    the page is the one that counts."""
    ref, store, record, docs = live
    line = here(ref, store, record, docs).expected[0]
    with pytest.raises(signing.SigningError, match="date they signed"):
        signing.record_signature(ref, line, when="  ", how="returned",
                                 store=store)
    signing.record_signature(ref, line, when="February 9, 2027",
                             how="returned", store=store,
                             today=date(2027, 2, 14))
    got = signing.signatures(ref, store)[0]
    assert (got.when, got.recorded) == ("February 9, 2027", "2027-02-14")


def test_the_log_is_appended_to_and_a_corrupt_one_is_kept(live):
    ref, store, record, docs = live
    (store / ref / "signatures.json").write_text("{not json", encoding="utf-8")
    for line in here(ref, store, record, docs).expected[:2]:
        signing.record_signature(ref, line, when="February 9, 2027",
                                 how="in-person", store=store)
    assert (store / ref / "signatures.corrupt").exists()
    assert len(signing.signatures(ref, store)) == 2


# ── the deadline nobody watched ───────────────────────────────────────────

def test_the_signature_deadline_is_compared_against_something(live):
    """It has been asked by the delivery event since that event was built,
    printed on the letter, and compared against nothing."""
    ref, store, record, docs = live
    assert not here(ref, store, record, docs,
                    deadline="April 10, 2027",
                    today=date(2027, 3, 1)).overdue
    assert here(ref, store, record, docs,
                deadline="April 10, 2027", today=date(2027, 5, 1)).overdue


def test_a_deadline_nobody_can_read_is_not_a_deadline_that_passed(live):
    """Saying otherwise raises a false alarm on every engagement whose
    deadline was typed in a shape this did not expect."""
    ref, store, record, docs = live
    assert not here(ref, store, record, docs, deadline="as soon as possible",
                    today=date(2030, 1, 1)).overdue
    assert not here(ref, store, record, docs, deadline="",
                    today=date(2030, 1, 1)).overdue


def test_a_signed_engagement_is_not_overdue(live):
    ref, store, record, docs = live
    for line in here(ref, store, record, docs).expected:
        signing.record_signature(ref, line, when="February 9, 2027",
                                 how="in-person", store=store)
    where = here(ref, store, record, docs, deadline="April 10, 2027",
                 today=date(2027, 5, 1))
    assert where.complete and not where.overdue


# ── what it knows, and what it only looks like it knows ───────────────────

def test_the_engagement_letter_gates_the_work_and_the_release_does_not(live):
    """The records release is addressed to the PREVIOUS accountant. Blocking
    on it would stop an engagement for a document somebody else acts on."""
    ref, store, record, docs = live
    gate = signing.may_file(ref, record, docs, cli.TEMPLATE_DIR, store=store)
    assert all("tax-letter" in b for b in gate.blockers)
    assert any("records-release" in u for u in gate.unknown)


def test_the_form_that_gates_filing_is_not_in_this_software(live):
    """Form 8879 comes out of Drake and none of the twelve templates is one.
    Reporting it satisfied because we cannot see it is the exact failure this
    module exists to stop."""
    ref, store, record, docs = live
    for line in here(ref, store, record, docs).expected:
        signing.record_signature(ref, line, when="February 9, 2027",
                                 how="in-person", store=store)
    gate = signing.may_file(ref, record, docs, cli.TEMPLATE_DIR, store=store)
    assert not gate.blockers, gate.blockers
    assert not gate.clear, "everything we can see is signed, and that is not enough"
    said = " ".join(gate.unknown)
    assert "8879" in said and "Drake" in said
    assert "invoice has been settled" in said


def test_an_empty_census_is_not_a_completion(live):
    """S2. A check that examined nothing once reported itself green."""
    ref, store, record, _ = live
    empty = signing.standing(ref, record, ["fee-estimate"], cli.TEMPLATE_DIR,
                             store=store)
    assert empty.examined == 0
    assert not empty.complete
    gate = signing.may_file(ref, record, ["fee-estimate"], cli.TEMPLATE_DIR,
                            store=store)
    assert any("nothing to have signed" in u for u in gate.unknown)


def test_nothing_here_asserts_a_compliance_claim():
    """`docs/research-e-signature.md` records that Pub 1345's KBA regime could
    NOT be confirmed to reach the entity forms, and that no US-storage rule
    was found. The software must not say otherwise."""
    source = (ROOT / "signing.py").read_text(encoding="utf-8").lower()
    for claim in ("compliant", "irs-approved", "meets pub", "satisfies pub",
                  "legally binding", "tamper-evident"):
        assert claim not in source, f"signing.py asserts {claim!r}"
