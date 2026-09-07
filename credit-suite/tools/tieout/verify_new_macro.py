"""Check all 41,751 new macro observations against the body that computes them.

The firm's answer on the standard was "same standard, gaps stated" -- the one
the existing 142 series are held to. FRED is where these are convenient to
fetch; it is never what they are checked against, because asking a
redistributor whether the redistributor is right is a mirror.

Four groups, four agencies:

  insurance          1 series   Bureau of Labor Statistics, via its own API
  g19_terms          3 series   Federal Reserve Board, G.19 terms-of-credit
                                historical table -- the same release the feed's
                                existing consumer credit balances come from
  h8                 5 series   Federal Reserve Board, H.8 data package
  state_unemployment 51 series  Bureau of Labor Statistics, LAUS

One thing worth naming before the numbers: **the state rates are
seasonally adjusted**. BLS publishes both, under near-identical identifiers --
`LASST060000000000003` adjusted, `LAUST060000000000003` not -- and for
California in July 2026 they are 5.1 and 5.3. FRED's `CAUR` is 5.1. Reaching
for the unadjusted one would have produced fifty-one series of differences that
were entirely our own mistake.
"""
import collections
import io
import json
import os
import pathlib
import re
import sys
import time
import urllib.request
import zipfile

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
C = SB / "sources"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ours = json.loads((SB / "deep" / "macro_new.json").read_text())
meta = json.loads((SB / "deep" / "macro_new_meta.json").read_text())
UA = {"User-Agent": "credit-suite tie-out (public data)"}

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56",
}


# ------------------------------------------------------------ G.19 terms ----
def g19_terms():
    """{(year, quarter): [columns]} from the Board's own historical table."""
    html = (C / "g19_cc_hist_tc_levels.html").read_text(encoding="utf-8",
                                                        errors="replace")
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if cells and re.fullmatch(r"\d{4} Q\d", cells[0]):
            out[(cells[0][:4], cells[0][-1])] = cells
    return out


G19T = g19_terms()
#: column index into a period row, read off the release's own header:
#: Date | 60-month new car | 72-month new car | All credit card amounts |
#: Credit card accounts assessed interest | 24-month personal | ...
G19_COL = {"RIFLPBCIANM60NM": 1, "TERMCBCCALLNS": 3, "TERMCBCCINTNS": 4}


