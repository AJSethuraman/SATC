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

  MATCH      every probe is on the page. For a claim that is a date, a
             threshold or a form number, that is the whole question, and a
             string check is more reliable than a person skimming.
  PARTIAL    some probes found, some not. Usually wording that was paraphrased
             rather than quoted -- a human decides.
  NO MATCH   nothing distinctive was found. Either the claim is not on that
             page, or the page moved its wording. Read it.
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


def probes(claim: str, note: str) -> list[str]:
    """The strings that would have to be on the page for the claim to hold."""
    out: list[str] = []
    # Anything the sources file put in quotation marks is a direct quote and is
    # the strongest probe available.
    for q in re.findall(r'"([^"]{8,160})"', note):
        out.append(q)
    # Then the claim's own hard facts: years, amounts, form numbers, day-month
    # pairs. These are what a client actually relies on.
    both = claim + " " + note
    out += re.findall(r"\$[\d,]+(?:\.\d\d)?", both)
    out += re.findall(r"\b(?:19|20)\d{2}\b", both)
    out += re.findall(r"\b(?:Form|Schedule|Publication|Pub\.?)\s*[\dA-Z][\dA-Z-]*", both)
    out += re.findall(r"\b(?:January|February|March|April|May|June|July|August|"
                      r"September|October|November|December)\s+\d{1,2}\b", both)
    seen, keep = set(), []
    for p in out:
        p = p.strip().strip(".,;")
        if len(p) < 3 or p.lower() in STOP or p.lower() in seen:
            continue
        seen.add(p.lower()); keep.append(p)
    return keep[:8]


def found(page: str, probe: str) -> bool:
    p = page.lower()
    q = re.sub(r"\s+", " ", probe.lower().strip())
    if q in p:
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
            m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", line)
            if not m or not guide:
                continue
            claim, src = m.group(1), m.group(2)
            if set(claim) <= set("-: ") or claim.startswith("Claim in the draft"):
                continue
            links = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", src)
            rows.append({
                "guide": guide, "section": section,
                "claim": re.sub(r"\*\*(.+?)\*\*", r"\1", claim),
                "note": re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", src),
                "urls": links,
                "already_read": "READ" in src,
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

    results, tally = [], {"MATCH": 0, "PARTIAL": 0, "NO MATCH": 0, "UNREACHED": 0}
    for r in rows:
        ps = probes(r["claim"], r["note"])
        text = " ".join(pages.get(u, "") for u in r["urls"])
        if not r["urls"]:
            verdict, hits, miss = "UNREACHED", [], []
        elif not text:
            verdict, hits, miss = "UNREACHED", [], ps
        elif not ps:
            verdict, hits, miss = "PARTIAL", [], []
        else:
            hits = [p for p in ps if found(text, p)]
            miss = [p for p in ps if p not in hits]
            verdict = "MATCH" if not miss else ("PARTIAL" if hits else "NO MATCH")
        tally[verdict] += 1
        results.append({**r, "verdict": verdict, "hit": hits, "miss": miss})

    for v in ("NO MATCH", "PARTIAL", "UNREACHED", "MATCH"):
        group = [x for x in results if x["verdict"] == v]
        if not group:
            continue
        print("=" * 78)
        print(f"{v} — {len(group)}")
        print("=" * 78)
        for x in group if v != "MATCH" else group[:0]:
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
