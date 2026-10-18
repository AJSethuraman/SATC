"""Set up the walkthrough's book: the repository's book, with only the cache moved.

Run from threshold-engine/:  python docs/walkthrough-book/prepare.py CACHE
Writes docs/walkthrough-book/out/book.json and out/series.csv: the same
settings, series, notes and peers build as books/consumer-public.json, except
that the FDIC cache (and the mergers and absorptions files in it) is CACHE, a
cache 'peers pull' already filled, and the peers build writes its series to
out/series. At work the cache is books/ind_cache, filled by the pull in
books/README.md; nothing else differs.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
cache = Path(sys.argv[1]).resolve()             # argv[2]: the SEC filings' cache
out = HERE / "out"
out.mkdir(exist_ok=True)
book = json.loads((ROOT / "books" / "consumer-public.json").read_text(encoding="utf-8"))
with (ROOT / "books" / "consumer-public-series.csv").open(newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))
for r in rows:
    if "data/industry/" in r["file"].replace("\\", "/"):
        r["file"] = str(ROOT / "data" / "industry" / Path(r["file"]).name)      # committed, not built
    else:
        r["file"] = "series/" + Path(r["file"]).name
with (out / "series.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
book["series"] = "series.csv"
book["peers"].update(cache=str(cache), mergers=str(cache / "mergers.json"), absorptions=str(cache / "absorptions.json"),
                     roster=str(ROOT / "config" / "peers.json"), series_dir="series")
# The SEC filings for the Peer loan classes tab: the cache 'peers classes-pull' filled.
book["loan_classes"] = {"file": str(ROOT / "config" / "peer-loan-classes.json"),
                        "cache": str(Path(sys.argv[2]).resolve())}
book["reporting_changes"] = str(ROOT / "config" / "reporting-changes.json")
if book.get("signals") is not None:
    sig = cache / "signals"
    book["signals"] = {"balances": str(sig / "26Q2-CreditCardBalances.csv"), "originations": str(sig / "26Q2-CreditCardOriginations.csv"),
                       "survey": str(sig / "DRTSCLCC.csv"), "nmdb": str(ROOT / "data" / "signals" / "nmdb.json"),
                       "fico": str(ROOT / "data" / "signals" / "fico-under-660.json")}
if book.get("large_banks") is not None:
    # The Philadelphia Fed file 'peers large-banks-pull' put beside the FDIC cache.
    book["large_banks"] = {"file": str(cache / "large-banks" / Path(book["large_banks"]["file"]).name)}
(out / "book.json").write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8")
print("wrote %s: %d series, cache %s" % (out / "book.json", len(rows), cache))
