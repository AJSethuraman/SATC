"""The bank credit series: each product's net charge-offs and its loans 30+ days past due incl. nonaccrual,
every FDIC filer summed and KeyBank on its own, for credit card, other consumer, mortgage and home equity.

The firm, 23 Oct 2026, asked to bring these in from FDIC at each pull ("Yes, from FDIC each pull"), so the
Dashboard can set a macro series beside bank credit. They are built by the threshold engine's own peers pull and
build (``threshold_engine.peers``), under the settings the consumer book records (``books/consumer-public.json``,
"peers"), so each figure is the one the threshold workbook shows. Public data only: the FDIC BankFind API. The
quarters already in the cache are never fetched again, as ``peers pull`` keeps them.

``build_file(cache_root, today)`` returns the bytes of one JSON file, written into the pull's folder like any
other download: each series' quarters and the threshold engine's own notes on how it was made.
"""
import datetime
import json
import pathlib
import tempfile

from ..peers import books, fdic, run
from ..peers import delinquency as D
from ..peers import roster as R
from .catalog import BANK_MEASURES, BANK_PRODUCTS, BANK_WHO, bank_source_id

HERE = pathlib.Path(__file__).resolve()
#: The threshold engine's own files the build reads, inside its folder: the book's settings, the roster, the
#: registry of reporting changes.
BOOK, ROSTER, CHANGES = (pathlib.Path("books", "consumer-public.json"), pathlib.Path("config", "peers.json"),
                         pathlib.Path("config", "reporting-changes.json"))
#: The merger record the industry series were built with: data/industry/README.md, "peers pull ... --mergers
#: 2005-01-01". A survivor's repeated year to date is taken off from then on.
MERGERS_SINCE = "2005-01-01"
FILE = "fdic_credit.json"
#: What the pull's manifest records as the file's address: it is built, not downloaded at one address.
URL = "https://api.fdic.gov/banks/financials (every filer, by quarter), built by the threshold engine's peers build"


def engine_folder():
    """The threshold engine's folder, which holds the book and the roster: the source checkout this file sits in,
    or, when the package is installed (``pip install .`` puts this file under site-packages, away from them), the
    working directory, as the tool says to run from threshold-engine/. Neither: refused, naming what is needed
    (Codex on #472). The files are read where they are kept, never copied into the package to drift apart."""
    for root in (HERE.parents[3], pathlib.Path.cwd()):
        if all((root / f).is_file() for f in (BOOK, ROSTER, CHANGES)):
            return root
    raise RuntimeError("the bank credit series are built under the threshold engine's own book and roster (%s), "
                       "and neither this copy of the tool nor the folder it was run from holds them: run it from "
                       "threshold-engine/" % ", ".join(f.as_posix() for f in (BOOK, ROSTER, CHANGES)))


def book_settings():
    """The consumer book's "peers" settings: the firm's answers for this data, read where they are recorded."""
    return json.loads((engine_folder() / BOOK).read_text("utf-8"))["peers"]


def latest_quarter(today):
    """The last quarter that has ended by ``today`` (YYYY-MM-DD), as 2026Q3."""
    d = datetime.date.fromisoformat(today)
    q = (d.month - 1) // 3                                   # this quarter, counted from 0
    year, q = (d.year, q - 1) if q else (d.year - 1, 3)
    return "%dQ%d" % (year, q + 1)


def _step_back(label):
    year, q = int(label[:4]), int(label[-1])
    return "%dQ%d" % ((year, q - 1) if q > 1 else (year - 1, 4))


