"""The prior-year omission diff — the gap tick-and-tie structurally cannot close.

The property under test: a document that was in hand last year and has no trace
this year gets NOTICED. Everything else exists to stop that signal being drowned
— an item already on the chase list is a different problem, and a genuinely new
account is not an alarm.

Since the evidence split these read the two entities directly. "Asked for" and
"arrived" are different tables, which is what lets the diff say a document was
received last year AND requested this year without a status string having to
mean two things at once.
"""

from __future__ import annotations

from satc.models.evidence import ReceivedDocument, RequestedItem
from satc.rollover import as_questions, omission_diff, opening_request_list


def _got(doc_type, year, *, client="C", note=""):
    """A document that ARRIVED."""
    return ReceivedDocument(document_id=f"{client}-{doc_type}-{year}", client_id=client,
                            tax_year=year, doc_type=doc_type, note=note)


def _ask(doc_type, year, *, client="C", note="", status="outstanding"):
    """A document we ASKED FOR."""
    return RequestedItem(request_id=f"req-{client}-{doc_type}-{year}", client_id=client,
                         tax_year=year, doc_type=doc_type, request_text=note,
                         status=status)


def _diff(received=(), requested=(), prior=2024, current=2025, client="C"):
    return omission_diff(received, requested, client_id=client,
                         prior_year=prior, current_year=current)


# --- the alarm ----------------------------------------------------------------

def test_a_document_in_hand_last_year_and_absent_this_year_is_flagged():
    """THE CASE. A closed account, a changed custodian, a lost page."""
    report = _diff([_got("W-2", 2024), _got("1099-INT", 2024, note="Fidelity"),
                    _got("W-2", 2025)])
    assert [k.doc_type for k in report.missing] == ["1099-INT"]
    assert report.missing[0].detail == "Fidelity"
    assert report.has_questions


def test_the_detail_makes_the_question_specific():
    report = _diff([_got("1099-INT", 2024, note="Fidelity brokerage")])
    assert any("Fidelity brokerage" in q for q in as_questions(report))


def test_an_omission_is_asked_as_a_question_not_asserted_as_a_finding():
    """People genuinely close accounts. The value is in asking."""
    question = as_questions(_diff([_got("1099-INT", 2024)]))[0]
    assert question.endswith("?")
    assert "is that still expected" in question


# --- what must NOT be flagged -------------------------------------------------

def test_something_already_requested_this_year_is_not_an_omission():
    """The case a single register could not express: the 1099-INT is both a
    2024 ARRIVAL and a 2025 open REQUEST."""
    report = _diff([_got("1099-INT", 2024)], [_ask("1099-INT", 2025)])
    assert report.missing == []
    assert [k.doc_type for k in report.outstanding] == ["1099-INT"]


def test_a_satisfied_request_does_not_count_as_outstanding():
    report = _diff([_got("1099-INT", 2024)],
                   [_ask("1099-INT", 2025, status="satisfied")])
    assert report.outstanding == []


def test_a_document_received_both_years_is_carried_not_flagged():
    report = _diff([_got("W-2", 2024), _got("W-2", 2025)])
    assert report.missing == []
    assert [k.doc_type for k in report.carried] == ["W-2"]


def test_a_new_document_this_year_is_noted_but_is_not_an_alarm():
    report = _diff([_got("W-2", 2024), _got("W-2", 2025), _got("1099-B", 2025)])
    assert report.missing == []
    assert [k.doc_type for k in report.new_this_year] == ["1099-B"]
    assert not report.has_questions


def test_a_prior_year_request_that_never_arrived_counts_for_nothing():
    """We asked last year and it never came — not evidence of anything now."""
    report = _diff([], [_ask("K-1-1065", 2024)])
    assert report.missing == []
    assert report.prior_year_count == 0


def test_another_clients_documents_are_never_mixed_in():
    report = _diff([_got("1099-INT", 2024, client="OTHER"),
                    _got("W-2", 2024), _got("W-2", 2025)])
    assert report.missing == []


# --- the summary --------------------------------------------------------------

def test_a_clean_year_says_so_plainly():
    report = _diff([_got("W-2", 2024), _got("W-2", 2025)])
    assert "Everything from 2024 has a 2025 counterpart" in report.summary_line()


def test_with_no_prior_year_the_diff_says_it_cannot_compare():
    """A first-year client must not read as "nothing is missing"."""
    report = _diff([_got("W-2", 2025)])
    assert "No 2024 documents on file to compare against" in report.summary_line()
    assert not report.has_questions


def test_the_summary_counts_against_the_prior_year_denominator():
    report = _diff([_got("W-2", 2024), _got("1099-INT", 2024),
                    _got("1099-DIV", 2024), _got("W-2", 2025)])
    assert "2 not seen this year" in report.summary_line()
    assert "of 3 on file for 2024" in report.summary_line()


# --- the opening request list -------------------------------------------------

