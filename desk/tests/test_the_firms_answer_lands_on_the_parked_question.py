"""The other half of the round trip: an answer closes a parked question.

THE OUTWARD HALF WAS BUILT FIRST AND THAT IS WHAT EXPOSED THIS. `notifying.line`
pushes the firm a parked question within seconds of it being parked -- proved
live on 8 September, a push reached their phone -- and their reply had nowhere
to land. The entry stayed open however fast they answered, and `tools/holes.py`
went on reporting it as a hole. A queue that can only grow is one nobody
finishes reading.

WHAT THIS IS NOT. Recording an answer is not ratifying a position. A position is
the firm's standing rule: it lives on a desk in `POSITIONS.md`, it changes what
the engine serves to everybody, and it enters the record only through a pull
request the firm merges. `settle` closes one question in one queue and changes
no desk's authority -- which is exactly what makes it safe to write straight
from a chat message.
"""
from __future__ import annotations

import pytest

import unsupported
from record import RecordError


def _queue(tmp_path, *questions):
    q = tmp_path / "CLOSE.md"
    for text in questions:
        existing = unsupported.parse(q.read_text(encoding="utf-8")) if q.exists() else []
        unsupported.append(q, unsupported.from_question(
            text, why="authority_absent", existing=existing))
    return q


def test_an_answer_closes_the_question_and_is_kept_verbatim(tmp_path):
    q = _queue(tmp_path, "are unidentified deposits gross receipts?")
    words = "Income unless traced to a loan or an owner contribution."
    unsupported.settle(q, "U1", words)
    entry = unsupported.parse(q.read_text(encoding="utf-8"))[0]
    assert entry.settled and entry.answer == words


def test_settling_one_entry_does_not_delete_it(tmp_path):
    """THE BUG THIS FILE WAS WRITTEN AGAINST, and it destroyed data silently.

    The first `settle` wrote `_refreshed("\\n".join(...))`. `_refreshed` takes
    WHOLE-FILE text: it finds the first "\\n## " and keeps everything from there.
    Handed bare entries, the first has no newline in front of it, so the search
    landed on the SECOND entry's heading and everything before it was thrown
    away. Settling U1 deleted U1 — the answer and the question both. No error,
    no warning; found only by running it and reading the file back.
    """
    q = _queue(tmp_path, "first question", "second question", "third question")
    unsupported.settle(q, "U1", "an answer")
    assert [e.id for e in unsupported.parse(q.read_text(encoding="utf-8"))] == ["U1", "U2", "U3"]


def test_settling_the_last_entry_keeps_the_others_too(tmp_path):
    q = _queue(tmp_path, "first question", "second question", "third question")
    unsupported.settle(q, "U3", "an answer")
    ids = [e.id for e in unsupported.parse(q.read_text(encoding="utf-8"))]
    assert ids == ["U1", "U2", "U3"]


def test_the_others_are_untouched_by_a_settlement(tmp_path):
    q = _queue(tmp_path, "first question", "second question")
    before = {e.id: e for e in unsupported.parse(q.read_text(encoding="utf-8"))}
    unsupported.settle(q, "U1", "an answer")
    after = {e.id: e for e in unsupported.parse(q.read_text(encoding="utf-8"))}
    assert after["U2"] == before["U2"]


def test_open_questions_drops_the_answered_but_the_file_keeps_them(tmp_path):
    """The queue is the record of what was ASKED, not only of what is left."""
    q = _queue(tmp_path, "first question", "second question")
    unsupported.settle(q, "U1", "an answer")
    assert [e.id for e in unsupported.open_questions(q)] == ["U2"]
    assert len(unsupported.parse(q.read_text(encoding="utf-8"))) == 2


def test_a_date_is_the_flag_so_a_short_answer_still_counts(tmp_path):
    """An answer of "no" is a real answer. Keying off the text would leave the
    shortest and most decisive answers looking open forever."""
    q = _queue(tmp_path, "a question")
    unsupported.settle(q, "U1", "No.")
    assert unsupported.parse(q.read_text(encoding="utf-8"))[0].settled


def test_an_unknown_id_refuses_and_says_what_the_queue_holds(tmp_path):
    q = _queue(tmp_path, "a question")
    with pytest.raises(RecordError) as e:
        unsupported.settle(q, "U9", "an answer")
    assert "U1" in str(e.value)


def test_an_empty_answer_refuses(tmp_path):
    """A settled entry with nothing in it reads as answered and tells the next
    reader nothing — worse than leaving it open."""
    q = _queue(tmp_path, "a question")
    with pytest.raises(RecordError):
        unsupported.settle(q, "U1", "   ")


def test_answering_twice_refuses_rather_than_choosing(tmp_path):
    """The second message might be a correction or a repeat. This cannot tell
    them apart, so a person does."""
    q = _queue(tmp_path, "a question")
    unsupported.settle(q, "U1", "the first answer")
    with pytest.raises(RecordError) as e:
        unsupported.settle(q, "U1", "a different answer")
    assert "already answered" in str(e.value)
    assert unsupported.parse(q.read_text(encoding="utf-8"))[0].answer == "the first answer"


def test_an_answer_that_looks_like_the_file_format_cannot_break_it(tmp_path):
    """The firm's answer arrives from a chat message, which makes it the most
    arbitrary text in the file. `render`'s docstring records four separate
    escaping failures in this format; this is the newest field to try it on."""
    q = _queue(tmp_path, "a question", "another question")
    nasty = "## U99 · not an entry\n**Failed because:** nonsense\n---"
    unsupported.settle(q, "U1", nasty)
    entries = unsupported.parse(q.read_text(encoding="utf-8"))
    assert [e.id for e in entries] == ["U1", "U2"]
    assert entries[0].answer == nasty


def test_settling_a_queue_that_does_not_exist_refuses(tmp_path):
    with pytest.raises(RecordError):
        unsupported.settle(tmp_path / "nothing.md", "U1", "an answer")
