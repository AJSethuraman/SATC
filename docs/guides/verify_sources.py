#!/usr/bin/env python3
"""Check every claim in the guides against the page it cites.

    python3 docs/guides/verify_sources.py              # check everything
    python3 docs/guides/verify_sources.py --refetch    # ignore the page cache
    python3 docs/guides/verify_sources.py --json OUT   # machine-readable result

WHY IT EXISTS

The guides were drafted on a machine that could not reach irs.gov, so every
citation was a URL found through search and quoted from a search extract. One
of them turned out to claim more than its page carries, and it took a human
reading a PDF to find that. This does the same job for the other eighty-odd,
and it does not get tired at row sixty.

WHAT IT CAN AND CANNOT SETTLE

It reads the cited page and looks for the claim's own load-bearing strings --
the phrases the sources file put in quotation marks, and the dates, amounts,
years and form numbers in the claim itself. So:

  MATCH      the page carries the QUOTED WORDING the sources file attributed
             to it, and every other probe too. This is the only verdict that
             means the claim's assertion was tested.

             Quotes inside a sentence that records what a page does NOT say
             are skipped -- see NEGATIVE. Without that, writing down a
             correction made the corrected row look like a failure.
  UNTESTED   the claim cites a page but the sources file quotes no wording from
             it, so there was nothing to test the assertion against. Bare years
             and form numbers being present proves only that the page mentions
             them. NOT a pass.
  PARTIAL    some probes found, some not. Usually wording that was paraphrased
             rather than quoted -- a human decides.
  NO MATCH   nothing distinctive was found. Either the claim is not on that
             page, or the page moved its wording. Read it.
  PRACTICE   the sources file labels this the firm's own practice or an
             explicit non-claim. There is no page to check it against, and the
             label -- not this tool -- is what discloses that.
  NO SOURCE  the sources file names no page for a claim that is not labelled
             practice. Nothing to check and nothing saying so. Fix the row.
  UNREACHED  the fetch failed. Not a verdict about the claim.

It cannot settle a claim of interpretation -- "an LLC changes nothing on a
federal return" is not a string. Those come back PARTIAL or NO MATCH by design,
which is the honest answer rather than a false green.

RE-RUN IT ANNUALLY. The IRS reissues these instructions every year, and a
verification pass done once rots. This is the part that makes that cheap.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".source-cache"
SOURCES = ["SOURCES.md", "SOURCES-entity-choice.md"]

# Words too common to prove anything. A probe made only of these is dropped
# rather than counted as found -- "January" appears on every IRS page.
STOP = {"january", "february", "march", "april", "may", "june", "july",
        "august", "september", "october", "november", "december",
        "the", "and", "for", "you", "your", "not", "that", "with", "form"}

# "Same", "Same page", "Same document", "Same two pages" -- shorthand in the
# sources files meaning "the row above". It does not always open the note:
# "**READ - open question closed.** Same document." puts it second, and
# anchoring to the start missed that row and reported it as having no source.
# Only consulted when the row names no URL of its own.
SAME = re.compile(r"(?:^|\.\s|\*\*\s*)Same\b(?:\s+(?:page|document|two pages|"
                  r"source|IRS|form)\b)?", re.I)

# Rows the sources files mark as the firm's own practice or as a deliberate
# non-claim. These are not assertions about a cited page and are reported in
# their own bucket rather than as unverified facts.
PRACTICE = re.compile(r"\b(?:Practice(?:[.,]|$| for | on |, resting)|"
                      r"\*\*Practice|Deliberate non-claim|"
                      r"is the firm's own|are the inputs the return needs)",
                      re.I)

# A sources note does two jobs: it quotes what the page says, and it records
# what the page turned out NOT to say. Both go in quotation marks, and a
# checker that cannot tell them apart reports the second kind as a failure --
# which is how correcting a bad citation used to make the row look worse.
#
# So: a SENTENCE carrying one of these cues contributes no probes. Its quotes
# are either negative evidence ("the string 2012 does not appear on that page")
# or a quote of our own draft rather than of the source ("the guide now says").
# Write those in their own sentence and the checker will stay out of the way.
NEGATIVE = re.compile(
    r"\b(?:"
    r"does not appear|do not appear|doesn't appear|never (?:says|states|appears)|"
    r"is not on (?:it|that page|the page)|not on that page|not on the page|"
    r"cannot support|can't support|does not (?:carry|say|state)|did not carry|"
    r"is not quoted|are \*\*not quoted|not quoted here|"
    r"the draft said|used to (?:say|cite|claim|assert)|previously (?:said|cited|claimed)|"
    r"the row used to|the guide now says|both places now say|now says|"
    r"is deliberately|are deliberately|deliberately (?:not|absent)|"
    r"stays out of|is not in the guide|"
    # A sentence about a fetch that FAILED quotes the error page, not the
    # source: "come back as an 853-byte 'official State of Ohio government
    # website' wrapper" was being probed for on the page that replaced it.
    r"comes? back as|cannot be fetched|can't be fetched|never downloaded|"
    r"was ever read|were ever read|wrapper rather than"
    r")\b", re.I)


def fetch(url: str, refetch: bool = False) -> str | None:
    CACHE.mkdir(exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9]+", "_", url)[:120] + ".txt"
    path = CACHE / key
    if path.exists() and not refetch:
        return path.read_text(encoding="utf-8", errors="replace")
    try:
        # Bytes, not text: some citations are PDFs, and one non-UTF-8 byte in a
        # single response used to kill the whole run at page 38 of 57.
        r = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "45", "-A",
             "Mozilla/5.0 (compatible; SATC-source-check)", url],
            capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    raw = r.stdout
    if raw[:5] == b"%PDF-":
        text = pdf_text(raw)
    else:
        text = strip_html(raw.decode("utf-8", errors="replace"))
    path.write_text(text, encoding="utf-8")
    time.sleep(0.6)                       # be polite to a government host
    return text


def pdf_text(raw: bytes) -> str:
    """Enough text out of a PDF to probe against.

    A cited PDF is a real source and skipping it would quietly under-report.
    This pulls the literal and hex strings out of the content streams; a font
    subset is decoded by its offset from ASCII, which is how the General
    Instructions PDF turned out to be encoded.
    """
    import zlib
    parts = []
    for m in re.finditer(rb"stream\r?\n?(.*?)endstream", raw, re.S):
        try:
            data = zlib.decompress(m.group(1).strip(b"\r\n"))
        except Exception:
            continue
        if b"BT" not in data or b"Tf" not in data:
            continue
        for tm in re.finditer(rb"\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]+)>", data):
            if tm.group(1):
                hx = re.sub(rb"\s", b"", tm.group(1))
                for i in range(0, len(hx) - 3, 4):
                    c = int(hx[i:i + 4], 16) + 29
                    if 32 <= c < 127:
                        parts.append(chr(c))
            else:
                v = tm.group(0)[1:-1]
                v = re.sub(rb"\\([()\\])", rb"\1", v)
                parts.append(v.decode("latin-1"))
    return re.sub(r"\s+", " ", "".join(parts))


def strip_html(src: str) -> str:
    src = re.sub(r"<(script|style|nav|footer|head)\b.*?</\1>", " ", src,
                 flags=re.S | re.I)
    src = re.sub(r"<[^>]+>", " ", src)
    src = html.unescape(src)
    for a, b in (("‑", "-"), ("‐", "-"), ("–", "-"),
                 ("—", " - "), ("’", "'"), ("“", '"'),
                 ("”", '"'), (" ", " ")):
        src = src.replace(a, b)
    return re.sub(r"\s+", " ", src)


def probes(claim: str, note: str) -> tuple[list[str], list[str]]:
    """Return (substantive, token) probes.

    THE DISTINCTION IS THE WHOLE POINT, and getting it wrong is what made the
    first version of this file overstate its results.

    A SUBSTANTIVE probe is a quoted phrase -- wording the sources file says the
    page actually contains. Finding it tests the claim's assertion.

    A TOKEN probe is a bare year, amount or form number. Finding one proves the
    page mentions that token and nothing else. "2025" appears on the 1099-DA
    page; so does "2026"; so does "Form 1099-DA". A claim whose only probes are
    tokens was never tested, and the first version of this script called that
    MATCH -- which is how "crypto statements for 2025 sales show proceeds and
    not cost" came back verified while the cited page says brokers report
    proceeds "(and in some cases, basis for)" digital assets. The firm caught
    it, not the tool.

    So a claim with no substantive probe is now UNTESTED, never MATCH.
    """
    sub: list[str] = []
    # Split on sentence enders, INCLUDING one that sits inside a closing quote
    # -- `...as a corporation". The page adds` is two sentences. Missing that
    # glued a positive quote to the correction sentence beside it, and the
    # correction's cue then suppressed the quote that was doing the work.
    # The quote character stays in the sentence -- match it in the LOOKBEHIND
    # rather than consuming it. Consuming it stripped the closing quote off
    # `...for the year."` and then no quoted phrase could be found at all.
    # Split the note into sentences, but NEVER inside a quotation -- a quote
    # that runs to two sentences ("...does not pay income tax. Instead, it
    # passes through...") was being cut in half, which orphaned its quotation
    # marks and lost the whole probe. Mask the quoted spans, split, restore.
    BAR = "\x00"
    # Only a period FOLLOWED BY SPACE, i.e. an internal sentence break. A
    # period sitting right before the closing quote is the quote's own ending
    # and the note's; masking that one re-merged the sentence with whatever
    # followed it.
    masked = re.sub(r'"[^"]*"',
                    lambda m: re.sub(r"\.(?=\s)", BAR, m.group(0)), note)
    # Sentence enders, including one followed by a closing quote or by markdown
    # bold. `...on that page at all.** What the page says is "..."` is two
    # sentences; treating it as one let the negative half suppress the quote in
    # the positive half, so a corrected row still counted as untested.
    positive = " ".join(
        s for s in re.split(r"""(?<=[.!?]\*\*)\s+|(?<=[.!?]["'\)\]])\s+|(?<=[.!?])\s+""", masked)
        if not NEGATIVE.search(s)).replace(BAR, ".")
    # Up to 320 characters. The cap was 160, which silently dropped the quotes
    # that carry the most -- a statutory sentence runs long ("In order to form
    # a limited liability company, one or more persons shall execute articles
    # of organization and deliver the articles to the secretary of state for
    # filing." is 175). A dropped quote left the row UNTESTED with no hint why.
    for q in re.findall(r'"([^"]{8,320})"', positive):
        if len(q.split()) >= 5:            # a phrase, not a stray fragment
            sub.append(q)

    tok: list[str] = []
    both = claim + " " + positive
    tok += re.findall(r"\$[\d,]+(?:\.\d\d)?", both)
    tok += re.findall(r"\b(?:19|20)\d{2}\b", both)
    tok += re.findall(r"\b(?:Form|Schedule|Publication|Pub\.?)\s*[\dA-Z][\dA-Z-]*", both)
    tok += re.findall(r"\b(?:January|February|March|April|May|June|July|August|"
                      r"September|October|November|December)\s+\d{1,2}\b", both)

    def dedupe(xs):
        seen, keep = set(), []
        for x in xs:
            x = x.strip().strip(".,;")
            if len(x) < 3 or x.lower() in STOP or x.lower() in seen:
                continue
            seen.add(x.lower()); keep.append(x)
        return keep
    return dedupe(sub)[:6], dedupe(tok)[:6]


