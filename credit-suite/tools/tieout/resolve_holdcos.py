"""Resolve HOLDING COMPANY names to the insured banks they own.

The firm sent ten peers as holding-company names -- US Bancorp, PNC Financial,
Truist Financial and so on. A holding company is not a bank: it files an FR Y-9C
with the Federal Reserve, it has no FDIC certificate, and it files no Call
Report. The whole feed is built on Call Reports, so a holding company cannot be
in it. Its BANK can.

Searching the FDIC for a holding-company name does not fail cleanly, which is
the danger. It falls back to matching single words and returns a real, live,
completely unrelated bank:

    "PNC Financial"     -> PlainsCapital Bank, University Park TX, $12.7bn
    "Truist Financial"  -> Parkside Financial Bank & Trust, Clayton MO, $1.1bn

Both matched on the word "Financial". Taking either would have put a Texas bank
in the feed labelled PNC, and every value would have tied perfectly -- against
the wrong institution's own filings. That is the one error in this project that
stays invisible, and it fired on the first name tried.

The FDIC publishes the linkage itself: every bank record carries `NAMEHCR`, its
holding company. So this searches THAT field and returns the banks a holding
company owns, largest first. No guessing at what a bank is probably called.
"""
import json
import sys
import urllib.parse
import urllib.request

API = "https://banks.data.fdic.gov/api/institutions"
FIELDS = "CERT,NAME,CITY,STALP,ASSET,BKCLASS,NAMEHCR,RSSDHCR,ACTIVE"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

#: Holding companies name themselves in the FDIC's data with abbreviations a
#: person would not type: "PNC FINL SERVICES GROUP INC", "US BANCORP". Matching
#: on the first distinctive word or two finds them; matching on the full name
#: the firm typed does not.
def stem(name):
    drop = {"financial", "bancorp", "bancorporation", "banc", "corp", "corp.",
            "group", "inc", "inc.", "co", "company", "services", "holdings",
            "holding", "the", "&", "and"}
    words = [w for w in name.replace(",", " ").split()
             if w.lower().strip(".") not in drop]
    return " ".join(words) if words else name


def search(field, terms, limit=8, active_only=True):
    params = {"search": "%s:%s" % (field, terms), "fields": FIELDS,
              "sort_by": "ASSET", "sort_order": "DESC",
              "limit": str(limit), "format": "json"}
    if active_only:
        params["filters"] = "ACTIVE:1"
    url = "%s?%s" % (API, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=120) as fh:
        return [r.get("data", r) for r in json.loads(fh.read()).get("data", [])]


names = [a for a in sys.argv[1:] if not a.startswith("-")]
if not names:
    print(__doc__)
    raise SystemExit("give one or more holding company names")

print("Each holding company, and the insured banks the FDIC says it owns.")
print("NOTHING is pulled until you confirm. The Call Report is filed by the")
print("BANK, so the bank is what can go in the feed.\n")

resolved = []
for name in names:
    key = stem(name)
    print("=== %s   (searching holding company for %r)" % (name, key))
    try:
        hits = search("NAMEHCR", key)
    except Exception as exc:                                     # noqa: BLE001
        print("   LOOKUP FAILED: %s\n" % str(exc)[:90])
        continue
    if not hits:
        print("   no bank has a holding company matching that.")
        try:
            direct = search("NAME", key, limit=3)
        except Exception:                                        # noqa: BLE001
            direct = []
        for h in direct:
            print("   as a BANK name: cert %-7s %-40s %s, %s"
                  % (h.get("CERT"), (h.get("NAME") or "")[:40],
                     h.get("CITY"), h.get("STALP")))
        print()
        continue
    for i, h in enumerate(hits):
        assets = h.get("ASSET")
        print("   %s cert %-7s %-42s %s, %-2s %s"
              % ("->" if i == 0 else "  ", h.get("CERT"),
                 (h.get("NAME") or "")[:42], h.get("CITY"), h.get("STALP"),
                 ("$%.1fbn" % (assets / 1e6)) if assets else "-"))
        if i == 0:
            print("      holding company on the FDIC's own record: %s"
                  % h.get("NAMEHCR"))
    top = hits[0]
    resolved.append({"asked": name, "cert": str(top.get("CERT")),
                     "bank": top.get("NAME"), "holdco": top.get("NAMEHCR"),
                     "city": top.get("CITY"), "state": top.get("STALP"),
                     "assets_thousands": top.get("ASSET"),
                     "other_banks_owned": len(hits) - 1})
    print()

print(json.dumps(resolved, indent=1))
