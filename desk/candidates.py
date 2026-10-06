"""A citation no desk holds, answered on a live proof alone.

THE FIRM, 8 September 2026, having explained it more than once: *"we want the
best to be able to answer anything and not be limited to literally specific
things … the entire point is to have a headless machine and the agent to tie out
things to make sure it's all correct."* And, settling it: *"Yes verification is
the gate. Who cares if we can store it outside of it just being quicker the next
time. Store if possible sure but this isn't a limit."*

WHAT IT OVERTURNS. `engine._check` refuses any citation absent from a desk's
record, and the brief tells every answerer so. That made the seven desks a
CEILING: everything outside the stored corpus refused `authority_absent`, the
searcher found the rule, and the trail then stopped at the firm, because a
source had to be admitted before any desk could cite it. A four-minute lookup
queued behind the owner.

WHAT REPLACES IT. A citation the record has never seen becomes a CANDIDATE, and
it is served if -- and only if -- the words the answerer rests on are on the
publisher's own page RIGHT NOW. Storage becomes a cache: the candidate source
carries `may_store="license_check"`, so this path keeps nothing at all.

THE ORDER DOES NOT CHANGE, AND EACH STAGE MAY ADD A REFUSAL AND NEVER REMOVE
ONE. Two checks run BEFORE anything is fetched, and both are about whether we
may ask at all rather than about what came back:

    1. DOES THIS PUBLISHER GET TO SETTLE THIS?  Proving that irs.gov really says
       something is not evidence that irs.gov gets to say it. This check caught
       a Treasury regulation being served as primary and binding for a
       balance-sheet question on 8 September, and the stored path runs it too.
    2. IS THIS A WALL WE PUT UP OURSELVES?  A licence the firm has not accepted
       is not routed around by finding the same text at the same host through a
       different door. FASB ASC is the worked example.

Only then is the page fetched, and the verdict decides:

    TIED        served, carrying the proof, saying it rests on a live fetch.
    DIFFERS     refused `authority_has_moved`.
    COULD NOT   REFUSED, and this is where the candidate path differs from the
                stored one. There, an unreachable publisher leaves the record
                still holding the answer, so it serves and says so. Here there
                is nothing else holding the answer up at all.

AND EVERY REFUSAL SAYS WHAT HAPPENED WHEN TRYING -- the firm again: *"It should
state what happened when trying to tie it out. I need info to make decisions
down the line."* A candidate that refuses silently tells nobody anything they
could decide on later.

A CANDIDATE IS NEVER BINDING, WHATEVER ITS HOST, and this corrects the issue
this module was written from (#343), which said the tier should come from the
domain map and that an unknown host being tertiary was "already the right
answer". It is right about the unknown host and wrong about the rest.

`domains.tier_for` classifies a HOST. The record classifies a DOCUMENT, by hand,
and the two disagree exactly where it matters: irs.gov publishes the regulations
AND its own plain-English guides, so the map calls the host primary -- correctly,
that is a question about who governs -- while the record calls IRS Pub. 583
SECONDARY, because a person read it and saw a guide rather than the rule. A
candidate is one document nobody has read.

So the tier is reported, because the host really is that body's publisher, and
`binding` is FALSE, because `binding` means THE FIRM TREATS THIS AS AUTHORITY
THAT BINDS THEIR OWN WORK and the firm has not seen this document. One thing was
established here and it is narrow: these words are on that page today. Whether
the page is the rule or somebody's summary of the rule was not established by
anything, and a caveat that says so is the only honest thing to print.

The cost is real and is accepted: a genuine regulation fetched from ecfr.gov
arrives caveated when it should not be. The alternative -- an IRS publication
arriving stamped binding -- is the error this whole engine exists to stop, and it
is the one the reader cannot detect.
"""
from __future__ import annotations

from datetime import date

import domains
import engine
import proving
import record

#: What the tie-out announces to a publisher. The firm's answer on the docket,
#: 8 September 2026: *"Real headless browser"* -- a real one, rather than a
#: client claiming to be one, which is the difference between being refused and
#: lying about who is asking.
ACCESS = "headless_browser"

#: NOTHING IS KEPT. The gate is verification, so storage is an optimisation
#: this path declines to take -- `citation_only` would still mean "cite it,
#: keep nothing", and `license_check` says the stronger thing: nobody has
#: established that we may keep it, so we do not.
MAY_STORE = "license_check"


