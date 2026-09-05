"""Write the deep feed's VALUE columns, before anything has been verified.

This exists to keep one property true: the "ours" side of every comparison is
read out of the artifact the firm opens, not out of the API response the
artifact was built from. So the order is build, then verify, then annotate --
never verify an intermediate and label the artifact with its verdict.

Two files come out, and they carry no verdict column yet:

    deep/bank-values-raw.csv    cert, bank, report_date, field, value
    deep/macro-observations-raw.csv   series_id, date, value

The verifiers read these back off disk. The finisher then rewrites them with
the verdicts attached and asserts, row by row, that not one value moved.
"""
import csv
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
DEEP = SB / "deep"
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import fields as FF               # noqa: E402

index = {e["cert"]: e["name"] for e in
         json.loads((SB / "banks" / "index.json").read_text())}
bank = json.loads((DEEP / "bank_deep.json").read_text())
macro = json.loads((DEEP / "macro_deep.json").read_text())


def iso(repdte):
    s = str(repdte)
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])


n = 0
with (DEEP / "bank-values-raw.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cert", "bank", "report_date", "field", "value"])
    for cert in sorted(bank, key=lambda c: index.get(c, c)):
        for row in sorted(bank[cert], key=lambda r: str(r["REPDTE"]), reverse=True):
            for field in FF.RAW_FIELDS:
                val = row.get(field)
                if val is None:
                    continue
                w.writerow([cert, index.get(cert, cert), iso(row["REPDTE"]),
                            field, val])
                n += 1
print("bank-values-raw.csv          : %6d values, %d banks" % (n, len(bank)))

m = 0
with (DEEP / "macro-observations-raw.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["series_id", "date", "value"])
    for sid in sorted(macro):
        for obs in macro[sid]:
            w.writerow([sid, obs["date"], obs["value"]])
            m += 1
print("macro-observations-raw.csv   : %6d observations, %d series"
      % (m, len(macro)))
print("\nNeither file carries a verdict. Verify against the filings and the")
print("agency documents next, reading the value column back out of these.")
