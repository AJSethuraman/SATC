#!/usr/bin/env python3
"""Does the page read like a person wrote it for a person?

    cd schedule-c-pl && python3 copy.spec.py

This checks the BUILT page, not the source, because the built page is what a
client reads. It follows the house rules for client-facing copy in CLAUDE.md:
no term of art from our own process, no contract-desk verbs, and no sentence so
long it was written to be complete rather than to be read.

It deliberately does NOT check the Schedule C line labels. Those are the IRS
form's own words, they are checked against the official PDF by
tests/lines.test.mjs, and rewriting them would defeat the point of a worksheet
someone copies figures off.

There is one more thing here that is not about style. A CPA's name is on this
page, so it is advertising, and the Ohio Accountancy Board's rules bar a claim
that is false or misleading. The last checks are about that.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parent / "website" / "tools" / "schedule-c-profit-and-loss" / "index.html"
GUIDE = HERE.parent / "website" / "guides" / "schedule-c-line-by-line" / "index.html"

checks: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    checks.append((bool(ok), label))


if not PAGE.exists():
    sys.exit(f"{PAGE} does not exist. Run: npm run build")

html = PAGE.read_text(encoding="utf-8")
script = html.split("<script type=\"module\">", 1)[1].rsplit("</script>", 1)[0]
markup = html.split("<script type=\"module\">", 1)[0]

# ── what counts as our copy ───────────────────────────────────────────
#
# From the markup: everything a browser would show. From the script: the string
# literals that reach a reader — headings, hints, blurbs, notices, refusals.
# `label:` is excluded on purpose: those are the IRS form's words.

body = re.sub(r"(?s)<style.*?</style>", " ", markup)
body = re.sub(r"(?s)<!--.*?-->", " ", body)
# Mark where one element ends and the next begins, so a heading and the
# paragraph under it are not measured as one 36-word sentence.
body = re.sub(r"</(?:p|li|h1|h2|h3|title|ul|div|section|header|footer|noscript|a)>", " \u00b6 ", body)
body = re.sub(r"<[^>]+>", " ", body)
body = (body.replace("&amp;", "&").replace("&nbsp;", " ")
        .replace("&#8209;", "-").replace("&quot;", '"'))
markup_pieces = [re.sub(r"\s+", " ", part).strip() for part in body.split("\u00b6")]
markup_pieces = [p for p in markup_pieces if p]
markup_text = " ".join(markup_pieces)

COPY_KEYS = ("text", "blurb", "hint", "message", "because", "instead", "subject",
             "caveat", "display", "error", "placeholder", "aria-label", "legend")
script_copy: list[str] = []
for key in COPY_KEYS:
    for m in re.finditer(rf"\b{key}:\s*'((?:[^'\\]|\\.)*)'", script):
        script_copy.append(m.group(1).replace("\\'", "'"))
# Plain-string arguments to the section() and choice() helpers, and the two
# standing paragraphs.
for m in re.finditer(r"section\('((?:[^'\\]|\\.)*)',\s*(?:'((?:[^'\\]|\\.)*)'|null)", script):
    script_copy += [g.replace("\\'", "'") for g in m.groups() if g]
for m in re.finditer(r"choice\('[^']*',\s*'((?:[^'\\]|\\.)*)'", script):
    script_copy.append(m.group(1).replace("\\'", "'"))
for name in ("DISCLAIMER", "INVITATION", "ROUNDING_NOTE"):
    for m in re.finditer(rf"const {name} =\s*((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+);", script):
        script_copy.append(re.sub(r"'\s*\+\s*'", "", m.group(1).strip()).strip("'"))

copy = [s for s in [*script_copy, *markup_pieces] if s.strip()]
check(len(copy) > 60, f"there is copy to check — {len(copy)} pieces found")

# ── 1 · no contract-desk verbs ────────────────────────────────────────
#
# From CLAUDE.md, rule 3. Each of these turns a sentence from something you
# would say into something a form would say.

BANNED = ["governs", "constitutes", "accompanies", "pursuant", "in accordance with",
          "at our discretion", "deemed", "shall be", "herein", "hereunder",
          "whereas", "aforementioned", "thereof", "notwithstanding"]
found = [(w, s) for s in copy for w in BANNED if re.search(rf"\b{re.escape(w)}\b", s, re.I)]
check(not found, "no contract-desk verbs"
      + (f" — found {found[0][0]!r} in: {found[0][1][:80]}" if found else f" (checked {len(BANNED)} of them)"))

# ── 2 · nothing longer than a sentence a person would say ─────────────
#
# From CLAUDE.md, rule 5: past about 25 words, a client-facing sentence was
# written to be complete rather than to be read.

LIMIT = 25
long_ones = []
for piece in copy:
    for sentence in re.split(r"(?<=[.?!])\s+", piece):
        words = [w for w in re.split(r"\s+", sentence.strip()) if w]
        if len(words) > LIMIT:
            long_ones.append((len(words), sentence.strip()))
long_ones.sort(reverse=True)
check(not long_ones, f"every sentence is {LIMIT} words or fewer"
      + (f" — the longest is {long_ones[0][0]}: {long_ones[0][1][:110]}" if long_ones else ""))

# ── 3 · no term of art we have not explained ──────────────────────────
#
# These are the words that make a reader feel they have walked into the wrong
# room. A word is allowed if the same sentence says what it means.

JARGON = {
    "engagement letter": None,
    "de minimis": None,
    "safe harbor": None,
    "materially participate": "work",
    "at-risk": "lose",
    "carryforward": None,
    "amortization": None,
    "basis": None,
    "pass-through": None,
    "self-employment tax": None,
    "qualified business income": None,
}
unexplained = []
for piece in copy:
    for term, escape_hatch in JARGON.items():
        for sentence in re.split(r"(?<=[.?!])\s+", piece):
            if not re.search(rf"\b{re.escape(term)}\b", sentence, re.I):
                continue
            if escape_hatch and re.search(rf"\b{escape_hatch}", sentence, re.I):
                continue
            unexplained.append((term, sentence.strip()))
check(not unexplained, "no term of art a first-time reader would have to look up"
      + (f" — {unexplained[0][0]!r} in: {unexplained[0][1][:90]}" if unexplained else
         f" (checked {len(JARGON)})"))

# ── 4 · no promise we cannot keep ─────────────────────────────────────
#
# Ohio Accountancy Board rules bar a false or misleading claim, and a tool with
# a CPA's name on it is advertising. Certainty is the easiest thing to promise
# and the hardest to be held to.

OVERSELL = ["guarantee", "guaranteed", "always correct", "never wrong", "audit-proof",
            "maximum refund", "biggest refund", "IRS approved", "IRS-approved",
            "best in", "#1", "risk-free", "100% accurate"]
sold = [(w, s) for s in copy for w in OVERSELL if w.lower() in s.lower()]
check(not sold, "nothing is promised that could not be kept"
      + (f" — {sold[0][0]!r} in: {sold[0][1][:80]}" if sold else f" (checked {len(OVERSELL)})"))

# ── 5 · the page says what it is, and what it is not ──────────────────

check("not a tax return" in markup_text.lower(),
      "the page says out loud that this is not a tax return")
check("does not make you a client" in markup_text.lower()
      or "not make you a client" in markup_text.lower(),
      "and that using it does not make someone a client")
check("Sethuraman Accounting, Tax & Consulting" in markup_text,
      "the firm behind it is named, not hidden")
check("satcllp.com" in markup_text, "and its website is on the page")

# ── 6 · the privacy claim on the page has to be literally true ────────
#
# build.mjs refuses to write a page that would talk to another machine. This
# checks the built file itself, so the claim and the artifact are checked
# against each other rather than against intentions.

promises_privacy = "never leave" in markup_text.lower() or "stay on your computer" in markup_text.lower()
check(promises_privacy, "the page makes the privacy claim")

leaks = []
for pattern, what in [
    (r"\bfetch\s*\(", "fetch()"),
    (r"XMLHttpRequest", "XMLHttpRequest"),
    (r"sendBeacon", "sendBeacon"),
    (r"<script[^>]+src=", "an external script"),
    (r"<link[^>]+rel=[\"'](?:stylesheet|preload|preconnect|dns-prefetch)[\"']", "an external stylesheet"),
    (r"<img[^>]+src=[\"']https?:", "a remote image"),
    (r"googletagmanager|google-analytics|plausible\.io|cloudflareinsights", "an analytics script"),
]:
    if re.search(pattern, html, re.I):
        leaks.append(what)
check(not leaks, "and the page really does make no requests"
      + (f" — found {', '.join(leaks)}" if leaks else ""))

# ── 7 · the reader is told where a tax figure came from ───────────────

check("Notice 2025-5" in script or "Notice 2025-5" in html,
      "the mileage rate on the page names the IRS notice it came from")
check("Instructions for Schedule C" in html,
      "and the square-foot figure names the instructions it came from")

# ── 8 · the guide page, held to the same register ─────────────────────
#
# It is longer and it carries terms the tool refuses to use at all -- there is
# no way to write about line 13 without naming what it is. The rule is not
# "never say it": it is show the term and then say what it means, in the same
# breath. These checks are on the guide's own prose.

if not GUIDE.exists():
    check(False, "the guide page exists (run: node guide/build-guide.mjs)")
else:
    g_html = GUIDE.read_text(encoding="utf-8")
    g_body = re.sub(r"(?s)<style.*?</style>", " ", g_html)
    g_body = re.sub(r"</(?:p|li|h1|h2|h3|ul|div|section|header|footer|article|a)>", " \u00b6 ", g_body)
    g_body = re.sub(r"<[^>]+>", " ", g_body)
    g_body = g_body.replace("&amp;", "&").replace("&quot;", '"').replace("&nbsp;", " ")
    g_pieces = [re.sub(r"\s+", " ", part).strip() for part in g_body.split("\u00b6")]
    g_pieces = [x for x in g_pieces if x]

    check(len(g_pieces) > 60, f"the guide has copy to check — {len(g_pieces)} pieces")

    g_found = [(w, x) for x in g_pieces for w in BANNED if re.search(rf"\b{re.escape(w)}\b", x, re.I)]
    check(not g_found, "the guide uses no contract-desk verbs"
          + (f" — {g_found[0][0]!r} in: {g_found[0][1][:80]}" if g_found else ""))

    g_long = []
    for piece in g_pieces:
        for sentence in re.split(r"(?<=[.?!])\s+", piece):
            words = [w for w in re.split(r"\s+", sentence.strip()) if w]
            if len(words) > LIMIT:
                g_long.append((len(words), sentence.strip()))
    g_long.sort(reverse=True)
    check(not g_long, f"every guide sentence is {LIMIT} words or fewer"
          + (f" — longest is {g_long[0][0]}: {g_long[0][1][:110]}" if g_long else ""))

    g_sold = [(w, x) for x in g_pieces for w in OVERSELL if w.lower() in x.lower()]
    check(not g_sold, "the guide promises nothing it could not keep"
          + (f" — {g_sold[0][0]!r} in: {g_sold[0][1][:80]}" if g_sold else ""))

    # A term of art must be EXPLAINED where it is used, not merely avoided.
    for term, gloss in [("self-employment tax", "Social Security"),
                        ("1099-NEC", "600"),
                        ("depreciation schedule", "running list")]:
        used = [x for x in g_pieces if term.lower() in x.lower()]
        if used:
            check(any(gloss.lower() in x.lower() for x in used),
                  f"the guide explains {term!r} where it uses it")

    # The guide's whole reason for being generated rather than typed.
    # NOT `"27a" not in g_html`: the note explaining the swap has to name the
    # old number, and that is the most useful sentence on the page for anyone
    # copying off last year's worksheet. What must not appear is 27a as a LINE
    # CHIP -- the number the page tells you to write in.
    chips = re.findall(r'<span class="line-no">([^<]+)</span>', g_html)
    check("27b" in chips and "27a" not in chips,
          f"other expenses is chipped as the 2025 line, not a typed-in guess (chips: {sorted(set(chips))[:6]}…)")
    check("27a" in g_html, "and the page still warns that the number moved")
    check("does not make you a client" in g_html,
          "and says reading it does not make someone a client")
    check("/tools/schedule-c-profit-and-loss/" in g_html,
          "and sends the reader to the tool")

# ── report ────────────────────────────────────────────────────────────
print("\nSchedule C tool — client-facing copy\n")
for ok, label in checks:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
failed = sum(1 for ok, _ in checks if not ok)
print(f"\n{len(checks) - failed} of {len(checks)} checks passed.\n")
sys.exit(1 if failed else 0)
