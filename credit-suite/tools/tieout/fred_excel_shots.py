"""A picture of the actual cell, for every one of the 142 FRED series.

The firm, on what a tie-out has to show: "i want to literally see the
screenshot of the excel sheet where i can find it, too. like it has to prove
it."

So each shot is taken out of the shipped workbook with Excel's own row numbers
and column letters printed, not a cropped range. A reader opens
FRED_Credit_Risk_Dashboard.xlsm, goes to that tab and that cell reference, and
lands on the same number. The workbook is opened read-only in an isolated Excel
instance and never saved.

Each shot shows the series' header row -- id, title, metadata -- and the
observation rows beneath it, so the identity of the series and the value being
proved are in the same picture. That is the same rule the source side follows:
the entity, the document and the period belong in the same shot as the number.
"""
import json
import pathlib
import queue
import sys
import threading

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
WB = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite\example-output"
                  r"\FRED_Credit_Risk_Dashboard.xlsm")
OUT = SB / "fredshots"
PDFS = SB / "fredpdf"
OUT.mkdir(exist_ok=True)
PDFS.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ours = json.loads((SB / "fred_ours.json").read_text())

#: How many observation rows to show under the header. Three is enough to see
#: the latest value, the one before it (which several ties are computed from),
#: and the dates that prove the frequency.
ROWS_BELOW = 3

PLAN = []
for sid, block in sorted(ours.items()):
    latest = block.get("latest")
    if latest is None:
        continue
    PLAN.append({"series": sid, "tab": block["tab"],
                 "top": block["header_row"],
                 "bottom": max(latest["row"] + ROWS_BELOW - 1,
                               block["header_row"] + ROWS_BELOW)})
print("series to photograph: %d across %s"
      % (len(PLAN), sorted({p["tab"] for p in PLAN})))


def work(q):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    xl = None
    done = []
    try:
        xl = win32com.client.DispatchEx("Excel.Application")
        xl.Visible = False
        xl.DisplayAlerts = False
        xl.AutomationSecurity = 3
        book = xl.Workbooks.Open(str(WB), ReadOnly=True)
        sheets = {}
        for spec in PLAN:
            ws = sheets.get(spec["tab"])
            if ws is None:
                ws = book.Worksheets(spec["tab"])
                page = ws.PageSetup
                page.PrintHeadings = True          # Excel's own row/col headings
                page.Orientation = 2               # landscape
                page.Zoom = False
                page.FitToPagesWide = 1
                page.FitToPagesTall = 1
                page.LeftMargin = page.RightMargin = 10
                page.TopMargin = page.BottomMargin = 10
                page.CenterHorizontally = True
                sheets[spec["tab"]] = ws
            ws.Activate()
            ws.PageSetup.PrintArea = "$A$%d:$C$%d" % (spec["top"], spec["bottom"])
            out = PDFS / ("%s.pdf" % spec["series"])
            ws.ExportAsFixedFormat(0, str(out))
            done.append((spec["series"], out.name))
        book.Close(SaveChanges=False)
        q.put(done)
    except Exception as exc:
        q.put("error " + repr(exc))
    finally:
        try:
            if xl:
                xl.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()


q = queue.Queue()
threading.Thread(target=work, args=(q,), daemon=True).start()
try:
    result = q.get(timeout=2400)
except queue.Empty:
    result = "blocked -- Excel did not answer"
if isinstance(result, str):
    print(result)
    raise SystemExit(1)
print("exported %d one-page PDFs" % len(result))

import pymupdf                                            # noqa: E402

made = 0
for sid, name in result:
    doc = pymupdf.open(PDFS / name)
    page = doc[0]
    words = page.get_text("words")
    if words:
        box = pymupdf.Rect(words[0][:4])
        for w in words[1:]:
            box |= pymupdf.Rect(w[:4])
        box = pymupdf.Rect(box.x0 - 7, box.y0 - 7, box.x1 + 7, box.y1 + 7) & page.rect
    else:
        box = page.rect
    page.get_pixmap(matrix=pymupdf.Matrix(3.0, 3.0), clip=box).save(OUT / ("%s.png" % sid))
    doc.close()
    made += 1
print("rendered %d PNGs to %s" % (made, OUT))
