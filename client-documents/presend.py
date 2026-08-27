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
class Result:
    findings: list[Finding] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

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


def assets_present(pack: Path) -> list[Finding]:
    """Every file a document points at is in the pack.

    This is the check that would have caught the plain-text pack on the day it
    started happening, and it costs nothing: no browser, no server, just the
    filesystem. It is a strict subset of what `renders` proves and it is kept
    separate because it says WHICH file is missing, which a screenshot cannot.
    """
    out: list[Finding] = []
    for doc in sorted(pack.glob("*.html")):
        html = doc.read_text(encoding="utf-8", errors="replace")
        for ref in referenced_files(html):
            target = (pack / ref.split("?", 1)[0].split("#", 1)[0]).resolve()
            if not target.exists():
                out.append(Finding(
                    "assets", doc.name,
                    f"references {ref!r}, which is not in the pack. The "
                    f"document will open without it and say nothing."))
    return out


# ── 3 · do the numbers on the page read 01..N ─────────────────────────────

_SECTION_N = re.compile(r'<h2[^>]*><span class="n">(\d+)</span>')


def numbering(pack: Path) -> list[Finding]:
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
    for doc in sorted(pack.glob("*.html")):
        nums = _SECTION_N.findall(doc.read_text(encoding="utf-8", errors="replace"))
        if not nums:
            continue                       # an unnumbered document is fine
        want = [f"{i:02d}" for i in range(1, len(nums) + 1)]
        if nums != want:
            out.append(Finding(
                "numbering", doc.name,
                f"the section numbers on the page read {' '.join(nums)}, not "
                f"{' '.join(want)}. A client reads a gap as a page they were "
                f"not sent."))
    return out


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


def retired_phrases(pack: Path) -> list[Finding]:
    """No document carries a sentence the firm has deleted.

    A note in a tenets file saying a phrase is "not yet swept" is not a
    control. This is. It caught the bookkeeping letter still carrying
    "Sign through Encyro and it comes straight back to us." a day after that
    sentence was replaced everywhere else.
    """
    try:
        retired = _load_retired()
    except ValueError as exc:
        return [Finding("retired", "(registry)", str(exc))]
    if not retired:
        return []

    out: list[Finding] = []
    for doc in sorted(pack.glob("*.html")):
        said = _normalize(_readable(doc.read_text(encoding="utf-8", errors="replace")))
        for entry in retired:
            if entry["_norm"] in said:
                out.append(Finding(
                    "retired", doc.name,
                    f"carries a sentence the firm deleted on "
                    f"{entry.get('retired', 'an earlier round')} "
                    f"({entry.get('tenet', '')}): \"{entry['phrase']}\" — "
                    f"{entry.get('why', '')}"))
    return out


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


def plain_language(pack: Path) -> list[Finding]:
    """No hard-banned legalese, and no British spelling.

    READS THE RENDERED PAGE, and that is load-bearing: three British spellings
    live in template `.ref` blocks, which `merge` strips before a client sees
    anything. A check that read the source would fire on all three and be
    wrong all three times.
    """
    out: list[Finding] = []
    for doc in sorted(pack.glob("*.html")):
        said = _normalize(_readable(doc.read_text(encoding="utf-8", errors="replace")))
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
    return out


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


def compliance_floor(pack: Path, keys: dict[str, str] | None = None) -> list[Finding]:
    """Sentences that may be reworded but must not be deleted.

    Checks PRESENCE, never absence, so no false positive is constructible: a
    reworded negation that keeps its words passes, and one that has lost the
    word "assurance" has lost the negation. That is deliberate -- no check here
    may pin the firm's prose, because they reword these most rounds and are
    right to.
    """
    import yaml
    if not _REQUIRED.exists():
        return []
    spec = yaml.safe_load(_REQUIRED.read_text(encoding="utf-8")) or {}
    rules = spec.get("required") or []
    if not rules:
        return []

    keys = document_keys(pack) if keys is None else keys
    if not keys:
        return [Finding("compliance", "(pack)",
                        "no MANIFEST.json, so nothing says which template each "
                        "document came from and the per-document rules were "
                        "not checked. Not a pass.", blocking=False)]

    out: list[Finding] = []
    for doc in sorted(pack.glob("*.html")):
        key = keys.get(doc.name)
        if not key:
            continue
        said = _normalize(_readable(doc.read_text(encoding="utf-8", errors="replace")))
        for rule in rules:
            if key not in (rule.get("applies_to") or []):
                continue
            for group in rule.get("must_contain_all") or []:
                if not any(_normalize(w) in said for w in group):
                    out.append(Finding(
                        "compliance", doc.name,
                        f"the compliance floor {rule['id']!r} is not on the "
                        f"page — none of {list(group)} appears. "
                        f"{(rule.get('why') or '').strip()}"))
    return out


# ── 7 · do the documents agree with each other ────────────────────────────

def agrees(record: dict, rendered: dict[str, str]) -> list[Finding]:
    """The pack tells one story.

    `consistency.report` already asks this well; this only turns its answer
    into findings so one gate speaks with one voice.
    """
    if not rendered:
        return [Finding("agrees", "(pack)",
                        "no document in the set renders from this record, so "
                        "nothing was compared. `doctor` says what is missing.")]
    return [Finding("agrees", "(pack)", f"{c.name} — {c.detail}")
            for c in consistency.report(record, rendered) if not c.ok]


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

    res.checked.append("every referenced file is in the pack")
    res.findings += assets_present(pack)

    res.checked.append("section numbers on the page read 01..N")
    res.findings += numbering(pack)

    res.checked.append("no sentence the firm has deleted has come back")
    res.findings += retired_phrases(pack)

    res.checked.append("no banned legalese and no British spelling")
    res.findings += plain_language(pack)

    res.checked.append("the compliance floor is on the page")
    res.findings += compliance_floor(pack)

    docs = sorted(pack.glob("*.html"))
    if skip_render:
        res.skipped.append(f"opening {len(docs)} document(s) in a browser")
    else:
        res.checked.append(f"all {len(docs)} document(s) open and render")
        res.findings += renders(docs)

    if rendered is None:
        res.skipped.append("the documents agree with each other")
    else:
        res.checked.append("the documents agree with each other")
        res.findings += agrees(record, rendered)

    return res


def format_result(res: Result) -> str:
    """What the gate says out loud. Says what it DID as well as what failed --
    a clean report that does not name its checks is indistinguishable from a
    check that never ran."""
    out: list[str] = []
    for line in res.checked:
        out.append(f"  ok     {line}")
    for line in res.skipped:
        out.append(f"  SKIP   {line} — not checked, so not known to be right")
    if res.findings:
        out.append("")
        out += [f.line() for f in res.findings]
    return "\n".join(out)
