"""Prove one served answer against the publisher, at the moment it is served.

THE FIRM'S IDEA, AND IT IS THEIRS: *"going forward thinking like the agents tie
out their position to prove it to the desk."* Answered on the fourth docket,
6 September 2026: **Build it.**

WHAT IT ADDS THAT THE GATE CANNOT. `engine.serve` checks that a citation resolves
in OUR RECORD. It has no way to check that the record is true, and it must not
grow one: verification reads stored text, or every test run depends on a
government website being up and "prove every check can fail" becomes
unsatisfiable. The corpus tie-out closes that gap for every stored passage, once, on
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
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import comparing
import record

TIED, DIFFERS, COULD_NOT = "TIED", "DIFFERS", "COULD NOT"


def _host(url: str) -> str:
    """The registered host of a URL, lowercased. Empty when there is none."""
    import urllib.parse
    host = urllib.parse.urlsplit(url or "").hostname or ""
    return host.lower().removeprefix("www.")

#: The reason a refusal carries when the source has moved under us. Named in
#: `engine.REASONS` so it can be counted like every other refusal.
MOVED = "authority_has_moved"


#: THE SHAPE OF A CITATION'S OWN IDENTIFIER. Anything beginning with a digit and
#: carrying the punctuation citations use -- `1.263(a)-2`, `842-20-25-1`, `583`.
#: Every citation has one and it needs no per-publisher knowledge, which is what
#: makes this a general check rather than another blocklist.
_MARK = __import__("re").compile(r"\d[\dA-Za-z().\-]*")


def identifiers(citation: str) -> tuple:
    """The distinctive tokens of a citation, longest first.

    TRAILING GROUPS ARE TRIMMED OFF AS WELL AS KEPT, and that is not tidiness --
    it is the difference between working and not. A desk cites the subparagraph
    it relies on, `1.263(a)-2(d)(1)`; the page that carries it is headed with the
    SECTION, `1.263(a)-2`, and contains the full path nowhere. Matching only the
    citation as written finds nothing on the genuine document, so every
    citation would look like an interstitial and DIFFERS would be unreachable.
    Found by this returning False on a real page in the first version.

    Only TRAILING groups come off. Removing `(a)` from the middle would leave
    `1.263-2`, which is a different rule.

    TWO CHARACTERS IS NOT AN IDENTIFIER -- a bare `2` is in every document ever
    written -- so anything shorter than three is dropped.
    """
    import re
    out = []
    for m in _MARK.finditer(citation or ""):
        seen = _balanced(m.group(0).strip(".-"))
        while seen:
            if len(seen) >= 3 and not _bare_year(seen) and seen not in out:
                out.append(seen)
            trimmed = _balanced(re.sub(r"\([^()]*\)$", "", seen).rstrip(".-"))
            if trimmed == seen:
                break
            seen = trimmed
    return tuple(sorted(set(out), key=len, reverse=True))


def _balanced(token: str) -> str:
    """Drop trailing `)` that closes nothing.

    `1.263(a)-2(d)(1)` ends inside its own parentheses and a blanket `rstrip`
    left `1.263(a)-2(d)(1` — after which the group-trimming regex, which needs a
    closing paren, matched nothing and the section-level `1.263(a)-2` was never
    produced. So the check returned False on the GENUINE page, which would have
    made every real document look like an interstitial.
    """
    while token.endswith(")") and token.count(")") > token.count("("):
        token = token[:-1]
    return token


def _bare_year(token: str) -> bool:
    """A four-digit year is not a citation identifier.

    `IRS Pub. 583 (12/2024)` yields `2024`, which appears in a great many
    documents that are not that publication — including, plausibly, the
    publisher's own refusal page. Dropping it costs nothing: `583` is the
    identifier and it survives.
    """
    return bool(re.fullmatch(r"(19|20)\d\d", token))


def about_this_citation(citation: str, text: str) -> bool:
    """Does this document even mention the thing we asked for?

    THE THIRD REFUSAL SHAPE, found on the Forge on 8 September 2026 and the
    reason this function exists. eCFR served a real headless browser an HTTP 200
    "Request Access" page -- 12,474 bytes, THE CORRECT HOST, no redirect, no
    error token, no body class. Every guard in `browser.py` passed it, our
    passage was not in it, and `prove` therefore said DIFFERS, which
    `ask.answer` turns into `authority_has_moved`.

        The product told a human to RETIRE A GOOD CITATION, on the strength of
        our own client being refused.

    The desk that found it named the general fix rather than another blocklist:

        "DOES THE FETCHED DOCUMENT EVEN MENTION THE SECTION WE ASKED FOR? Every
         citation carries its own identifier, so this needs no per-publisher
         knowledge."

    Measured against that interstitial: `1.263(a)-2` absent, `263(a)-2` absent,
    `eCFR` PRESENT -- which is why a check on the publisher's name would have
    missed it.
    """
    marks = identifiers(citation)
    if not marks:
        return False
    live = comparing.normalise(text or "").lower()
    return any(comparing.normalise(m).lower() in live for m in marks)


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


def prove_passage(citation: str, passage: str, source, transport) -> Proof:
    """Is THIS passage in the document THIS source publishes, right now?

    The core, and it knows nothing about a record. It is handed the citation to
    name, the words to look for, the source to fetch and the transport to fetch
    with — which is the whole of what a comparison needs. `prove` resolves those
    four out of a served answer; the candidate path (#343) has a citation no desk
    holds and constructs them instead, and neither one is the privileged caller.

    THE SPLIT IS A PREFACTOR AND CHANGES NOTHING. Every property the docstring
    above claims is a property of this function: the transport is a callable so
    no configuration reaches the network by accident, the three verdicts keep
    their meanings, and COULD NOT is never upgraded to TIED.

    The comparison comes from `comparing`, which the corpus tie-out uses too.
    One folding table, one meaning for a marked omission, no second copy to
    drift -- and, as importantly, nothing on the import path that can reach the
    network. The first version of this reached `tools/tieout.py` lazily; that
    module fetches, so the import pulled in `ssl`, and every test here failed
    inside `ssl.py` because the suite replaces the socket layer. The guard was
    right.
    """
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

    # WE NEVER REACHED THE PUBLISHER, WHICH IS NOT THE SAME AS THE TEXT MOVING.
    #
    # See `fetch.Response.url`. A bot filter that answers 200 with an
    # interstitial on ANOTHER HOST is indistinguishable, byte for byte, from a
    # publisher who rewrote the page — unless you look at where you landed.
    # `authority_has_moved` is a claim ABOUT THE PUBLISHER and this is not one:
    # it is a claim about us, and the honest verdict is COULD NOT.
    #
    # Host, not exact URL, because a publisher redirecting within its own site
    # (http to https, a canonical path, a trailing slash) has served us its page
    # and the comparison is valid.
    landed, asked = _host(here["url"]), _host(source.url)
    if landed and asked and landed != asked:
        return Proof(COULD_NOT, citation, url=source.url,
                     note=f"asked {asked} and landed on {landed} — this is not "
                          f"the publisher's page, so nothing here says whether "
                          f"the passage moved. Most likely the source refused "
                          f"this client rather than the text changing.")

    ours, live = comparing.normalise(passage), comparing.normalise(text)
    if comparing.ELLIPSIS in passage:
        ok, failed = comparing.elided_match(ours, live)
        if ok:
            return Proof(TIED, matched_chars=len(ours), **here)
        return _absent(citation, text, f"not found from {failed[:60]!r}", here)
    if ours and ours in live:
        return Proof(TIED, matched_chars=len(ours), **here)
    return _absent(citation, text,
                   "the stored passage is not in the document the publisher "
                   "serves today", here)


def _absent(citation, text, why, here) -> Proof:
    """Our passage is not in what came back. DIFFERS only with evidence.

    DIFFERS IS A CLAIM ABOUT THE PUBLISHER AND IT WITHDRAWS A CITATION. Saying
    it requires positive evidence that this IS the publisher's document for this
    citation -- because from our own side "the text changed" and "we were
    refused" are the same observation, and one of them is not the publisher's
    fault.

    ONE DIRECTION ONLY, WHICH IS WHY THIS IS SAFE TO ADD. It can turn a DIFFERS
    into a COULD NOT and never the reverse, so the engine can only become more
    cautious. The cost is real and is the right way round: a rule that genuinely
    moved, on a page that does not name itself, is now reported as unchecked
    rather than withdrawn -- and `staleness.py` reports drift separately. The
    other error told a person to retire a rule that had not moved at all.
    """
    if about_this_citation(citation, text):
        return Proof(DIFFERS, matched_chars=0, note=why, **here)
    return Proof(COULD_NOT, matched_chars=0, **here,
                 note=f"{why} — AND the document does not mention {citation!r} "
                      f"at all, so nothing here says it is that document. From "
                      f"this side a publisher that changed its text and a "
                      f"publisher that refused us look the same, and only one "
                      f"of those is a finding about the publisher.")


def prove(served, desk, transport) -> Proof:
    """Prove a served answer: resolve its authority, then `prove_passage`.

    THIS FUNCTION IS THE RECORD HALF and does nothing else. Two of its three
    outcomes never reach a fetch, and both are about what the record holds
    rather than about what a publisher serves -- which is exactly why they live
    here and not in the core.
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
    return prove_passage(citation, obj.text, source, transport)
