"""A fact with nowhere to live becomes one decision, sent to the firm.

`dec-fields`, 10 September 2026. Two desks asked for a fact, were given it, and
had nowhere to put it. `no_field_for_this_fact` fired correctly both times. The
docket offered two options — audit every desk and bring back a list, or add
fields one refusal at a time — and the firm refused both, because the framing
was the survey they keep refusing:

    "I have said before I want the desk to propose fields that are clearly
     holes. I can sign off on them in the same way as a position. Like if
     something is missing and we have to have it then we would make that the
     plan. I don't want the list, I want this part of the process -- it sends me
     the notification or whatever saying there's something for me to decide
     which in this case would be 'do we add this field' I think."

THE CHANNEL ALREADY EXISTED AND NOTHING HAD EVER PUT ANYTHING IN IT. This is the
part worth reading. `Unsupported` carries `needs_field` and `asked_by` — the
fact, and the position that asked for it. `unsupported.from_refusal` reads them
off `result.fact` and `result.by_position`. The renderer prints them, the parser
reads them back, and `tools/holes.py` reports on them.

`ask.answer` built an `engine.Result` to hand to `from_refusal`, and
**`engine.Result` has neither field**. So every `no_field_for_this_fact` ever
filed on the live path landed with both empty: a field request naming no field,
with no chain back to the position behind it — which is precisely the condition
the firm approved field requests under (*"that seems low stakes and required and
i would approve it fairly easily"*, on the ask arriving with which position
wanted it).

Five pieces of a mechanism, each correct, connected by a sixth that dropped the
payload. Found by filing one and reading the file back, which is the only way it
could have been found — nothing about it fails, and every count it feeds stays
green.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import engine                                               # noqa: E402
import notifying                                            # noqa: E402
import record                                               # noqa: E402
import unsupported                                          # noqa: E402
from conftest import CORPUS                                 # noqa: E402


@pytest.fixture
def undeclared(tmp_path):
    """The corpus with one declared fact taken off its `Records:` line.

    CONSTRUCTED, BECAUSE THE RECORD IS CORRECT. Every fact a position needs is
    declared today — `record.load` refuses a record where one is not — so the
    case this fires on cannot be found on disk and must be built. The position
    is left alone: what is removed is the FIELD, which is exactly the hole the
    firm is being asked to fill.
    """
    dst = tmp_path / "corpus"
    shutil.copytree(CORPUS, dst)
    f = dst / "SUBJECTS.md"
    text = f.read_text(encoding="utf-8")
    assert "capitalization_rule" in text, "the fixture's premise moved"
    f.write_text(re.sub(r"^\*\*Records:\*\*.*?(?=\n\n|\n\*\*|\Z)",
                        "**Records:** trade, taxpayer", text,
                        flags=re.M | re.S), encoding="utf-8")
    desk = record.load(dst)
    assert "capitalization_rule" not in desk.records, "the fixture did not bite"
    return dst, desk


def _default_needing(desk, fact):
    return next(q for q in desk.positions
                if not q.proposed and fact in (q.unless or ()))


def _file_one(corpus, desk):
    position = _default_needing(desk, "capitalization_rule")
    out = ask.answer("what is our threshold", position=position.position,
                     citation=position.citation, corpus=corpus, keep=True)
    assert isinstance(out, engine.Refusal), "it served an answer needing a field"
    assert out.reason == "no_field_for_this_fact", out.reason
    entries = unsupported.parse(
        (corpus / "unsupported" / "asked.md").read_text(encoding="utf-8"))
    return out, entries[-1], position


# ── the chain arrives ───────────────────────────────────────────────────────

def test_the_refusal_names_the_fact_and_the_position(undeclared):
    """The engine's half, which was never the broken one."""
    out, _entry, position = _file_one(*undeclared)
    assert out.fact == "capitalization_rule"
    assert out.by_position == position.id


