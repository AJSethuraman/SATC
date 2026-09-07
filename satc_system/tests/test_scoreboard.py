"""The reading scoreboard — and the one number that must be perfect.

Every other test of the reader used fixtures written by the same hand that wrote
the reader. This measures against documents with values a human verified, and
separates two failures that must never share a number:

    a MISSED read   costs the owner thirty seconds of typing
    a SILENT error  puts a wrong number on a tax return, unseen

Precision at HIGH confidence is a correctness metric. Recall is a convenience
one. The build fails on the first, never on the second.
"""

from __future__ import annotations

import pytest

from satc.ingest.scoreboard import (
    Expectation,
    FieldResult,
    Scoreboard,
    load_corpus,
    score,
)


# --- the scoring logic, which must be right before the numbers mean anything --

def _f(expected, got, confidence="HIGH"):
    return FieldResult(label="doc:Box 1", expected=expected, got=got,
                       confidence=confidence)


def test_a_value_read_correctly_counts_as_correct():
    assert _f("145000", "145000").is_correct


def test_formatting_differences_are_not_errors():
    """"$145,000.00" and "145000" are the same number off the same box.
    Scoring them as a mismatch would drown the signal that matters."""
    assert _f("145000", "$145,000.00").is_correct
    assert _f("145000.00", "145,000").is_correct


def test_a_wrong_value_read_confidently_is_a_SILENT_error():
    """The one that must never happen: accepted with no human looking, wrong."""
    wrong = _f("145000", "154000", confidence="HIGH")
    assert not wrong.is_correct
    assert wrong.is_silent_error


def test_a_wrong_value_read_uncertainly_is_only_a_caught_error():
    """Still wrong — but the owner sees it at the gate. Tolerable."""
    wrong = _f("145000", "154000", confidence="LOW")
    assert not wrong.is_correct
    assert not wrong.is_silent_error


def test_a_missing_value_is_never_an_error():
    missing = _f("145000", "")
    assert missing.is_missing
    assert not missing.is_silent_error


def test_the_bar_is_silent_errors_only():
    board = Scoreboard(documents=1, fields=[
        _f("1", ""),                      # missed
        _f("2", "9", confidence="LOW"),   # wrong but caught
        _f("3", "3"),                     # correct
    ])
    assert board.is_acceptable
    assert len(board.misses) == 1
    assert len(board.caught_errors) == 1

    board.fields.append(_f("4", "9", confidence="HIGH"))
    assert not board.is_acceptable


def test_precision_with_no_denominator_is_unknown_not_perfect():
    """Doctrine rule 10: a metric with nothing behind it is not evidence."""
    board = Scoreboard(documents=1, fields=[_f("1", "", confidence="LOW")])
    assert board.precision_at_high is None
    assert "unmeasured" in board.report()


def test_an_empty_corpus_says_reading_is_unmeasured():
    """It must not read as a pass. Nothing was measured."""
    report = Scoreboard().report()
    assert "UNMEASURED" in report
    assert "plumbing" in report


def test_expectations_can_be_named_the_way_a_person_would():
    """The owner writes expectations looking at a document, not at
    configs/extraction/*.yaml. If only the internal label matched, the
    scoreboard would report reading failures that were really typing
    mismatches — worse than useless."""
    from satc.ingest.scoreboard import _by_any_name

    cfg = {"fields": [{"field_path": "w2.box1_wages",
                       "label": "Box 1 - Wages, tips, other comp",
                       "aliases": ["wages", "box1"]}]}
    found = _by_any_name({"Box 1 - Wages, tips, other comp": "84500"},
                         {"Box 1 - Wages, tips, other comp": "HIGH"}, cfg)
    for spelling in ("Box 1 - Wages, tips, other comp", "box1", "Box 1",
                     "wages", "w2.box1_wages", "Wages, tips, other comp"):
        from satc.ingest.scoreboard import _key

        assert _key(spelling) in found, spelling


# --- against whatever corpus exists on this machine ---------------------------

_CORPUS = load_corpus()
has_corpus = pytest.mark.skipif(
    not _CORPUS, reason="no document corpus on this machine (see corpus/README.md)")


@has_corpus
def test_no_document_is_read_confidently_and_wrongly():
    """THE bar. Everything else in this file exists to make this line meaningful.

    A failure here is not "the reader got something wrong" — it is "the reader
    got something wrong AND nobody was going to look." The fix is to make that
    reader less confident, not to make it smarter.
    """
    board = score(_CORPUS)
    assert board.is_acceptable, "\\n" + board.report()


@has_corpus
def test_the_corpus_actually_exercises_the_reader():
    """A scoreboard that silently measures nothing is worse than none."""
    board = score(_CORPUS)
    assert board.documents > 0
    assert board.fields, "no verified values were scored — expectations may be empty"
