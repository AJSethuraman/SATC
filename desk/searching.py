"""Go and find the authority the record does not hold — and store none of it.

THE FIRM SETTLED THE DESIGN BY KILLING THE OBVIOUS ONE. The first version had an
allow-list: the searcher could reach only publishers already declared on a desk.
Their question ended it in one line — *"how would you know you need to access a
site not on the whitelist before being asked?"* You cannot ask permission for a
site you do not yet know you need, so a list of admitted publishers makes
DISCOVERY the one thing the discovery tool cannot do. It would have found only
what the record already knew about, which is the definition of no use at all.

SO: SEARCH EVERYWHERE. STORING IS THE GATED ACT. `look` applies no host filter of
any kind and `test_the_searcher_looks_everywhere.py` holds it to that. What is
gated is the record: a find from a publisher this desk has declared can become a
passage; a find from anywhere else becomes a SOURCE PROPOSAL and the firm admits
the publisher or does not. The gate moved from the question "may I look here" —
unanswerable in advance — to "may this go in the record", which is exactly the
question the firm is placed to answer, and which they answer after seeing the
passage rather than before.

FOUR THINGS THIS MODULE WILL NOT DO, EACH ENFORCED BY SOMETHING OTHER THAN CARE.

  It cannot answer.        It imports neither `engine` nor `ask`, so there is no
                           path from here to a `Served`. The searcher repairs the
                           record; the record answers. That is an import-graph
                           fact a test asserts, in the manner `proving` learned
                           from `ssl`: a constraint the import graph enforces
                           survives an editor who has not read this paragraph.
  It cannot search idly.   A `Gap` is built only from a refusal that says
                           `authority_absent`. There is no constructor taking a
                           bare question, so the searcher is a repair path for a
                           named hole, never a second way to answer.
  It never stores a
  search result.           The snippet a search engine returns is that engine's
                           summary of a page — truncated, sometimes generated,
                           always someone else's rendering. `check` ignores it
                           entirely and fetches the document, and where a
                           declared source covers the citation it fetches THAT
                           SOURCE'S url rather than the hit's. The hit is a
                           pointer and nothing more.
  It refuses what it
  cannot place.            See AMBIGUOUS below.

WHY THIS NEEDS A CHECK THE EXTRACTOR DOES NOT. `tools/extract_ecfr.py` stores
passages as short as eight characters and is right to: it took them from a known
position in the document's own outline, so the outline is its warrant that the
text belongs to the citation. A searcher has no outline. Its only evidence is
that the words occur in the document — and words that occur four times prove
nothing about WHICH paragraph they came from. So containment is not enough here:
the quoted text must occur EXACTLY ONCE, or the verdict is AMBIGUOUS and the
candidate is refused. Not a length floor, which would be a number nobody
measured; a uniqueness rule, which is the property the length floor was reaching
for.

AND IT MAY NOT ELIDE. A passage recorded for the first time carries no `[...]`.
Marking an omission is a curatorial act taken over text already in the record for
a reason someone can state; a quote read off a page on first sight has no such
reason, and allowing one would let a searcher assemble a sentence the publisher
does not have.
"""
from __future__ import annotations

import re

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from urllib.parse import urlsplit

import comparing
import record
from proving import COULD_NOT, DIFFERS, TIED

#: The one refusal that opens a gap. Held as a literal rather than imported from
#: `engine.REASONS`, because importing `engine` is the thing this module must not
#: do; `test_the_searcher_cannot_answer.py` asserts the two agree.
ABSENT = "authority_absent"

#: Verdicts on a candidate. The first three are `proving`'s, imported rather than
#: restated so a scoreboard can count both kinds of check in one column.
UNCHECKED = "UNCHECKED"
AMBIGUOUS = "AMBIGUOUS"

#: What may become of a checked candidate. Four, and the middle two are not
#: failures: PROPOSE is the whole point of searching outside the record, and HELD
#: says the desk was searched for something it already has — which is a routing
#: defect worth seeing, not a bad result.
STORE, PROPOSE, HELD, REFUSE = "store", "propose a source", "already held", "refuse"


class SearchError(Exception):
    """A caller asked this module to do something it does not do."""


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


@dataclass(frozen=True)
class Gap:
    """The hole that sent us looking, and the desk that has it."""
    question: str
    desk: str
    reason: str
    opened_at: str = ""

    @classmethod
    def from_refusal(cls, refusal, desk_name: str, question: str) -> "Gap":
        """The ONLY way to open a gap.

        A searcher that could be pointed at any question would be a second
        answering path, competing with the record instead of repairing it — and
        the first thing it would do is find on the open web what the desk holds
        three feet away, unverified.
        """
        reason = getattr(refusal, "reason", "")
        if reason != ABSENT:
            raise SearchError(
                f"a gap opens on {ABSENT!r} and this refusal is {reason!r}. "
                f"Searching does not fix it: {getattr(refusal, 'detail', '')}"
            )
        return cls(question=question, desk=desk_name, reason=reason,
                   opened_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))


