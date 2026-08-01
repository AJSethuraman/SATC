"""The prior-year omission diff — the gap tick-and-tie structurally cannot close.

The property under test: a document that was in hand last year and has no trace
this year gets NOTICED. Everything else is there to stop that signal being
drowned — an item already on the chase list is a different problem, and a
genuinely new account is not an alarm.
"""

from __future__ import annotations

from satc.models.mart import DocumentRecord
from satc.rollover import (
    as_questions,
    omission_diff,
    opening_request_list,
)


def _doc(doc_type, year, status="Received", *, client="C", note=""):
    return DocumentRecord(
        document_id=f"{client}-{doc_type}-{year}-{status}", client_id=client,
        tax_year=year, doc_type=doc_type, status=status, note=note)


def _diff(docs, prior=2024, current=2025, client="C"):
    return omission_diff(docs, client_id=client, prior_year=prior, current_year=current)


# --- the alarm ----------------------------------------------------------------

def test_a_document_in_hand_last_year_and_absent_this_year_is_flagged():
    """THE CASE. A closed account, a changed custodian, a lost page."""
    report = _diff([
        _doc("W-2", 2024), _doc("1099-INT", 2024, note="Fidelity"),
        _doc("W-2", 2025),
    ])
    assert [k.doc_type for k in report.missing] == ["1099-INT"]
    assert report.missing[0].detail == "Fidelity"
    assert report.has_questions


def test_the_detail_makes_the_question_specific():
    """"Your 1099-INT" is a worse question than "your 1099-INT from Fidelity"."""
    report = _diff([_doc("1099-INT", 2024, note="Fidelity brokerage")])
    questions = as_questions(report)
    assert any("Fidelity brokerage" in q for q in questions)


def test_an_omission_is_asked_as_a_question_not_asserted_as_a_finding():
    """People genuinely close accounts. The value is in asking."""
    report = _diff([_doc("1099-INT", 2024)])
    question = as_questions(report)[0]
    assert question.endswith("?")
    assert "is that still expected" in question


# --- what must NOT be flagged -------------------------------------------------

def test_something_already_requested_this_year_is_not_an_omission():
    """It is on the chase list — a different problem with a different message."""
    report = _diff([
        _doc("1099-INT", 2024),
        _doc("1099-INT", 2025, status="Requested"),
    ])
    assert report.missing == []
    assert [k.doc_type for k in report.outstanding] == ["1099-INT"]


def test_a_document_received_both_years_is_carried_not_flagged():
    report = _diff([_doc("W-2", 2024), _doc("W-2", 2025)])
    assert report.missing == []
    assert [k.doc_type for k in report.carried] == ["W-2"]


def test_a_new_document_this_year_is_noted_but_is_not_an_alarm():
    report = _diff([_doc("W-2", 2024), _doc("W-2", 2025), _doc("1099-B", 2025)])
    assert report.missing == []
    assert [k.doc_type for k in report.new_this_year] == ["1099-B"]
    assert not report.has_questions


def test_a_prior_year_document_that_was_only_requested_never_counts():
    """We asked for it last year and it never came — it is not evidence of
    anything this year, so it must not generate a phantom omission."""
    report = _diff([_doc("K-1-1065", 2024, status="Requested")])
    assert report.missing == []
    assert report.prior_year_count == 0


def test_another_clients_documents_are_never_mixed_in():
    report = _diff([
        _doc("1099-INT", 2024, client="OTHER"),
        _doc("W-2", 2024), _doc("W-2", 2025),
    ])
    assert report.missing == []


def test_a_signed_document_counts_as_in_hand():
    """An 8879 that came back signed is in hand, not outstanding."""
    report = _diff([_doc("Form 8879", 2024, status="Signed")])
    assert [k.doc_type for k in report.missing] == ["Form 8879"]


# --- the summary --------------------------------------------------------------

def test_a_clean_year_says_so_plainly():
    report = _diff([_doc("W-2", 2024), _doc("W-2", 2025)])
    assert "Everything from 2024 has a 2025 counterpart" in report.summary_line()


def test_with_no_prior_year_the_diff_says_it_cannot_compare():
    """A first-year client must not read as "nothing is missing"."""
    report = _diff([_doc("W-2", 2025)])
    assert "No 2024 documents on file to compare against" in report.summary_line()
    assert not report.has_questions


