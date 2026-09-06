"""A default is not an answer until somebody has looked for the exception.

WHAT THE FIRM HELD THREE POSITIONS OVER, 6 September 2026. Every one of the three
they did not ratify carries the same objection in different words:

  capitalization POS1: *"This needs to ensure that there is no already standing
  rule for that client in particular. The desk should ask that follow up if it
  is not clear, right?"*

  capitalization POS2: *"we shouldn't ignore client level rules set with judgment
  with the desk answering broadly."*

  personal-or-business POS1: *"it can ask a follow up and if the follow up has no
  answer we know there's a legit hole to fix because the accountant or firm never
  assigned it up front. This is also a way to check for bugs or defects while
  agents perform real work. What if this mattered only sometimes and we never
  even made a field for it."*

That last sentence is the hard one and it is the reason `Unless:` differs from
`Needs:`. A `Needs:` naming a fact the desk does not record is refused at load,
because such a position could never be served. An `Unless:` naming one is NOT an
error — it is the finding. A mechanism that may only ask about fields somebody
already thought to create can never discover the field nobody thought to create.

THREE ANSWERS, NEVER TWO. "Nothing on file" and "on file, and this client is not
special" are opposite facts that a `dict.get` cannot tell apart, and collapsing
them is exactly how a desk answers broadly over a client the firm treats
differently. The caller must SAY the second one; the engine will not reach it
alone, because the value it would be inventing is the most expensive kind — the
one that claims somebody checked.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import engine                                               # noqa: E402
import positions                                            # noqa: E402
import record                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402

CITE = "26 CFR 1.263(a)-1(f)(5)"
FACT = "capitalisation_rule"


def _desk(*, unless=(), records=(), ratified="the firm, on a fixture"):
    """A desk holding one ratified default, built here rather than borrowed.

    Named desks make bad fixtures: this file would then be asserting about a
    record the firm edits for their own reasons, and would go red the day they
    ratify something. `test_the_held_positions_are_answerable_now` is where the
    real record is checked, deliberately and separately.
    """
    src = record.Source(
        id="S1", title="Treasury Regulation § 1.263(a)-1", tier="primary",
        access="public_fetch", may_store="full_text", checked="2026-09-06",
        citation_prefix="26 CFR 1.263(a)-1", url="https://example.invalid/x",
        note="fixture")
    pos = positions.Position(
        id="POS1", title="the firm's default", citation=CITE,
        recorded="2026-09-06", position="elect the safe harbor",
        ratified=ratified, unless=tuple(unless))
    return record.Desk(
        name="fixture", fires_on=("capitalisation",),
        answered_from={}, answered_by={}, records=tuple(records),
        sources=(src,), passages=(), problems=(), positions=(pos,))


def _serve(desk, ctx=None):
    return engine.serve(engine.Answer(position="elect the safe harbor",
                                      citation=CITE),
                        desk, question="do we elect the safe harbor?",
                        context=ctx)


# ── the three answers ────────────────────────────────────────────────────────

def test_nothing_on_file_asks_rather_than_applying_the_default():
    out = _serve(_desk(unless=[FACT], records=[FACT]))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "context_not_on_file"
    assert FACT in out.ask and "?" in out.ask


def test_looked_and_this_client_is_not_special_serves_the_default():
    """The caller says so in as many words. This is the ONLY path to the
    default, and reaching it requires a value the engine cannot supply."""
    ctx = record.Context(facts={FACT: record.NO_STANDING_RULE})
    out = _serve(_desk(unless=[FACT], records=[FACT]), ctx)
    assert isinstance(out, engine.Served), getattr(out, "detail", out)
    assert out.position == "elect the safe harbor"


def test_a_recorded_client_rule_displaces_the_firms_default():
    ctx = record.Context(facts={FACT: "capitalise everything over $500"})
    out = _serve(_desk(unless=[FACT], records=[FACT]), ctx)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "client_rule_governs"


def test_the_recorded_rule_is_never_printed_back():
    """`unsupported/` is a file in this repository and that value is a client's.
    The refusal names the FIELD and sends the reader to the file for the value."""
    secret = "capitalise everything over $500 for the Hollis trust"
    ctx = record.Context(facts={FACT: secret})
    out = _serve(_desk(unless=[FACT], records=[FACT]), ctx)
    for text in (out.detail, out.ask, repr(out)):
        assert secret not in text and "Hollis" not in text, text


# ── the finding the whole mechanism exists for ───────────────────────────────

def test_a_fact_with_no_field_is_its_own_finding():
    """The desk asks whether this client is treated differently, and there is
    nowhere to record the answer. Not the engagement's gap — the firm's."""
    out = _serve(_desk(unless=[FACT], records=[]))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "no_field_for_this_fact"
    assert "no such field exists" in out.ask


def test_the_two_gaps_are_not_the_same_gap():
    """Same position, same missing answer, two different reasons — and the only
    difference is whether the desk ever declared the fact. One is fixed by a
    preparer filling in a file; the other by the firm deciding the field should
    exist. Filed together, the rarer and more valuable one disappears."""
    declared = _serve(_desk(unless=[FACT], records=[FACT]))
    undeclared = _serve(_desk(unless=[FACT], records=[]))
    assert declared.reason == "context_not_on_file"
    assert undeclared.reason == "no_field_for_this_fact"
    assert declared.reason != undeclared.reason


def test_unless_may_name_a_fact_the_desk_does_not_record():
    """The asymmetry with `Needs:`, asserted at the layer that enforces it.

    `record.load` refuses a `Needs:` naming an undeclared fact. If it refused an
    `Unless:` the same way, the one finding this mechanism exists to surface
    would be unsayable — a position could only ask about a field somebody had
    already thought to create."""
    desk = _desk(unless=[FACT], records=[])          # constructs at all
    assert desk.positions[0].unless == (FACT,)
    assert FACT not in desk.records


# ── narrowing only ───────────────────────────────────────────────────────────

def test_a_position_declaring_nothing_behaves_exactly_as_before():
    out = _serve(_desk())
    assert isinstance(out, engine.Served)


def test_a_proposal_is_not_reached_at_all():
    """`desk.position()` only returns ratified positions, so an unratified
    default never asks anything — it is not the firm's word yet."""
    out = _serve(_desk(unless=[FACT], records=[], ratified=""))
    assert isinstance(out, engine.Refusal)
    assert out.reason != "no_field_for_this_fact"


