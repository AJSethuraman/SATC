"""The gate a pack has to pass before it can leave the building.

WHY THIS EXISTS. On 27 August 2026 the firm opened a document that had been
sent to them as proof the system worked and asked: *"these html files are plain
text?"* They were. Every template links `satc-doc.css` and `doc-page.js` by
relative path and the pack copied neither, so every document in every pack
opened with no masthead, no rules, browser-default Times. With ``--no-pdf``
that was the entire deliverable.

Nothing caught it. Not the 749 tests -- they read the HTML as strings and
assert on its tokens, which is exactly right for checking a merge and totally
blind to whether the thing renders. Not ``check``, because ``check`` was
optional and an optional gate is a suggestion. And not me: I had published "190
documents produced, 0 surprises" having read those files as strings and never
opened one.

So this module asks the four questions that were never asked, on the real pack,
on its way to a real client:

  1. Does every document actually RENDER -- in a browser, not in a string?
  2. Is every file each document REFERENCES actually in the pack?
  3. Do the documents in the pack AGREE with each other?
  4. (reserved) Do they honour the document tenets?

THE FIRM'S CHOICE, 27 August 2026: blocking, with a logged override. A gate
with no override will one day stop a return going out at 11pm on the 14th and
there will be nothing to do about it. A gate that can be waved through silently
is not a gate. So ``--force`` writes the pack and records what failed and why
into the engagement's own file, where it can be read back at year end.

The findings are deliberately plain about which check failed and on which
document. A check that announces a failure and refuses to name it is barely
better than no check -- see the hourly-copy check in the website spec, which
failed with the message "Missing []" and cost half an hour.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import consistency
import merge

# Files a pack is expected to carry beside the documents. Kept here rather than
# in cli so the gate can say "this is missing" without importing the command.
PACK_ASSETS = ("satc-doc.css", "doc-page.js")

# Chromium. The repo's sandbox ships one at a known path; anywhere else,
# Playwright's own resolution is used.
CHROMIUM = os.environ.get("SATC_CHROMIUM") or "/opt/pw-browsers/chromium"


@dataclass(frozen=True)
class Finding:
    """One thing wrong with a pack.

    ``blocking`` is the whole design. Exact checks -- a document that does not
    render, a file it references that is not there -- block. Judgement calls
    advise, and are promoted to blocking only after a cycle with no false
    positive. A linter that cries wolf gets muted, and then it is worse than
    nothing.
    """

    check: str
    document: str
    detail: str
    blocking: bool = True

    def line(self) -> str:
        mark = "BLOCK" if self.blocking else "note "
        return f"  {mark}  {self.document}\n         {self.detail}"


@dataclass
class Counted:
    """What a check found, AND what it looked at to find it.

    SOFTWARE-TENETS S2: a green result from a check that examined nothing is
    worse than a red one. This is not hypothetical here. `cited_clauses` ran
    on all 29 packs and printed "ok every cited clause name is a real section"
    every time -- while examining ZERO citations, because all seven live in the
    delivery, disengagement, extension and invoice documents and none of those
    is in the opening pack. The check was right, useless, and indistinguishable
    from a check that was working.

    The count is not computed separately from the check; each check builds its
    census and then walks it, so the number reported is the number of things
    the check actually put its eyes on. Two functions that must agree about a
    denominator will one day disagree (S3).
    """

    findings: list[Finding] = field(default_factory=list)
    examined: int = 0
    unit: str = "item"
    units: str = ""            # plural, where "unit + s" would read wrong

    def counted(self) -> str:
        n = self.examined
        if n == 1:
            return f"1 {self.unit}"
        return f"{n} {self.units or self.unit + 's'}"

    def line(self, what: str) -> str:
        if not self.examined:
            return (f"  NONE   {what} — {self.counted()} to examine, so this "
                    f"is not known to be right")
        mark = "FAIL " if any(f.blocking for f in self.findings) else "ok   "
        return f"  {mark}  {what} — {self.counted()} examined"


@dataclass
class Result:
    findings: list[Finding] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    counts: list[tuple[str, Counted]] = field(default_factory=list)

    def add(self, what: str, got: Counted) -> None:
        self.checked.append(what)
        self.counts.append((what, got))
        self.findings += got.findings

    @property
    def examined_nothing(self) -> list[str]:
        """Checks that ran and had nothing to look at.

        Not a failure -- a fee estimate on its own carries no cited clause and
        never will. But it is not a pass either, and the report must not let
        the two look alike.
        """
        return [what for what, got in self.counts if not got.examined]

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.blocking]

    @property
    def advisory(self) -> list[Finding]:
        return [f for f in self.findings if not f.blocking]

    @property
    def ok(self) -> bool:
        return not self.blocking


# ── 1 · does it render ────────────────────────────────────────────────────

def renders(paths: list[Path]) -> list[Finding]:
    """Open each document in a browser and check it actually rendered.

    "PRODUCED" MUST NOT MEAN "WROTE BYTES". Two things are checked, and they
    are the two that fail together when the assets are missing: the `doc-page`
    custom element upgraded (it defines the page, and without its script there
    is no shadow root), and the type resolved to the firm's rather than the
    browser's default serif.

    Proved by deleting the two assets from a pack and confirming all three
    documents fail this -- a gate nobody has watched fail is not known to work.
    """
    if not paths:
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [Finding("renders", "(all)",
                        "playwright is not installed, so nothing was opened. "
                        "This is not a pass -- install it or run with "
                        "--skip-render and know that you did.",
                        blocking=False)]

    out: list[Finding] = []
    with sync_playwright() as pw:
        launch = {"executable_path": CHROMIUM} if Path(CHROMIUM).exists() else {}
        browser = pw.chromium.launch(**launch)
        page = browser.new_page()
        # THE FONT CDN IS NOT PART OF THE PACK, so do not wait for it. Every
        # template links Google Fonts, and a render-blocking stylesheet ahead
        # of `doc-page.js` holds up DOMContentLoaded itself -- through this
        # sandbox's proxy that cost ~13 SECONDS PER DOCUMENT and turned a
        # 2-minute suite into a 15-minute one. A gate slow enough that people
        # reach for --skip-render is a gate that does not run.
        #
        # Nothing here needs the font FILE. The check reads the computed
        # `font-family`, which comes from the DECLARATION in the pack's own
        # stylesheet, and the component upgrade needs only its own script.
        # Cutting the CDN off also makes the check stricter, not looser: it
        # proves the pack renders on a machine with no internet, which is the
        # situation a client opening an emailed folder is often in.
        page.route(re.compile(r"https?://fonts\.(googleapis|gstatic)\.com/"),
                   lambda route: route.abort())
        try:
            for f in paths:
                try:
                    # NOT `networkidle`. Every document links Google Fonts,
                    # and behind a slow proxy waiting for that request to
                    # settle cost ~13 seconds PER DOCUMENT -- a gate slow
                    # enough that people reach for --skip-render is a gate
                    # that is not run. Nothing here needs the font FILE: the
                    # check reads the computed `font-family`, which comes from
                    # the stylesheet, and the component upgrade needs only its
                    # own script. Both are local to the pack.
                    page.goto(f.resolve().as_uri(), wait_until="domcontentloaded")
                    try:
                        page.wait_for_function(
                            "() => { const d = document.querySelector('doc-page');"
                            "        return !d || !!d.shadowRoot; }",
                            timeout=4000)
                    except Exception:                          # noqa: BLE001
                        pass          # the evaluate below reports what it sees
                    page.wait_for_timeout(120)
                    seen = page.evaluate("""() => {
                        const dp = document.querySelector('doc-page');
                        const el = document.querySelector('.mast .wm') || document.body;
                        return {upgraded: !!(dp && dp.shadowRoot),
                                font: getComputedStyle(el).fontFamily};
                    }""")
                except Exception as exc:                       # noqa: BLE001
                    out.append(Finding("renders", f.name,
                                       f"the browser could not open it — "
                                       f"{type(exc).__name__}: {exc}"))
                    continue
                if not seen["upgraded"] or "Plex" not in seen["font"]:
                    why = ("the page component did not upgrade"
                           if not seen["upgraded"] else "the component upgraded")
                    out.append(Finding(
                        "renders", f.name,
                        f"opens as plain text — {why}, and the type is "
                        f"{seen['font'][:40]}. A client opening this sees no "
                        f"masthead, no rules, no layout."))
        finally:
            browser.close()
    return out


# ── 2 · is everything it points at actually here ──────────────────────────

# href="..." / src="..." with either quote. Anything with a scheme, a data URI
# or a bare fragment is somebody else's problem; what matters is the relative
# path, because that is the one that silently resolves to nothing.
_REF = re.compile(r"""\b(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
_EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#|mailto:|tel:)", re.I)


def referenced_files(html: str) -> list[str]:
    """The relative files a document needs beside it to render."""
    return [r for r in _REF.findall(html) if not _EXTERNAL.match(r.strip())]


def assets_present_counted(pack: Path) -> Counted:
    """Every file a document points at is in the pack.

    This is the check that would have caught the plain-text pack on the day it
    started happening, and it costs nothing: no browser, no server, just the
    filesystem. It is a strict subset of what `renders` proves and it is kept
    separate because it says WHICH file is missing, which a screenshot cannot.
    """
    out: list[Finding] = []
    seen = 0
    for doc in sorted(pack.glob("*.html")):
        html = doc.read_text(encoding="utf-8", errors="replace")
        for ref in referenced_files(html):
            seen += 1
            target = (pack / ref.split("?", 1)[0].split("#", 1)[0]).resolve()
            if not target.exists():
                out.append(Finding(
                    "assets", doc.name,
                    f"references {ref!r}, which is not in the pack. The "
                    f"document will open without it and say nothing."))
    return Counted(out, seen, "referenced file")


def assets_present(pack: Path) -> list[Finding]:
    return assets_present_counted(pack).findings


# ── 3 · do the numbers on the page read 01..N ─────────────────────────────

_SECTION_N = re.compile(r'<h2[^>]*><span class="n">(\d+)</span>')


def numbering_counted(pack: Path) -> Counted:
    """Section numbers on the rendered page are contiguous from 01.

    `merge` renumbers after conditionals resolve, so this should never fire.
    That is the point: it is the regression guard for the fix, and it catches
    the second shape too -- both halves of an inverse pair rendering, which
    puts a contradiction on the page and shows up here as a repeat.

    NO FALSE POSITIVE IS CONSTRUCTIBLE. There is no document in this set for
    which 01, 02, 04, 05 is the right answer.

    IT MUST READ THE RENDERED PAGE. Run against template source, with every
    `[[IF]]` branch still present, the disengagement letter reads 01 02 03 04
    05 05 06 07 and the delivery letter 01 02 03 03 04 05 06 07 -- both
    correct-by-design mutual exclusions, both false positives. Two on the
    templates, none on the output.
    """
    out: list[Finding] = []
    seen = 0
    for doc in sorted(pack.glob("*.html")):
        nums = _SECTION_N.findall(doc.read_text(encoding="utf-8", errors="replace"))
        if not nums:
            continue                       # an unnumbered document is fine
        seen += 1
        want = [f"{i:02d}" for i in range(1, len(nums) + 1)]
        if nums != want:
            out.append(Finding(
                "numbering", doc.name,
                f"the section numbers on the page read {' '.join(nums)}, not "
                f"{' '.join(want)}. A client reads a gap as a page they were "
                f"not sent."))
    return Counted(out, seen, "numbered document")


def numbering(pack: Path) -> list[Finding]:
    return numbering_counted(pack).findings


# ── 4 · sentences the firm has deleted ────────────────────────────────────

_RETIRED = Path(__file__).resolve().parent / "registry" / "retired.yaml"
_HEADING = re.compile(r"<h[1-6][^>]*>.*?</h[1-6]>", re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")
_PUNCT = re.compile(r"[^\w\s]")


def _normalize(text: str) -> str:
    """Lowercase, punctuation gone, whitespace collapsed.

    So a phrase still matches after somebody changes a comma or a dash, which
    is exactly the edit that would otherwise let a deleted sentence back in
    wearing a hat.
    """
    return " ".join(_PUNCT.sub(" ", text.lower()).split())


def _readable(html: str) -> str:
    """What a client actually reads, with the headings taken out.

    HEADINGS ARE EXEMPT ON PURPOSE, and it is not a fudge. "this estimate
    assumes" is retired as a bullet opener -- the firm: "the section is titled
    'what this estimate assumes' so why say 'this estimate assumes' in each
    bullet" -- and live as the heading itself. Excluding headings is the one
    rule that makes the check exact rather than nearly exact.
    """
    # THE `.ref` BLOCK GOES FIRST, and this is the difference between a check
    # that is right and one that is wrong five times out of five. Every
    # template carries a screen-only FIELDS reference table; `merge` strips it
    # before anything reaches a client. Run over template SOURCE without
    # stripping it, the spelling sweep reports `recognise`, `cheque`,
    # `behaviour`, `organised` and `authorisation` -- all five inside the ref
    # block, all five invisible to every client, all five false. Over the same
    # twelve documents rendered: zero.
    return _TAGS.sub(" ", _HEADING.sub(" ", merge._REF_BLOCK.sub(" ", html)))


def _load_retired() -> list[dict]:
    import yaml
    if not _RETIRED.exists():
        return []
    spec = yaml.safe_load(_RETIRED.read_text(encoding="utf-8")) or {}
    out = []
    for entry in spec.get("phrases") or []:
        phrase = (entry.get("phrase") or "").strip()
        # THE FIVE-WORD FLOOR IS A CORRECTNESS RULE, not tidiness. A shorter
        # phrase is not a sentence, and a fragment collides with innocent copy
        # sooner or later -- measured: one of the two hits this check produced
        # on its first run was exactly that.
        if len(phrase.split()) < 5:
            raise ValueError(
                f"retired.yaml: {phrase!r} is shorter than five words. Store "
                f"the whole sentence the firm deleted, never a prefix — a "
                f"fragment will match copy nobody objected to.")
        out.append({**entry, "phrase": phrase, "_norm": _normalize(phrase)})
    return out


def retired_phrases_counted(pack: Path) -> Counted:
    """No document carries a sentence the firm has deleted.

    A note in a tenets file saying a phrase is "not yet swept" is not a
    control. This is. It caught the bookkeeping letter still carrying
    "Sign through Encyro and it comes straight back to us." a day after that
    sentence was replaced everywhere else.
    """
    try:
        retired = _load_retired()
    except ValueError as exc:
        return Counted([Finding("retired", "(registry)", str(exc))], 0,
                       "retired sentence")
    docs = sorted(pack.glob("*.html"))
    if not retired:
        return Counted([], 0, "retired sentence")

    out: list[Finding] = []
    for doc in docs:
        said = _normalize(_readable(doc.read_text(encoding="utf-8", errors="replace")))
        for entry in retired:
            if entry["_norm"] in said:
                out.append(Finding(
                    "retired", doc.name,
                    f"carries a sentence the firm deleted on "
                    f"{entry.get('retired', 'an earlier round')} "
                    f"({entry.get('tenet', '')}): \"{entry['phrase']}\" — "
                    f"{entry.get('why', '')}"))
    # The denominator is sentences LOOKED FOR, not documents: "3 documents
    # examined" hides a registry that has quietly become empty, and an empty
    # registry is the one state where this check passes everything.
    return Counted(out, len(retired) * len(docs), "sentence-in-document pair")


def retired_phrases(pack: Path) -> list[Finding]:
    return retired_phrases_counted(pack).findings


# ── 5 · plain language ────────────────────────────────────────────────────

# Words the firm has ruled out of anything a client reads. `accompanies` and
# `accompanying` are DELIBERATELY ABSENT: DOCUMENT-TENETS lists them, and they
# are live in five templates in copy the firm has now approved four times.
# Shipping the list with them in would make this check cry wolf on its first
# run, and a linter that cries wolf gets muted.
LEGALESE = ("governs", "constitutes", "pursuant", "at our discretion",
            "deemed", "shall be", "herein")

# The firm writes American English. A British spelling in a client document is
# a sentence somebody imported from somewhere else.
BRITISH = ("authorisation", "organise", "organised", "organising",
           "organisation", "recognise", "recognised", "realise", "realised",
           "licence", "behaviour", "centre", "cheque", "whilst", "amongst",
           "programme", "enrol")


def plain_language_counted(pack: Path) -> Counted:
    """No hard-banned legalese, and no British spelling.

    READS THE RENDERED PAGE, and that is load-bearing: three British spellings
    live in template `.ref` blocks, which `merge` strips before a client sees
    anything. A check that read the source would fire on all three and be
    wrong all three times.
    """
    out: list[Finding] = []
    seen = 0
    for doc in sorted(pack.glob("*.html")):
        said = _normalize(_readable(doc.read_text(encoding="utf-8", errors="replace")))
        if not said:
            # A document whose readable text is empty is not a clean document.
            # It is a document that rendered to nothing, and the word sweep
            # would call it clean all day.
            out.append(Finding(
                "plain", doc.name,
                "has no readable text at all once the reference block is "
                "stripped. Nothing was swept, so nothing is known."))
            continue
        seen += len(LEGALESE) + len(BRITISH)
        for word in LEGALESE:
            if re.search(rf"\b{re.escape(_normalize(word))}\b", said):
                out.append(Finding(
                    "plain", doc.name,
                    f"uses {word!r}, which the firm has ruled out of anything "
                    f"a client reads. Say the thing itself instead."))
        for word in BRITISH:
            if re.search(rf"\b{word}\b", said):
                out.append(Finding(
                    "plain", doc.name,
                    f"spells {word!r} the British way in a document for an "
                    f"American client."))
    return Counted(out, seen, "word-in-document pair")


def plain_language(pack: Path) -> list[Finding]:
    return plain_language_counted(pack).findings


# ── 6 · the compliance floor ──────────────────────────────────────────────

_REQUIRED = Path(__file__).resolve().parent / "registry" / "required.yaml"


def document_keys(pack: Path) -> dict[str, str]:
    """{filename -> document key}, from the pack's own manifest.

    A rendered document is named for the client, so nothing about the file on
    disk says which template it came from. The manifest is the only place that
    knows, which is why a pack without one cannot be checked against rules
    that are per-document -- and says so rather than passing.
    """
    import json
    book = pack / "MANIFEST.json"
    if not book.exists():
        return {}
    try:
        data = json.loads(book.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out = {}
    for entry in data.get("Documents") or []:
        for name in entry.get("files") or []:
            out[name] = entry.get("key", "")
    return out


def compliance_floor_counted(pack: Path,
                             keys: dict[str, str] | None = None) -> Counted:
    """Sentences that may be reworded but must not be deleted.

    Checks PRESENCE, never absence, so no false positive is constructible: a
    reworded negation that keeps its words passes, and one that has lost the
    word "assurance" has lost the negation. That is deliberate -- no check here
    may pin the firm's prose, because they reword these most rounds and are
    right to.
    """
    import yaml
    if not _REQUIRED.exists():
        return Counted([], 0, "floor sentence")
    spec = yaml.safe_load(_REQUIRED.read_text(encoding="utf-8")) or {}
    rules = spec.get("required") or []
    if not rules:
        return Counted([], 0, "floor sentence")

    keys = document_keys(pack) if keys is None else keys
    if not keys:
        return Counted(
            [Finding("compliance", "(pack)",
                     "no MANIFEST.json, so nothing says which template each "
                     "document came from and the per-document rules were "
                     "not checked. Not a pass.", blocking=False)],
            0, "floor sentence")

    out: list[Finding] = []
    seen = 0
    for doc in sorted(pack.glob("*.html")):
        key = keys.get(doc.name)
        if not key:
            continue
        said = _normalize(_readable(doc.read_text(encoding="utf-8", errors="replace")))
        for rule in rules:
            if key not in (rule.get("applies_to") or []):
                continue
            for group in rule.get("must_contain_all") or []:
                seen += 1
                if not any(_normalize(w) in said for w in group):
                    out.append(Finding(
                        "compliance", doc.name,
                        f"the compliance floor {rule['id']!r} is not on the "
                        f"page — none of {list(group)} appears. "
                        f"{(rule.get('why') or '').strip()}"))
    # A pack of documents no floor rule applies to -- an invoice on its own --
    # examines nothing, and must not read as "the floor is intact".
    return Counted(out, seen, "floor requirement")


def compliance_floor(pack: Path,
                     keys: dict[str, str] | None = None) -> list[Finding]:
    return compliance_floor_counted(pack, keys).findings


# ── 7 · a cited clause name exists ────────────────────────────────────────

_CITE = re.compile(
    r"(?:<b>|<strong>)([^<]{4,60})</(?:b|strong)>\s*section of your engagement letter",
    re.I)
_H2_TEXT = re.compile(r'<h2[^>]*>(?:<span class="n">\d+</span>)?([^<]+)</h2>', re.I)

# The four documents a client might sign. A clause is cited from whichever one
# they got, and the citing document does not know which -- so it resolves
# against the UNION. Anything narrower fires on a letter this client will
# never receive.
ENGAGEMENT_LETTERS = ("tax-letter", "business-letter", "ccorp-letter",
                      "bookkeeping-letter")


def _clause_name(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(",.")


def citations_in(pack: Path) -> list[tuple[str, str]]:
    """Every "the X section of your engagement letter" in the pack.

    The census AND the loop. `cited_clauses` walks this list and the gate
    counts it, so the denominator it reports cannot drift away from the thing
    the check looked at.
    """
    out: list[tuple[str, str]] = []
    for doc in sorted(pack.glob("*.html")):
        html_text = doc.read_text(encoding="utf-8", errors="replace")
        out += [(doc.name, raw)
                for raw in _CITE.findall(merge._REF_BLOCK.sub(" ", html_text))]
    return out


def cited_clauses_counted(pack: Path,
                          section_names: set[str] | None = None) -> Counted:
    """Every cited clause names a real section.

    Pure regression value: this is the only thing that would notice a section
    being renamed in an engagement letter and silently orphaning the pointers
    to it in four other documents. Nothing else in the pipeline reads one
    document's prose against another document's headings.

    IT USUALLY EXAMINES NOTHING, and that is why it reports its denominator.
    All seven live citations are in the delivery letter, the disengagement
    letter, the extension notice and the invoice -- none of which is in the
    opening pack. Run over an opening pack this check is correct and empty,
    and for a while it printed "ok" for both.
    """
    if section_names is None:
        section_names = engagement_section_names()
    found = citations_in(pack)
    if not section_names:
        return Counted(
            [Finding("cited", "(templates)",
                     "the engagement letters could not be read, so no "
                     "citation was resolved. Not a pass.", blocking=False)],
            0, "cited clause")

    out: list[Finding] = []
    for name, raw in found:
        if _clause_name(raw) not in section_names:
            out.append(Finding(
                "cited", name,
                f"points the reader at \"the {raw.strip()} section of your "
                f"engagement letter\", and no engagement letter has a "
                f"section by that name. Either the section was renamed or "
                f"this pointer was."))
    return Counted(out, len(found), "cited clause")


def cited_clauses(pack: Path, section_names: set[str] | None = None) -> list[Finding]:
    return cited_clauses_counted(pack, section_names).findings


def engagement_section_names() -> set[str]:
    """Every section heading across all four engagement letters."""
    import cli                       # local: cli imports this module
    out: set[str] = set()
    for key in ENGAGEMENT_LETTERS:
        entry = cli.DOCUMENTS.get(key)
        if not entry:
            continue
        path = cli.TEMPLATE_DIR / entry[0]
        if not path.exists():
            continue
        for head in _H2_TEXT.findall(path.read_text(encoding="utf-8")):
            out.add(_clause_name(head))
    return out


# ── 8 · the pointer test ──────────────────────────────────────────────────
#
# `packaging.py` carries the incident in its own comment: `package` never
# carried the records release, so a client with a predecessor got a pack whose
# onboarding letter says "We have included a short authorization for you to
# sign" and did not include one. A pack that promises an enclosure it does not
# carry is the same failure as a pack with a hole in it, arriving by the back
# door.
#
# THE CHECK THE FIRM ASKED FOR BY NAME, and it has two halves. Either alone is
# a proxy:
#
#   Half A  no sentence CLAIMS an enclosure without declaring what it is.
#           Without this the check only ever finds what somebody remembered to
#           annotate, which is the proxy trap in SOFTWARE-TENETS §0.
#   Half B  every declaration RESOLVES against what the pack actually holds.

_ENCL_SPAN = re.compile(r'<span[^>]*\bdata-encl\s*=\s*"([^"]*)"[^>]*>(.*?)</span>',
                        re.S | re.I)
_CUE = re.compile(
    r"\b(enclosed|enclosure|attached|accompanies|accompanying"
    r"|(?:is|are) included with|included with (?:this|your)"
    r"|we have included|returned with this letter"
    r"|(?:sent|comes) with this letter)\b", re.I)

# An engagement letter is a ROLE, not a document: a client signs exactly one of
# these four and the fee estimate does not know which. Without the alias the
# estimate's "Accompanies our engagement letter" fails in every pack there is.
_ROLES = {"engagement-letter": {"tax-letter", "business-letter",
                                "ccorp-letter", "bookkeeping-letter"}}


_SPAN_OPEN = re.compile(r"<span\b[^>]*>", re.I)
_SPAN_ANY = re.compile(r"<span\b[^>]*>|</span\s*>", re.I)
_ENCL_OPEN = re.compile(r'<span\b[^>]*\bdata-encl\s*=\s*"([^"]*)"[^>]*>', re.I)


def _declared_spans(html: str) -> list[tuple[str, int, int]]:
    """(value, start, end) for every `data-encl` span, matched by DEPTH.

    A regex cannot do this. `<span data-encl="…">Your organizer for the
    <span class="f">&lt;&lt;TaxYear&gt;&gt;</span> tax year is enclosed.</span>`
    stops a non-greedy `(.*?)</span>` at the INNER close, leaving "tax year is
    enclosed" outside the declared region -- so the sweep reported the
    organizer letter's own annotated sentence as unclassified. Found by the
    migration test, which is what that test is for.
    """
    out = []
    for m in _ENCL_OPEN.finditer(html):
        depth, pos = 1, m.end()
        while depth and pos < len(html):
            nxt = _SPAN_ANY.search(html, pos)
            if not nxt:
                break
            depth += 1 if nxt.group(0).lower().startswith("<span") else -1
            pos = nxt.end()
        out.append((m.group(1), m.start(), pos))
    return out


def _strip_declared(html: str) -> str:
    """The document with every declared enclosure claim removed.

    What is left is prose that claims an enclosure and says nothing about
    what.
    """
    for _value, start, end in reversed(_declared_spans(html)):
        html = html[:start] + " " + html[end:]
    return html


def pointer_test_counted(pack: Path) -> Counted:
    """A promised enclosure is in the pack, and every promise says what it is."""
    import json
    book = pack / "MANIFEST.json"
    if not book.exists():
        return Counted(
            [Finding("pointer", "(pack)",
                     "no MANIFEST.json, so there is nothing to resolve an "
                     "enclosure claim against. Not a pass.", blocking=False)],
            0, "enclosure claim")
    try:
        data = json.loads(book.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Counted(
            [Finding("pointer", "MANIFEST.json",
                     f"will not parse ({exc}), so no enclosure claim could "
                     f"be resolved. Not a pass.", blocking=False)],
            0, "enclosure claim")

    have_docs = {d.get("key", "") for d in (data.get("Documents") or [])}
    have_attached = {f"attachment:{a.get('id', '')}"
                     for a in (data.get("Attachments") or [])}

    out: list[Finding] = []
    seen = 0
    for doc in sorted(pack.glob("*.html")):
        html_text = merge._REF_BLOCK.sub(" ", doc.read_text(encoding="utf-8",
                                                            errors="replace"))

        # Half A — nothing claims an enclosure anonymously.
        for m in _CUE.finditer(_TAGS.sub(" ", _strip_declared(html_text))):
            said = " ".join(_TAGS.sub(" ", _strip_declared(html_text))
                            [max(0, m.start() - 90):m.start() + 90].split())
            out.append(Finding(
                "pointer", doc.name,
                f"claims an enclosure and does not declare what: \"…{said}…\". "
                f"Wrap it in <span data-encl=\"…\"> naming the document or "
                f"attachment it promises, or data-encl=\"client\" if the client "
                f"encloses it, or data-encl=\"none\" if it says the opposite."))

        # Half B — every declaration resolves.
        for value, _start, _end in _declared_spans(html_text):
            seen += 1
            value = value.strip()
            # DIRECTION IS DECLARED, NEVER INFERRED. "Your original records are
            # returned with this letter" (ours) and "Return the completed
            # organizer with the documents you gathered" (theirs) are
            # grammatically identical. A regex right on today's thirteen
            # sentences is wrong on the fourteenth.
            if value in ("client", "none"):
                continue
            if value in _ROLES:
                if have_docs & _ROLES[value]:
                    continue
                out.append(Finding(
                    "pointer", doc.name,
                    f"promises the {value.replace('-', ' ')}, and this pack "
                    f"holds none of {sorted(_ROLES[value])}."))
                continue
            if value.startswith("attachment:"):
                if value in have_attached:
                    continue
                out.append(Finding(
                    "pointer", doc.name,
                    f"promises {value.split(':', 1)[1]!r}, which this software "
                    f"does not render and nobody declared going in the "
                    f"envelope. Declare it: package --attach "
                    f"{value.split(':', 1)[1]}."))
                continue
            if value in have_docs:
                continue
            out.append(Finding(
                "pointer", doc.name,
                f"promises the {value!r} document and the pack does not carry "
                f"one. This is the records-release bug: a client reads "
                f"\"included\" and finds nothing."))
    return Counted(out, seen, "declared enclosure claim")


def pointer_test(pack: Path) -> list[Finding]:
    return pointer_test_counted(pack).findings


# ── 9 · nothing on the page is empty ──────────────────────────────────────

_EMPTY_LI = re.compile(r"<li\b[^>]*>\s*</li>", re.I)
_ANY_LI = re.compile(r"<li\b", re.I)
_ANY_ROW = re.compile(r"<tr\b", re.I)
_EMPTY_CELL_ROW = re.compile(r"<tr\b[^>]*>(?:\s*<t[dh]\b[^>]*>\s*</t[dh]>)+\s*</tr>", re.I)


def nothing_empty_counted(pack: Path) -> Counted:
    """No bullet with nothing beside it, and no row with nothing in it.

    A conditional written INSIDE a list item instead of around it drops its
    contents and leaves the item: the invoice carried
    `<li>[[IF EstimateReference]]...[[END IF]]</li>`, so every invoice with no
    estimate reference printed a bullet pointing at nothing. The engine is not
    at fault -- it dropped exactly what it was told to.

    Reads the RENDERED SOURCE, not the browser's DOM. A previous version of
    this check looked at the live tree and counted `<tbody>` rows the browser
    inserts on its own, so it failed to fire when it should have.
    """
    out: list[Finding] = []
    seen = 0
    for doc in sorted(pack.glob("*.html")):
        html_text = merge._REF_BLOCK.sub(" ", doc.read_text(encoding="utf-8",
                                                            errors="replace"))
        # The denominator is elements that COULD be empty. A pack of documents
        # with no lists and no tables examines nothing here, and saying "ok"
        # over it would be a claim about a page this check never saw.
        seen += len(_ANY_LI.findall(html_text)) + len(_ANY_ROW.findall(html_text))
        for count, what in ((len(_EMPTY_LI.findall(html_text)), "list item"),
                            (len(_EMPTY_CELL_ROW.findall(html_text)), "table row")):
            if count:
                out.append(Finding(
                    "empty", doc.name,
                    f"{count} empty {what}{'s' if count > 1 else ''} on the "
                    f"page. Usually a conditional written inside the element "
                    f"instead of around it: the contents drop and the bullet "
                    f"stays."))
    return Counted(out, seen, "bullet or row", "bullets and rows")


def nothing_empty(pack: Path) -> list[Finding]:
    return nothing_empty_counted(pack).findings


# ── 10 · do the documents agree with each other ───────────────────────────

def agrees_counted(record: dict, rendered: dict[str, str]) -> Counted:
    """The pack tells one story.

    `consistency.report` already asks this well; this only turns its answer
    into findings so one gate speaks with one voice.
    """
    if not rendered:
        return Counted(
            [Finding("agrees", "(pack)",
                     "no document in the set renders from this record, so "
                     "nothing was compared. `doctor` says what is missing.")],
            0, "agreement")
    checks = consistency.report(record, rendered)
    return Counted([Finding("agrees", "(pack)", f"{c.name} — {c.detail}")
                    for c in checks if not c.ok], len(checks), "agreement")


def agrees(record: dict, rendered: dict[str, str]) -> list[Finding]:
    return agrees_counted(record, rendered).findings


# ── the gate ──────────────────────────────────────────────────────────────

def gate(pack: Path, record: dict, *, rendered: dict[str, str] | None = None,
         skip_render: bool = False) -> Result:
    """Everything above, on one pack, in one answer.

    ``rendered`` is the document text keyed by name when the caller already has
    it (``cli`` does, from the merge it just ran). Passing it avoids rendering
    the pack twice and, more to the point, means the agreement check reads the
    SAME text the client will.
    """
    res = Result()

    res.add("every referenced file is in the pack", assets_present_counted(pack))
    res.add("section numbers on the page read 01..N", numbering_counted(pack))
    res.add("no sentence the firm has deleted has come back",
            retired_phrases_counted(pack))
    res.add("no banned legalese and no British spelling",
            plain_language_counted(pack))
    res.add("the compliance floor is on the page", compliance_floor_counted(pack))
    res.add("every cited clause name is a real section", cited_clauses_counted(pack))
    res.add("every promised enclosure is in the pack", pointer_test_counted(pack))
    res.add("no empty bullet and no empty row", nothing_empty_counted(pack))

    docs = sorted(pack.glob("*.html"))
    if skip_render:
        res.skipped.append(f"opening {len(docs)} document(s) in a browser")
    else:
        res.add("every document opens and renders",
                Counted(renders(docs), len(docs), "document"))

    if rendered is None:
        res.skipped.append("the documents agree with each other")
    else:
        res.add("the documents agree with each other",
                agrees_counted(record, rendered))

    return res


def format_result(res: Result) -> str:
    """What the gate says out loud. Says what it DID as well as what failed --
    a clean report that does not name its checks is indistinguishable from a
    check that never ran."""
    out: list[str] = []
    for what, got in res.counts:
        out.append(got.line(what))
    for line in res.skipped:
        out.append(f"  SKIP   {line} — not checked, so not known to be right")
    if res.findings:
        out.append("")
        out += [f.line() for f in res.findings]
    empty = res.examined_nothing
    if empty:
        out.append("")
        out.append(f"  {len(empty)} check(s) above had nothing to examine and "
                   f"are marked NONE, not ok.")
        out.append("  Nothing is wrong with them. Nothing is known about them "
                   "either.")
    return "\n".join(out)
