"""The last leg of V1: the asker receives an ANSWER, not a paragraph.

`desk/relay.py:5-9`, the firm's own criterion: *"the final check for this for V1
will be to have Forge - Occam install the new plugin we are designing and run a
close from start to finish on Sarcia Services [...] this implies that the skill
is able to call for questions and **receive back answers** from Forge - Desk"*

WHAT THE RECEIVING SIDE WAS, UNTIL NOW. `reply_opens` — a boolean saying *this
is the answer to that question*, and nothing saying what it was. Everything
after that was a person reading prose. The reply is prose on purpose:
`Served.__str__` is written for a human and is the one channel that reaches an
agent whose SKILL.md is four releases stale. That is right, and it is not the
same as the asker having no way to tell a refusal from an answer.

THIS IS `dec-coverage` ON THE RETURN LEG. Occam on the consult leg: *"silence is
indistinguishable from 'there is nothing to say here.' A doer reads it as
permission. I nearly did."* A refusal read as an answer is that same mistake one
step later and under more pressure, because by then the doer is holding
something that looks like a reply. And it has already happened once in the small:
on 8 September a doer went looking for `passage` on a refusal — *"a doer looking
for `passage` in a refusal will not find it and has been given no signal that is
expected."*

NO SECOND WIRE PROTOCOL. `relay.read` parses the rendering the envelope already
instructs the answerer to send (`print(out)` in full), so there is nothing to
keep in step, and an answerer on a stale skill still produces something readable
because printing the object IS the rendering.

MEASURED, NOT ASSERTED: every one of the record's 98 recorded problems is served
or refused, rendered, and read back below. Nothing is misread.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import engine                                                # noqa: E402
import record                                                # noqa: E402
import relay                                                 # noqa: E402
from conftest import CORPUS                                  # noqa: E402

ME = "session_01M1pBzTxE9u2xD6d8Yz57dV"


@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


def _answer(desk, pid):
    p = next(x for x in desk.problems if x.id == pid)
    return p, engine.serve(
        engine.Answer(position=p.answer, citation=p.citation),
        desk, question=p.facts, context=p.context)


# ── the whole record, through the wire and back ─────────────────────────────

def test_every_recorded_answer_survives_the_round_trip(desk):
    """THE DENOMINATOR IS THE WHOLE RECORD, not a handful of examples. A reader
    built against three fixtures is a reader that works on three fixtures."""
    served = refused = 0
    for p in desk.problems:
        out = engine.serve(
            engine.Answer(position=p.answer, citation=p.citation),
            desk, question=p.facts, context=p.context)
        got = relay.read(f"DESK ANSWER abc123def456\n\n{out}")
        if isinstance(out, engine.Served):
            served += 1
            assert got.answered, f"{p.id}: a served answer read as a refusal"
            assert got.citation == out.citation, p.id
            assert got.binding == out.binding, p.id
            assert got.tier and got.checked, p.id
        else:
            refused += 1
            assert not got.answered, f"{p.id}: a refusal read as an answer"
            assert got.reason == out.reason, p.id
            assert not got.citation, (
                f"{p.id}: a refusal came back with a citation. A refusal cites "
                f"nothing — that is what makes it a refusal")
    assert served + refused == len(desk.problems) == 98
    assert refused >= 1, (
        "nothing on the record refuses any more, so the refusal half of this "
        "is proved by nothing. Build one rather than deleting the assertion.")


def test_a_refusal_hands_back_its_reason_and_its_follow_up(desk):
    """A refusal that names a gap and not a question is a dead end wearing a
    reason code. `ask` is the part a preparer can act on."""
    _, out = _answer(desk, "RW7")
    assert isinstance(out, engine.Refusal)
    got = relay.read(f"DESK ANSWER abc123\n\n{out}")
    assert not got.answered
    assert got.reason == "authority_permits_choice"
    assert got.ask and got.ask == out.ask.strip()


def test_a_guidance_answer_is_answered_but_not_usable_unaided(desk):
    """`dec-guidance` decided these serve, MARKED. The mark means a person reads
    the caveat before it is relied on, so `usable` must not be true of them —
    and `answered` must not be false either, because it is a real answer."""
    _, out = _answer(desk, "TP1")
    assert isinstance(out, engine.Served) and not out.binding
    got = relay.read(f"DESK ANSWER abc123\n\n{out}")
    assert got.answered and not got.binding
    assert not got.usable
    assert got.tier == "secondary"


def test_a_binding_answer_is_usable(desk):
    binding = next(
        p for p in desk.problems
        if isinstance(o := engine.serve(
            engine.Answer(position=p.answer, citation=p.citation),
            desk, question=p.facts, context=p.context), engine.Served)
        and o.binding)
    _, out = _answer(desk, binding.id)
    assert relay.read(f"DESK ANSWER abc\n\n{out}").usable


# ── and it refuses to guess, which is the whole safety property ─────────────

def test_an_empty_reply_is_not_a_refusal(desk):
    """A delivery that did not happen and a desk that said no call for opposite
    next steps. `relay`'s own envelope says a 200 from `fire_trigger` is not
    delivery — so silence here means nothing arrived, not that nothing was
    held."""
    for body in ("", "   \n\n  "):
        with pytest.raises(relay.RelayError, match="not a refusal"):
            relay.read(body)


def test_something_it_cannot_place_raises_rather_than_reading_as_a_no(desk):
    """THE DIRECTION OF THE FAILURE IS THE POINT. Returning `answered=False`
    here would look cautious and would silently throw away a mangled ANSWER —
    and a doer told "the desk refused" does not go back and check."""
    with pytest.raises(relay.RelayError, match="neither"):
        relay.read("DESK ANSWER abc123\n\nyeah I think that's fine, deduct it")


def test_a_reply_carrying_both_is_handed_to_a_person(desk):
    """Two replies in one message, or an answer quoting a refusal. Picking the
    first match would prefer whichever the author happened to type first."""
    _, served = _answer(desk, "TP1")
    _, refused = _answer(desk, "RW7")
    with pytest.raises(relay.RelayError, match="BOTH"):
        relay.read(f"DESK ANSWER abc\n\n{refused}\n\n---\n\n{served}")


def test_the_hand_back_fallback_still_reads(desk):
    """THE PATH OCCAM ACTUALLY TOOK. On 9 September they had neither
    `create_trigger` nor `fire_trigger`, ran each desk as a subagent and handed
    the answer back as a report — and the envelope now names that fallback. An
    answer that arrives wrapped in a covering sentence is still the answer."""
    _, out = _answer(desk, "TP1")
    wrapped = (
        "The relay tools were unavailable in my toolset, so this is coming "
        "back to you by hand rather than through a trigger.\n\n"
        f"DESK ANSWER abc123\n\n{out}\n\n"
        "Let me know if you need the passage in full.")
    got = relay.read(wrapped)
    assert got.answered and got.citation == out.citation


# ── the rendering is a person's, and this must not start owning it ──────────

def test_the_reader_keys_on_what_the_rendering_already_guarantees(desk):
    """`Served.__str__`'s docstring is explicit that the rendering exists to
    reach a person, and a stale agent, through the object rather than the skill.
    A parser that made the rendering harder to read would invert that. These are
    the two anchors it uses, asserted against the real output so a change to
    either breaks here rather than in the field."""
    _, served = _answer(desk, "TP1")
    _, refused = _answer(desk, "RW7")
    assert str(refused).startswith("THE DESK DID NOT ANSWER — ")
    lines = str(served).split("\n")
    i = next(n for n, l in enumerate(lines) if l.startswith("    ") and "·" not in l)
    assert lines[i + 1].startswith("    ") and " · confirmed " in lines[i + 1]