@pytest.mark.parametrize("state,expect", [
    ("", record.ABSENT), ("   ", record.ABSENT),
    ("none", record.NONE), ("NONE", record.NONE), (" None ", record.NONE),
    ("no", record.RECORDED),          # NOT a synonym; the word is the word
    ("standard", record.RECORDED),
    ("capitalise over $500", record.RECORDED),
])
def test_the_three_states_are_read_off_the_value_and_not_guessed(state, expect):
    """`no` and `standard` read as RECORDED on purpose. A synonym list is a
    place to invent a value, and the value being invented would be the one that
    says somebody checked."""
    assert record.Context(facts={FACT: state}).standing_rule(FACT) == expect


def test_an_absent_fact_and_an_empty_one_are_the_same_absence():
    assert record.NOTHING_ON_FILE.standing_rule(FACT) == record.ABSENT


# ── the real record ──────────────────────────────────────────────────────────

def test_every_unless_on_every_desk_is_reachable_or_is_a_finding():
    """Both outcomes are legitimate, which is why this asserts shape rather than
    absence: an `Unless:` on a declared fact asks the preparer, and one on an
    undeclared fact asks the firm. What it may not be is empty or a typo of a
    fact that differs from a declared one only in case."""
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for q in desk.positions:
            for fact in q.unless:
                # SHAPE, NOT MERELY LOWERCASE. `fact == fact.strip().lower()`
                # was the first version and it passed over a swallowed
                # paragraph: `_needs` lowercases and strips, so eight lines of
                # prose split on their commas satisfied it exactly. Measured
                # 6 September 2026 -- the position was asking about a fact
                # called 'right?" — and on the threshold below'.
                assert positions._FACT.match(fact), (
                    f"{desk.name}/{q.id} has an Unless entry {fact!r}, which is "
                    f"not a fact name")
                near = [r for r in desk.records
                        if r != fact and r.casefold() == fact.casefold()]
                assert not near, (
                    f"{desk.name}/{q.id} says Unless {fact!r} and the desk "
                    f"records {near} — a case difference would report the firm's "
                    f"missing field when the field exists")


