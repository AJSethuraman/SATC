#!/usr/bin/env python3
"""Check every published page against the copy tenets.

    cd website && python3 copy.spec.py

WHY THIS FILE EXISTS
--------------------
`CLAUDE.md` grew six rules about client-facing copy in the middle of the price
page build. Two of them became code — a contract-word list and a sentence-length
cap, inside `pricing.spec.py`. Four stayed judgment.

The two that became code have not been broken since. The four that stayed
judgment were broken every time afterwards, by drafters who had read them and
believed they were complying. The clearest case: the sentence the firm killed
with "literally AI dribble, why can't you get that?" passes all six rules on a
careful reading. That is the whole argument for this file. A tenet enforced by
the judgment of the party whose judgment already failed is not enforced.

So the checks here are the mechanical half of `website/TENETS.md`, run over
every page rather than the price page alone. They are deliberately blunt. A
word list will not catch a bad sentence dressed carefully, and it is not
supposed to — it catches the ordinary case, which is most of them, and leaves
the drafter the job the list cannot do.

WHAT IT DOES NOT DO
-------------------
Tenet 2 (nothing may look unfinished) and tenet 4 (two things doing the same job
must look identical) are measured in a browser, not in text, so they live with
`intake.spec.py` and the layout assertions in the build rather than here.
"""

from __future__ import annotations

import html
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGES = ["index.html", "pricing.html", "privacy.html",
         # Generated from docs/guides/ by build-guides.py. They are checked here
         # as published pages, on top of the draft check in docs/guides -- the
         # tenets apply to what a visitor reads, whatever produced it.
         "guides/records.html", "guides/business-records.html", "guides/s-corp.html"]

#: Copy that reaches a visitor WITHOUT being in any .html file. THE BLIND SPOT,
#: found 7 September 2026: `intake-config.js` carries the questions, help text
#: and placeholders the intake form renders, so a visitor reads them on the page
#: -- and this file checked `.html` only. The banned phrase "as soon as we can"
#: sat in it, live, while the spec reported 36/36 green. A tenet about what a
#: visitor reads has to read everything a visitor reads, whatever produced it.
COPY_IN_SCRIPTS = ["intake-config.js"]

#: THE OTHER HALF OF THE SAME BLIND SPOT, found the same day by walking the form
#: in a browser. `intake-config.js` above holds the QUESTIONS; `intake.js` is the
#: RENDERER, and it carries copy of its own -- the consent checkbox, the buttons,
#: the validation messages. The banned phrase "engagement letter" sat in it,
#: live on the home page, while this spec reported 39/39 green with
#: intake-config.js already covered. Half a blind spot still reads as green.
#:
#: It needs its own extractor rather than a third entry in COPY_IN_SCRIPTS: that
#: list is read by `key: "value"` pairs, and a renderer has none -- it builds
#: HTML by concatenating fragments, so the key-based reader finds nothing and
#: the assert below would fire on an empty result.
COPY_IN_RENDERERS = ["intake.js"]

#: The keys in those scripts whose values are shown to a person. Deliberately a
#: list and not "every string": a URL, an id or a field name is not copy, and
#: sweeping them in would make this noisy enough to be ignored.
VISIBLE_KEYS = ("question", "help", "placeholder", "label", "title",
                "intro", "note", "hint", "legend", "blurb", "text")

_fail = 0
_pass = 0


def check(ok, msg):
    global _fail, _pass
    if ok:
        _pass += 1
        print(f"  PASS  {msg}")
    else:
        _fail += 1
        print(f"  FAIL  {msg}")


# ── the lists ─────────────────────────────────────────────────────────────
#
# Tenet 7. Terms of art and contract-desk verbs. Kept in step with the copy of
# this list inside pricing.spec.py, which predates it and guards the generated
# config as well as the markup.
CONTRACT_WORDS = [
    "governs", "governed by", "engagement letter", "constitutes",
    "in accordance with", "pursuant", "herein", "thereof", "aforementioned",
    "accompanies", "at our discretion", "in the event that", "utilize",
    "commence", "deemed", "whereupon", "notwithstanding", "shall be",
    "we reserve the right", "hereby", "aforesaid", "retain the right",
    "multi-jurisdictional", "right-sized", "best-in-class", "leverage",
    "holistic", "bespoke", "seamless", "end-to-end",
]

