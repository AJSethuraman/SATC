"""A position the firm ratified must be reachable, or ratifying it did nothing.

THE DEFECT, 7 September 2026, and it is the firm's own words being refused.
`rewards-and-information-returns/POS3` — ratified that afternoon — sat on
§ 1.6050W-1(c)(3), which was that desk's source S6. The subject word
`peer-to-peer` was registered to S3 and to nothing else. So the close's own
question, *"do payments to individuals create a 1099-NEC obligation? Peer-to-peer
payments to individuals for services can"*, reached the desk, the desk cited POS3
correctly and quoting the firm, and `engine.serve` refused it
`citation_does_not_support` — because no source answering that question's
subjects covered that citation.

**Ratifying a position and not routing to its source is ratifying nothing**, and
this repository had already written the same sentence about admitting a publisher
and not routing to it (the `materials and supplies` move). The same shape, one
desk over, found by asking a real question rather than by an audit.

ONE CORPUS, 10 September 2026 (`dec-kill`). The desks are gone and so is the
routing that produced the defect — but `answered_from` survives, because it is
what `engine._check` reads to decide whether a citation has anything to do with
the question. So does this check. What moved is the addressing: POS3 is POS15 in
the merged corpus and S6 is S25, and neither is written down below — the position
is FOUND BY ITS CITATION, which is the thing that did not change and the thing
the defect was actually about.

WHAT THIS CHECKS, and it is a property rather than an instance: for every
ratified position, at least one subject the corpus answers on must be registered
to a source whose citation prefix covers that position's citation. It does not
check that the position is right — only that it is REACHABLE. An unreachable one
is dead text that reads like authority.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402

CORPUS = HERE / "corpus"

#: The paragraph the 7 September defect was about. Named by CITATION and not by
#: position id, because the merge renumbered every id and a test that pinned
#: `POS3` would have died of bookkeeping rather than of the defect returning.
THE_DEFECT = "26 CFR 1.6050W-1(c)(3)"
THE_WORD = "peer-to-peer"


def _reachable(desk, citation):
    """The source ids whose prefix covers this citation AND which at least one
    declared subject reaches.

    `answered_from` IS ON THE RECORD, and always was. It came off a
    `Registration` here because `routing.registry` was the only thing that built
    one — the Registration carried the routing half beside it, and `dec-kill`
    deleted that half rather than this.
    """
    covering = {s.id for s in desk.sources
                if citation.startswith(s.citation_prefix)}
    declared = {sid for sid, terms in desk.answered_from.items() if terms}
    return covering & declared


def test_every_ratified_position_sits_on_a_source_the_corpus_answers_from():
    desk = record.load(CORPUS)
    ratified = [q for q in desk.positions if not q.proposed]
    assert ratified, "no ratified positions at all — the fixture moved"
    for q in ratified:
        assert _reachable(desk, q.citation), (
            f"{q.id} is ratified on {q.citation!r}, and no subject this corpus "
            f"answers on is registered to a source covering it. The corpus can "
            f"cite the firm's own position and the engine will refuse it "
            f"`citation_does_not_support`. Register the subject that brings this "
            f"question in on that source.")


def test_the_defect_this_was_written_for_is_actually_fixed():
    """The instance, not just the property — so a rewrite of the check that
    stopped covering this case goes red."""
    desk = record.load(CORPUS)
    pos = [q for q in desk.positions if q.citation == THE_DEFECT]
    assert pos, f"nothing sits on {THE_DEFECT} any more"
    assert not pos[0].proposed, "the position stopped being ratified"
    assert _reachable(desk, THE_DEFECT), "the 1099 position is unreachable again"

    on_the_paragraph = {
        sid for sid in _reachable(desk, THE_DEFECT)
        if THE_WORD in {t.lower() for t in desk.answered_from.get(sid, ())}}
    assert on_the_paragraph, (
        f"`{THE_WORD}` is the word the close's own question used, and "
        f"§ 1.6050W-1(c)(3) is the paragraph that decides it — no source "
        f"covering that paragraph is answered from it")


def test_the_check_would_catch_it_if_it_came_back():
    """Check the checker. With the subject stripped everywhere, the guard must
    go red — otherwise it is a test that passes because nothing is wrong rather
    than because it is looking.

    AND IT STATES WHAT IT DOES NOT CATCH. Removing `peer-to-peer` alone leaves
    the covering sources carrying other subjects, so they are still answered from
    and the property still holds. THAT IS THE HONEST RESULT: this check catches a
    position on a source NOTHING answers from, not one whose particular question
    cannot reach it. The narrower case is what the test above pins.
    """
    import dataclasses

    desk = record.load(CORPUS)
    covering = {s.id for s in desk.sources
                if THE_DEFECT.startswith(s.citation_prefix)}
    assert covering, "nothing covers the citation, so there is nothing to strip"

    without_the_word = {
        sid: tuple(t for t in terms if t.lower() != THE_WORD)
        for sid, terms in desk.answered_from.items()}
    still_reachable = dataclasses.replace(desk, answered_from=without_the_word)
    assert _reachable(still_reachable, THE_DEFECT), (
        "if this now fails, the guard has become stronger than documented — "
        "update this comment rather than deleting the test")

    emptied = dataclasses.replace(
        desk, answered_from={sid: (() if sid in covering else terms)
                             for sid, terms in desk.answered_from.items()})
    assert not _reachable(emptied, THE_DEFECT), (
        "with nothing answered from any source covering it, the position must "
        "read as unreachable")
