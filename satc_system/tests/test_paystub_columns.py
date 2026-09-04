"""The column reader, the corpus that measures it, and the model boundary.

Read `corpus/paystubs/cases.yaml` before this file. The cases are shapes, not
documents; nothing here or there is a client's stub, and nothing ever may be.

WHAT EACH TEST IS FOR is written on it, and each names a real failure it would
catch. Three of them were watched red before they were watched green, by the
mutations recorded in `test_the_guards_can_fail`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from satc.ingest.paystub_corpus import REFUSE, load_cases, score
from satc.ingest.readers.paystub import (
    LABEL_FED_WH_CURRENT,
    LABEL_FED_WH_YTD,
    LABEL_GROSS_CURRENT,
    LABEL_GROSS_YTD,
    LABEL_PAY_FREQUENCY,
    LABEL_RETIREMENT_CURRENT,
)
from satc.ingest.readers.paystub_columns import (
    LABEL_RETIREMENT_YTD,
    PaystubColumnReader,
)
from satc.ingest.readers.paystub_judgement import (
    ASKABLE,
    Claim,
    ModelBoundary,
    ask,
    askable,
    with_claims,
)


@pytest.fixture(scope="module")
def scored(tmp_path_factory):
    return score(tmp_path_factory.mktemp("paystubs"))


# ---------------------------------------------------------------------------
# The measurement, and its denominator
# ---------------------------------------------------------------------------

def test_the_corpus_is_big_enough_to_mean_anything(scored):
    """S2. A score over three fields on one stub is not a score.

    The reader this replaces was tested against ONE hand-written sample laid
    out exactly the way it assumed, which is a check tested on the case it
    cannot fail (S18). The floor is asserted so a corpus that quietly stops
    rendering reports RED rather than a clean sheet.
    """
    assert len(scored.censuses) >= 18, "the corpus rendered fewer stubs than it holds"
    assert scored.total >= 125, "fewer figures were asked for than the corpus defines"
    looked = sum(c["rows_examined"] for c in scored.censuses.values())
    assert looked >= 100, f"the reader only examined {looked} rows across the corpus"


def test_no_figure_in_the_corpus_is_read_wrong(scored):
    """THE ONE THAT MATTERS. A refusal is a gap; a wrong figure is a wrong return.

    Failure prints the case, the field, what the stub says and what came back,
    because a bare count tells whoever hits this nothing about which shape broke.
    """
    assert not scored.wrong, "\n" + scored.report()


def test_nothing_the_corpus_says_is_readable_comes_back_refused(scored):
    """The other half of "no figure is read wrong", and it needs saying separately.

    A reader that gets shy — a row label matched too loosely, a heading no
    longer recognised — produces refusals, not wrong answers, so
    `test_no_figure_in_the_corpus_is_read_wrong` stays green while the reader
    stops working. Mutation testing on 2 September 2026 found exactly that:
    matching a row label by substring made "Employer 401(k) Match" collide with
    the employee's own deferral, the reader refused both, and nothing failed.
    """
    shy = [o for o in scored.outcomes if o.verdict == "refused"]
    assert not shy, "\n".join(
        f"{o.case} · {o.field}: the stub says {o.expected}, the reader stopped "
        f"for {o.reason!r}" for o in shy)


def test_every_case_that_must_refuse_refuses_for_its_own_reason(scored):
    """S11. An empty box is not a refusal.

    A reader whose labels drifted would find nothing, produce nothing, and
    score full marks on every refusal case in the corpus. The case names WHICH
    stop, so silence cannot pass for judgement.
    """
    named = [o for o in scored.outcomes if o.want_reason]
    assert len(named) >= 12, "the corpus stopped naming its refusal reasons"
    for o in named:
        assert o.got is None, f"{o.case} · {o.field} answered where it had to stop"
        assert o.reason == o.want_reason, (
            f"{o.case} · {o.field} stopped for {o.reason!r}, not {o.want_reason!r}")


def test_the_reader_beats_the_one_it_replaces_on_the_number_that_hurts(tmp_path):
    """The comparison, on one corpus, run both ways.

    This is not a boast: it is the reason to carry two readers at all, and it
    goes red the day the column reader regresses to counting positions.
    """
    columns = score(tmp_path / "a", reader="columns")
    lines = score(tmp_path / "b", reader="lines")
    assert lines.counted("wrong") > 0, (
        "the corpus no longer contains a shape the positional reader gets wrong, "
        "so it no longer measures the thing it was built to measure")
    assert columns.counted("wrong") < lines.counted("wrong")


# ---------------------------------------------------------------------------
# The specific harms, named
# ---------------------------------------------------------------------------

def _read(tmp_path, case_id):
    from satc.ingest.paystub_corpus import render

    case = next(c for c in load_cases() if c["id"] == case_id)
    return case, PaystubColumnReader().read(str(render(case, tmp_path)))


def test_a_rate_and_an_hours_count_are_never_read_as_money(tmp_path):
    """The failure the whole design exists to stop.

    On the same page the positional reader reports 44 hours as $44.00 of gross
    pay for the period, this period's gross as the year-to-date total, and a 5%
    deferral rate as $5.00 of retirement contributions. All three at HIGH
    confidence, none of them flagged.
    """
    _, read = _read(tmp_path, "rate_and_hours_on_the_figure_rows")
    assert read.figures[LABEL_GROSS_CURRENT].value == "1437.52"
    assert read.figures[LABEL_GROSS_YTD].value == "27656.40"
    assert read.figures[LABEL_RETIREMENT_CURRENT].value == "71.88"
    assert read.figures[LABEL_RETIREMENT_YTD].value == "1382.82"
    # And it knows WHICH heading placed each one, which is the whole claim.
    assert "period" in read.figures[LABEL_GROSS_CURRENT].column_said.lower()
    assert "year" in read.figures[LABEL_GROSS_YTD].column_said.lower()


def test_reversing_the_columns_does_not_reverse_the_answer(tmp_path):
    """Reading the heading makes the order irrelevant. Counting makes it fatal."""
    _, read = _read(tmp_path, "ytd_before_current")
    assert read.figures[LABEL_GROSS_CURRENT].value == "4000.00"
    assert read.figures[LABEL_GROSS_YTD].value == "48000.00"


def test_a_total_on_the_last_page_is_found_and_cited_to_that_page(tmp_path):
    """The firm: "it needs to read all pages available".

    And the page is recorded, because `ReadResult.pages` exists precisely so a
    citation can say where a figure came off, and the reader this replaces
    never filled it in — every paystub figure was cited with no page at all.
    """
    _, read = _read(tmp_path, "multipage_total_on_page_three")
    assert read.pages_examined == 3
    assert read.figures[LABEL_GROSS_CURRENT].value == "2950.00"
    assert read.figures[LABEL_GROSS_CURRENT].page == 3
    assert read.to_read_result().pages[LABEL_GROSS_CURRENT] == 3


def test_two_pages_that_disagree_refuse_and_name_both_pages(tmp_path):
    """S12/S5. Picking one silently and reading correctly look identical."""
    _, read = _read(tmp_path, "pages_disagree")
    fig = read.figures[LABEL_GROSS_YTD]
    assert fig.value is None and fig.reason_code == "pages_disagree"
    assert "1" in fig.problem and "2" in fig.problem
    assert "26,000.00" in fig.problem or "26000.00" in fig.problem
    # The figure the two pages AGREE on is still read. A disagreement about one
    # number is not a reason to refuse the others.
    assert read.figures[LABEL_GROSS_CURRENT].value == "2000.00"


def test_an_employee_block_beside_the_table_does_not_hide_the_table(tmp_path):
    """The only case here shaped like a real stub, and it was found by looking.

    Every other case is one table running down the page. A real stub prints
    employee number, department, cheque number and net pay in a block at the
    left, so one line carries words from two unrelated blocks and the row label
    is not the first thing on the line. Nothing in the suite could have told me
    that; rendering a case to an image and opening it did (S1).
    """
    _, read = _read(tmp_path, "side_by_side_blocks")
    assert read.figures[LABEL_GROSS_CURRENT].value == "2400.00"
    assert read.figures[LABEL_RETIREMENT_YTD].value == "1560.00"
    # And the block at the left is not mistaken for a figure: "Net 1,982.00"
    # sits under no column and must not become anything.
    assert "1982.00" not in {f.value for f in read.figures.values()}


def test_the_same_stub_printed_twice_is_read_once(tmp_path):
    """Employee copy and employer copy agree, so agreement is not a conflict."""
    _, read = _read(tmp_path, "duplicate_employee_and_employer_copy")
    assert read.pages_examined == 2
    assert read.figures[LABEL_GROSS_YTD].value == "42000.00"
    assert read.figures[LABEL_FED_WH_YTD].value == "5460.00"


def test_a_stub_that_names_no_columns_is_not_read_at_all(tmp_path):
    """The case that decides whether this reader guesses. It must not.

    The figures are right there and legible. Reading them would require
    deciding, with nothing to decide on, which column is the year. That is the
    guess, and the guess is what produces a confidently wrong return.
    """
    _, read = _read(tmp_path, "unlabelled_columns")
    for label in (LABEL_GROSS_CURRENT, LABEL_GROSS_YTD, LABEL_FED_WH_CURRENT,
                  LABEL_FED_WH_YTD, LABEL_RETIREMENT_CURRENT, LABEL_RETIREMENT_YTD):
        fig = read.figures[label]
        assert fig.value is None
        assert fig.reason_code == "no_columns"
    assert read.money_seen >= 6, "it must have SEEN the figures and declined them"


def test_a_schedule_that_fights_its_own_dates_is_refused_not_averaged(tmp_path):
    """Two deterministic signals disagreeing is a finding, not a tie to break."""
    from satc.ingest.readers.paystub_columns import IN_WORDS

    _, read = _read(tmp_path, "frequency_conflict")
    fig = read.figures[LABEL_PAY_FREQUENCY]
    assert fig.value is None and fig.reason_code == "frequency_conflict"
    # NOT PINNED TO THE WORDING (S24) — pinned to the property, which is that
    # the refusal names BOTH signals, so the preparer can see what disagrees
    # without going back to the stub to work out what the software meant.
    assert IN_WORDS["monthly"] in fig.problem
    assert IN_WORDS["biweekly"] in fig.problem
    assert "14" in fig.problem


def test_a_schedule_read_from_dates_alone_asks_to_be_confirmed(tmp_path):
    """One signal is an answer; two agreeing is a confirmed answer."""
    _, read = _read(tmp_path, "dates_only_semimonthly")
    fig = read.figures[LABEL_PAY_FREQUENCY]
    assert fig.value == "semimonthly"
    assert fig.reason_code == "confirm"
    assert LABEL_PAY_FREQUENCY in read.to_read_result().uncertain_labels


def test_the_year_to_date_retirement_figure_is_read_rather_than_multiplied(tmp_path):
    """It is printed on the stub, and it was being reconstructed by arithmetic.

    `withholding.intake` computes `ytd_gross - this_period_deferral * elapsed`,
    which is only right for somebody whose deferral never changed all year. A
    rate changed in March, a plan maxed out in October, or a deferral taken from
    a bonus all make that number up.
    """
    _, read = _read(tmp_path, "two_column_plain")
    assert read.figures[LABEL_RETIREMENT_YTD].value == "3000.00"


def test_a_year_to_date_below_the_period_figure_drops_both(tmp_path):
    """A runtime control (S30) on the one case the heading rule cannot see.

    If a stub's headings are printed the wrong way round, every figure is under
    a named column and the reader has no complaint — except that the year's
    total is then smaller than one cheque, which cannot be true.
    """
    from satc.ingest.paystub_corpus import render

    case = next(c for c in load_cases() if c["id"] == "two_column_plain")
    swap = {"r:Current": "r:YTD", "r:YTD": "r:Current"}
    swapped = {**case, "id": "swapped_headings"}
    swapped["pages"] = [{"rows": [[[c[0], swap.get(c[1], c[1])] for c in (row or [])]
                                  for row in case["pages"][0]["rows"]]}]
    read = PaystubColumnReader().read(str(render(swapped, tmp_path)))
    fig = read.figures[LABEL_GROSS_YTD]
    assert fig.value is None, "a year's total smaller than one cheque was accepted"
    assert fig.reason_code == "ytd_below_period"
    assert read.figures[LABEL_GROSS_CURRENT].value is None, \
        "the contradicting pair must both go; nothing here knows which is wrong"


def test_every_read_states_how_much_it_looked_at(tmp_path):
    """S2, on the reader itself rather than on the corpus."""
    _, read = _read(tmp_path, "adp_four_column")
    c = read.census()
    assert c["pages_examined"] == 1 and c["tables_found"] == 2
    assert c["rows_examined"] > 0 and c["money_seen"] > 0
    assert c["fields_read"] + c["fields_refused"] == c["fields_asked"]
    assert "of" in read.summary()


def test_a_read_of_a_page_with_nothing_on_it_says_so_rather_than_passing(tmp_path):
    """S2's corollary: a nil result and a nil look are different reports."""
    import pymupdf

    blank = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(blank))
    doc.close()
    read = PaystubColumnReader().read(str(blank))
    assert read.census()["fields_read"] == 0
    assert read.census()["rows_examined"] == 0