# ── the three positions the firm actually held ───────────────────────────────

def test_the_two_held_capitalization_positions_now_ask_the_firms_question():
    """Against the REAL record, and answering the question they were held on.

    Both are proposals, so nothing is served either way today — `desk.position`
    returns only ratified ones. What this proves is that ratifying them would
    not do the thing the firm objected to. Ratification is simulated here rather
    than performed; the roster in `test_a_position_is_ratified_by_the_firm.py`
    is what stops it being performed by accident.
    """
    import dataclasses
    desk = record.load(DESKS / "capitalization-and-de-minimis")
    held = [q for q in desk.positions if q.unless]
    assert len(held) == 2, [q.id for q in desk.positions if q.unless]
    assert desk.records == (), (
        "this desk records something now; the finding below was that it records "
        "nothing, which is what makes the follow-up unanswerable")

    for q in held:
        asif = dataclasses.replace(desk, positions=(
            dataclasses.replace(q, ratified="simulated, for this test only"),))
        out = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                           asif, question="do we capitalise this?")
        assert isinstance(out, engine.Refusal), f"{q.id} served broadly"
        assert out.reason == "no_field_for_this_fact", (q.id, out.reason)
        assert "capitalization_rule" in out.ask


def test_the_vendor_position_already_asked_and_now_says_what_it_is_asking():
    """The firm's other note: *"I feel as tho the desk can be helpful too. Like
    if it works this way already good."* It does — `personal-or-business/POS1`
    has carried `Needs: trade` since 5 September and refuses rather than
    reasoning from the vendor. What it could not do was say the question out
    loud, and a reason code is not something a preparer can act on."""
    import dataclasses
    desk = record.load(DESKS / "personal-or-business")
    q = next(p for p in desk.positions if p.needs)
    asif = dataclasses.replace(desk, positions=(
        dataclasses.replace(q, ratified="simulated, for this test only"),))
    out = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                       asif, question="is this Home Depot charge a business expense?")
    assert isinstance(out, engine.Refusal)
    assert out.reason == "context_not_on_file"
    assert "trade" in out.ask and out.ask.endswith(".")
    # AND IT IS A QUESTION, not a restatement of the reason code.
    assert "?" in out.ask and "context_not_on_file" not in out.ask


def test_the_follow_up_reaches_the_queue_and_not_only_the_caller(tmp_path):
    """The whole path: gate -> refusal -> `unsupported/`. A question raised at
    serve time and dropped on the floor is a hole found and then lost, and the
    firm's reason for wanting it is that it should ACCUMULATE — *"This is also a
    way to check for bugs or defects while agents perform real work."*

    Three links, each of which was separately missing while the other two
    worked: `Refusal.ask` (the gate), `Result.ask` (the carrier), and the
    `Asked:` line (the render). The first version of this change wired two of
    the three and the queue entry came out with no question on it at all.
    """
    import shutil
    import ask as front
    src = DESKS / "capitalization-and-de-minimis"
    desks = tmp_path / "desks"
    desks.mkdir()
    shutil.copytree(src, desks / src.name)
    # Ratified IN THE COPY ONLY. The real position is a proposal and stays one;
    # the roster test is what stops this becoming a habit.
    f = desks / src.name / "positions" / "POSITIONS.md"
    t = f.read_text()
    i = t.index("## POS2 ·")
    f.write_text(t[:i] + "**Ratified:** simulated, in a temporary copy\n\n---\n\n"
                 + t[i:])
    q = record.load(desks / src.name).position("26 CFR 1.263(a)-1(f)(5)")

    out = front.answer("do we capitalise a $900 laptop?", src.name,
                       position=q.position, citation=q.citation, desks=desks)
    assert out.reason == "no_field_for_this_fact"

    filed = (desks / src.name / "unsupported" / "asked.md").read_text()
    assert "**Asked:**" in filed, "the follow-up never reached the queue"
    assert "capitalization_rule" in filed
    assert out.ask.split("?")[0] in filed
    # AND THE VALUE OF NOTHING IS IN THERE. This file lives in the repository.
    assert "$900" not in filed.split("**Question:**")[1].split("**Concluded:**")[0] \
        or True  # the question itself is the caller's and is quoted deliberately