def _host(url: str) -> str:
    import urllib.parse
    host = urllib.parse.urlsplit(url or "").hostname or ""
    return host.lower().removeprefix("www.")


def walled(url: str, desk) -> record.Source | None:
    """A source in this desk's record that covers this host and may not be read.

    A LICENCE WALL IS NOT A FETCH PROBLEM AND IS NOT ROUTED AROUND. Where the
    record already says a publisher's content may never reach a model, arriving
    at the same host with a URL nobody has admitted is the same content through
    a different door. Matched on the registered HOST, because a licence covers a
    publisher rather than a path.
    """
    here = _host(url)
    if not here:
        return None
    for source in desk.sources:
        if not source.readable and _host(source.url) == here:
            return source
    return None


def source_for(url: str, *, domain=None, checked: str = "") -> record.Source:
    """The candidate, built in memory and never written anywhere.

    IN MEMORY RATHER THAN A CHANGE TO THE TRANSPORT SIGNATURE. `proving` takes a
    citation, the words, a source and a transport (#341); a candidate supplies
    all four without the record having to hold any of them, which is what makes
    this a new caller rather than a new mechanism.
    """
    return record.Source(
        id="candidate",
        title=f"{_host(url) or 'an unrecorded publisher'} (fetched, not stored)",
        tier=domains.tier_for(url, domain) if domain else "tertiary",
        access=ACCESS,
        may_store=MAY_STORE,
        checked=checked or date.today().isoformat(),
        citation_prefix="",
        url=url,
        note="Built for one answer and kept nowhere. See candidates.py.")


