"""A quotation may leave something out. It may not leave it out quietly.

THE DEFECT, FOUND BY THE TIE-OUT AND BY NOTHING ELSE. Publication 583 says the
statement balance may not agree if the statement *"Includes bank charges you did
not enter in your books ..., or Does not include deposits made after the
statement date"*. Two branches, opposite answers, one sentence. The cash desk
stores them as two passages, which is RIGHT and was decided in #264 — served as
one entry, a desk asked about an uncleared cheque is handed the bank-charge
branch as well.

What was wrong is that the second passage stored the sentence's opening and then
jumped to its own branch, with nothing saying a branch had been removed. Every
test in this suite passed: they all read the same stored file, so a passage
trimmed wrongly is stored wrongly, served wrongly and asserted wrongly. Only a
fetch of the publisher's own words could see it, and that is what saw it.

THE FIRM'S ANSWER, fourth docket, 6 September 2026: *"Mark the omission."*

AND THE MARK HAD TO COST SOMETHING. A tie-out asks whether our text occurs in the
publisher's document; inserting `[...]` breaks that outright, so the easy version
of "mark the omission" is an exemption — the passage becomes unverifiable and
says so in a way nobody reads. Instead the mark is a CLAIM: each segment must
appear in the live document, in order. What goes unchecked is only the material
between segments, which is precisely what the reader is being asked to notice.

These tests run offline, against fixture strings, which is why `elided_match` was
split out of `check`. `check` fetches, and this desk's `conftest.py` replaces the
socket layer, so anything left inside it is unreachable by any test here.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
import tieout                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402

LIVE = ("when you receive your bank statement, make sure the statement, your "
        "checkbook, and your books agree. the statement balance may not agree "
        "with the balance in your checkbook and books if the statement: "
        "includes bank charges you did not enter in your books and subtract "
        "from your checkbook balance, or does not include deposits made after "
        "the statement date or checks that did not clear your account before "
        "the statement date.")


def _ours(text):
    return tieout.normalise(text)


def test_a_marked_omission_matches_when_every_segment_is_there_in_order():
    ours = _ours("the statement balance may not agree with the balance in your "
                 "checkbook and books if the statement: [...] or does not "
                 "include deposits made after the statement date")
    assert tieout.elided_match(ours, LIVE) == (True, "")


def test_the_segments_must_appear_in_the_source_s_order():
    """The strictness that makes the mark worth having. Reversed, both segments
    are present in the document and the passage is still a misquotation."""
    ours = _ours("or does not include deposits made after the statement date "
                 "[...] the statement balance may not agree")
    ok, failed = tieout.elided_match(ours, LIVE)
    assert not ok and failed.startswith("the statement balance")


def test_a_word_changed_inside_a_segment_is_not_covered_by_the_mark():
    """A mark excuses what is BETWEEN segments and nothing inside one. Without
    this, `[...]` would launder any edit that happened to sit near it."""
    ours = _ours("the statement balance must not agree with the balance in your "
                 "checkbook and books if the statement: [...] or does not include")
    ok, failed = tieout.elided_match(ours, LIVE)
    assert not ok and "must not agree" in failed


def test_a_segment_the_source_does_not_carry_at_all_fails():
    ours = _ours("if the statement: [...] or includes a wire transfer fee")
    ok, failed = tieout.elided_match(ours, LIVE)
    assert not ok and "wire transfer" in failed


def test_an_unmarked_passage_is_unaffected():
    """Narrowing only. A passage carrying no mark is one segment, so this
    behaves exactly as the plain containment check it sits beside."""
    ours = _ours("if the statement: includes bank charges you did not enter")
    assert tieout.elided_match(ours, LIVE) == (True, "")
    assert tieout._segments(ours) == [ours]


def test_the_two_passages_in_the_record_actually_carry_the_mark():
    """The record, not the mechanism. A guard for an omission nobody marked is
    a guard for nothing, and this is the pair the firm answered about."""
    desk = record.load(DESKS / "cash-and-bank")
    marked = [p for p in desk.passages if tieout.ELLIPSIS in p.text]
    assert len(marked) == 2, (
        f"{len(marked)} passages carry a marked omission, not 2: "
        f"{[p.citation for p in marked]}")
    assert all("Reconciling the checking account" in p.citation for p in marked)
    # AND THE TWO HALVES BETWEEN THEM CARRY THE WHOLE SENTENCE. Marking an
    # omission is honest; losing the branch entirely is not, and the mark would
    # hide that just as well.
    joined = " ".join(p.text for p in marked)
    for branch in ("Includes bank charges you did not enter",
                   "Does not include deposits made after the statement date"):
        assert branch in joined, f"the pair no longer carries {branch!r}"


def test_no_marked_passage_leaves_nothing_to_check():
    """Every segment of every marked passage is substantial enough to locate.

    I FIRST WROTE THIS DEMANDING TWO SEGMENTS, and it went red on the honest
    half of the very pair it was written for. The bank-charge passage ends on a
    trailing mark — *"...subtract from your checkbook balance, [...]"* — which
    says the sentence continues past what we kept. That is exactly the disclosure
    the firm asked for, and it costs nothing: one segment, checked in full by
    plain containment, with the mark adding a fact the reader did not have.

    What a mark can actually hide is material BETWEEN two segments, and the
    in-order rule above is what makes that checkable. A trailing or leading mark
    hides nothing that was ever inside the quotation. So the rule here is the one
    that is true: a segment must be long enough to identify a place in the
    source, and a passage that is nothing but a mark claims an omission with
    nothing left to check it against.
    """
    seen = 0
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        for p in record.load(d).passages:
            if tieout.ELLIPSIS not in p.text:
                continue
            seen += 1
            segs = tieout._segments(tieout.normalise(p.text))
            assert segs, (
                f"{d.name}/{p.citation} is a mark and nothing else; there is no "
                f"text left for a tie-out to find in the source")
            assert all(len(s) > 20 for s in segs), (
                f"{d.name}/{p.citation} has a segment too short to identify a "
                f"place in the source: {[s for s in segs if len(s) <= 20]}")
    assert seen == 2, f"{seen} marked passages across every desk, not 2"