# ---------------------------------------------------------------------------
# What a preparer is shown
# ---------------------------------------------------------------------------

def test_no_refusal_talks_about_the_software(tmp_path):
    """`client-documents/plainspoken.py`'s rule, applied to this surface.

    The firm, 2 September 2026, on a screen that mentioned a file name: *"why
    would that be in our software? what software says stuff like that to its
    user?"* These sentences reach a preparer mid-call.
    """
    import re

    from satc.ingest.readers.paystub_columns import REASONS

    tells = [
        (r"\b[\w-]+\.(?:yaml|yml|py|json)\b", "names a file"),
        (r"`[a-z_]+`", "a code identifier in backticks"),
        (r"\bschema\b|\bregistry\b|\bparser\b|\banchor\b|\bregex\b|\btoken\b",
         "a word about the software rather than about the work"),
        (r"\bdeterministic\b|\bheuristic\b", "our vocabulary, not theirs"),
    ]
    examined = 0
    for code, text in REASONS.items():
        examined += 1
        flat = " ".join(text.split())
        for pattern, why in tells:
            assert not re.search(pattern, flat, re.IGNORECASE), \
                f"{code}: {why}\n  {flat}"
        assert len(flat.split()) <= 45, f"{code} is a paragraph, not a sentence"
    assert examined >= 8, "the refusal wording moved and this stopped reading it"