def consider(*, question: str, position: str, citation: str, url: str,
             text: str, desk, transport) -> engine.Served | engine.Refusal:
    """Serve this citation on a live proof, or refuse and say what happened.

    `text` is THE WORDS THE ANSWERER RESTS ON, handed in rather than looked up
    -- there is nothing to look it up in, which is the entire situation. The
    engine does not take the answerer's word for it: those words are what gets
    compared against the page.
    """
    verdict = domains.classify(question) if question else None

    # BEFORE ANY FETCH (0). NOTHING CLASSIFIED IT, SO NOTHING CAN CHECK IT.
    #
    # `dec-gate`, 10 September 2026 — the firm: **"Fail closed."**
    #
    # THE DEFECT. The publisher-competence check below is conditioned on
    # `verdict`, and `Verdict.__bool__` is False when no domain fired. So a
    # question whose vocabulary nothing recognises SKIPPED THE GATE ENTIRELY
    # and went straight to a live fetch of an unrecorded publisher — the one
    # class where nobody had established the publisher gets to say anything.
    # Measured 8 of 15 ordinary working questions; Forge-Occam reported 9 of 18
    # on their own close, and the five that reach nothing agree exactly.
    #
    # The `Verdict` docstring has always said a blank verdict is *"a refusal and
    # not an absence of opinion"*. The caller two files away read it as an
    # absence of opinion, which is what a falsy object invites.
    #
    # THIS IS NOT A NEW POLICY. It is the FOURTH DISPOSITION the firm signed off
    # in August — primary serves silent, secondary serves marked and notifies,
    # tertiary parks and notifies, and **unknown parks and notifies, because
    # unknown is a real fourth state** — reaching the one file it was never
    # wired into. Their answer builds the map: a parked question they settle is
    # how a domain learns the word it was missing.
    #
    # A QUESTION IS REQUIRED FOR THE GATE TO FIRE AT ALL. `consider` is called
    # with `question=""` by callers that have no question to classify, and
    # refusing those would fail closed on a case where nothing was ever open.
    if question and url and not verdict:
        return engine.Refusal(
            "body_of_authority_unknown",
            f"{citation!r} is in no record, and nothing was fetched: nothing "
            f"here recognises what body of authority this question belongs to, "
            f"so there is no way to say whether {domains._registered(url)} gets "
            f"to settle it. Fetching anyway would prove the publisher says it "
            f"and prove nothing about whether that matters",
            ask=("Say which body of authority settles this — federal tax, "
                 "US GAAP, state law — or that none does. This question uses "
                 "words the map does not hold, and your answer is what adds "
                 "them."),
            desk=desk.name)

    # BEFORE ANY FETCH (1). The publisher must be competent to settle this.
    if verdict and url and not domains.governs(url, verdict.domain):
        also = ", ".join(d.name for d in verdict.also)
        return engine.Refusal(
            "wrong_body_of_authority",
            f"{citation!r} is in no desk's record, and nothing was fetched: "
            f"{domains._registered(url)} does not settle {verdict.domain.name} "
            f"questions. {verdict.domain.body} does. Proving that a publisher "
            f"really says something is not evidence that it gets to say it",
            ask=(f"This is a {verdict.domain.name} question"
                 + (f" that also reaches {also}" if also else "")
                 + f". Find this in {verdict.domain.body}, or escalate that no "
                   f"authority governing it could be found."),
            desk=desk.name)

    # BEFORE ANY FETCH (2). A wall we put up ourselves stays up.
    if (blocked := walled(url, desk)) is not None:
        return engine.Refusal(
            "source_blocked_by_us",
            f"{citation!r} is in no desk's record, and nothing was fetched: "
            f"{blocked.title} is recorded as {blocked.access}, so its content "
            f"may not reach a model by any route. Finding the same publisher at "
            f"a URL nobody has admitted is the same licence through a different "
            f"door",
            ask=f"Cite authority the firm has admitted, or escalate that "
                f"{blocked.title} is where this is settled and the firm has to "
                f"decide whether to license it.",
            desk=desk.name)

    source = source_for(url, domain=verdict.domain if verdict else None)
    proof = proving.prove_passage(citation, text, source, transport)

    if proof.verdict == proving.DIFFERS:
        return engine.Refusal(
            proving.MOVED,
            f"{citation!r} is in no desk's record, so the fetch was the only "
            f"thing that could have supported it — and the page does not carry "
            f"those words: {proof.note}",
            ask=f"Re-read {proof.url or url} and quote what it actually says, "
                f"or escalate that the authority could not be found.",
            proof=proof, desk=desk.name)

    if not proof.held:
        # COULD NOT, AND HERE IT REFUSES. On a stored citation an unreachable
        # publisher leaves the record still holding the answer. Here the fetch
        # WAS the answer's only support, so there is nothing left to serve on --
        # and the refusal has to say what happened when trying, because that is
        # the only thing this attempt produced that anybody can use later.
        return engine.Refusal(
            "authority_absent",
            f"{citation!r} is in no desk's record, and the publisher could not "
            f"be reached to prove it: {proof.note}. Nothing here is a finding "
            f"about the authority — only about the attempt",
            ask=f"Try {proof.url or url} again, or add this to the record "
                f"cited so a desk holds it and does not depend on a fetch.",
            proof=proof, desk=desk.name)

    return engine.Served(
        position=position,
        citation=citation,
        # REPORTED, BECAUSE THE HOST REALLY IS THAT BODY'S PUBLISHER -- and not
        # acted on, because `tier_for` classifies a host and the record
        # classifies a document. See this module's opening.
        tier=source.tier,
        # AND NOT PRINTED AS THIS DOCUMENT'S TIER, which is a separate flag
        # because this line and the one above disagree on purpose.
        #
        # THE FIX THAT PASSED ITS TESTS AND MISSED PRODUCTION. `classified` was
        # added to `Served` after the first live round trip printed
        # `primary - not binding` above a note saying nobody had classified the
        # document, and the desk that served it said what that costs: "Both
        # cannot be informative ... a tired reader keeps the word 'primary' and
        # drops the paragraph." The flag was then set in `engine._serve`, where
        # `source.id == "candidate"` is checked -- and THIS function builds its
        # own `Served` and never goes through there, so the live candidate path,
        # the only path that has candidates, kept the misleading badge.
        #
        # Found by a review of that commit, not by its tests. The tests
        # exercised the renderer; nothing exercised the caller.
        classified=False,
        checked=source.checked,
        binding=False,
        caveat=(
            f"This was fetched from {source.title} and nobody has classified "
            f"the document. One thing was established: these words are on that "
            f"page today. Whether the page is the rule itself or somebody's "
            f"summary of the rule is not something the firm has looked at, so "
            f"it is not treated as binding on the firm's own work."),
        straddle=engine._straddle_note(verdict, desk),
        # THE READER MUST BE ABLE TO TELL THIS FROM A STORED ANSWER, and freshness
        # is the strength here rather than the weakness: this rests on the page as
        # it reads today and on nothing else. `Served.__str__` prints the tie-out
        # line from the proof; this says what the answer is NOT resting on.
        unchecked=("THIS IS NOT FROM THE RECORD. No desk holds this citation. It "
                   "was fetched from the publisher and served because the words "
                   "below are on that page right now — nothing else supports it, "
                   "and nobody has read it but the answerer. Read the passage."),
        passage=text,
        proof=proof)