def found(page: str, probe: str) -> bool:
    p = page.lower()
    q = re.sub(r"\s+", " ", probe.lower().strip())
    if q in p:
        return True
    # A PDF content stream carries no spaces between text-showing operators, so
    # extraction glues words: the RITA Form 37 instructions come out as
    # "residentmunicipality", and a correct phrase probe misses. Compare with
    # all whitespace removed before concluding the wording is absent.
    if re.sub(r"\s", "", q) in re.sub(r"\s", "", p):
        return True
    # A quote can be broken by markup or a line break in the source; fall back
    # to requiring most of its distinctive words, in any order.
    words = [w for w in re.findall(r"[a-z0-9$.,-]{3,}", q) if w not in STOP]
    if len(words) >= 4:
        hit = sum(1 for w in words if w in p)
        return hit >= max(4, int(len(words) * 0.8))
    return False


def parse_sources() -> list[dict]:
    rows, guide, section = [], "", ""
    for name in SOURCES:
        fixed = "entity-choice.md" if "entity" in name else ""
        guide = fixed
        for line in (HERE / name).read_text(encoding="utf-8").split("\n"):
            h = re.match(r"^## `?(.+?)`?$", line)
            if h:
                g = h.group(1)
                if g.endswith(".md"):
                    guide, section = g, ""
                else:
                    section = g
                continue
            h3 = re.match(r"^### (.+)$", line)
            if h3:
                section = h3.group(1).strip(); continue
            # Exactly two cells. SOURCES.md also carries a three-column
            # weekend/holiday table, and a looser pattern read its rows as
            # claims -- inventing five entries called "Stated", "January 31",
            # "February 15", "March 15" and "May 31", each of them UNREACHED
            # because a date is not a claim and has no source.
            if not guide or not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 2 or not all(cells):
                continue
            claim, src = cells
            if set(claim) <= set("-: ") or claim.startswith("Claim in the draft"):
                continue
            links = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", src)
            # "Same", "Same page", "Same two pages" -- the file's own shorthand
            # for the row above. Without following it, a correctly sourced row
            # was reported as having no source at all, which put twenty-one
            # rows in a bucket that read like a failure and was not one.
            if not links and SAME.search(src) and rows:
                links = rows[-1]["urls"]
            rows.append({
                "guide": guide, "section": section,
                "claim": re.sub(r"\*\*(.+?)\*\*", r"\1", claim),
                "note": re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", src),
                "urls": links,
                "already_read": "READ" in src,
                # A claim of practice is not a claim about a page, and holding
                # it against a citation it never had is how the honest count
                # got buried. It still has to be LABELLED practice in the file.
                "practice": bool(PRACTICE.search(src)),
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--json")
    args = ap.parse_args()

    rows = parse_sources()
    urls = sorted({u for r in rows for u in r["urls"]})
    print(f"{len(rows)} claims · {len(urls)} distinct pages\n")

    pages, dead = {}, []
    for i, u in enumerate(urls, 1):
        text = fetch(u, args.refetch)
        if text is None or len(text) < 400:
            dead.append(u)
        else:
            pages[u] = text
        print(f"  fetched {i}/{len(urls)}  {'ok ' if u in pages else 'FAIL'} {u[:78]}")
    print()

    results, tally = [], {"MATCH": 0, "PARTIAL": 0, "NO MATCH": 0, "UNTESTED": 0,
                          "PRACTICE": 0, "NO SOURCE": 0, "UNREACHED": 0}
    for r in rows:
        sub, tok = probes(r["claim"], r["note"])
        ps = sub + tok
        text = " ".join(pages.get(u, "") for u in r["urls"])
        if r["practice"] and not sub:
            # Labelled practice in the sources file. Nothing to check, and
            # nothing being hidden either -- the label is the disclosure.
            verdict, hits, miss = "PRACTICE", [], []
        elif not r["urls"]:
            verdict, hits, miss = "NO SOURCE", [], []
        elif not text:
            verdict, hits, miss = "UNREACHED", [], ps
        elif not sub:
            # No quoted wording to test against. Whatever the tokens do, the
            # claim's assertion was not checked -- say so rather than imply it.
            hits = [p for p in tok if found(text, p)]
            verdict, miss = "UNTESTED", [p for p in tok if p not in hits]
        else:
            hits = [p for p in ps if found(text, p)]
            miss = [p for p in ps if p not in hits]
            sub_miss = [p for p in sub if p not in hits]
            if sub_miss:
                verdict = "PARTIAL" if hits else "NO MATCH"
            else:
                verdict = "MATCH" if not miss else "PARTIAL"
        tally[verdict] += 1
        results.append({**r, "verdict": verdict, "hit": hits, "miss": miss})

    for v in ("NO MATCH", "PARTIAL", "UNTESTED", "NO SOURCE", "UNREACHED",
              "PRACTICE", "MATCH"):
        group = [x for x in results if x["verdict"] == v]
        if not group:
            continue
        print("=" * 78)
        print(f"{v} — {len(group)}")
        print("=" * 78)
        for x in group if v not in ("MATCH", "PRACTICE") else group[:0]:
            print(f"\n  {x['guide']} · {x['section']}")
            print(f"  {x['claim'][:150]}")
            if x["miss"]:
                print(f"    not on the page: {x['miss']}")
            if x["hit"]:
                print(f"    found:           {x['hit']}")
            for u in x["urls"]:
                print(f"    {u}")
        print()

    print("-" * 78)
    for k, n in tally.items():
        print(f"  {k:10} {n}")
    if dead:
        print(f"\n  {len(dead)} page(s) could not be fetched:")
        for u in dead:
            print(f"    {u}")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"\n  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
