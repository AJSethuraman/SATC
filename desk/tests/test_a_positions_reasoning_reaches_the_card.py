"""The whole of a position's reasoning reaches the card, folded.

`dec-whytrunc`, 18 September 2026 — the firm, on the eighth docket: **"Read the
whole thing, folded."**

THE DEFECT, AND IT WAS NEVER A CHOICE. `record._field` ends a value at
`_FIELD_END`, which is any line starting `**`. That is right for a value that
wraps onto the next line. It is wrong for prose, because **a paragraph written
to be read starts with its point in bold** — so a position's `Why:` stopped at
its second paragraph and everything after it reached nothing.

MEASURED ACROSS THE TWENTY RATIFIED POSITIONS: **23,044 characters reached no
card.** POS13 lost 6,364 of its 6,658; every single position lost something.
Sources lose another 1,802 the same way.

WHERE IT LANDED IS WHY IT MATTERED. The field feeds the ratification card and
the docket card — the pages the firm reads a position on when deciding whether
to ratify it. The card POS2 was ratified from showed **429 characters of about
2,262**, and the part that did not arrive contains:

    "And $2,500 is a ceiling, not the number. § 1.263(a)-1(f)(1)(ii)(B) requires
     the client to have a book policy at the beginning of the year; the safe
     harbour protects amounts under whichever is lower, that policy or the
     ceiling."

which is exactly the caveat that makes the firm's own capitalisation default
something to be careful with. **No served answer was ever affected** — the brief
prints a position's WORDS, not its reasoning.

WHY FOLDED AND NOT SIMPLY LONGER. The other option on the card was the whole
thing at full length, and the firm declined it. The reason is in the defect: a
card nobody finishes is how this became invisible. Folded, the default view is
byte-for-byte what they were already reading, and the rest is one disclosure
below it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import docket_form                                          # noqa: E402
import ratification_page                                    # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

CEILING = "ceiling, not the number"


@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


def _pos(desk, pid):
    return next(q for q in desk.positions if q.id == pid)


# ── the parser reads the whole thing ────────────────────────────────────────

def test_the_caveat_that_started_this_now_reaches_the_record(desk):
    why = _pos(desk, "POS2").why
    assert CEILING in why, (
        "POS2's reasoning still stops before the sentence saying $2,500 is a "
        "ceiling rather than the number — the caveat the firm's capitalisation "
        "default turns on")


def test_a_bolded_paragraph_no_longer_ends_the_reasoning(desk):
    """The mechanism, stated as its own test rather than left to the numbers."""
    why = _pos(desk, "POS2").why
    assert "**Read the citation" in why or "Read the citation" in why
    assert "WHY THIS CARRIES AN" in why, (
        "the explanation of the `Unless:` line is a bolded paragraph and is "
        "missing, which is the truncation")


def test_every_position_keeps_everything_its_entry_holds(desk):
    """THE WHOLE DENOMINATOR, not a sample. Each position's `Why:` must be as
    long as the text between its own `**Why:**` and the next FIELD."""
    import re
    raw = (CORPUS / "positions" / "POSITIONS.md").read_text(encoding="utf-8")
    blocks = re.split(r"^## ", raw, flags=re.M)[1:]
    short = []
    for q in desk.positions:
        block = next((b for b in blocks if b.startswith(q.id + " ")), None)
        assert block, f"{q.id} is not in the file"
        body = block[block.index("**Why:**") + len("**Why:**"):]
        for label in ("Ratified:", "Kind:", "Reviewed:", "Needs:", "Unless:",
                      "Default:", "Citation:", "Recorded:", "Position:"):
            cut = body.find("**" + label)
            if cut > -1:
                body = body[:cut]
        expected = len(body.strip())
        if len(q.why) < expected * 0.98:
            short.append(f"{q.id}: reads {len(q.why)} of {expected}")
    assert not short, "reasoning is still being truncated:\n  " + "\n  ".join(short)


def test_a_paragraph_that_looks_like_a_field_does_not_end_it(desk):
    """THE HEURISTIC THAT WAS CONSIDERED AND REJECTED. Ending prose at bold text
    followed by a colon would have worked on almost everything — and
    `POSITIONS.md` contains *"**What this position does NOT settle, and why it
    is a position at all:**"*, a paragraph lead ending in a colon. It would have
    truncated the reasoning at the sentence a reader most needs.

    So prose ends at the entry's OWN declared labels, which is exact."""
    carrier = [q for q in desk.positions
               if "does NOT settle, and why it is a position" in q.why]
    assert carrier, (
        "the paragraph this test is about is gone from the record; if it was "
        "reworded, find the new one or delete this test and say so")
    for q in carrier:
        after = q.why.split("does NOT settle, and why it is a position", 1)[1]
        assert len(after) > 80, (
            f"{q.id}'s reasoning stops at a paragraph lead ending in a colon")