# Tenet 1, and the gap the six rules missed entirely. Rule 4 covered sentences
# that PROTECT us; nothing covered sentences that FLATTER us, which was the
# largest single category the firm deleted. Every entry here was either cut from
# this site or is the same shape as one that was.
SELF_CLAIMS = [
    "no surprises", "we pride", "committed to", "dedicated to",
    "our mission", "we strive", "we believe in", "passionate about",
    "trusted advisor", "expertise", "world-class", "second to none",
    "you can act on", "without the last-minute", "without the last minute",
    "peace of mind", "hassle-free", "stress-free", "we go the extra",
    "unlike other firms", "we're upfront", "we are upfront",
    "we're transparent", "we are transparent",
]

# Tenet 6. A promise about a person, a time or a number. The firm's own
# instructions, in its words: "do not promise the one business day thing", "do
# not say things like 'by one person' in general, never promise it is by someone
# in particular", "literally do not specify stuff like we fix our own errors for
# free".
# SUPERSEDED 7 September 2026: "as soon as we can" came OFF this list.
# It was swept in while the one-business-day promise was being removed, and it
# is the opposite of what this tenet bans -- a deliberate refusal to promise a
# time, not a promise of one. Asked on the docket "Do you want to promise a
# reply within one business day, in writing?", the firm answered: *"No -- keep
# 'as soon as we can'"*. That is the phrase they chose, knowingly, over the
# alternative. It is on the live site in intake-config.js and now in index.html.
# The rest of the list is untouched, including "business day", which is the
# thing actually being refused.
PROMISES = [
    "business day", "within 24 hours", "same day",
    "guaranteed", "we guarantee", "always available", "never miss",
    "at no charge", "free of charge", "no extra charge", "personally",
    "by one person", "you'll work directly with", "your dedicated",
    "around the clock", "any time of day",
]

MAX_WORDS = 28