@dataclass(frozen=True)
class Hit:
    """One result a search engine returned. Not authority, and not evidence."""
    url: str
    title: str = ""
    snippet: str = ""
    query: str = ""

    @property
    def host(self) -> str:
        return _host(self.url)


@dataclass(frozen=True)
class Candidate:
    """A passage read off a publisher, and what checking it against that
    publisher found.

    `found_at` is where the search pointed; `fetched_from` is where the words
    were actually read, and the two differ exactly when a declared source covers
    the citation. Keeping both is what lets a reader see that a quote of the CFR
    turned up on somebody's blog and was verified against eCFR anyway.
    """
    citation: str
    text: str
    kind: str
    found_at: str
    query: str = ""
    source_id: str = ""
    verdict: str = UNCHECKED
    fetched_from: str = ""
    checked: str = ""
    occurrences: int = 0
    note: str = ""

    @property
    def declared(self) -> bool:
        """Whether a source this desk has already declared covers the citation."""
        return bool(self.source_id)


def read(hit: Hit, citation: str, quoted: str, kind: str) -> Candidate:
    """What a reader proposes from a hit: this citation, these exact words.

    `kind` is required and validated for the same reason `parse_passages`
    requires it — a worked example read as a rule is how the first corpus leaked
    its own answer key, and a default here would reopen that without failing
    anything.
    """
    if kind not in record.KINDS:
        raise SearchError(
            f"kind must be one of {record.KINDS}, not {kind!r}. A worked example "
            f"stored as a rule is shown to a model that is being graded on it."
        )
    if comparing.ELLIPSIS in quoted:
        raise SearchError(
            f"a candidate may not elide. {citation} was quoted with "
            f"{comparing.ELLIPSIS!r} in it; record what the page says, and let "
            f"whoever has a reason to cut it do so with the reason on the record."
        )
    if not comparing.normalise(quoted):
        raise SearchError(f"{citation} was quoted with no text at all")
    return Candidate(citation=citation, text=quoted, kind=kind,
                     found_at=hit.url, query=hit.query)


def covering(desk, citation: str):
    """The declared source whose citations begin where this one does, or None."""
    return next((s for s in desk.sources
                 if record.from_source(citation, s.citation_prefix)), None)


def check(cand: Candidate, desk, transport) -> Candidate:
    """Fetch the document and ask whether these words are in it exactly once.

    WHERE IT FETCHES FROM IS THE SAFETY PROPERTY. If a declared source covers the
    citation, the words are checked against THAT source's url — so a correct
    quote of § 1.263(a)-3 found on a tax blog is verified against eCFR, and the
    blog never becomes the publisher of record for it. Only when nothing covers
    the citation is the hit's own url read, and then the candidate can never
    reach STORE: it is a proposal about a publisher, decided by the firm.
    """
    source = covering(desk, cand.citation)
    if source is not None and not source.readable:
        # NEVER FETCHED. `human_only` is the absence of a fetch, not a stricter
        # one, and a searcher reaching for it would be the licence broken by the
        # component whose whole job is to reach.
        return replace(cand, source_id=source.id, verdict=COULD_NOT,
                       note=f"{source.title} is access={source.access!r}: the "
                            f"engine never reaches for it")

    url = source.url if source is not None and source.url else cand.found_at
    try:
        raw = transport(url)
    except Exception as exc:
        return replace(cand, source_id=source.id if source else "",
                       verdict=COULD_NOT, fetched_from=url,
                       note=f"{type(exc).__name__}: {exc}")

    live = comparing.normalise(raw.text if hasattr(raw, "text") else str(raw))
    ours = comparing.normalise(cand.text)
    seen = live.count(ours)
    here = dict(
        source_id=source.id if source else "",
        # THE URL THE BYTES CAME FROM, which is not always the one asked for: a
        # transport may normalise an eCFR page to the versioner XML that serves
        # the same section to a plain client. Recording what was asked for would
        # put a url in the report that a reader following it cannot read.
        fetched_from=getattr(raw, "url", "") or url,
        occurrences=seen,
        checked=(getattr(raw, "at", "") or
                 datetime.now(timezone.utc).isoformat(timespec="seconds"))[:10],
    )
    if seen == 0:
        return replace(cand, verdict=DIFFERS, note=(
            "these words are not in the document that url serves"), **here)
    if seen > 1:
        return replace(cand, verdict=AMBIGUOUS, note=(
            f"the words occur {seen} times in the document, so finding them "
            f"does not show they are {cand.citation}"), **here)
    return replace(cand, verdict=TIED, **here)


#: WHERE A CITATION'S SECTION STOPS AND ITS PARAGRAPHS START. Splitting on the
#: first "(" turns `26 CFR 1.263(a)-2(d)(1)` into `26 CFR 1.263`, because the
#: section name has a parenthesis IN it -- and the firm would be asked to declare
#: a source that does not exist. Matched instead on the shape a section has:
#: number, dot, number, an optional letter, an optional (x), a dash, a number,
#: and an optional trailing letter for the temporary regulations.
_SECTION = re.compile(r"^(.*?\d+\.\d+[A-Z]*(?:\([a-z]\))?-\d+[A-Z]?)")


