#!/usr/bin/env python3
"""Check sitemap.xml against the pages that actually exist, and against git.

    cd website && python3 sitemap.spec.py

WHY THIS EXISTS

`sitemap.xml` and `robots.txt` were the only two published files with no test of
any kind. On 7 September 2026 the three guide pages were added to the sitemap in
commit 061ac96 -- the same commit that created them -- and stamped
`lastmod 2026-08-26`, twelve days before the files existed. Nobody could have
noticed: nothing read the file.

The file's own comment states the rule it broke:

    `lastmod` is a real date per page, not the date this file was touched; a
    sitemap that claims everything changed today is a sitemap a crawler stops
    believing.

The rule was kept for the two rows that predated the commit and broken for the
three new ones, because the new rows were written by copying the rows above.

WHAT A WRONG `lastmod` COSTS

A date in the past is worse than no date. It tells a crawler the page has not
changed since before it was published, so the wording the firm has just approved
is the change least likely to be fetched again.

WHAT THIS DOES NOT DO

It does not check that the sitemap is complete against a crawl of the site --
only against `PAGES` below, which is the published set this repository knows
about. If a seventh page is ever published without being added here, this file
is one of the two places to update.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITEMAP = HERE / "sitemap.xml"

#: Published page -> the files whose last change is that page's last change.
#: The guides are GENERATED, so their real source is the draft in docs/guides/
#: plus the generator: editing a draft changes the page even though the .html is
#: written by a machine. A page whose date came only from its own .html would be
#: right by accident here and wrong the first time someone rebuilt without
#: editing.
PAGES = {
    "https://satcllp.com/": ["website/index.html"],
    "https://satcllp.com/pricing.html": [
        "website/pricing.html", "website/pricing-config.js"],
    "https://satcllp.com/privacy.html": ["website/privacy.html"],
    "https://satcllp.com/guides/records.html": [
        "website/guides/records.html", "docs/guides/good-records-individuals.md"],
    "https://satcllp.com/guides/business-records.html": [
        "website/guides/business-records.html", "docs/guides/good-records-business.md"],
    "https://satcllp.com/guides/s-corp.html": [
        "website/guides/s-corp.html", "docs/guides/entity-choice.md"],
}

_fail = 0


def check(ok, msg):
    global _fail
    if ok:
        print(f"  PASS  {msg}")
    else:
        _fail += 1
        print(f"  FAIL  {msg}")


def last_commit_date(paths: list[str]) -> str | None:
    """The most recent commit date touching any of these files, as YYYY-MM-DD.

    Returns None when git cannot answer -- a shallow clone, or a file with no
    history yet. That is reported as UNKNOWN rather than guessed: a date this
    file invented would be exactly the defect it exists to catch.
    """
    dates = []
    for p in paths:
        try:
            out = subprocess.run(
                ["git", "log", "-1", "--format=%as", "--", p],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode == 0 and out.stdout.strip():
            dates.append(out.stdout.strip())
    return max(dates) if dates else None


print("SATC — sitemap.xml against the pages that exist\n")

xml = SITEMAP.read_text(encoding="utf-8")
entries = dict(re.findall(
    r"<loc>\s*([^<]+?)\s*</loc>\s*<lastmod>\s*([0-9-]+)\s*</lastmod>", xml, re.S))

check(entries, f"the sitemap parses and has entries — found {len(entries)}")

print("\n--- every published page is listed")
for url in PAGES:
    check(url in entries, f"listed: {url}")

print("\n--- nothing is listed that is not a published page")
for url in entries:
    check(url in PAGES, f"known page: {url}")

print("\n--- the file each URL points at exists")
for url in PAGES:
    rel = url.replace("https://satcllp.com/", "") or "index.html"
    check((HERE / rel).exists(), f"file on disk for {url}")

print("\n--- lastmod is not in the future")
today = subprocess.run(["git", "log", "-1", "--format=%as"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
for url, when in entries.items():
    check(when <= today if today else True,
          f"not dated after the last commit ({today}): {url} says {when}")

print("\n--- lastmod is not EARLIER than the page's own last change")
# The direction that matters. A date later than the truth only costs a wasted
# re-crawl; a date EARLIER tells a crawler the newest wording is old, which is
# the failure this file was written for. Equal or later is accepted, because a
# sitemap is allowed to be conservative -- it is not a changelog.
for url, files in PAGES.items():
    real = last_commit_date(files)
    said = entries.get(url)
    if real is None:
        print(f"  n/a   git could not date {url} — reported, not guessed")
        continue
    if said is None:
        continue
    check(said >= real,
          f"{url}: sitemap says {said}, last real change {real}"
          + ("" if said >= real else "  <-- a crawler is told the newest wording is old"))

print(f"\n{'FAILED' if _fail else 'OK'} — {_fail} failing check(s)")
sys.exit(1 if _fail else 0)
