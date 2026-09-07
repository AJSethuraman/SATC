"""Run one gap through the searcher, against the live publishers.

WHERE THE MODEL STOPS AND THE ENGINE STARTS, WHICH IS THE POINT OF THE SEAM.
Two of the four steps are judgement and cannot be anything else, and two are
mechanical and must not be anything else:

    1. turn a refused question into search queries        the model
    2. read a page and say WHICH citation these words are the model
    3. fetch, tie out, and decide what may be stored       THIS TOOL
    4. admit a publisher, ratify a position                the firm

So the input here is what the model PROPOSES — a citation, the exact words it
read, and where it read them — and nothing this file does can be talked out of
step 3. `searching.check` re-fetches rather than trusting the quoted page, and
where a declared source covers the citation it fetches that source instead. A
proposal that names the wrong paragraph, or quotes words the publisher does not
have, or quotes words the publisher has four times, fails here regardless of how
confident the reading was.

IT WRITES NOTHING INTO A DESK. The report says what could be stored; adding it is
`tools/add_examples.py`, which refuses anything the firm has not admitted. A
searcher that could write its own finds into the record would be a model
ratifying its own research, and the whole two-store split exists to stop that.

    python3 tools/search_run.py found.json > SEARCH.md

`found.json` is `{desk, question, reason, queries[], hits[], proposals[]}`. Hits
are recorded even when nothing was read off them: the count is this operation's
noise floor, and a gap searched and found empty is a different fact from a gap
nobody has searched.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
for p in (str(HERE), str(HERE / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import record                                               # noqa: E402
import searching                                            # noqa: E402
import tieout                                               # noqa: E402

DESKS = HERE / "desks"


class _Refused:
    """The refusal the record actually made, carried in so `Gap.from_refusal`
    can turn it down. Reconstructed from the run rather than assumed: a gap that
    opens on a reason nobody recorded is a search with no warrant."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason, self.detail = reason, detail


def transport(url: str):
    """The live fetch, borrowed from the corpus tie-out rather than rewritten.

    `comparing.py` exists because this repository once kept two copies of one
    comparison and they disagreed within a week. The same argument applies to
    reaching a publisher: one user agent, one retry rule, one PDF reader.
    """
    if "ecfr.gov" in url:
        # THE SAME NORMALISATION THE CORPUS TIE-OUT DOES, and the searcher is
        # what proved it was needed for a second URL shape. eCFR serves a plain
        # client a JavaScript shell; the versioner serves the section as dated
        # XML. A desk records the short `/title-26/section-X` form because a
        # person typed it, and a search engine returns the full outline form —
        # which `_ecfr_url` did not recognise until this ran against it.
        url = tieout._ecfr_url(url)
    raw = tieout._fetch(url)
    text = (tieout._pdf_text(raw) if url.lower().endswith(".pdf")
            else tieout._markup_text(raw))
    return tieout.Fetched(text, url, "", len(raw), tieout.datetime.now(
        tieout.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"))


def run(spec: dict) -> searching.Search:
    desk = record.load(DESKS / spec["desk"])
    gap = searching.Gap.from_refusal(
        _Refused(spec.get("reason", searching.ABSENT), spec.get("detail", "")),
        spec["desk"], spec["question"])

    hits = tuple(searching.Hit(url=h["url"], title=h.get("title", ""),
                               snippet=h.get("snippet", ""), query=h.get("query", ""))
                 for h in spec.get("hits", ()))

    findings = []
    for prop in spec.get("proposals", ()):
        hit = next((h for h in hits if h.url == prop["found_at"]),
                   searching.Hit(url=prop["found_at"], query=prop.get("query", "")))
        missing = [k for k in ("citation", "quoted", "found_at") if k not in prop]
        if missing:
            # A KeyError here is a traceback at whoever is running this, on a
            # machine that may be nobody's. Say which key, and say it in the
            # words the file uses -- `quoted`, not `text`, which is what the
            # skill's own example got wrong until this ran.
            findings.append(searching.Finding(
                hit, searching.REFUSE,
                f"the proposal has no {', '.join(missing)}. A proposal needs "
                f"`citation`, `quoted` (the words EXACTLY as printed) and "
                f"`found_at`."))
            continue
        try:
            cand = searching.read(hit, prop["citation"], prop["quoted"],
                                  prop.get("kind", ""))
        except searching.SearchError as exc:
            findings.append(searching.Finding(hit, searching.REFUSE, str(exc)))
            continue
        cand = searching.check(cand, desk, transport)
        what, why = searching.dispose(cand, desk)
        findings.append(searching.Finding(hit, what, why, cand))

    return searching.Search(gap=gap, queries=tuple(spec.get("queries", ())),
                            hits=hits, findings=tuple(findings))


def report(s: searching.Search) -> str:
    """What a person reads. THE RECOMMENDATION IS THE FIRST LINE OF EACH ENTRY.

    Not a house style. A card that spends four labelled blocks setting up its own
    conclusion makes the reader do the assembling, and the firm said so in as
    many words on 7 September 2026 — asked to lead with the most important point.
    So each finding opens on what it is asking for, and the evidence sits under
    it for whoever wants to check.
    """
    read = len(s.findings)
    out = [f"# {s.gap.question}",
           "",
           f"`{s.gap.desk}` refused this as **{s.gap.reason}**. "
           f"{len(s.queries)} quer{'y' if len(s.queries) == 1 else 'ies'}, "
           f"{len(s.hits)} results, {read} read.",
           ""]

    for what, heading in ((searching.STORE, "Ready to add"),
                          (searching.PROPOSE, "Waiting on the firm"),
                          (searching.HELD, "Already held — the routing is the gap"),
                          (searching.REFUSE, "Refused")):
        group = s.of(what)
        if not group:
            continue
        out += [f"## {heading} ({len(group)})", ""]
        for f in group:
            c = f.candidate
            out += [f"**{c.citation if c else f.hit.url}** — {f.why}", ""]
            if c is not None:
                out += [f"> {c.text}", "",
                        f"Found at {f.hit.url}"
                        + (f", read from {c.fetched_from}"
                           if c.fetched_from and c.fetched_from != f.hit.url else "")
                        + f" · {c.verdict}"
                        + (f", {c.occurrences}×" if c.occurrences else "")
                        + (f" · {c.checked}" if c.checked else ""), ""]

    seen = {f.hit.url for f in s.findings}
    rest = [h for h in s.hits if h.url not in seen]
    if rest:
        out += [f"## Not read ({len(rest)})", "",
                "Results nobody read a passage off. This is the noise floor, "
                "measured rather than described.", ""]
        out += [f"- {h.url}" for h in rest] + [""]
    return "\n".join(out)


if __name__ == "__main__":                                  # pragma: no cover
    if len(sys.argv) != 2:
        sys.exit("usage: search_run.py found.json > SEARCH.md\n"
                 "  found.json: {desk, question, reason, queries[], hits[], "
                 "proposals[]}\n"
                 "  a proposal: {citation, quoted, found_at, kind}")
    print(report(run(json.loads(pathlib.Path(sys.argv[1]).read_text()))))