def section_of(citation: str) -> str:
    """The section a citation names, or the whole citation when it names no
    section at all -- a publication heading, say. Never a truncation."""
    m = _SECTION.match(citation)
    return m.group(1).strip() if m else citation.strip()


def dispose(cand: Candidate, desk) -> tuple[str, str]:
    """What may become of this candidate, and why. NEVER an answer to anything."""
    if cand.verdict == UNCHECKED:
        raise SearchError(
            f"{cand.citation} has not been checked against its publisher. "
            f"Nothing is disposed of on the strength of a search result."
        )
    if desk.passage(cand.citation) is not None:
        return HELD, (
            f"fix the routing, not the record. The desk already holds this and "
            f"still refused the question as {ABSENT}, so what is missing is the "
            f"way to the authority rather than the authority.")
    if cand.verdict != TIED:
        return REFUSE, {
            DIFFERS: "the publisher's document does not carry these words",
            AMBIGUOUS: cand.note,
            COULD_NOT: f"the document could not be read: {cand.note}",
        }[cand.verdict]
    if not cand.declared:
        # WHICH DECISION THIS IS, and they are not the same size. Admitting a
        # publisher nobody here reads is a judgement about who we trust;
        # declaring one more section from a publisher this desk ALREADY reads is
        # a much smaller ask, and putting it to the firm in the bigger words
        # invites them to re-litigate something they have already answered --
        # which is the "asking an answered question" fault in another costume.
        host = _host(cand.fetched_from)
        if host and host in {_host(s.url) for s in desk.sources if s.url}:
            already = sorted({s.citation_prefix for s in desk.sources
                              if s.url and _host(s.url) == host})
            return PROPOSE, (
                f"declare {section_of(cand.citation)} as a source on "
                f"this desk, or leave the gap open. The words tied out, and "
                f"this desk already reads {host} for "
                f"{', '.join(already)} — so this is one more section from a "
                f"publisher you have accepted here, not a new publisher.")
        return PROPOSE, (
            f"admit {host} as a source, or leave the gap "
            f"open. The words tied out there and the desk has not declared it; "
            f"whether it is authority this desk relies on is the firm's to say.")
    source = desk.source(cand.source_id)
    if source.may_store != "full_text":
        return REFUSE, (
            f"cite it, do not copy it. {source.title} is "
            f"may_store={source.may_store!r}, so the firm reads it and takes a "
            f"position; the words do not come into the record.")
    return STORE, (
        f"add it. Tied out once against {source.title}, which this desk already "
        f"relies on, and no passage sits at this citation today.")


def as_passage(cand: Candidate) -> record.Passage:
    """The candidate as authority, carrying NOTHING about how it was found.

    THE JUDGE MUST BE BLIND TO THE SEARCH. Whether a passage answers a question
    is the same question whether the passage was extracted last month or found
    this minute, and a judge that could see the query, the ranking or the
    snippet would be reading the searcher's confidence as evidence about the law.
    So the handover is a `record.Passage` — the same shape `parse_passages`
    produces — and there is nowhere in it for any of that to travel.
    """
    if cand.verdict != TIED:
        raise SearchError(
            f"{cand.citation} is {cand.verdict}, and only a passage that tied out "
            f"against its publisher becomes authority")
    if not cand.declared:
        raise SearchError(
            f"{cand.citation} came from {_host(cand.fetched_from)}, which no "
            f"declared source covers. It is a proposal about a publisher, and a "
            f"passage exists only once the firm has admitted one")
    return record.Passage(citation=cand.citation, source_id=cand.source_id,
                          checked=cand.checked, text=cand.text, kind=cand.kind)


@dataclass(frozen=True)
class Finding:
    """One hit, followed all the way through, with what became of it."""
    hit: Hit
    disposition: str
    why: str
    candidate: Candidate | None = None


@dataclass(frozen=True)
class Search:
    """A gap, everything asked about it, and what came back.

    RECORDED EVEN WHEN NOTHING CAME OF IT, because a gap that was searched and
    found empty and a gap nobody has searched are the same hole in the record and
    call for opposite next steps. `hits` is every result seen, including the ones
    read as not authority at all: the count is this operation's noise floor, and
    it is a measurement rather than an impression.
    """
    gap: Gap
    queries: tuple[str, ...] = ()
    hits: tuple[Hit, ...] = ()
    findings: tuple[Finding, ...] = ()

    def of(self, disposition: str) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.disposition == disposition)


def look(gap: Gap, queries, engine) -> tuple[Hit, ...]:
    """Run the queries. NO HOST FILTER, DELIBERATELY — see this file's header.

    `engine` is injected for the reason every transport in this plugin is: the
    suite replaces the socket layer, and a searcher that imported its own client
    would be a searcher no test could run.
    """
    out, seen = [], set()
    for q in queries:
        for r in engine(q) or ():
            url = r.url if hasattr(r, "url") else r.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(Hit(url=url, query=q,
                           title=getattr(r, "title", None) or (
                               r.get("title", "") if isinstance(r, dict) else ""),
                           snippet=getattr(r, "snippet", None) or (
                               r.get("snippet", "") if isinstance(r, dict) else "")))
    return tuple(out)
