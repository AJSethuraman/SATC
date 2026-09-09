"""A value cannot impersonate the field that holds it.

FOUND BY A REVIEW, on the morning the firm was about to run a live close against
this code. `record._inline` searched the WHOLE block for `**Label:**`, so the
same characters appearing inside a value were indistinguishable from the field.

WHAT IT COST, WHICH IS EVERYTHING RATHER THAN ONE ROW. A parked question reading
*"Should the report say **Answered:** here?"* was read as the `Answered` field,
`here?` reached the date parser, and the RecordError that raised made the ENTIRE
FILE unreadable: every other parked question with it, `holes.py` blind,
`settle` unable to load, and nothing naming the sentence that did it.

IT WAS NEVER ABOUT ONE FIELD. Every value in these files is arbitrary text from
outside — a question is the caller's, an answer is the firm's, a conclusion is a
model's. `Failed because`, `Recorded` and the rest were shadowable the same way;
nobody had tried.

THE LINE START IS NOT THE TEST, and that is why the fix is not a `^`. `render`
writes `**Failed because:** x · **Recorded:** y`, so the second field is
genuinely mid-line. What separates a field from a look-alike is that every
free-form value goes through `_quote`, which prefixes `> `.
"""
from __future__ import annotations

import pytest

import unsupported
from record import RecordError


def _queue(tmp_path, question):
    q = tmp_path / "CLOSE.md"
    unsupported.append(q, unsupported.from_question(
        question, why="authority_absent", existing=[]))
    return q


def test_a_question_naming_the_answered_field_is_still_readable(tmp_path):
    q = _queue(tmp_path, "Should the report say **Answered:** here?")
    entries = unsupported.parse(q.read_text(encoding="utf-8"))
    assert [e.id for e in entries] == ["U1"]
    assert not entries[0].settled, (
        "a question that MENTIONS the field is not an entry the firm answered")


def test_the_rest_of_the_queue_survives_such_a_question(tmp_path):
    """The failure was total, not local: one sentence took every entry with it."""
    q = tmp_path / "CLOSE.md"
    for text in ("an ordinary question",
                 "Should the report say **Answered:** here?",
                 "another ordinary question"):
        unsupported.append(q, unsupported.from_question(
            text, why="authority_absent",
            existing=unsupported.parse(q.read_text(encoding="utf-8"))
            if q.exists() else []))
    assert [e.id for e in unsupported.parse(q.read_text(encoding="utf-8"))] == \
        ["U1", "U2", "U3"]


def test_an_answer_naming_a_field_cannot_break_the_entry(tmp_path):
    """The answer is the firm's own words, typed into a chat message — the most
    arbitrary text in the file."""
    q = _queue(tmp_path, "a question")
    unsupported.settle(q, "U1", "yes — and **Failed because:** cannot break it")
    entry = unsupported.parse(q.read_text(encoding="utf-8"))[0]
    assert entry.settled
    assert entry.failed_because == "authority_absent", (
        "a look-alike inside the answer was read as the real field")


def test_a_field_after_the_separator_is_still_found(tmp_path):
    """The reason the fix is not an anchor: `Recorded` is genuinely mid-line."""
    q = _queue(tmp_path, "a question")
    entry = unsupported.parse(q.read_text(encoding="utf-8"))[0]
    assert entry.recorded and entry.failed_because == "authority_absent"


def test_a_missing_field_still_refuses(tmp_path):
    """The guard narrows what counts as a field; it must not invent one."""
    q = _queue(tmp_path, "a question")
    text = q.read_text(encoding="utf-8").replace("**Failed because:**", "**Was:**")
    with pytest.raises(RecordError):
        unsupported.parse(text)
