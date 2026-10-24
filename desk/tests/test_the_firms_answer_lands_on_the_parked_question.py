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

from pathlib import Path

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


# --- reading the reply ------------------------------------------------------
# The firm, 9 September 2026, asked whether they could reply to a session from a
# phone notification: "Of course I can, that's how I'm talking to you now." So
# there is no transport to build. This is the whole remaining seam, and it is in
# the engine rather than in skill prose for the reason the README gives about
# the citation rule.

import notifying


def test_a_reply_names_the_entry_it_answers():
    assert notifying.reply_in("U1 income unless traced to a loan") == (
        "U1", "U1 income unless traced to a loan")


def test_the_answer_is_their_message_verbatim():
    """THE CORRECTION THIS FUNCTION WAS REWRITTEN FOR. The first version cut the
    reference out and tidied around it, so *"For [U1]: treat it as income."*
    came back as *"For [ ]: treat it as income."* — an empty bracket that was
    never typed — and a message quoting the notification back had words removed
    from the middle. The record's job is to show what the firm said; a stray
    "U1" in a sentence is truthful where a hole in it is not."""
    said = "For [U1]: treat it as income."
    uid, answer = notifying.reply_in(said)
    assert (uid, answer) == ("U1", said)


def test_the_reference_is_found_however_it_is_written():
    for said in ("U1 yes", "[U1] yes", "u1 yes", "for u1, yes", "(U1) yes"):
        assert notifying.reply_in(said)[0] == "U1", said


def test_a_message_that_answers_nothing_is_not_an_answer():
    """Most messages a desk session gets are not replies to parked questions. A
    function that always found one would settle an entry with a passing remark."""
    for said in ("looks good, thanks", "run the close again", "", "   "):
        assert notifying.reply_in(said) == ("", "")


def test_two_references_refuse_rather_than_choose():
    """"U1 and U2 are both income" is a real thing a person types, and the words
    belong to both entries and to neither. The desk asks instead of filing half
    a sentence twice."""
    assert notifying.reply_in("U1 and U2 are both income") == ("", "")


def test_a_bare_reference_carries_no_decision():
    for said in ("[U1]", "U1", "Desk parked: [U1]", "U1 —"):
        assert notifying.reply_in(said) == ("", ""), said


def test_the_quoted_notification_alone_is_not_an_answer():
    """A QUESTION IS NOT AN ANSWER TO ITSELF, and a test caught that this needs
    `sent` to know. Tapping the notification quotes the line, and the line
    carries the QUESTION — so an echo with nothing added read as substance to a
    check that only stripped the reference and the label."""
    echoed = notifying.line("are unidentified deposits gross receipts?", ref="U1")
    assert notifying.reply_in(echoed, sent=echoed) == ("", "")


def test_an_echo_with_a_decision_added_is_an_answer():
    echoed = notifying.line("are unidentified deposits gross receipts?", ref="U1")
    uid, answer = notifying.reply_in(echoed + " — income unless traced", sent=echoed)
    assert uid == "U1" and "income unless traced" in answer


def test_a_rewrapped_echo_is_still_an_echo():
    """Compared word by word rather than as a substring: a quoted notification
    comes back re-wrapped and re-punctuated, so `sent in text` misses it."""
    echoed = notifying.line("are unidentified deposits gross receipts?", ref="U1")
    mangled = "Desk parked:  are unidentified deposits gross receipts?\n[U1]"
    assert notifying.reply_in(mangled, sent=echoed) == ("", "")


def test_a_plain_answer_is_unaffected_by_passing_sent():
    echoed = notifying.line("are unidentified deposits gross receipts?", ref="U1")
    assert notifying.reply_in("U1 income unless traced", sent=echoed) == (
        "U1", "U1 income unless traced")


def test_a_reply_reaches_settle_end_to_end(tmp_path):
    """The round trip in one test: parked, notified, replied, closed."""
    q = _queue(tmp_path, "are unidentified deposits gross receipts?")
    entry = unsupported.parse(q.read_text(encoding="utf-8"))[0]
    sent = notifying.for_entry(entry)
    assert entry.id in sent

    uid, answer = notifying.reply_in(f"{entry.id} income unless it traces to a loan")
    assert uid == entry.id
    unsupported.settle(q, uid, answer)

    assert unsupported.open_questions(q) == []
    assert "income unless it traces to a loan" in \
        unsupported.parse(q.read_text(encoding="utf-8"))[0].answer


def test_the_answer_keeps_markdown_the_firm_typed():
    """VERBATIM MEANT VERBATIM, and it did not. `reply_in` returned
    `_flatten(text)` — a helper written to decide what a NOTIFICATION may carry,
    which strips `*`, backticks, `#` and `>` because a notification renders no
    markdown. An answer is not a notification, so
    "U1 use **income** and `loan`" was stored as "U1 use income and loan".
    A quieter version of the mangling this function was already rewritten once
    to stop, and it contradicted the word "verbatim" in its own docstring."""
    said = "U1 use **income** and `loan`"
    assert notifying.reply_in(said) == ("U1", said)


def test_a_multi_line_answer_keeps_its_lines():
    said = "U1 income.\nUnless it traces to a loan."
    uid, answer = notifying.reply_in(said)
    assert uid == "U1" and answer == said


def _holes():
    import sys
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "tools"))
    import holes
    return holes


def test_the_report_stops_naming_an_answered_question(tmp_path, monkeypatch):
    """`settle` closes an entry and the entry STAYS in the file, so the reader
    has to filter what the store deliberately does not. Without this the report
    went on naming a hole the firm had already answered — the whole thing
    settling was built to stop. Caught by a review."""
    monkeypatch.setenv(unsupported.QUEUE_ENV, str(tmp_path / "CLOSE.md"))
    q = _queue(tmp_path, "first question", "second question")
    holes = _holes()
    before = holes.read([q])
    unsupported.settle(q, "U1", "an answer")
    after = holes.read([q])
    assert len(before) - len(after) == 1, (
        "settling an entry did not remove it from the report")
