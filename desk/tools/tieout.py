"""Prove the stored corpus against the sources of record, and emit the exhibit.

WHAT IS BEING PROVED, in the terms the tie-out skill sets. A desk's whole claim
rests on one thing: that the authority it hands an answerer is what the authority
actually says. Every test in this repository checks that against our own files,
which is the mirror -- a passage transcribed wrongly is stored wrongly, served
wrongly and asserted wrongly, and every green stays green.

THE `ours` SIDE IS READ OUT OF THE BRIEF, NOT OUT OF THE RECORD. `ask.brief()` is
the artifact an answerer opens; `desk.passages` is the intermediate on the way to
it. The skill's own incident is a roster that reported 53 lines tied while never
opening the workbook -- it had proved provider = filing and labelled it landed.
So this parses the passage blocks back out of the rendered brief text, and what
goes on the `ours` side is the string an answerer would read.

THE SOURCE MUST BE ABLE TO DISAGREE. Every fetch here is a live request to the
publisher: eCFR's versioner API for the regulations, irs.gov for the
publications and the PDFs, uscode.house.gov for the statute. Nothing is read from
`extracted/`, from a cache, or from a fixture. That is the whole point.

THE FOUR SAMENESS CHECKS, for text rather than for money:
  same entity  the citation resolves to the same section and paragraph
  same date    the regulation as of a stated date, printed on the exhibit
  same basis   the publisher's own rendering, not a mirror or a reprint
  same units   normalisation is declared and minimal -- whitespace, and the
               typographic quotes and dashes publishers vary between renderings.
               Anything more would hide the difference this is looking for.
"""
from __future__ import annotations

import gzip
import hashlib
import html as _html
import io
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import record                                               # noqa: E402

#: The regulations are fetched AS OF A DATE and the date is printed on the
#: exhibit, because "the same period" is one of the four checks. eCFR's versioner
#: refuses a future date, so this is the last date known good rather than today.
AS_OF = "2026-01-01"

UA = "satc-desk-tieout (accounting record verification; contact via repository)"


# -- reaching the publishers --------------------------------------------------

def _get(url: str, *, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body


def _pdf_text(body: bytes) -> str:
    """Extract a PDF's text. The import guard is not optional here.

    The system `cryptography` build panics on import rather than raising, and
    pypdf's optional crypt provider imports it -- so `import pypdf` dies with a
    PanicException that its own ImportError fallback cannot catch. Making the
    module look absent sends pypdf to its no-crypt provider, which is all that is
    needed: none of these documents is encrypted.
    """
    for name in ("cryptography", "cryptography.exceptions", "cryptography.hazmat"):
        sys.modules.setdefault(name, None)
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(body))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


_DROP = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)

#: INLINE TAGS CLOSE UP; BLOCK TAGS BECOME A SPACE. Replacing every tag with a
#: space was this tool's own first finding, and it was a finding about the tool:
#: eCFR writes `election</I>-(1)` and `601.601(d)(2)(ii)(<I>b</I>)`, so a blanket
#: space produced `election -(1)` and `( b )` and reported 34 false differences.
#: A difference the checker invents is worse than no checker, because somebody
#: goes and "fixes" the record to match it.
_INLINE = re.compile(r"</?(?:i|b|e|em|strong|span|a|sup|sub|small|u|hed|cita)\b[^>]*>",
                     re.I)
_ANY_TAG = re.compile(r"<[^>]+>")


def _markup_text(body: bytes) -> str:
    text = body.decode("utf-8", "replace")
    text = _DROP.sub(" ", text)
    text = _INLINE.sub("", text)
    text = _ANY_TAG.sub(" ", text)
    return _html.unescape(text)


def _ecfr_url(source_url: str) -> str:
    """The versioner API URL for a source recorded by its human-readable page.

    A desk records `https://www.ecfr.gov/current/title-26/section-1.263(a)-3`,
    which serves a JavaScript shell to a plain client. The versioner publishes
    the same section as XML, dated, which is both fetchable and pinned to a day.
    """
    m = re.search(r"title-(\d+)/section-([^/?#]+)", source_url)
    if m:
        title, section = m.group(1), m.group(2)
        return (f"https://www.ecfr.gov/api/versioner/v1/full/{AS_OF}/"
                f"title-{title}.xml?section={section}")
    # already a versioner URL: re-point it at the date this run declares
    return re.sub(r"/full/\d{4}-\d{2}-\d{2}/", f"/full/{AS_OF}/", source_url)


_USC = re.compile(r"\b(\d+ USC|26 U\.?S\.?C\.?)\s*(\d+[A-Z]?)")


