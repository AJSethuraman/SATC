"""A position the firm ratified must be reachable, or ratifying it did nothing.

THE DEFECT, 7 September 2026, and it is the firm's own words being refused.
`rewards-and-information-returns/POS3` — ratified that afternoon — sits on
§ 1.6050W-1(c)(3), which is source S6. The subject word `peer-to-peer` was
registered to S3 and to nothing else. So the close's own question, *"do payments
to individuals create a 1099-NEC obligation? Peer-to-peer payments to individuals
for services can"*, reached the desk, the desk cited POS3 correctly and quoting
the firm, and `engine.serve` refused it `citation_does_not_support` — because no
source answering that question's subjects covers that citation.

**Ratifying a position and not routing to its source is ratifying nothing**, and
this repository had already written the same sentence about admitting a publisher
and not routing to it (`fixed-assets/SUBJECTS.md`, the `materials and supplies`
move). The same shape, one desk over, found by asking a real question rather than
by an audit.

WHAT THIS CHECKS, and it is a property rather than an instance: for every
ratified position on every desk, at least one subject the desk routes on must be
registered to a source whose citation prefix covers that position's citation. It
does not check that the position is right, or that the routing is good — only
that the position is REACHABLE. An unreachable one is dead text that reads like
authority.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
import routing                                              # noqa: E402


def _desks():
    return [d for d in sorted((HERE / "desks").iterdir())
            if (d / "SOURCES.md").is_file()]


def _reachable(desk, reg, citation):
    """The source ids whose prefix covers this citation AND which at least one
    registered subject routes to."""
    covering = {s.id for s in desk.sources
                if citation.startswith(s.citation_prefix)}
    routed = {sid for sid, terms in reg.answered_from.items() if terms}
    return covering & routed


@pytest.mark.parametrize("d", _desks(), ids=lambda d: d.name)
def test_every_ratified_position_sits_on_a_source_the_desk_routes_to(d):
    desk = record.load(d)
    reg = next(r for r in routing.registry(HERE / "desks") if r.desk == d.name)
    for q in desk.positions:
        if q.proposed:
            continue
        assert _reachable(desk, reg, q.citation), (
            f"{d.name}/{q.id} is ratified on {q.citation!r}, and no subject this "
            f"desk routes on is registered to a source covering it. The desk can "
            f"cite the firm's own position and the engine will refuse it "
            f"`citation_does_not_support`. Register the subject that brings this "
            f"question in on that source.")


def test_the_defect_this_was_written_for_is_actually_fixed():
    """The instance, not just the property — so a rewrite of the check that
    stopped covering this case goes red."""
    d = HERE / "desks" / "rewards-and-information-returns"
    desk = record.load(d)
    reg = next(r for r in routing.registry(HERE / "desks") if r.desk == d.name)
    pos3 = next(q for q in desk.positions if q.id == "POS3")
    assert pos3.citation.startswith("26 CFR 1.6050W-1")
    assert _reachable(desk, reg, pos3.citation), "POS3 is unreachable again"

    on_s6 = {t.lower() for t in reg.answered_from.get("S6", ())}
    assert "peer-to-peer" in on_s6, (
        "`peer-to-peer` is the word the close's own question used, and "
        "§ 1.6050W-1(c)(3) is the paragraph that decides it")


def test_the_check_would_catch_it_if_it_came_back(monkeypatch):
    """Check the checker. With the subject removed, the guard must go red —
    otherwise it is a test that passes because nothing is wrong rather than
    because it is looking."""
    d = HERE / "desks" / "rewards-and-information-returns"
    desk = record.load(d)
    reg = next(r for r in routing.registry(HERE / "desks") if r.desk == d.name)
    stripped = dict(reg.answered_from)
    stripped["S6"] = tuple(t for t in stripped.get("S6", ())
                           if t.lower() != "peer-to-peer")
    broken = type(reg)(**{**reg.__dict__, "answered_from": stripped})

    pos3 = next(q for q in desk.positions if q.id == "POS3")
    # S6 still carries other subjects, so it is still routed to -- the guard as
    # written passes. THAT IS THE HONEST RESULT and it is worth stating: this
    # check catches a position on a source NOTHING routes to, not one whose
    # particular question cannot reach it. The narrower case is what
    # `test_the_defect_this_was_written_for_is_actually_fixed` pins.
    assert _reachable(desk, broken, pos3.citation), (
        "if this now fails, the guard has become stronger than documented — "
        "update this comment rather than deleting the test")
    stripped["S6"] = ()
    emptied = type(reg)(**{**reg.__dict__, "answered_from": stripped})
    assert not _reachable(desk, emptied, pos3.citation), (
        "with nothing routed to S6 at all, POS3 must read as unreachable")
