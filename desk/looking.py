"""The desk goes and looks — and hands what it finds to the firm, never serves it.

`dec-lookjoin`, 11 September 2026 — the firm: **"Run it by me — build it."**
Their own earlier words, which this is built to:

    "if it is not directly authoritative it would run the opinion by me."

WHAT WAS MISSING, AND IT WAS THE JOIN AND NOT THE SEARCHER. `searching.py` has
worked since 8 September: it searches anywhere, fetches the publisher's own page,
and refuses a quote it cannot place in that page exactly once. Nothing on the
answering path imported it. The only caller was `tools/search_run.py`, which a
person runs by hand against a JSON file — so a question asked during a close
reached a parked hole and stopped there, and the firm was told three times over
that the desk goes and looks while it did not.

THIS MODULE IS THE JOIN AND NOTHING ELSE. It owns no searching, no fetching and
no verdicts; every one of those is `searching`'s, unchanged. What it adds is the
one thing `searching` is forbidden to have — a way back to the answering path —
and the shape of that way back is the firm's answer: **park it and tell them.**

NOTHING FOUND BY SEARCHING IS EVER SERVED. Not the non-binding find, which is
what the firm ruled on; and not the binding one either, which they did not have
to rule on because the record already says so. `searching.dispose` returns STORE
for a passage that ties out against a source the firm has already admitted — and
STORE means *this may be added by pull request*, never *this may be answered
from now*. A find that skipped the merge would be a model writing the record it
then reads, which is the whole of what the two-store split exists to stop. So
every disposition lands in the same place here: the queue, and a line to the
firm. What differs is what the line SAYS.

WHY THE SEAM IS A CALLABLE AND NOT A URL. Two of the four steps in a search are
judgement and cannot be anything else — turning a refused question into queries,
and reading a page to say which citation these words are. A model does those. So
this takes them as arguments, exactly as `tools/search_run.py` takes them from a
file, and the engine and transport are injected for the reason every transport
in this plugin is: a test must be able to run the whole path without a network,
and `conftest.py` replaces the socket layer to prove nothing here reaches one by
accident.

WHAT A CALLER THAT CANNOT SEARCH GETS. Exactly what it got before. `ask` calls
this only when it is handed a search engine, so a close run somewhere with no
browser behaves as it did on 10 September rather than failing in a new way.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import domains
import engine
import notifying
import record
import searching
import unsupported

#: WHAT THE FIRM IS TOLD IN THE FIRST THREE WORDS, per disposition. `notifying`
#: keeps its verbs a fixed set on purpose — a model composing the wording is a
#: model deciding how alarming its own finding is.
VERBS = {
    searching.STORE: "Desk found",
    searching.PROPOSE: "Desk found",
    # NOT "Desk found", and not "Desk parked" either. HELD means the search
    # landed on a paragraph the record already carries, so nothing was found
    # and nothing is missing -- what is missing is the way to it. The firm
    # reading "Desk found" would go looking for a source to admit.
    searching.HELD: "Desk could not reach",
    searching.REFUSE: "Desk parked",
}


@dataclass(frozen=True)
class Looked:
    """What the desk did when the record held nothing, and where it went.

    `search` is `searching`'s own record of it, unedited. `entry` is the queue
    row the firm will answer. `told` is the exact characters sent, or empty when
    there was nothing sendable — `notifying.line` refuses a question that looks
    like it carries a name or a number, and a refusal to notify must not become
    a refusal to file.
    """
    search: searching.Search
    entry: unsupported.Unsupported
    told: str = ""

    @property
    def worth_the_firms_time(self) -> bool:
        """Whether anything tied out at all. A search that found nothing is a
        real result and is filed — it turns a gap nobody has examined into one
        somebody has — but it is not a finding to put in front of the firm as
        though it were."""
        return bool(self.search.of(searching.STORE)
                    or self.search.of(searching.PROPOSE))


def _how_binding(cand: searching.Candidate, desk) -> str:
    """How much weight this carries, in the words a reader already has.

    READ OFF THE RECORD, NEVER OFF THE HOST. `domains.tier_for` grades a
    PUBLISHER, and irs.gov publishes the regulations and its own plain-English
    guides alike; the record grades a document because a person read it. A
    candidate is a document nobody has read, so the honest answer is that nobody
    has graded it — and saying so is the finding the firm is being asked about.
    """
    if cand.declared:
        source = desk.source(cand.source_id)
        return (f"{source.tier} authority, and the firm has already admitted "
                f"{source.title}")
    return ("NOT graded. Nobody has read this document, so nothing here says "
            "how binding it is — which is the decision being put to you")


def _finding_line(f: searching.Finding, desk) -> str:
    cand = f.candidate
    if cand is None:
        return f"{f.hit.url} — {f.why}"
    return (f"{cand.citation} — {_how_binding(cand, desk)}. "
            f"Read at {cand.fetched_from or cand.found_at}. {f.why}")


def _working(s: searching.Search, desk) -> str:
    """What goes into the queue row's own reasoning, so `tools/holes.py` reads
    out a hole that was searched rather than one that was only recorded.

    NO PASSAGE TEXT. This file lands in the repository. The citation, the
    publisher and the verdict are what a decision is made from; the words
    themselves are in the document at the url, where the firm reads them with
    the rest of the paragraph around them rather than as a quote somebody chose.
    """
    out = [f"Searched. {len(s.queries)} quer{'y' if len(s.queries) == 1 else 'ies'}, "
           f"{len(s.hits)} hit{'' if len(s.hits) == 1 else 's'}, "
           f"{len(s.findings)} read."]
    if not s.findings:
        out.append(
            "Nothing was read off any of them. A gap searched and found empty "
            "is a different fact from a gap nobody has searched, which is why "
            "this is filed rather than dropped.")
    for f in s.findings:
        out.append(f"[{f.disposition}] {_finding_line(f, desk)}")
    return "\n".join(out)


def run(question: str, *, corpus: Path, queue: Path, queries, proposals,
        engine_, transport, model: str = "") -> Looked:
    """Search for the authority the record does not hold, and file what came back.

    RETURNS NOTHING SERVEABLE, BY CONSTRUCTION. There is no path from here to a
    `Served`: this hands back a queue entry and the characters to send, and a
    caller wanting an answer has to get it from the record after the firm has
    admitted what was found. `test_the_join_can_never_answer` holds that.
    """
    desk = record.load(corpus)
    gap = searching.Gap.from_refusal(
        engine.Refusal(
            "authority_absent",
            f"nothing on file shares this question's language: {question}"),
        desk.name, question)

    hits = searching.look(gap, queries, engine_)
    by_url = {h.url: h for h in hits}

    # THE BODY OF AUTHORITY, DECIDED ONCE, FROM THE FIRM'S OWN MAP. Passed to
    # `dispose` rather than worked out inside it — see its docstring and the
    # 7 September lease incident: four IRS passages tied out perfectly and were
    # still the wrong body of authority for the question asked.
    verdict = domains.classify(question)

    findings = []
    for prop in proposals or ():
        hit = by_url.get(prop.get("found_at", ""),
                         searching.Hit(url=prop.get("found_at", ""),
                                       query=prop.get("query", "")))
        missing = [k for k in ("citation", "quoted", "found_at") if not prop.get(k)]
        if missing:
            findings.append(searching.Finding(
                hit, searching.REFUSE,
                f"the proposal has no {', '.join(missing)}. A proposal needs "
                f"`citation`, `quoted` (the words EXACTLY as printed) and "
                f"`found_at`."))
            continue
        try:
            cand = searching.read(hit, prop["citation"], prop["quoted"],
                                  prop.get("kind", ""))
            cand = searching.check(cand, desk, transport)
        except searching.SearchError as exc:
            findings.append(searching.Finding(hit, searching.REFUSE, str(exc)))
            continue
        what, why = searching.dispose(
            cand, desk, verdict.domain if verdict else None,
            verdict.also if verdict else ())
        findings.append(searching.Finding(hit, what, why, cand))

    search = searching.Search(gap=gap, queries=tuple(queries or ()),
                              hits=hits, findings=tuple(findings))

    existing = (unsupported.parse(queue.read_text(encoding="utf-8"))
                if queue.exists() else [])
    entry = unsupported.from_question(
        question,
        why=_working(search, desk),
        model=model,
        existing=existing,
    )
    unsupported.append(queue, entry)

    # THE VERB IS THE LOUDEST THING THE FIRM READS, so it says what happened
    # rather than that something did. A find they have to rule on and a gap that
    # stayed empty are different asks and must not open with the same three
    # words.
    # HELD COUNTS AS SOMETHING TO SAY, and it very nearly did not. It means the
    # record already carries the citation the search landed on -- so the
    # authority is not missing and the way to it is, which is a defect in
    # retrieval and the most actionable thing a search comes back with. Ranked
    # below a real find and above silence.
    best = next((f for f in search.findings
                 if f.disposition in (searching.STORE, searching.PROPOSE)), None)
    if best is None:
        best = next((f for f in search.findings
                     if f.disposition == searching.HELD), None)
    told = ""
    try:
        told = notifying.line(
            question, ref=entry.id,
            why=(("already on file: " + best.candidate.citation
                   if best.disposition == searching.HELD and best.candidate
                   else _finding_line(best, desk).split(" Read at ")[0])
                 if best else "searched, nothing tied out"),
            verb=VERBS.get(best.disposition if best else searching.REFUSE,
                           "Desk parked"))
    except ValueError:
        # A REFUSAL TO NOTIFY IS NOT A REFUSAL TO FILE. `notifying.line` raises
        # where the question looks like it carries a name or a figure, and the
        # entry is already in the queue by then — losing it because the outward
        # half would not send is the worst of both.
        told = ""
    return Looked(search=search, entry=entry, told=told)
