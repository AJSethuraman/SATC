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
PROMISES = [
    "as soon as we can", "business day", "within 24 hours", "same day",
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

for page in PAGES:
    src = (HERE / page).read_text(encoding="utf-8")
    text = visible_text(src)
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
