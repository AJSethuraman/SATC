"""Turn bank NAMES into FDIC certificate numbers, and show the match first.

The firm will send competitors as names. A name is not an identifier: several
banks share one, holding companies are named almost identically to their banks,
and picking the wrong "First National Bank" is the one error in this whole
exercise that stays invisible -- every value would tie perfectly, against the
wrong institution's filings.

So this resolves, and then STOPS. It prints the legal name, city, state, class
and total assets for each match and waits for a person to say yes. Nothing is
pulled on a guess.

    python tools/tieout/resolve_banks.py "Fifth Third Bank" "Regions Bank"

Two things the FDIC's search does quietly, both of which this exists to survive:

* The query must be `search=NAME:<terms>`. A bare `search=fifth third` returns
  an empty list, and so does a `filters=NAME:"FIFTH THIRD*"` wildcard. Empty
  reads as "no such bank" rather than "wrong query", and the first version of
  this reported that Fifth Third Bank does not exist.
* Names outlive institutions. "Fifth Third Bank" matches the live cert 6672 AND
  a dead cert 993. Only active institutions are offered, because a bank that no
  longer files has no filings to tie to -- but an inactive near-miss is PRINTED
  when nothing active matches, since a competitor that was absorbed is a
  different answer from one that was mistyped.
"""
import json
import sys
import urllib.parse
import urllib.request

API = "https://banks.data.fdic.gov/api/institutions"
FIELDS = "CERT,NAME,CITY,STALP,ASSET,BKCLASS,ACTIVE"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def search(name, limit=6, active_only=True):
    params = {"search": "NAME:%s" % name, "fields": FIELDS,
              "sort_by": "ASSET", "sort_order": "DESC",
              "limit": str(limit), "format": "json"}
    if active_only:
        params["filters"] = "ACTIVE:1"
    url = "%s?%s" % (API, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=120) as fh:
        data = json.loads(fh.read())
    return [r.get("data", r) for r in data.get("data", [])]


def line(h, arrow=False):
    assets = h.get("ASSET")
    return ("   %s cert %-7s %-44s %s, %-2s  %-5s %s"
            % ("->" if arrow else "  ", h.get("CERT"),
               (h.get("NAME") or "")[:44], h.get("CITY"), h.get("STALP"),
               h.get("BKCLASS"),
               ("$%.1fbn" % (assets / 1e6)) if assets else "-"))


names = [a for a in sys.argv[1:] if not a.startswith("-")]
if not names:
    print(__doc__)
    raise SystemExit("give one or more bank names")

print("Matches, largest first. NOTHING is pulled until you confirm a row.\n")
picked = []
for name in names:
    print("=== %s" % name)
    try:
        hits = search(name)
    except Exception as exc:                                     # noqa: BLE001
        print("   LOOKUP FAILED: %s\n" % str(exc)[:90])
        continue
    if not hits:
        print("   no ACTIVE institution matches that name.")
        try:
            dead = search(name, limit=3, active_only=False)
        except Exception:                                        # noqa: BLE001
            dead = []
        for h in dead:
            print("      inactive: cert %-7s %s (%s, %s)"
                  % (h.get("CERT"), (h.get("NAME") or "")[:40],
                     h.get("CITY"), h.get("STALP")))
        if not dead:
            print("      and nothing inactive either -- check the spelling")
        print()
        continue
    for i, h in enumerate(hits):
        print(line(h, arrow=(i == 0)))
    picked.append({"asked": name, "cert": str(hits[0].get("CERT")),
                   "name": hits[0].get("NAME"), "city": hits[0].get("CITY"),
                   "state": hits[0].get("STALP"),
                   "assets_thousands": hits[0].get("ASSET"),
                   "other_matches": len(hits) - 1})
    print()

print("The arrow marks the largest match. That is usually the answer and is not")
print("always: a holding company and its bank differ by a word, and the bigger")
print("row can be the holding company. Confirm each before anything is pulled.")
print()
print(json.dumps(picked, indent=1))