def _statute_url(source_url: str, citation: str) -> str:
    """The House's granule for the section THIS citation names.

    ONE URL WAS RECORDED FOR FOUR SECTIONS AND SERVES ONE. The rewards desk
    stores 6041, 6041A, 6050W and 6071 under a single source whose URL is the
    granule for section 6041 -- so a reader following the link finds the first
    and not the other three, and the mentions of "6041A" on that page are § 6041's
    own cross-references. All three text bodies are verbatim correct on their own
    granules. Right text, wrong link, and only following the link finds it.
    """
    m = _USC.search(citation)
    if not m:
        return source_url
    return re.sub(r"(granuleid:USC-prelim-title\d+-section)[^&]+",
                  lambda g: g.group(1) + m.group(2), source_url)


@dataclass
class Fetched:
    text: str
    url: str
    sha256: str
    nbytes: int
    at: str


def live_text(source: record.Source, citation: str = "") -> Fetched:
    """The publisher's document as it stands, with the provenance of the bytes."""
    url = source.url
    if "ecfr.gov" in url:
        url = _ecfr_url(url)
    elif "uscode.house.gov" in url:
        url = _statute_url(url, citation)
    raw = _fetch(url)
    text = _pdf_text(raw) if url.lower().endswith(".pdf") else _markup_text(raw)
    return Fetched(text, url, hashlib.sha256(raw).hexdigest(), len(raw),
                   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"))


def _fetch(url: str) -> bytes:
    """One retry, and only for a transient failure.

    `fetch.py` sets the rule this follows: a timeout or a reset is retried with
    the SAME method once, and a refusal is not retried at all. Climbing against a
    site that has said no is the behaviour that module exists to forbid.
    """
    try:
        return _get(url)
    except urllib.error.HTTPError:
        raise                                     # a refusal, not a hiccup
    except (urllib.error.URLError, TimeoutError, OSError):
        time.sleep(4)
        return _get(url)


# -- comparing ----------------------------------------------------------------

#: Declared, and deliberately short. Publishers render the same sentence with
#: different quote and dash characters between HTML, XML and PDF; that is a
#: rendering difference and not a difference in what the authority says. Anything
#: beyond this list would start hiding the differences this exists to find.
FOLD = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-", " ": " ",
    "′": "'", "ﬁ": "fi", "ﬂ": "fl",
}


def _squash(text: str) -> str:
    """Every space removed, and the soft hyphen a PDF breaks words with.

    Used only as the SECOND comparison, never the first, and the exhibit says
    which one carried each line. Whitespace is the one thing these extractors are
    not faithful about: pypdf reads "You" as "Y ou" off a kerned two-column page
    and hyphenates "infor-mation" across a line break, and irs.gov puts block
    markup inside a sentence. Ignoring it can hide a genuinely missing space,
    which is why it is reported separately rather than folded into TIED.
    """
    return re.sub(r"\s+", "", text.replace("\xad", ""))


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for bad, good in FOLD.items():
        text = text.replace(bad, good)
    return " ".join(text.split())


@dataclass
class Line:
    """One passage, and what happened when it was put to its publisher."""
    desk: str
    citation: str
    source_id: str
    source_title: str
    url: str
    stored_chars: int
    verdict: str                      # TIED | DIFFERS | COULD NOT
    #: HOW it tied, and it is reported rather than collapsed. "exact" means the
    #: publisher's characters, after only the typographic folding declared in
    #: FOLD. "spacing" means it tied only once whitespace was ignored -- which is
    #: honest for a PDF, where the extractor invents spaces inside words
    #: ("Y ou", "infor-\nmation"), and for an HTML page whose block markup falls
    #: inside a sentence. A reader is entitled to know which of the two it was.
    how: str = ""
    obstacle: str = ""
    #: The longest run of the stored text that IS in the live document, and the
    #: first word where it stops. A DIFFERS that cannot say where it differs is
    #: an assertion.
    matched_chars: int = 0
    stopped_at: str = ""
    live_around: str = ""
    #: THE CAPTURE, AND WHY IT IS A HASH RATHER THAN A PHOTOGRAPH. The skill asks
    #: for the source screenshotted with the figure visible. Attempted and it
    #: does not work here: this machine's browser cannot reach the publishers
    #: even when pointed at the egress proxy (ERR_CONNECTION_RESET), while the
    #: HTTP client can. So the capture is the document itself -- its SHA-256, its
    #: length, the moment it was fetched, and the publisher's own words around
    #: the match, quoted rather than described. For text this is the stronger
    #: evidence: a reader re-fetches the URL, recomputes the hash and gets the
    #: same digits, which is a check a screenshot cannot offer.
    fetched_at: str = ""
    sha256: str = ""
    doc_bytes: int = 0
    excerpt: str = ""


