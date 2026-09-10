"""Two ways a corpus can say nothing, and neither may read as a yes.

`dec-coverage`, 10 September 2026 — the firm: **"Both."** Say why the silence is
silence, and build the missing coverage. This file is the first half.

FORGE-OCCAM, REPORTING THE FAILURE, after a real close on the installed plugin:

    "silence is indistinguishable from 'there is nothing to say here.'
     A doer reads it as permission. I nearly did."

THE TWO SILENCES ARE NOT THE SAME AND BOTH WERE UNMARKED.

  1. NOTHING CAME BACK. `consult` returned `""`. Ambiguous between *nothing here
     settles this, go and ask* and *nothing here objects, carry on* — and a doer
     under time pressure reads the second. Closed by `ask.nothing_on_file`: a
     short paper saying what was searched, how big it is, and that it is not
     permission.

  2. SOMETHING CAME BACK AND SETTLED NOTHING. Harder, and it is the one this
     repository cannot close with a threshold. `pool.look` returns its closest
     text for every question that shares any word, and
     `test_a_score_cannot_tell_you_nothing_answers_this.py` measures that NO
     SCORE CUTOFF separates answerable from not-on-file: five of six questions
     with no answer on file outscore the weakest question that has one. So the
     brief says how its passages were chosen, in the brief, where the answerer
     reads it — the disclosure that stops a model doing badly the job the engine
     does properly afterwards.

WHAT THIS FILE DOES NOT CLAIM. That a model obeys the paragraph. Prose policy in
this operation is policy one run in three (LOCAL-LLM-PATTERN rule 6), which is
why the citation rule is an engine check rather than a prompt. This is a
disclosure and not a gate: the gate is `engine.serve`, which still refuses a
citation that does not resolve however confidently it was offered.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

#: A question no tax authority anywhere addresses, and the corpus answers it.
#: NOT INVENTED FOR THIS FILE — it is the case measured while building the pool:
#: 7,384 characters of tax authority came back, more than the real
#: prepaid-insurance question's 5,060.
SHAKESPEARE = "Which sonnet did Shakespeare write about a summer day?"

#: And one sharing no word at all, so `look` returns nothing.
GIBBERISH = "zzqx vvbbnn"


# ── 1 · nothing came back ───────────────────────────────────────────────────

def test_the_empty_result_is_a_document_and_not_an_empty_string():
    assert ask.looked(GIBBERISH) == (), "the fixture retrieves something"
    out = ask.consult(GIBBERISH)
    assert out.strip(), "silence is an empty string again, which reads as a yes"


def test_it_says_what_was_searched_with_numbers():
    """"Nothing found" from a corpus of twelve citations and from one of 785 are
    different findings, and only one of them means the question is unusual."""
    desk = record.load(CORPUS)
    out = ask.consult(GIBBERISH)
    assert str(len(desk.passages)) in out
    assert str(len(desk.sources)) in out


def test_it_says_in_words_that_it_is_not_permission():
    out = ask.consult(GIBBERISH)
    assert "not permission" in out
    assert "quiet yes" in out or "not read this page as a" in out


def test_it_names_the_next_step_rather_than_the_gap():
    """A refusal that names a gap and not the question is a dead end wearing a
    reason code — the same rule the escalation contract states."""
    out = ask.consult(GIBBERISH)
    assert "consult_or_file" in out, "it does not say how to park it"


def test_it_shows_no_authority_at_all():
    """The failure it would be easiest to introduce: printing the nearest
    passages under a heading that says nothing was found."""
    out = ask.consult(GIBBERISH)
    assert "## The authority" not in out
    assert ">" not in out, "a quoted passage reached a page that found none"


def test_the_file_path_still_files_it():
    """`consult_or_file` decides on what the POOL returned, not on the brief's
    length. A caller testing emptiness would now file nothing, ever — which is
    the regression this shape exists to make impossible."""
    import unsupported

    queue = Path(HERE / "runs" / "_silence-spec.md")
    try:
        out, filed = ask.consult_or_file(GIBBERISH, queue=queue)
        assert filed is not None, "a question nothing holds was not parked"
        assert out.strip(), "and the caller still got the explanation"
        assert unsupported.parse(queue.read_text(encoding="utf-8"))
    finally:
        queue.unlink(missing_ok=True)


def test_a_question_the_corpus_does_hold_is_not_filed():
    """The other half. A queue that grew a row per question would be a traffic
    log and the count would stop meaning anything."""
    out, filed = ask.consult_or_file(
        "is a brewery tab a business meal?",
        queue=Path(HERE / "runs" / "_never-written.md"))
    assert filed is None
    assert "## The authority" in out


# ── 2 · something came back and settled nothing ─────────────────────────────

def test_the_corpus_answers_a_question_it_holds_no_authority_on():
    """THE MEASUREMENT, not an argument. If this ever returns nothing, the
    always-answering problem is solved and the disclosure below can be
    reconsidered — until then it is what the brief has instead of a cutoff."""
    found = ask.looked(SHAKESPEARE)
    assert found, (
        "the pool no longer answers a question about Shakespeare out of tax "
        "law. That is a real change — measure it and rewrite this file rather "
        "than deleting the assertion.")
    assert all("CFR" in f.held.citation or "IRS" in f.held.citation
               or "Rev." in f.held.citation or "Pub." in f.held.citation
               for f in found), [f.held.citation for f in found]


def test_the_brief_says_how_its_passages_were_chosen():
    """A result that is not empty and settles nothing is the same misreading as
    silence-as-permission, one step further in."""
    out = ask.consult(SHAKESPEARE)
    assert "chosen by word overlap" in out
    assert "not evidence that it settles anything" in out


def test_it_says_so_on_a_real_question_too():
    """NOT ONLY ON THE ABSURD ONE. A disclosure that appeared only where the
    corpus was obviously wrong would be a disclosure nobody ever reads: the
    questions that matter are the ones where the passages look plausible."""
    for question in ("is a brewery tab a business meal?",
                     "mileage or actual expenses for the van?",
                     "hand tools bought for the trade - deducted or capitalized?"):
        assert "chosen by word overlap" in ask.consult(question), question


def test_it_names_the_escalation_a_reader_should_use_instead():
    out = ask.consult(SHAKESPEARE)
    assert "authority_absent" in out


@pytest.mark.parametrize("question", [SHAKESPEARE, GIBBERISH,
                                      "is a brewery tab a business meal?"])
def test_no_path_out_of_consult_is_empty(question):
    """The property under all of it, checked on every branch: whatever a caller
    asks, what comes back can be read. An empty string is the one answer this
    function may not give."""
    assert ask.consult(question).strip()