def test_the_filed_entry_carries_both(undeclared):
    """THE BUG, AS A TEST. Both were empty on every entry ever filed, and
    nothing anywhere went red."""
    _out, entry, position = _file_one(*undeclared)
    assert entry.needs_field == "capitalization_rule", (
        "the entry names no field, so it is a field request the firm cannot "
        "act on and `tools/holes.py` cannot report")
    assert entry.asked_by == position.id, (
        "the entry has no chain back to the position that wanted the field, "
        "and that chain is the condition the firm approved these under")


def test_both_or_neither_survives_the_round_trip(undeclared):
    """`needs_field` never appears without `asked_by`. A half-filled pair is a
    field request with no chain, which is the shape this file is about."""
    corpus, _ = undeclared
    _out, entry, _ = _file_one(*undeclared)
    text = (corpus / "unsupported" / "asked.md").read_text(encoding="utf-8")
    assert "**Needs field:** capitalization_rule" in text
    assert f"**Asked by:** {entry.asked_by}" in text
    for e in unsupported.parse(text):
        assert bool(e.needs_field) == bool(e.asked_by), (
            f"{e.id} has one half of the pair and not the other")


def test_a_refusal_that_is_not_about_a_field_carries_neither(undeclared):
    """The narrowing. If `from_refusal` started copying these off every
    refusal, every entry would read as a field request and the count that is
    supposed to mean something would stop meaning it."""
    corpus, desk = undeclared
    out = ask.answer("what is our threshold", position="something else entirely",
                     citation="26 CFR 9.9(z)(z)", corpus=corpus, keep=True)
    assert isinstance(out, engine.Refusal)
    assert out.reason != "no_field_for_this_fact"
    entry = unsupported.parse(
        (corpus / "unsupported" / "asked.md").read_text(encoding="utf-8"))[-1]
    assert entry.needs_field == "" and entry.asked_by == ""


# ── and it reaches the firm as a decision ───────────────────────────────────

def test_the_notification_says_what_there_is_to_decide(undeclared):
    """*"it sends me the notification [...] saying there's something for me to
    decide which in this case would be 'do we add this field'"*.

    "Desk parked: what is our threshold — no_field_for_this_fact" says a
    question stalled. The firm's decision is a different thing and gets
    different words."""
    _out, entry, position = _file_one(*undeclared)
    said = notifying.for_entry(entry)
    assert said.startswith("Desk proposes"), said
    assert "add a field for capitalization_rule?" in said
    assert position.id in said, "which position needs it is half the ask"
    assert entry.id in said, "the firm cannot answer a notification with no ref"


def test_an_ordinary_parked_question_is_unchanged(undeclared):
    """The other half: a question waiting on an answer must not start reading
    as a decision waiting on a signature."""
    corpus, _ = undeclared
    _out, filed = ask.consult_or_file(
        "zzqx vvbbnn", queue=corpus / "unfiled" / "q.md", corpus=corpus)
    assert filed is not None
    said = notifying.for_entry(filed)
    assert said.startswith("Desk parked"), said
    assert "add a field" not in said


def test_the_notification_is_still_checked_for_pii(undeclared):
    """The new branch composes its own text, so it must go through the same
    door. A field name comes from a position's `Unless:` line and can never
    carry a client's details — but a branch that skipped the check would be one
    nobody notices until something else writes to that field."""
    _out, entry, _ = _file_one(*undeclared)
    import dataclasses

    leaky = dataclasses.replace(entry, needs_field="123-45-6789")
    with pytest.raises(ValueError, match="refusing to send"):
        notifying.for_entry(leaky)


# ── it is not a survey ──────────────────────────────────────────────────────

def test_one_refusal_files_one_decision_and_not_an_audit(undeclared):
    """*"I don't want the list, I want this part of the process."*

    A field request arrives because a real question hit a real hole, one at a
    time. Nothing here enumerates what else might be missing, and the count of
    entries is the count of times the work actually stopped.
    """
    corpus, desk = undeclared
    _file_one(corpus, desk)
    entries = unsupported.parse(
        (corpus / "unsupported" / "asked.md").read_text(encoding="utf-8"))
    fields = [e for e in entries if e.needs_field]
    assert len(fields) == 1, (
        f"{len(fields)} field requests from one refusal. This channel fires "
        f"where the work stopped; anything that enumerates candidates is the "
        f"survey the firm refused.")