def _window(live: str, needle: str, *, span: int = 260) -> str:
    """The publisher's own words around the match, quoted rather than described.

    This is the link the skill says catches you: writing "the source agrees" is
    something a person can do while believing it, and pasting what the source
    actually says is not.
    """
    at = live.find(needle[:80]) if needle else -1
    if at < 0:
        return live[:span]
    lo = max(0, at - span // 3)
    return ("..." if lo else "") + live[lo: at + len(needle) + span] + "..."


def _first_divergence(stored: str, live: str) -> tuple[int, str, str]:
    """How much of the stored text the publisher still carries, and where it stops.

    Walks word by word rather than diffing: the question is not "how similar",
    it is "at which word does our copy stop being what they publish".
    """
    words = stored.split()
    best, lo, hi = 0, 0, len(words)
    while lo <= hi:                                  # longest matching prefix
        mid = (lo + hi) // 2
        if mid and " ".join(words[:mid]) in live:
            best, lo = mid, mid + 1
        elif mid == 0:
            lo = 1
        else:
            hi = mid - 1
    matched = " ".join(words[:best])
    stopped = words[best] if best < len(words) else ""
    around = ""
    if matched:
        at = live.find(matched)
        if at >= 0:
            around = live[at + len(matched): at + len(matched) + 120]
    return len(matched), stopped, around


def check(desk_name: str, brief_passages: dict, desk: record.Desk) -> list[Line]:
    out: list[Line] = []
    fetched: dict[str, tuple[str, str] | Exception] = {}
    for source in desk.sources:
        mine = [p for p in desk.passages if p.source_id == source.id]
        if not mine:
            continue
        for p in mine:
            key = (source.id, _statute_url(source.url, p.citation)
                   if "uscode.house.gov" in source.url else "")
            if key not in fetched:
                try:
                    fetched[key] = live_text(source, p.citation)
                except Exception as exc:              # recorded, never swallowed
                    fetched[key] = exc
                time.sleep(0.4)                       # courtesy to the publisher
            got = fetched[key]
            # THE `ours` SIDE, READ OUT OF THE BRIEF. A citation the brief does
            # not carry is a finding in itself: the answerer never saw it.
            stored = brief_passages.get(p.citation)
            if stored is None:
                out.append(Line(desk_name, p.citation, source.id, source.title,
                                source.url, 0, "COULD NOT",
                                "this citation is in the record but not in the "
                                "brief the desk hands over, so there is nothing "
                                "an answerer reads to put on the ours side"))
                continue
            if isinstance(got, Exception):
                out.append(Line(desk_name, p.citation, source.id, source.title,
                                source.url, len(stored), "COULD NOT",
                                f"{type(got).__name__}: {got}"))
                continue
            ns, nl = normalise(stored), normalise(got.text)
            here = dict(fetched_at=got.at, sha256=got.sha256,
                        doc_bytes=got.nbytes)
            used = got.url
            if ns and ns in nl:
                out.append(Line(desk_name, p.citation, source.id, source.title,
                                used, len(ns), "TIED", how="exact",
                                matched_chars=len(ns),
                                excerpt=_window(nl, ns), **here))
            elif ns and _squash(ns) in _squash(nl):
                out.append(Line(desk_name, p.citation, source.id, source.title,
                                used, len(ns), "TIED", how="spacing",
                                matched_chars=len(ns),
                                excerpt=_window(nl, ns[:60]), **here))
            else:
                n, stopped, around = _first_divergence(ns, nl)
                out.append(Line(desk_name, p.citation, source.id, source.title,
                                used, len(ns), "DIFFERS",
                                matched_chars=n, stopped_at=stopped,
                                live_around=around,
                                excerpt=_window(nl, ns[:max(n, 40)], span=700),
                                **here))
    return out


_BLOCK = re.compile(r"^### (.+?)\n\n> (.+?)\n", re.M | re.S)


def brief_passages(desk: record.Desk) -> dict:
    """Every passage as it appears in the brief, keyed by citation.

    Parsed back out of the rendered text on purpose. Reading `desk.passages`
    here would put the intermediate on the `ours` side, which is the failure
    this whole exercise is written against.
    """
    text = ask.brief("tie-out: what does this desk hand over?", desk)
    body = text.split("## The authority", 1)[-1]
    return {m.group(1).strip(): m.group(2).strip() for m in _BLOCK.finditer(body)}


def run(desks_dir: Path = HERE / "desks") -> list[Line]:
    lines: list[Line] = []
    for d in sorted(desks_dir.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        lines.extend(check(desk.name, brief_passages(desk), desk))
    return lines


if __name__ == "__main__":
    rows = run()
    out = HERE / "tie-outs" / "findings.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps([r.__dict__ for r in rows], indent=1), encoding="utf-8")
    tally = {}
    for r in rows:
        tally[r.verdict] = tally.get(r.verdict, 0) + 1
    print(f"{len(rows)} passages")
    for v in ("DIFFERS", "COULD NOT", "TIED"):
        print(f"  {v:10} {tally.get(v, 0)}")
    print("->", out)