def test_the_summary_counts_against_the_prior_year_denominator():
    report = _diff([
        _doc("W-2", 2024), _doc("1099-INT", 2024), _doc("1099-DIV", 2024),
        _doc("W-2", 2025),
    ])
    assert "2 not seen this year" in report.summary_line()
    assert "of 3 on file for 2024" in report.summary_line()


# --- the opening request list -------------------------------------------------

def test_last_years_documents_become_this_years_expected_list():
    docs = [_doc("W-2", 2024), _doc("1099-INT", 2024), _doc("K-1-1065", 2024)]
    expected = opening_request_list(docs, client_id="C", prior_year=2024)
    assert [k.doc_type for k in expected] == ["1099-INT", "K-1-1065", "W-2"]


def test_the_opening_list_excludes_what_never_arrived():
    """Asking again for something they never sent is a worse starting point than
    not asking — it was probably not applicable."""
    docs = [_doc("W-2", 2024), _doc("K-1-1065", 2024, status="Requested")]
    expected = opening_request_list(docs, client_id="C", prior_year=2024)
    assert [k.doc_type for k in expected] == ["W-2"]


def test_the_opening_list_carries_the_detail_forward():
    docs = [_doc("1099-INT", 2024, note="Fidelity")]
    assert opening_request_list(docs, client_id="C", prior_year=2024)[0].detail == "Fidelity"


# --- nothing is written -------------------------------------------------------

def test_the_diff_writes_nothing():
    """A question generator, not a decision. It takes records and returns a report."""
    docs = [_doc("W-2", 2024), _doc("1099-INT", 2024)]
    before = [(d.document_id, d.status) for d in docs]
    _diff(docs)
    opening_request_list(docs, client_id="C", prior_year=2024)
    assert [(d.document_id, d.status) for d in docs] == before


def test_it_runs_against_the_seeded_practice():
    """End-to-end against real fixture data, not hand-built records."""
    from satc.app.state import STATE

    client_id = STATE.client_choices()[0][0]
    report = omission_diff(STATE.documents(), client_id=client_id,
                           prior_year=2023, current_year=2024)
    assert report.client_id == client_id
    assert isinstance(report.summary_line(), str)


# --- the loop that makes it useful: diff -> a client email --------------------

def test_the_diff_reaches_the_comms_context_as_questions():
    """The whole point: the omission becomes a draft the owner sends."""
    from satc.comms import build_context

    docs = [_doc("W-2", 2024), _doc("1099-INT", 2024, note="Fidelity"),
            _doc("W-2", 2025)]
    values = build_context(client_id="C", documents=docs,
                           tax_year=2025, prior_year=2024)
    assert "prior_year_questions" in values
    assert "1099-INT" in values["prior_year_questions"]
    assert "Fidelity" in values["prior_year_questions"]


def test_no_omissions_means_no_merge_value_and_a_visibly_unfilled_draft():
    """Absent, not blank — so the renderer marks it rather than sending a gap."""
    from satc.comms import build_context, library, render

    docs = [_doc("W-2", 2024), _doc("W-2", 2025)]
    values = build_context(client_id="C", documents=docs,
                           tax_year=2025, prior_year=2024)
    assert "prior_year_questions" not in values

    draft = render(library().template("prior_year_check"), values, library=library())
    assert "prior_year_questions" in draft.unfilled
    assert "[[ Prior-year questions: fill in ]]" in draft.body


def test_the_prior_year_check_draft_renders_end_to_end():
    from satc.comms import build_context, library, render

    lib = library()
    docs = [_doc("1099-INT", 2024, note="Fidelity"), _doc("W-2", 2024),
            _doc("W-2", 2025)]
    values = build_context(client_id="C", client_name="Jordan Rivera",
                           documents=docs, tax_year=2025, prior_year=2024,
                           firm_values=lib.firm_values())
    draft = render(lib.template("prior_year_check"), values, library=lib)
    assert draft.is_complete, f"unfilled: {draft.unfilled}"
    assert "Dear Jordan," in draft.body
    assert "1099-INT" in draft.body
    assert "DRAFT" in draft.body


def test_the_diff_does_not_leak_the_prior_year_into_the_narrowed_register():
    """missing_items must still describe THIS year only."""
    from satc.comms import build_context

    docs = [_doc("1099-INT", 2024), _doc("K-1-1065", 2025, status="Requested")]
    values = build_context(client_id="C", documents=docs,
                           tax_year=2025, prior_year=2024)
    assert "K-1-1065" in values["missing_items"]
    assert "1099-INT" not in values.get("missing_items", "")