def test_last_years_arrivals_become_this_years_expected_list():
    received = [_got("W-2", 2024), _got("1099-INT", 2024), _got("K-1-1065", 2024)]
    expected = opening_request_list(received, client_id="C", prior_year=2024)
    assert [k.doc_type for k in expected] == ["1099-INT", "K-1-1065", "W-2"]


def test_the_opening_list_is_built_from_arrivals_not_asks():
    """Asking again for something they never sent is a worse starting point."""
    expected = opening_request_list([_got("W-2", 2024)], client_id="C", prior_year=2024)
    assert [k.doc_type for k in expected] == ["W-2"]


def test_the_opening_list_carries_the_detail_forward():
    expected = opening_request_list([_got("1099-INT", 2024, note="Fidelity")],
                                    client_id="C", prior_year=2024)
    assert expected[0].detail == "Fidelity"


# --- nothing is written -------------------------------------------------------

def test_the_diff_writes_nothing():
    """A question generator, not a decision."""
    received = [_got("W-2", 2024), _got("1099-INT", 2024)]
    requested = [_ask("1099-DIV", 2025)]
    before = ([(d.document_id, d.doc_type) for d in received],
              [(r.request_id, r.status) for r in requested])
    _diff(received, requested)
    opening_request_list(received, client_id="C", prior_year=2024)
    after = ([(d.document_id, d.doc_type) for d in received],
             [(r.request_id, r.status) for r in requested])
    assert before == after


def test_it_runs_against_the_seeded_practice():
    from satc.app.state import STATE

    client_id = STATE.client_choices()[0][0]
    report = omission_diff(STATE.received_documents(), STATE.requested_items(),
                           client_id=client_id, prior_year=2023, current_year=2024)
    assert report.client_id == client_id
    assert isinstance(report.summary_line(), str)


def test_the_seeded_practice_really_does_have_the_omission():
    """The demo client is a RETURNING client whose 1099-INT stopped arriving.

    Asserted against the FIXTURE rather than the module-level STATE singleton,
    which other tests mutate — a shared mutable singleton makes any assertion
    about its contents order-dependent, and this one silently flipped when a
    test elsewhere closed the 1099-DIV request.
    """
    from satc.fixtures import synthetic_mart

    mart = synthetic_mart()
    report = omission_diff(mart.received_documents, mart.requested_items,
                           client_id="SATC-001000", prior_year=2023, current_year=2024)
    assert [k.doc_type for k in report.missing] == ["1099-INT"]
    assert "Lakeside" in report.missing[0].detail
    # And the 1099-DIV is OUTSTANDING, not missing — it was asked for this year.
    assert [k.doc_type for k in report.outstanding] == ["1099-DIV"]


# --- the loop that makes it useful: diff -> a client email --------------------

def test_the_diff_reaches_the_comms_context_as_questions():
    from satc.comms import build_context

    values = build_context(
        client_id="C",
        received=[_got("W-2", 2024), _got("1099-INT", 2024, note="Fidelity"),
                  _got("W-2", 2025)],
        tax_year=2025, prior_year=2024)
    assert "prior_year_questions" in values
    assert "1099-INT" in values["prior_year_questions"]
    assert "Fidelity" in values["prior_year_questions"]


def test_no_omissions_means_no_merge_value_and_a_visibly_unfilled_draft():
    """Absent, not blank — so the renderer marks it rather than sending a gap."""
    from satc.comms import build_context, library, render

    values = build_context(client_id="C",
                           received=[_got("W-2", 2024), _got("W-2", 2025)],
                           tax_year=2025, prior_year=2024)
    assert "prior_year_questions" not in values
    draft = render(library().template("prior_year_check"), values, library=library())
    assert "prior_year_questions" in draft.unfilled
    assert "[[ Prior-year questions: fill in ]]" in draft.body


def test_the_prior_year_check_draft_renders_end_to_end():
    from satc.comms import build_context, library, render

    lib = library()
    values = build_context(
        client_id="C", client_name="Jordan Rivera",
        received=[_got("1099-INT", 2024, note="Fidelity"), _got("W-2", 2024),
                  _got("W-2", 2025)],
        tax_year=2025, prior_year=2024, firm_values=lib.firm_values())
    draft = render(lib.template("prior_year_check"), values, library=lib)
    assert draft.is_complete, f"unfilled: {draft.unfilled}"
    assert "Dear Jordan," in draft.body
    assert "1099-INT" in draft.body


def test_the_diff_does_not_leak_the_prior_year_into_this_years_chase():
    """missing_items must describe THIS year's open requests only."""
    from satc.comms import build_context

    values = build_context(client_id="C",
                           received=[_got("1099-INT", 2024)],
                           requested=[_ask("K-1-1065", 2025)],
                           tax_year=2025, prior_year=2024)
    assert "K-1-1065" in values["missing_items"]
    assert "1099-INT" not in values.get("missing_items", "")
