"""Download every catalog series into a dated folder, and keep every download.

    CACHE/2026-10-15/fred-UNRATE.csv
    CACHE/2026-10-15/manifest.json

Each pull is its own folder, named for the day it ran, so a rating can always
say which release of the data it was made from; nothing earlier is
overwritten. A second pull on the same day goes to CACHE/<day>-2, a third to
<day>-3: a workbook made from the morning's pull still names a folder that
holds what it read. The manifest records, per file, the address, when it was fetched,
its size and SHA-256, and, per series, how many observations it holds, the
first and last, and every missing one.

A file the catalog shares (the Fed's spread file, FHFA's mortgage file) is
downloaded once. A series that fails is recorded with the reason; the pull
does not stop, and it exits non-zero if anything failed.
"""
import datetime
import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request

from . import sources
from .catalog import DERIVED_BY_KEY, SERIES

USER_AGENT = "Mozilla/5.0 (compatible; threshold-engine macro pull; public data)"


def fetch(url, timeout=60):
    """One download. The User-Agent differs by host, because the hosts differ:
    FRED stops answering any request that names a browser (seen 15 Oct 2026:
    20-second timeouts with one, under a second without), while the Federal
    Reserve Board refuses (403) a request that does not."""
    host = urllib.parse.urlparse(url).netloc
    headers = {} if host == "fred.stlouisfed.org" else {"User-Agent": USER_AGENT}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        return r.read()


def file_name(series):
    if series.source in ("fed_ebp", "fhfa_nmdb"):
        return series.source + (".csv" if series.source == "fed_ebp" else ".zip")
    ext = ".csv" if series.source == "fred" else ".html"
    return "%s-%s%s" % (series.source, series.source_id, ext)


def summarise(points):
    values = [(d, v) for d, v in points]
    present = [(d, v) for d, v in values if v is not None]
    if not present:
        return {"observations": len(values), "present": 0}
    first = present[0][0]
    missing = [d for d, v in values if v is None and d >= first]
    return {"observations": len(values), "present": len(present), "first": first,
            "last": present[-1][0], "last_value": present[-1][1], "missing_after_first": missing}


def pull(cache, keys=None, today=None, fetcher=fetch):
    """Fetch the catalog (or ``keys``) into CACHE/<today>/; return the manifest."""
    today = today or datetime.date.today().isoformat()
    if keys:
        # A reading made from two series pulls those two (Fable on #452: `pull mortgage_spread` said "not in
        # the catalog", pointing at `list`, which lists it).
        keys = [k for key in keys for k in (DERIVED_BY_KEY[key].inputs if key in DERIVED_BY_KEY else [key])]
        unknown = sorted(set(keys) - {s.key for s in SERIES})
        if unknown:
            # Refused before anything is written: a refused pull used to leave an empty folder for the day,
            # so the day's real pull went to "-2" (Fable on #452).
            raise SystemExit("not in the catalog: %s (list them with: python -m threshold_engine.macro list)"
                             % ", ".join(unknown))
    folder, n = pathlib.Path(cache) / today, 2
    while folder.exists():                  # never write into an earlier pull, even today's
        folder, n = pathlib.Path(cache) / ("%s-%d" % (today, n)), n + 1
    folder.mkdir(parents=True)
    wanted = [s for s in SERIES if keys is None or s.key in keys]
    files, series_out = {}, {}
    for s in wanted:
        name = file_name(s)
        if name not in files:
            url = sources.url_for(s, today[:4])
            try:
                raw = fetcher(url)
            except Exception as e:  # recorded, not raised: one bad series must not hide the rest
                files[name] = {"url": url, "error": "%s: %s" % (type(e).__name__, e)}
            else:
                (folder / name).write_bytes(raw)
                files[name] = {"url": url, "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(
                    timespec="seconds"), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if "error" in files[name]:
            series_out[s.key] = {"file": name, "error": files[name]["error"]}
            continue
        try:
            points = sources.read(s, (folder / name).read_bytes())
        except Exception as e:
            series_out[s.key] = {"file": name, "error": "could not read: %s" % e}
            continue
        series_out[s.key] = dict(file=name, **summarise(points))
    manifest = {"pulled": folder.name, "files": files, "series": series_out,
                "failed": sorted(k for k, v in series_out.items() if "error" in v)}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1), "utf-8")
    return manifest


VINTAGE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(\d+))?$")


def latest(cache):
    """The newest pull folder under CACHE, or None: the latest day, and on that
    day the latest pull (2026-10-16-10 after 2026-10-16-9)."""
    found = []
    for p in pathlib.Path(cache).glob("????-??-??*"):
        m = VINTAGE.match(p.name)
        if m and (p / "manifest.json").exists():
            found.append(((m.group(1), int(m.group(2) or 1)), p))
    return max(found)[1] if found else None


def load(cache, key, vintage=None, seen=None):
    """One series' points from a pull: the newest, or the folder named ``vintage``.

    ``seen``, when given, records the SHA-256 of the bytes read, by file name: the fingerprint of what was
    rated, not of the file as it is later (Codex on #452)."""
    from .catalog import BY_KEY
    s = BY_KEY[key]
    folder = pathlib.Path(cache) / vintage if vintage else latest(cache)
    if folder is None or not (folder / file_name(s)).exists():
        raise SystemExit("no pull of %s under %s: run python -m threshold_engine.macro pull --cache %s"
                         % (key, cache, cache))
    data = (folder / file_name(s)).read_bytes()
    if seen is not None:
        seen[file_name(s)] = hashlib.sha256(data).hexdigest()
    return sources.read(s, data), folder.name
