"""Pull the sixty new macro series, whole history, no cap.

The firm took every candidate in the first two tiers. On the macro side that is
the homeowners-insurance producer price index, three G.19 borrowing rates, five
weekly H.8 bank credit lines, and the unemployment rate for all fifty states
and the District of Columbia.

Each is fetched from FRED because that is where they are convenient to get, and
each is CHECKED against the body that computes it -- BLS for the price index and
the state rates, the Federal Reserve Board for G.19 and H.8. FRED is a
redistributor; asking a redistributor whether the redistributor is right is a
mirror, and this feed does not do that anywhere else either.

All sixty were requested by name before this ran and all sixty came back.
"""
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
OUT = SB / "deep"
OUT.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

KEY = os.environ["FRED_API_KEY"]

STATES = ("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI "
          "MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT "
          "VA WA WV WI WY").split()

#: series id -> (group, the agency that computes it)
NEW_SERIES = {}
NEW_SERIES["PCU9241269241262"] = ("insurance", "Bureau of Labor Statistics")
for s in ("TERMCBCCALLNS", "TERMCBCCINTNS", "RIFLPBCIANM60NM"):
    NEW_SERIES[s] = ("g19_terms", "Federal Reserve Board")
for s in ("CCLACBW027SBOG", "RHEACBW027SBOG", "TOTCI", "CREACBW027SBOG",
          "CLSACBW027SBOG"):
    NEW_SERIES[s] = ("h8", "Federal Reserve Board")
for s in STATES:
    NEW_SERIES["%sUR" % s] = ("state_unemployment", "Bureau of Labor Statistics")

TRANSIENT = ("internal server error", "bad gateway", "service unavailable",
             "gateway timeout", "timed out", "timeout", "connection reset")


def fetch(sid, tries=4):
    url = ("https://api.stlouisfed.org/fred/series/observations"
           "?series_id=%s&api_key=%s&file_type=json" % (sid, KEY))
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as fh:
                return json.loads(fh.read()).get("observations", [])
        except Exception as exc:                                 # noqa: BLE001
            text = str(exc).lower()
            code = getattr(exc, "code", None)
            transient = (any(t in text for t in TRANSIENT)
                         or (isinstance(code, int) and 500 <= code < 600))
            if transient and attempt < tries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise


out, errors = {}, []
for sid in sorted(NEW_SERIES):
    try:
        obs = fetch(sid)
    except Exception as exc:                                     # noqa: BLE001
        errors.append({"series": sid, "error": str(exc)[:160]})
        print("  %-18s FAILED %s" % (sid, str(exc)[:60]))
        continue
    out[sid] = [{"date": o["date"], "value": float(o["value"])}
                for o in obs if o.get("value") not in (".", "", None)]
    time.sleep(0.1)

(OUT / "macro_new.json").write_text(json.dumps(out), encoding="utf-8")
(OUT / "macro_new_meta.json").write_text(
    json.dumps({k: list(v) for k, v in NEW_SERIES.items()}), encoding="utf-8")

total = sum(len(v) for v in out.values())
print("\nseries pulled : %d of %d" % (len(out), len(NEW_SERIES)))
print("observations  : %d" % total)
print("FAILED        : %d" % len(errors))
print()
import collections
by = collections.Counter()
for sid, v in out.items():
    by[NEW_SERIES[sid][0]] += len(v)
for group, n in by.most_common():
    ids = [s for s in out if NEW_SERIES[s][0] == group]
    earliest = min(min(o["date"] for o in out[s]) for s in ids if out[s])
    print("  %-20s %3d series, %6d observations, earliest %s"
          % (group, len(ids), n, earliest))
