""""primary" on a document nobody has read is a badge doing vouching work.

FOUND BY THE DESK, ON THE FIRST LIVE ROUND TRIP ON 0.17.0, 8 September 2026.
Asked how depreciation is worked out, it reached no stored authority, took the
candidate path, and served a passage fetched live from irs.gov. The header read:

    IRS Pub. 946 (2025), "Figuring Depreciation"
    primary · not binding — read the note below · confirmed 2026-09-08

and the note under it said nobody has classified the document. The desk:

    "Both cannot be informative. 'primary' is derived from the HOST — irs.gov is
     in federal-tax's publishes list — but Pub 946 is the Service EXPLAINING
     itself, which DOMAINS.md's own rule makes SECONDARY. So the label is wrong
     for this document class, the note correctly refuses to stand behind it, and
     a tired reader keeps the word 'primary' and drops the paragraph."

THIS IS NOT THE COST `candidates.py` ACCEPTED. That docstring accepts one
direction — "a genuine regulation fetched from ecfr.gov arrives caveated when it
should not be" — which errs toward caution. This is the other direction: a
plain-English guide arriving stamped with the tier of the rules it explains.

AND THE FIRM ALREADY RULED ON THIS EXACT SHAPE, about where the straddle note
goes (`engine.py`): *"a badge saying primary and binding reads as two
independent things vouching for it. The warning then has to un-sell something I
have already bought."* A tier printed above a note retracting it is that same
retraction, one field over.

On a candidate the tier is not known BY CONSTRUCTION — `domains.tier_for`
classifies a host, the record classifies a document by hand, and a candidate is
one document nobody has read. So it says so.
"""
from __future__ import annotations

import engine


def _served(tier: str, classified: bool) -> str:
    return str(engine.Served(
        position="determine the basis of the property first",
        citation='IRS Pub. 946 (2025), "Figuring Depreciation"',
        tier=tier, checked="2026-09-08", binding=False, classified=classified))


def test_a_candidate_does_not_print_the_host_s_tier_as_the_document_s():
    out = _served("primary", classified=False)
    header = [l for l in out.splitlines() if "confirmed 2026-09-08" in l]
    assert header, "the header line is gone entirely"
    assert "primary" not in header[0], (
        "the header still stamps the host's tier onto a document nobody has "
        "classified — the exact badge the note below has to retract")


def test_a_candidate_says_plainly_that_nothing_classified_it():
    out = _served("primary", classified=False)
    assert "not established" in out, (
        "silence about the tier is not the same as saying it is unknown; "
        "unknown is a third answer and has to be printed as one")


def test_a_recorded_source_still_prints_its_tier():
    """The record HAS classified those, by hand. This must not flatten them."""
    out = _served("secondary", classified=True)
    header = [l for l in out.splitlines() if "confirmed 2026-09-08" in l][0]
    assert "secondary" in header
    assert "not established" not in out


def test_the_default_is_classified():
    """Every existing construction site keeps its tier; only candidates change."""
    assert engine.Served(position="p", citation="c", tier="primary",
                         checked="2026-09-08").classified is True