def g19_lookup(sid, iso):
    col = G19_COL.get(sid)
    y, m = iso[:4], int(iso[5:7])
    row = G19T.get((y, str((m - 1) // 3 + 1)))
    if not row or col is None or col >= len(row):
        return None
    try:
        return float(row[col].replace(",", ""))
    except ValueError:
        return None


# -------------------------------------------------------------------- H.8 ---
def h8_tables():
    """{Board series name: {date: value}} from the H.8 SDMX package.

    The package is XML, not CSV. Four files, none of them a `.csv` -- and a
    parser looking for CSVs reported the Board as publishing nothing.
    """
    import xml.etree.ElementTree as ET
    out, name, path = {}, None, C / "h8_csv.zip"
    with zipfile.ZipFile(path) as z:
        with z.open("H8_data.xml") as fh:
            for event, elem in ET.iterparse(fh, events=("start", "end")):
                tag = elem.tag.rsplit("}", 1)[-1]
                if event == "start" and tag == "Series":
                    name = elem.get("SERIES_NAME")
                    mult = float(elem.get("UNIT_MULT") or 1)
                    out[name] = {"_mult": mult}
                elif event == "start" and tag == "Obs" and name:
                    d, v = elem.get("TIME_PERIOD"), elem.get("OBS_VALUE")
                    if d and v not in (None, "", "ND"):
                        try:
                            out[name][d] = float(v)
                        except ValueError:
                            pass
                elif event == "end" and tag == "Series":
                    elem.clear()
    return out


def match_h8(ours_series, board):
    """FRED id -> Board series name, established by equal VALUES.

    The package carries the Board's own identifiers and FRED carries its own.
    A crosswalk guessed from the names can be plausible and wrong; a series
    that agrees on every week both publish cannot be. The Board reports
    millions and FRED billions, so the scale is read off the data.
    """
    pairs = {}
    for sid, obs in ours_series.items():
        mine = {o["date"]: float(o["value"]) for o in obs}
        best = None
        for bname, series in board.items():
            common = [d for d in mine if d in series and d != "_mult"]
            if len(common) < 60:
                continue
            for scale in (1.0, 1000.0, 0.001):
                hits = sum(1 for d in common
                           if abs(series[d] / scale - mine[d]) < 0.051)
                if hits >= len(common) - 2:
                    if best is None or hits > best[2]:
                        best = (bname, scale, hits, len(common))
                    break
        pairs[sid] = best
    return pairs


H8 = h8_tables()
H8_MATCH = match_h8({s: ours[s] for s in ours if meta[s][0] == "h8"}, H8)
for _sid, _m in sorted(H8_MATCH.items()):
    if _m:
        print("  H.8 %-16s -> Board %-12s %d of %d weeks equal, scale /%g"
              % (_sid, _m[0], _m[2], _m[3], _m[1]))
    else:
        print("  H.8 %-16s -> NO BOARD SERIES MATCHES" % _sid)


def h8_lookup(sid, iso):
    m = H8_MATCH.get(sid)
    if not m:
        return None
    v = H8.get(m[0], {}).get(iso)
    return None if v is None else v / m[1]


# -------------------------------------------------------------------- BLS ---
def bls(series_ids, start, end):
    payload = {"seriesid": list(series_ids),
               "startyear": str(start), "endyear": str(end)}
    if os.environ.get("BLS_API_KEY"):
        payload["registrationkey"] = os.environ["BLS_API_KEY"]
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/", data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "credit-suite tie-out (public data)"})
    d = json.loads(urllib.request.urlopen(req, timeout=180).read())
    if d.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError("%s %s" % (d.get("status"), d.get("message")))
    out = {}
    for s in d.get("Results", {}).get("series", []):
        vals = {}
        for p in s.get("data", []):
            if not p["period"].startswith("M") or p["period"] == "M13":
                continue
            try:
                # BLS prints `-` for a suppressed point. One dash is one
                # missing observation; letting it raise here discarded an
                # entire ten-year batch and reported 6,069 observations as
                # having no source.
                vals["%s-%s-01" % (p["year"], p["period"][1:])] = float(p["value"])
            except (ValueError, TypeError):
                continue
        out[s["seriesID"]] = vals
    return out


#: FRED id -> BLS id. The state rates are SEASONALLY ADJUSTED: `LASST`, not
#: `LAUST`. California July 2026 is 5.1 adjusted and 5.3 unadjusted, and FRED
#: publishes 5.1.
BLS_ID = {"PCU9241269241262": "PCU9241269241262"}
for st, fips in STATE_FIPS.items():
    BLS_ID["%sUR" % st] = "LASST%s0000000000003" % fips

#: INCREMENTAL. Without a registered key BLS allows 25 requests a day, and the
#: first run spent them -- one of them on a batch that then threw away its whole
#: decade over a single `-`. So the cache is kept and only the year-spans that
#: are actually missing are requested, and every success is written down
#: immediately rather than at the end of a loop that may not reach the end.
#:
#: `BLS_API_KEY` in the environment raises the allowance to 50 series and 20
#: years per request and 500 requests a day, which finishes the whole thing in
#: six calls. Registration is free and is the firm's to do; nothing here
#: creates an account.
cache = C / "bls_new_series.json"
BLS_DATA = json.loads(cache.read_text()) if cache.exists() else {}
API_KEY = os.environ.get("BLS_API_KEY")
SPAN = 19 if API_KEY else 9
PER = 50 if API_KEY else 25
ids = sorted(set(BLS_ID.values()))
years = [(y, min(y + SPAN, 2026)) for y in range(1976, 2027, SPAN + 1)]


def have(sid, lo, hi):
    """Whether the cache already holds the WHOLE span for that series.

    The first version asked whether it held ANY month in the span, so a span
    that had been half-filled by a failed batch looked complete and was never
    re-requested. That left Wyoming missing 1986-1995 -- one state, one decade,
    120 observations -- while every other state was whole, which is exactly the
    shape of gap that gets called a data limitation instead of a bug.

    A span counts as held when every year in it has at least one month. That is
    still not "every month", but it cannot be satisfied by a single stray year.
    """
    got = BLS_DATA.get(sid, {})
    years = {int(d[:4]) for d in got}
    return all(y in years for y in range(lo, hi + 1))


for lo, hi in years:
    for i in range(0, len(ids), PER):
        batch = [s for s in ids[i:i + PER] if not have(s, lo, hi)]
        if not batch:
            continue
        try:
            got = bls(batch, lo, hi)
        except Exception as exc:                                 # noqa: BLE001
            print("  BLS %d-%d FAILED for %d series: %s"
                  % (lo, hi, len(batch), str(exc)[:80]), flush=True)
            continue
        for k, v in got.items():
            BLS_DATA.setdefault(k, {}).update(v)
        cache.write_text(json.dumps(BLS_DATA), encoding="utf-8")
        print("  BLS %d-%d fetched %d series" % (lo, hi, len(batch)), flush=True)
        time.sleep(0.5)
held = sum(len(v) for v in BLS_DATA.values())
print("  BLS cache holds %d series, %d observations" % (len(BLS_DATA), held))


def bls_lookup(sid, iso):
    return BLS_DATA.get(BLS_ID.get(sid, ""), {}).get(iso[:8] + "01")


LOOKUP = {"insurance": bls_lookup, "state_unemployment": bls_lookup,
          "g19_terms": g19_lookup, "h8": h8_lookup}
SOURCE = {"insurance": "Bureau of Labor Statistics producer price index",
          "state_unemployment": "BLS Local Area Unemployment Statistics",
          "g19_terms": "Federal Reserve Board G.19 terms of credit",
          "h8": "Federal Reserve Board H.8 data package"}

rows, per = [], {}
for sid in sorted(ours):
    group = meta[sid][0]
    fn = LOOKUP[group]
    n = tied = differ = nosrc = 0
    for obs in ours[sid]:
        n += 1
        theirs = fn(sid, obs["date"])
        if theirs is None:
            nosrc += 1
            verdict = "NO SOURCE FOR THIS PERIOD"
        else:
            ok = abs(float(obs["value"]) - float(theirs)) < 0.005
            verdict = "TIED" if ok else "DIFFERS"
            tied += ok
            differ += (not ok)
        rows.append({"series": sid, "date": obs["date"], "ours": obs["value"],
                     "theirs": theirs, "verdict": verdict,
                     "source": SOURCE[group]})
    per[sid] = {"n": n, "tied": tied, "differs": differ, "no_source": nosrc,
                "group": group, "source": SOURCE[group]}

(SB / "macro_new_rows.json").write_text(json.dumps(rows), encoding="utf-8")
(SB / "macro_new_summary.json").write_text(json.dumps(per, indent=1),
                                           encoding="utf-8")

tot = sum(v["n"] for v in per.values())
print("\nobservations   : %d" % tot)
print("  tied         : %d" % sum(v["tied"] for v in per.values()))
print("  DIFFER       : %d" % sum(v["differs"] for v in per.values()))
print("  no source    : %d" % sum(v["no_source"] for v in per.values()))
print()
for group in ("insurance", "g19_terms", "h8", "state_unemployment"):
    ids = [s for s in per if per[s]["group"] == group]
    if not ids:
        continue
    print("  %-20s %2d series %6d obs %6d tied %5d differ %5d no source"
          % (group, len(ids), sum(per[s]["n"] for s in ids),
             sum(per[s]["tied"] for s in ids),
             sum(per[s]["differs"] for s in ids),
             sum(per[s]["no_source"] for s in ids)))
bad = [s for s in per if per[s]["differs"]]
if bad:
    print("\nseries with any DIFFERS:")
    for s in sorted(bad)[:12]:
        print("   %-18s %d of %d" % (s, per[s]["differs"], per[s]["n"]))
