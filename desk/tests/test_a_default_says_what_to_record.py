"""The firm's default is recorded by a person, and the refusal says what to write.

`dec-caprule`, 14 September 2026 — the firm, on the eighth docket: **"Record it
at intake"**, with the note that is the actual decision:

    "The firm's threshold for our clients if non specified will be based on IRS
     rules for simplicity."

THE MOST EXPENSIVE ITEM ON THAT DOCKET. POS1 and POS2 both carry
`Unless: capitalization_rule` and the field was blank on every client, so both
refused `context_not_on_file` on every engagement — correctly: *"a default
applied without looking is not a default"*. Two of the firm's twenty ratified
positions had been unreachable since 5 September.

WHAT WAS **NOT** BUILT, and it was on the card: a silent default in the code.
The firm declined it. An engine supplying this value itself would be inventing
the one fact that says somebody checked, and *never invent a value* is the
principle the refusal rests on. So the refusal STANDS; it stops being a dead end.

THE THREE STATES, AND THE FIRST DRAFT OF THIS GOT THEM WRONG. The `Default:`
line first said to record the ceiling — and recording a figure is how a preparer
tells the desk this client is DIFFERENT. Found by running it rather than
reasoning about it:

    ''                          -> Refusal   context_not_on_file
    'none'                      -> SERVED    (the firm's threshold applies)
    'the IRS ceiling, $2,500'   -> Refusal   client_rule_governs
    '$500 per item'             -> Refusal   client_rule_governs

The middle one is the firm's answer. `none` says somebody looked and there is no
client-level rule; POS2 then supplies the number itself.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import conftest                                             # noqa: E402
import engine                                               # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

ASKED = "what is the client's capitalisation threshold?"


@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


def _pos(desk, pid):
    return next(q for q in desk.positions if q.id == pid)


def _answer(desk, pid, facts=None):
    q = _pos(desk, pid)
    ctx = record.Context(facts=facts) if facts is not None else None
    return conftest.answer_judged(ASKED, position=q.position,
                                  citation=q.citation, keep=False, context=ctx)


# ── the firm's answer is in the record, not in the code ─────────────────────

def test_both_blocked_positions_now_carry_a_default(desk):
    for pid in ("POS1", "POS2"):
        assert _pos(desk, pid).default, (
            f"{pid} carries `Unless: capitalization_rule` and no `Default:`, "
            f"which is the state that made it unservable on every client")


def test_the_default_names_the_word_and_the_firms_threshold(desk):
    said = _pos(desk, "POS2").default
    assert "`none`" in said, "the default does not name the word to record"
    assert "$2,500" in said and "$5,000" in said, (
        "the default does not carry the IRS figures the firm's note points at")
    assert "Do NOT record the figure" in said, (
        "nothing warns against recording the number, which is the mistake that "
        "reads as a client-specific rule and makes the desk step back")


def test_a_default_on_a_position_with_no_unless_is_refused(tmp_path):
    """A default answers an `Unless:`. With no displacing fact the line sits in
    the record looking like firm policy and the engine will never print it."""
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    f = corpus / "positions" / "POSITIONS.md"
    text = f.read_text(encoding="utf-8")
    head = "**Position:** a reconciling item, no entry in the books"
    assert head in text, "the fixture's premise moved"
    f.write_text(text.replace(head, head + "\n\n**Default:** something", 1),
                 encoding="utf-8")
    with pytest.raises(record.RecordError, match="Default"):
        record.load(corpus)


def test_the_default_is_one_line_and_does_not_swallow_the_page(desk):
    """WRITTEN WITH THE WRAPPING READER FIRST AND IT OVER-READ IMMEDIATELY: it
    ran to the next `**` and returned the firm's quoted words, the note about
    not assuming, and the POS3 consequence as the default VALUE. The refusal
    would have printed four paragraphs where a preparer needs a word."""
    said = _pos(desk, "POS2").default
    assert "\\n\\n" not in said, "the default swallowed the paragraph under it"
    assert len(said) < 500, f"the default is {len(said)} characters long"


# ── the three states, run rather than reasoned about ────────────────────────

def test_a_silent_file_still_refuses(desk):
    """The firm declined a silent default in the code. Nothing may start
    answering on its own."""
    out = _answer(desk, "POS2")
    assert isinstance(out, engine.Refusal)
    assert out.reason == "context_not_on_file"


def test_recording_the_word_serves_the_firms_threshold(desk):
    out = _answer(desk, "POS2", {"capitalization_rule": record.NO_STANDING_RULE})
    assert isinstance(out, engine.Served), (
        "recording that this client has no rule of its own does not serve the "
        "firm's position, so the firm's answer does not actually land")
    assert "$2,500" in out.position


def test_recording_a_figure_is_read_as_a_client_rule(desk):
    """The mistake the `Default:` line warns about, pinned. A preparer who
    writes the ceiling rather than the word gets a refusal — which is right,
    because a value there means this client is treated differently."""
    for wrote in ("the IRS de minimis ceiling, $2,500", "$500 per item", "2500"):
        out = _answer(desk, "POS2", {"capitalization_rule": wrote})
        assert isinstance(out, engine.Refusal) and \
            out.reason == "client_rule_governs", (
            f"{wrote!r} was not read as a client-level rule")


def test_a_client_with_its_own_lower_rule_is_not_answered_broadly(desk):
    """The firm, 6 September 2026: *"we shouldn't ignore client level rules set
    with judgment with the desk answering broadly."* The default must not have
    weakened that."""
    out = _answer(desk, "POS2", {"capitalization_rule": "$500 per item"})
    assert isinstance(out, engine.Refusal)
    assert "$2,500" not in str(out.detail or ""), (
        "the firm's general threshold is quoted at a client treated differently")


# ── the refusal is actionable ───────────────────────────────────────────────

def test_the_refusal_says_what_to_write(desk):
    """A refusal that names a gap and not the remedy is a dead end wearing a
    reason code. The preparer holding this one had to go and ask what the firm's
    threshold was before they could close it."""
    out = _answer(desk, "POS2")
    assert "`none`" in out.ask
    assert "$2,500" in out.ask
    assert "POS2" in out.ask, "the follow-up does not say whose position waits"


def test_a_position_with_no_default_asks_without_inventing_one(desk):
    """This must never start printing a default a position does not carry."""
    for q in [q for q in desk.positions if q.unless and not q.default]:
        out = conftest.answer_judged(ASKED, position=q.position,
                                     citation=q.citation, keep=False)
        if isinstance(out, engine.Refusal) and out.ask:
            assert "Where the client has no rule of its own" not in out.ask, (
                f"{q.id} has no Default and the refusal offers one anyway")
