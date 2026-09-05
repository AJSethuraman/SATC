"""Every acquisition by the twelve banks over the ten years the feed covers.

The sixteen-quarter run recorded six. Ten years is not sixteen quarters, and a
merger the record never saw is a quarter that nothing marks -- which is exactly
how a false finding gets made. The PNC one was: five lines reported as the FDIC
disagreeing with itself, when PNC had absorbed FirstBank of Lakewood mid-quarter
and the software's own merger tab already said so.

This does not query the history endpoint by hand. It calls the shipped module,
`credit_suite.sources.fdic.mergers`, which is what builds the workbook's own
`_mergers` tab -- the same code, the same change codes, the same classification.
Rolling my own query on the wrong date field is how the last one was missed.
"""
import json
import pathlib
import sys
import urllib.request

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import mergers as M                # noqa: E402

index = json.loads((SB / "banks" / "index.json").read_text())
names = {e["cert"]: e["name"] for e in index}
quarters = json.loads((SB / "deep" / "deep_quarters.json").read_text())
earliest = min(quarters)


def download(url, _what):
    req = urllib.request.Request(
        url, headers={"User-Agent": "credit-suite tie-out (public data)"})
    return urllib.request.urlopen(req, timeout=180).read()


# The window starts one quarter before the earliest report date, because a
# merger effective in the first quarter of the feed still makes that quarter a
# quarter of two banks.
found, unclassified = M.fetch(sorted(names), download, since=earliest[:4] + "-01-01")

records = []
for mg in found:
    if mg.quarter not in quarters:
        continue
    records.append({"survivor": str(mg.cert),
                    "name": names.get(str(mg.cert), ""),
                    "effective": mg.effective, "quarter": mg.quarter,
                    "acquired": str(mg.out_cert),
                    "code": "%d -- %s" % (mg.code, mg.description),
                    "meaning": mg.meaning,
                    "sentence": mg.sentence(names.get(str(mg.cert), ""))})

records.sort(key=lambda r: (r["quarter"], r["name"]))
(SB / "merger_records_deep.json").write_text(json.dumps(records, indent=1),
                                             encoding="utf-8")

print("history rows classified as acquisitions : %d" % len(found))
print("falling inside the feed's %d quarters    : %d" % (len(quarters), len(records)))
if unclassified:
    print("UNCLASSIFIED history rows               : %d -- change codes %s"
          % (len(unclassified),
             sorted({str(r.get("CHANGECODE")) for r in unclassified})))
print()
for r in records:
    print("  %-26s %s  absorbed cert %-6s (%s)"
          % (r["name"][:26], r["quarter"], r["acquired"], r["effective"]))