def build_file(cache_root, today, fetch=None, first=None, say=lambda s: None):
    """Pull what the cache lacks, build the series with the threshold engine and return the JSON file's bytes.

    ``cache_root`` holds the FDIC cache (``fdic/``) across pulls. The last quarter is the latest the FDIC has
    published: the quarter just ended is tried first and, when the FDIC holds no filer for it yet, the one before.
    ``fetch`` is the FDIC downloader (``fetch(url) -> dict``), the API's by default."""
    root = engine_folder()
    s = book_settings()
    first = first or s["first"]
    names = [p for p, *_ in BANK_PRODUCTS]
    fields = run.charge_off_fields(names) + [books.PARENT]
    fields += [f for f in D.fields_for(names) if f not in fields]
    cache = pathlib.Path(cache_root) / "fdic"
    last = latest_quarter(today)
    try:
        data = fdic.pull(fdic.quarter_ends(first, last), fields, cache, fetch=fetch)
    except RuntimeError as e:
        # fdic.pull: "the FDIC has no filers for 20260930: the quarter is not published yet". Only the quarter
        # just ended may be missing; any other refusal stops the pull.
        if "not published yet" not in str(e) or fdic.quarter_ends(last, last)[0] not in str(e):
            raise
        say("FDIC: %s holds no filer yet; built to the quarter before" % last)
        last = _step_back(last)
        data = fdic.pull(fdic.quarter_ends(first, last), fields, cache, fetch=fetch)
    rows = fdic.history(MERGERS_SINCE, fetch)
    mergers, absorptions = cache / "mergers.json", cache / "absorptions.json"
    mergers.write_text(json.dumps(fdic.classify(rows), indent=1, sort_keys=True), "utf-8")
    absorptions.write_text(json.dumps(fdic.absorptions(rows), indent=1), "utf-8")
    me = R.self_bank(R.load(root / ROSTER))
    with tempfile.TemporaryDirectory() as tmp:
        from openpyxl import Workbook
        run.build(None, cache=cache, roster=root / ROSTER, series_dir=pathlib.Path(tmp), first=first, last=last,
                  products=names, mergers=mergers, absorptions=absorptions,
                  extra_acquisitions=s["extra_acquisitions"], industry_combined=[], jump=s["jump"],
                  acquisition_share=s["acquisition_share"], min_book=float(s["min_book"]),
                  exempt_self=s["exempt_self"], pro_forma=s["pro_forma"], pack=s["pack"], min_banks=s["min_banks"],
                  rank_by=s["rank_by"], last_n=s["last_n"], min_obs=s["min_obs"], base_quarter=s["base_quarter"],
                  index_min_book=float(s["index_min_book"]), lagged_years=s["lagged_years"],
                  lag_years=s["lag_years"], normalisation_years=s["normalisation_years"],
                  mix_base_year=s["mix_base_year"], delinquency=True, reporting_changes=root / CHANGES,
                  say=say, into=Workbook())
        series = {}
        for product, *_ in BANK_PRODUCTS:
            for who, *_ in BANK_WHO:
                for measure, *_ in BANK_MEASURES:
                    sid = bank_source_id(product, measure, who)
                    path = pathlib.Path(tmp) / (sid + ".csv")
                    note, points = [], []
                    if path.exists():
                        for line in path.read_text("utf-8").splitlines():
                            if line.startswith("# "):
                                # The cache's place on this machine stays out of the file and the workbook.
                                note.append(line[2:].replace(str(cache), "the pull's FDIC cache"))
                            elif line and not line.startswith(("#", "date,")):
                                d, v = line.split(",")
                                points.append([d, float(v)])
                    series[sid] = {"note": note, "points": points}
    out = {"what": "Bank credit series built by the threshold engine's peers build from FDIC Call Reports",
           "first": first, "last": last, "filers": len(data[fdic.quarter_ends(last, last)[0]]),
           "self": {"cert": me["cert"], "name": me["name"]},
           "settings": {k: s[k] for k in ("jump", "acquisition_share", "min_book", "exempt_self", "pro_forma",
                                          "extra_acquisitions")},
           "book": "threshold-engine/books/consumer-public.json", "mergers_since": MERGERS_SINCE,
           "series": series}
    return (json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8")


def read(raw, sid):
    """One series from the file: (the quarter's first day, value) pairs, as every quarterly series is dated here;
    a quarter the build left out is absent, never filled."""
    try:
        got = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError("not the bank credit file: %s" % e)
    if not isinstance(got, dict) or sid not in got.get("series", {}):
        raise ValueError("the bank credit file has no series %r" % sid)
    out = []
    for d, v in got["series"][sid]["points"]:
        q = (int(d[5:7]) - 1) // 3
        out.append(("%s-%02d-01" % (d[:4], 3 * q + 1), float(v)))
    if not out:
        raise ValueError("the bank credit file's %s has no quarter: the build wrote none" % sid)
    return out
