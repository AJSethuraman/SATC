"""Prove one served answer against the publisher, at the moment it is served.

THE FIRM'S IDEA, AND IT IS THEIRS: *"going forward thinking like the agents tie
out their position to prove it to the desk."* Answered on the fourth docket,
6 September 2026: **Build it.**

WHAT IT ADDS THAT THE GATE CANNOT. `engine.serve` checks that a citation resolves
in OUR RECORD. It has no way to check that the record is true, and it must not
grow one: verification reads stored text, or every test run depends on a
government website being up and "prove every check can fail" becomes
unsatisfiable. The corpus tie-out closes that gap for all 533 passages, once, on
demand. This closes it for ONE answer, in front of the person reading it.

They answer different questions and the firm asked for both:

    the corpus tie-out    is the record still what the publishers publish?
    prove(...)            is THIS answer's authority still there, right now?

THREE VERDICTS, AND THE THIRD IS NOT A FAILURE.

    TIED        the passage is in the live document. Serve, with the proof.
    DIFFERS     the source no longer carries what we stored. REFUSE. Serving it
                would hand over text the publisher has changed or removed, with
                our own record as the only witness.
    COULD NOT   the publisher could not be reached. SERVE, and say so. Refusing
                here would make a client's answer depend on irs.gov being up,
                and would teach a reader that a proof they cannot see is a
                problem with the answer rather than with the network. Unknown is
                a third answer -- it is disclosed, not fatal, and never silently
                upgraded to TIED.

OFF BY DEFAULT, AND OFF MEANS OFF. `prove` takes a TRANSPORT rather than a
boolean, so there is no configuration that reaches the network by accident: with
no transport there is no fetch, and the suite passes none. `fetch.py` draws the
same line for the same reason.

IT PROVES CONTAINMENT, NOT COMPLETENESS -- the same limit the corpus tie-out
reports. It asks whether our passage occurs in the publisher's document today. It
cannot tell whether we stored the whole of what the citation covers, and it says
so rather than implying otherwise.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import comparing
import record

TIED, DIFFERS, COULD_NOT = "TIED", "DIFFERS", "COULD NOT"

#: The reason a refusal carries when the source has moved under us. Named in
#: `engine.REASONS` so it can be counted like every other refusal.
MOVED = "authority_has_moved"


@dataclass(frozen=True)
class Proof:
    """What was fetched, when, and whether it still says what we hold.

    EVERY FIELD IS EVIDENCE A READER CAN RE-CHECK BY HAND, which is the standard
    the tie-out skill sets: the URL to open, the moment it was opened, the digest
    of exactly the bytes that came back, and how much of our passage was found in
    them. A proof that only said "verified" would be this record's own word for
    itself, which is the mirror it exists to escape.
    """
    verdict: str
    citation: str
    url: str = ""
    fetched_at: str = ""
    sha256: str = ""
    doc_bytes: int = 0
    matched_chars: int = 0
    note: str = ""

    @property
    def held(self) -> bool:
        """True only for TIED. COULD NOT is never read as a pass."""
        return self.verdict == TIED


def prove(served, desk, transport) -> Proof:
    """Fetch the cited source and compare it with what was served.

    The comparison comes from `comparing`, which the corpus tie-out uses too.
    One folding table, one meaning for a marked omission, no second copy to
    drift -- and, as importantly, nothing on the import path that can reach the
    network. The first version of this reached `tools/tieout.py` lazily; that
    module fetches, so the import pulled in `ssl`, and every test here failed
    inside `ssl.py` because the suite replaces the socket layer. The guard was
    right.
    """
    citation = served.citation
    backing = desk.authority_for(citation)
    if backing is None:                                     # pragma: no cover
        return Proof(COULD_NOT, citation,
                     note="this citation is no longer in the desk's record")
    kind, obj, source = backing
    if kind == "position":
        # A POSITION IS THE FIRM'S OWN WORDS AND HAS NO PUBLISHER TO ASK. What
        # could be proved is the paragraph underneath it, which is a different
        # claim from the one being served, and reporting that as a proof of the
        # answer would be the mirror wearing a hat.
        return Proof(COULD_NOT, citation, url=source.url if source else "",
                     note="served from the firm's own position; there is no "
                          "publisher to check it against, and the paragraph "
                          "beneath it is not what was served")
    if source is None or not source.readable:               # pragma: no cover
        return Proof(COULD_NOT, citation,
                     note="this source may not be fetched at all")

    try:
        raw = transport(source, citation)
    except Exception as exc:
        # RECORDED, NEVER SWALLOWED, and never turned into DIFFERS. A network
        # that is down says nothing about whether the text moved.
        return Proof(COULD_NOT, citation, url=source.url,
                     note=f"{type(exc).__name__}: {exc}")

    text = raw.text if hasattr(raw, "text") else str(raw)
    body = raw.body if hasattr(raw, "body") else text.encode("utf-8")
    here = dict(
        citation=citation,
        url=getattr(raw, "url", source.url),
        fetched_at=getattr(raw, "at", None) or datetime.now(timezone.utc)
        .isoformat(timespec="seconds"),
        sha256=getattr(raw, "sha256", None) or hashlib.sha256(body).hexdigest(),
        doc_bytes=getattr(raw, "nbytes", None) or len(body),
    )

    ours, live = comparing.normalise(obj.text), comparing.normalise(text)
    if comparing.ELLIPSIS in obj.text:
        ok, failed = comparing.elided_match(ours, live)
        return Proof(TIED if ok else DIFFERS, matched_chars=len(ours) if ok else 0,
                     note="" if ok else f"not found from {failed[:60]!r}", **here)
    if ours and ours in live:
        return Proof(TIED, matched_chars=len(ours), **here)
    return Proof(DIFFERS, matched_chars=0,
                 note="the stored passage is not in the document the publisher "
                      "serves today", **here)
