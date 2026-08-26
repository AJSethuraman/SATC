#!/usr/bin/env python3
"""Run the mechanical half of the website tenets over the guide drafts.

    cd docs/guides && python3 tenets.spec.py

WHY THIS EXISTS
---------------
`website/copy.spec.py` guards `index.html`, `pricing.html` and `privacy.html`.
These drafts are client-facing copy that has not reached `website/` yet, and
the argument in that file applies here word for word: the tenets left to
judgment were the ones broken every time afterwards, by drafters who had read
them and believed they were complying.

So the word lists are imported rather than copied. If `website/copy.spec.py`
adds a banned phrase, these drafts are held to it on the next run — a copy
would drift the day someone edits one and not the other.

WHAT IT DOES NOT DO
-------------------
Tenets 2 and 4 are measured in a browser. There is no browser here because
there is no page yet; they apply when this copy is built into HTML.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
COPY_SPEC = HERE.parent.parent / "website" / "copy.spec.py"
DRAFTS = ["good-records-individuals.md", "good-records-business.md",
          "entity-choice.md"]

_fail = 0


def check(ok, msg):
    global _fail
    if ok:
        print(f"  PASS  {msg}")
    else:
        _fail += 1
        print(f"  FAIL  {msg}")


def load_lists():
    """Import the lists out of website/copy.spec.py without running its checks.

    That file executes its checks at import time against the published pages,
    so it cannot simply be imported. The lists are read out of the source
    instead — literal-only, so nothing in that file runs here.
    """
    src = COPY_SPEC.read_text(encoding="utf-8")
    out = {}
    for name in ("CONTRACT_WORDS", "SELF_CLAIMS", "PROMISES"):
        m = re.search(rf"^{name} = (\[.*?\n\])", src, re.S | re.M)
        if not m:
            raise SystemExit(f"{COPY_SPEC} no longer defines {name}")
        out[name] = eval(m.group(1))  # noqa: S307 — a list literal from our repo
    m = re.search(r"^MAX_WORDS = (\d+)", src, re.M)
    out["MAX_WORDS"] = int(m.group(1)) if m else 28
    return out


# Ported from pricing.spec.py. A US LLP filing US returns.
BRITISH = ("cancelled", "itemised", "recognise", "licence", "colour", "organis",
           "analyse", "centre", "grey", "whilst", "amongst", "practise",
           "defence", "summarised")


def visible_text(md: str) -> str:
    """What a reader sees. HTML comments carry the [CONFIRM: notes and are
    addressed to the firm, not to a client, so they come out first — the same
    reason copy.spec.py strips source comments before matching."""
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    md = re.sub(r"^\s*[-*]\s+", "", md, flags=re.M)   # bullets are sentences
    md = re.sub(r"^#{1,6}\s+", "", md, flags=re.M)
    md = re.sub(r"^---+\s*$", "", md, flags=re.M)
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)  # link text only
    md = md.replace("**", "").replace("*", "").replace("`", "")
    for fancy, plain in (("‑", "-"), ("‐", "-"), ("–", "-"),
                         ("—", " - "), ("’", "'"), ("‘", "'"),
                         ("“", '"'), ("”", '"'), (" ", " "),
                         ("·", ".")):
        md = md.replace(fancy, plain)
    return md


def sentences(text: str) -> list[str]:
    out = []
    for chunk in re.split(r"[.!?]+[\s\n]|\n{2,}", text):
        s = " ".join(chunk.split())
        if s:
            out.append(s)
    return out


L = load_lists()
print("SATC — the copy tenets, over the guide drafts\n")

for name in DRAFTS:
    path = HERE / name
    text = visible_text(path.read_text(encoding="utf-8"))
    low = text.lower()
    sents = sentences(text)

    print(f"--- {name}")

    hits = [w for w in L["CONTRACT_WORDS"] if w in low]
    check(not hits, f"tenet 7 — no contract-desk language or terms of art {hits or ''}")

    hits = [w for w in L["SELF_CLAIMS"] if w in low]
    check(not hits, f"tenet 1 — no sentence about how we behave {hits or ''}")

    hits = [w for w in L["PROMISES"] if w in low]
    check(not hits, f"tenet 6 — no promise about a person, a time or a number {hits or ''}")

    longs = [s for s in sents if len(s.split()) > L["MAX_WORDS"]]
    check(not longs,
          f"tenet 9 — no sentence past {L['MAX_WORDS']} words "
          f"{[s[:60] + '...' for s in longs] or ''}")

    seen = Counter(s.lower() for s in sents if len(s.split()) >= 5)
    dupes = [s for s, n in seen.items() if n > 1]
    check(not dupes, f"tenet 5 — nothing said twice {[d[:50] for d in dupes] or ''}")

    hits = [w for w in BRITISH if w in low]
    check(not hits, f"American spelling throughout {hits or ''}")

# Tenet 5 across the set. Two guides that repeat each other are one guide split
# in half, which is the failure the separate-pages decision has to survive. It
# was written for a pair and now runs over every pair, because the third guide
# overlaps BOTH of the others in subject — an S corporation owner appears in the
# business guide's section 06 and its K-1 in the individual guide's section 01.
print("--- the pages against each other")

# One sentence is SUPPOSED to be on every page, word for word: the line saying
# this is general information rather than advice. The firm settled its register
# on 26 August -- "make the wording fairly generic" -- and three pages carrying
# three different versions of the same disclaimer reads worse than one carrying
# it three times. So it is furniture, like a wordmark in a header and again in
# a footer, and it comes out before the pages are compared.
#
# Exempted by matching the sentence, not by skipping a trailing block: a real
# repetition that happened to sit at the foot of a page would still be caught.
FURNITURE = re.compile(
    r"this is general information,? not advice about a particular [a-z]+\.?",
    re.I)

grams = {}
for name in DRAFTS:
    text = visible_text((HERE / name).read_text(encoding="utf-8"))
    text = FURNITURE.sub(" ", text)
    words = re.findall(r"[a-z']+", text.lower())
    grams[name] = {" ".join(words[i:i + 7]) for i in range(len(words) - 6)}
for i, a in enumerate(DRAFTS):
    for b in DRAFTS[i + 1:]:
        shared = grams[a] & grams[b]
        check(not shared,
              f"{a} and {b} share no run of prose {list(shared)[:3] or ''}")

# The claim the price page will link to. If the phrase the link hangs on is not
# answered on the page, the link is decoration.
first = (HERE / DRAFTS[0]).read_text(encoding="utf-8").lower()
check("complete means" in first,
      "the individual guide answers the price page's word 'complete' outright")

print(f"\n{'FAILED' if _fail else 'OK'} — {_fail} failing check(s)")
sys.exit(1 if _fail else 0)