# ---------------------------------------------------------------------------
# The model boundary
# ---------------------------------------------------------------------------

class _Recorder:
    """A stand-in for a local model that answers everything, confidently."""

    def __init__(self, answer="99999.99"):
        self.asked: list[list[str]] = []
        self.answer = answer

    def __call__(self, labels):
        self.asked.append(list(labels))
        return {label: self.answer for label in labels}


def test_a_model_is_never_asked_about_a_figure_the_software_read(tmp_path):
    """THE BOUNDARY, asserted as an equality rather than a subset.

    A subset assertion ("it only asked about things it could not read") passes
    for a ladder that asks about everything and then discards. The set of
    labels that crossed the wire must EQUAL the set the reader gave up on, so
    widening the ask later fails here instead of quietly costing money.
    """
    _, read = _read(tmp_path, "unlabelled_columns")
    recorder = _Recorder()
    ask(read, page=1, source="OllamaVisionReader[test]", transport=recorder)

    assert len(recorder.asked) == 1
    assert set(recorder.asked[0]) == set(askable(read))
    assert set(recorder.asked[0]) & set(read.to_read_result().labeled_fields) == set()
    assert len(recorder.asked[0]) >= 6, "the boundary was measured against nothing"


def test_a_contradiction_is_never_handed_to_a_model(tmp_path):
    """A model asked to settle a contradiction settles it, and deletes the finding.

    Both pages of `pages_disagree` are legible. The year-to-date figure is not
    unreadable — the stub says two different things, and that is what the
    preparer has to take back to the client.
    """
    _, read = _read(tmp_path, "pages_disagree")
    assert LABEL_GROSS_YTD not in askable(read)
    assert read.figures[LABEL_GROSS_YTD].reason_code not in ASKABLE

    _, freq = _read(tmp_path, "frequency_conflict")
    assert LABEL_PAY_FREQUENCY not in askable(freq)