def visible_text(src: str) -> str:
    """The words a visitor actually reads, with block tags turned into stops.

    Turning </li> and </p> into ". " matters: without it the bullets of a card
    concatenate into one long pseudo-sentence and the length check reports a
    violation nobody wrote.
    """
    body = src[src.find("<body"):] if "<body" in src else src
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    body = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"</(li|p|h[1-6]|div|section|td|th|b|button|a)>", ". ", body, flags=re.I)
    body = re.sub(r"<br\s*/?>", ". ", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(body)
    # The site writes &#8209; (a non-breaking hyphen) wherever a hyphenated term
    # must not wrap, and &rsquo;/&mdash; elsewhere. Unescaped those are U+2011,
    # U+2019 and U+2014 — so "multi-jurisdictional" in a word list below would
    # never match "multi‑jurisdictional" on the page. That is not a hypothetical:
    # both hyphenated terms in the first run of this file went undetected until
    # this line existed. Fold the typography back to ASCII before matching.
    for fancy, plain in (("‑", "-"), ("‐", "-"), ("–", "-"),
                         ("—", " - "), ("’", "'"), ("‘", "'"),
                         ("“", '"'), ("”", '"'), (" ", " ")):
        body = body.replace(fancy, plain)
    return body


# Site furniture, which is SUPPOSED to appear twice. The wordmark sits in the
# header and again in the footer; the back link sits above and below the page.
# Repeating those is what makes a site feel like one site — the tenet is about
# an argument being made twice, not about a logo. Kept as a short explicit list
# rather than a class-name filter: chrome is rare and named, and a regex that
# tries to delete whole nested elements from HTML gets the wrong ones.
CHROME = [
    re.compile(r"sat.{0,3}c\s+llp", re.I),
    re.compile(r"back to the site", re.I),
    re.compile(r"^sethuraman accounting", re.I),
]


def is_chrome(s: str) -> bool:
    return any(p.search(s) for p in CHROME)


def sentences(text: str) -> list[str]:
    out = []
    for chunk in re.split(r"[.!?]+\s", text):
        s = " ".join(chunk.split())
        if s:
            out.append(s)
    return out


print("SATC — the copy tenets, over every published page\n")

def script_copy(path: Path) -> str:
    """The visitor-facing strings out of a config script.

    Matches `key: "value"` and `key: 'value'` for the keys in VISIBLE_KEYS.
    Not a JavaScript parser and not trying to be -- these files are hand-written
    literals, and a parser would be a second thing to keep correct.
    """
    src = path.read_text(encoding="utf-8")
    keys = "|".join(VISIBLE_KEYS)
    # No backreference and no lookbehind: two plain alternatives instead.
    # These are hand-written config literals, not arbitrary JavaScript.
    pattern = (r"\b(?:" + keys
               + r')\s*:\s*(?:"([^"]*)"'
               + r"|'([^']*)')")
    return " ".join(a or b for a, b in re.findall(pattern, src, re.S))


def renderer_copy(path: Path) -> str:
    """The prose a renderer script emits, out of the HTML it concatenates.

    A renderer has no `key: "value"` pairs to read, so script_copy() finds
    nothing in it. What it does have is quoted fragments that are glued into
    HTML, and the visitor reads whatever ends up between the tags.

    So: take every quoted literal, join them in source order, and put the result
    through the same tag-stripper the .html pages go through. A fragment that
    ends mid-tag simply leaves a tag the stripper removes.

    Deliberately NOT a JavaScript parser. It over-collects -- class names and
    attribute fragments come along too -- and that is the safe direction here,
    because every check run against this text looks for a banned English phrase.
    "wiz-step" matches nothing on any list. Missing real copy would be the
    dangerous error; carrying a few class names is not.
    """
    src = path.read_text(encoding="utf-8")
    parts = re.findall(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"", src)
    glued = "".join(a or b for a, b in parts)
    return visible_text(glued)


for page in PAGES + COPY_IN_SCRIPTS + COPY_IN_RENDERERS:
    path = HERE / page
    # A config script holds DISCRETE LABELS, not prose. The vocabulary tenets
    # apply to both -- a banned phrase is banned wherever a visitor reads it --
    # but the shape tenets do not: "Individual tax preparation" is a three-word
    # option, and 83 of them are not one 300-word sentence. Two of them repeat
    # on purpose ("None of these", "I am not sure"), which is how a form is
    # meant to work, not copy said twice.
    is_page = page not in COPY_IN_SCRIPTS and page not in COPY_IN_RENDERERS
    if is_page:
        text = visible_text(path.read_text(encoding="utf-8"))
    elif page in COPY_IN_SCRIPTS:
        text = script_copy(path)
        assert text.strip(), f"{page}: no visitor-facing strings found -- has it changed shape?"
    else:
        text = renderer_copy(path)
        assert text.strip(), f"{page}: no visitor-facing strings found -- has it changed shape?"
    low = text.lower()
    sents = sentences(text)

    print(f"--- {page}")

    # Tenet 7
    hits = [w for w in CONTRACT_WORDS if w in low]
    check(not hits, f"no contract-desk language or terms of art — found {hits}")

    # Tenet 1
    hits = [w for w in SELF_CLAIMS if w in low]
    check(not hits,
          f"no sentence about how we behave — found {hits}. Say the thing, "
          "not how well we do it")

    # Tenet 6
    hits = [w for w in PROMISES if w in low]
    check(not hits,
          f"no promise about a person, a time or a number — found {hits}")

    # Tenets 9 and 5 measure the SHAPE of prose -- how long a sentence runs, and
    # whether a claim is made twice. Neither is meaningful over a list of
    # discrete form labels, so they are not run there and this says so instead
    # of quietly skipping: a check that did not happen must not read as one that
    # passed.
    if not is_page:
        print("  n/a   sentence length and repetition — not prose, "
              "83 form labels are not one sentence and repeated options are "
              "how a form works")
        print()
        continue

    # Tenet 9
    longs = [s for s in sents if len(s.split()) > MAX_WORDS]
    check(not longs,
          f"no sentence past {MAX_WORDS} words — {[s[:70] + '…' for s in longs]}")

    # Tenet 5. The most-violated one, and the reason it kept surviving review is
    # that nobody reads a whole page at once — the two copies are 500px apart.
    # A machine reads it all at once, which is the only advantage it has here.
    prose = [s for s in sents if not is_chrome(s)]
    seen = Counter(s.lower() for s in prose if len(s.split()) >= 5)
    dupes = [s for s, n in seen.items() if n > 1]
    check(not dupes,
          f"nothing is said twice — {[s[:60] + '…' for s in dupes]}")

    # Tenet 5 again, for the case that is not a whole repeated sentence: the
    # same claim reworded a screen apart. A shared run of words is the only part
    # of that a machine can see, so it looks for one and leaves the rest to a
    # reader.
    words = re.findall(r"[a-z']+", " . ".join(prose).lower())
    grams = Counter(" ".join(words[i:i + 6]) for i in range(len(words) - 5))
    echoes = [g for g, n in grams.items() if n > 1]
    check(not echoes, f"no phrase repeats across the page — {echoes}")

    print()

total = _pass + _fail
print(f"{_pass}/{total} checks passed")
if _fail:
    print("\nA tenet is broken. website/TENETS.md says which and why.")
    sys.exit(1)
print("Every page reads the way the firm asked for.")
