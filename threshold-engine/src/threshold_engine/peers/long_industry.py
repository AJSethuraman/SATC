"""The industry's charge-off rates from 1990: every filer summed, as
``books.industry`` sums them, over a cache that reaches back before the
book's 2006 start.

The analyst, 17 Oct 2026: the industry's card, home equity and other
consumer charge-offs back to 1990Q1, as separate series under the source
"Industry (every bank) from 1990", with the 2006 series left as they are.
The long series give the lines a second credit cycle (1990-92, 2001-02) and
the 2008 peak with years before it; the 2006 series stay the ones the peer
group and KeyBank are set beside.

What the long series are not: pro forma for anything. Absorptions under
common control are taken off only where the absorptions file names them
(the merger record is pulled from a date, 2005 in the book), so a survivor's
repeated year-to-date before that date stays in the sum, and the note says
so. The registry's reporting changes touching the quarters are noted on each
file as ever.

``peers industry-long OUT_DIR --cache DIR --first 1990Q1 --last 2026Q2
--products ... --absorptions FILE --reporting-changes FILE`` writes
``<product>_industry-from-<year>_<net|gross>.csv`` into OUT_DIR.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, List, Sequence, Tuple

from . import books, fdic
from .. import reporting_changes as RC
from .run import REPULL, charge_off_fields, read_absorptions, series_note, slug, unbroken_tail

SOURCE = "Industry (every bank) from %s"


def write(out_dir, *, cache, first: str, last: str, products: Sequence[str], absorptions, reporting_changes,
          say: Callable[[str], None] = print) -> List[Tuple[Tuple[str, str, str], Path, int]]:
    """Write each product's net and gross series; returns ``[((product,
    measure, source), path, quarters written)]``. Reads the cache only."""
    quarters = fdic.quarter_ends(first, last)
    cache = Path(cache)
    missing = [q for q in quarters if not (cache / ("q%s.json" % q)).exists()]
    if missing:
        raise ValueError("%s has no %d of the %d quarters asked for (first missing %s): run 'peers pull' first"
                         % (cache, len(missing), len(quarters), missing[0]))
    for p in products:
        if p not in books.CONSUMER:
            raise ValueError("industry-long is for the consumer products (%s), not %r"
                             % (", ".join(books.CONSUMER), p))
    try:
        changes = RC.load(reporting_changes)
    except RC.RegistryError as e:
        raise ValueError("--reporting-changes: %s" % e) from None

    def no_fetch(url):
        raise ValueError("industry-long reads the cache only and never fetches")
    data = fdic.pull(quarters, charge_off_fields(list(products)) + [books.PARENT], cache, fetch=no_fetch)
    # The record may start after the history (the module docstring); since
    # 18 Oct 2026 it says when (question 22), and the note gives the date.
    since, links_ = read_absorptions(absorptions, again=REPULL)
    repeats = books.repeated_ytd(data, links_, list(products))
    data = books.without_repeats(data, repeats)
    merged = sorted({(r["acquirer"], r["quarter"]) for r in repeats})
    year = first[:4]
    source = SOURCE % year
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reg_sha = hashlib.sha256(Path(reporting_changes).read_bytes()).hexdigest()
    made = []
    for p in products:
        rows = books.industry(data, p)
        n_last = books.industry_filers(data, [p], quarters[-1])
        for kind in ("gross", "net"):
            measure = RC.charge_off_measure(kind)
            measure = measure[0].upper() + measure[1:]
            tail, before, after = unbroken_tail([(r["quarter"], r[kind + "_rate"]) for r in rows])
            note = ["%s, %s charge-off rate, trailing four quarters, %%." % (p, kind),
                    "Industry from %s: every filer in the cache (%d in %s), no jump or minimum rule. A separate "
                    "series from the book's industry series that starts in 2006, with the same sums over a longer "
                    "cache: the earlier quarters are a second credit cycle for the lines, and the series the peer "
                    "group and KeyBank are set beside stay as they are." % (year, n_last, last),
                    "Source: FDIC BankFind financials, %s to %s, from the cache %s." % (first, last, cache.name),
                    "Absorptions under common control: the absorbed bank's year-to-date charge-offs and recoveries, "
                    "which the survivor's filing repeats, are taken off the survivor's for the rest of that year "
                    "where %s names the absorption (%d survivor-quarters); before the merger record begins (%s), a "
                    "repeated year to date stays in the sum." % (Path(absorptions).name, len(merged), since),
                    "Reporting changes: %s, SHA-256 %s." % (Path(reporting_changes).name, reg_sha)]
            note += books.definitions(p)
            if tail:
                note += RC.note_lines(changes, books.members(p), RC.charge_off_measure(kind), tail[0][0],
                                      tail[-1][0], note)
            path = out_dir / ("%s_industry-from-%s_%s.csv" % (slug(p), year, kind))
            if not tail:
                say("Not written: %s has no value" % path.name)
                made.append(((p, measure, source), path, 0))
                continue
            books.write_series(tail, path, series_note(note, tail, before, after))
            say("Wrote %s: %d quarters, %s to %s%s" % (
                path, len(tail), tail[0][0], tail[-1][0],
                "; %d earlier left out at a break (%s to %s)" % (len(before), before[0], before[-1]) if before
                else ""))
            made.append(((p, measure, source), path, len(tail)))
    return made