def test_a_model_is_not_reached_at_all_when_nothing_was_refused(tmp_path):
    """Deterministic first means exhausted, not merely earlier in the file."""
    _, read = _read(tmp_path, "two_column_plain")
    recorder = _Recorder()
    with pytest.raises(ModelBoundary):
        ask(read, page=1, source="x", transport=recorder)
    assert recorder.asked == [], "a model was reached on a stub that read clean"


def test_a_model_answer_can_never_arrive_looking_deterministic(tmp_path):
    """S31, and the half of `test_deterministic_first` this surface was missing.

    `ReadResult.confidence_map` puts every field of a non-deterministic read at
    LOW, and `auto_confirm_high` only writes HIGH — so this assertion is the
    join that keeps a model's reading of a wage figure out of a workpaper with
    nobody looking at it.
    """
    _, read = _read(tmp_path, "unlabelled_columns")
    claims = ask(read, page=1, source="OllamaVisionReader[test]",
                 transport=_Recorder("1,100.00"))
    assert claims, "the fixture answered nothing, so this proved nothing"

    merged = with_claims(read, claims)
    assert merged.deterministic is False
    for claim in claims:
        assert claim.label in merged.uncertain_labels
    assert set(merged.confidence_map().values()) == {"LOW"}
    assert "OllamaVisionReader" in merged.backend