def test_a_source_why_is_read_whole_too(desk):
    """The same defect in a second place. A source's `Why` reaches only
    `guards.py`, which checks it is non-empty, so nothing a reader sees moved —
    but it is fixed rather than left to be found again."""
    longest = max(desk.sources, key=lambda s: len(s.note or ""))
    assert len(longest.note) > 400, (
        "no source carries more than 400 characters of reasoning, which "
        "suggests they are still being cut at the first bolded line")


# ── and the card folds it ───────────────────────────────────────────────────

def test_the_opening_is_exactly_what_the_card_showed_before(desk):
    """The firm chose folding over full length, so the default view must not
    move. 429 characters is what the POS2 card carried before any of this."""
    why = _pos(desk, "POS2").why
    assert len(docket_form._opening(why)) == 429
    assert CEILING not in docket_form._opening(why)


def test_the_rest_is_there_and_behind_a_fold(desk):
    why = _pos(desk, "POS2").why
    rest = docket_form._after_the_opening(why)
    assert CEILING in rest, "the caveat is not in the folded remainder either"
    assert len(rest) > 1_500


def test_the_fold_says_how_much_is_behind_it(desk):
    """A disclosure with no size on it is one a reader takes for a footnote, and
    the whole finding was that it is not."""
    said = docket_form._how_much(_pos(desk, "POS2").why)
    assert "paragraph" in said and "words" in said
    assert said.startswith("4 more paragraphs"), said


def test_a_one_paragraph_reasoning_gets_no_fold_at_all():
    """A fold over nothing is a control that does nothing."""
    assert docket_form._after_the_opening("just the one paragraph") == ""
    assert docket_form._how_much("just the one paragraph") == ""
    assert docket_form._opening("") == ""
    assert docket_form._how_much("") == ""


def test_the_ratification_card_folds_the_same_way(desk):
    """The other page a position is read on. It renders only PROPOSED positions
    and every one in the record is ratified, so this exercises the renderer
    directly rather than the page — the page would be empty and prove nothing."""
    html = ratification_page._reasoning(_pos(desk, "POS2").why)
    assert '<details class="more">' in html, "the rest is not folded"
    assert CEILING in html, "the caveat does not reach the card"
    opening_at = html.index("Q4 asked")
    fold_at = html.index('<details class="more">')
    assert opening_at < fold_at, "the fold precedes the opening paragraph"


def test_nothing_is_dropped_between_the_record_and_the_card(desk):
    """Folding moves text; it must never lose it. Every paragraph of every
    position has to appear in one half or the other."""
    for q in desk.positions:
        if not q.why.strip():
            continue
        paras = [b.strip() for b in q.why.strip().split("\n\n") if b.strip()]
        shown = docket_form._opening(q.why)
        rest = docket_form._after_the_opening(q.why)
        for para in paras:
            assert para in shown or para in rest, (
                f"{q.id} loses a paragraph between the record and the card")

def test_the_row_the_card_receives_carries_the_OPENING_and_not_the_whole(desk,
                                                                 monkeypatch):
    """THE GAP THIS TEST EXISTS TO CLOSE, and it was a real one.

    Every other test here calls `_opening` directly. So when the row built for
    the card was mutated back to the whole reasoning — the option the firm
    DECLINED — the whole file stayed green. A test that checks a helper and not
    the thing that uses it proves the helper works and nothing about the page.

    The record holds no PROPOSED position (all twenty are ratified), so the
    walkthrough is given one. That is the state this path exists for: the
    factory proposes, and the firm reads the proposal on a card.
    """
    real = _pos(desk, "POS2")
    monkeypatch.setattr(docket_form, "positions", lambda: [{
        "desk": "corpus", "id": real.id, "title": real.title,
        "position": real.position, "citation": real.citation,
        "source": "S3", "tier": "secondary", "kind": "authority",
        "shape": "rule", "unlocks": 0, "why": real.why, "note": None,
    }])
    row = next(r for r in docket_form.items() if r["kind"] == "position")

    assert CEILING not in row["why"], (
        "the card's default view carries the whole reasoning; the firm was "
        "offered that and chose folded")
    assert CEILING in row["why_rest"], (
        "the caveat is in neither half — folding has lost it")
    assert row["why_more"], "the fold does not say how much is behind it"