def test_a_model_answer_can_never_replace_a_figure_read_off_the_stub(tmp_path):
    """Structurally, by refusing — not by ordering the merge carefully."""
    _, read = _read(tmp_path, "two_column_plain")
    forged = Claim(label=LABEL_GROSS_CURRENT, value="99999.99", page=1,
                   asked_because="", source="OllamaVisionReader[test]")
    with pytest.raises(ModelBoundary):
        with_claims(read, [forged])


def test_a_clean_read_stays_deterministic_through_the_merge(tmp_path):
    """The other side of the boundary: no claims, no downgrade."""
    _, read = _read(tmp_path, "two_column_plain")
    merged = with_claims(read, [])
    assert merged.deterministic is True
    assert merged.confidence_map()[LABEL_GROSS_CURRENT] == "HIGH"


# ---------------------------------------------------------------------------
# The corpus and the software have to agree about what a field is called
# ---------------------------------------------------------------------------

def test_the_corpus_scores_fields_the_reader_actually_emits(tmp_path):
    """S34 / S7. A corpus keyed on labels that drifted scores nothing and says
    nothing — it just quietly stops finding anything and reports refusals."""
    from satc.ingest.paystub_corpus import _labels
    from satc.ingest.readers.paystub_columns import ROWS

    emitted = {r.current_label for r in ROWS} | {r.ytd_label for r in ROWS}
    emitted.add(LABEL_PAY_FREQUENCY)
    assert set(_labels().values()) == emitted


def test_every_case_declares_where_its_shape_came_from():
    """A layout nobody can source is a layout nobody should trust. `found:` is
    where that is admitted, and an unsourced case has to SAY it is invented."""
    cases = load_cases()
    assert len(cases) >= 18
    for case in cases:
        found = (case.get("found") or "").strip()
        assert found, f"{case['id']} does not say where its shape came from"
        truth = case.get("truth") or {}
        assert truth, f"{case['id']} asserts nothing"
        assert any(v not in (None, REFUSE) for v in truth.values()) or \
            all(v in (None, REFUSE) for v in truth.values())
