"""A picture of the actual cell, for every line of every bank.

The firm's standard: "i want to literally see the screenshot of the excel sheet
where i can find it, too. like it has to prove it."

So each shot comes out of the shipped `Bank_Peer_Monitor.xlsm` with Excel's own
row numbers and column letters printed -- not a cropped range -- and shows the
period column beside the field column, with everything between them hidden for
the shot. A reader opens Raw_FDIC, goes to that reference, and lands on the same
number. The workbook is opened read-only and never saved.
"""
import json
import pathlib
import queue
import sys
import threading

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
WB = CS / "example-output" / "Bank_Peer_Monitor.xlsm"
OUT = SB / "bankshots"
PDFS = SB / "bankpdf"
OUT.mkdir(exist_ok=True)
PDFS.mkdir(exist_ok=True)
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import openpyxl                                                  # noqa: E402
from credit_suite.engine import rawlayout                        # noqa: E402
from credit_suite.sources.fdic import fields as FIELDS           # noqa: E402

rosters = json.loads((SB / "bank_rosters.json").read_text())


def col_letter(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


PLAN = []
for bank in rosters:
    first = bank["block_first_row"]
    for line in bank["lines"]:
        if line["note"]:
            continue                      # ratios the runner skips on purpose
        field = line["field"]
        try:
            col = rawlayout.field_col(field, FIELDS.RAW_FIELDS)
        except Exception:
            continue
        PLAN.append({"cert": bank["cert"], "field": field, "col": col,
                     "row": first, "header_row": first - 2,
                     "label_row": first - 1,
                     "name": "%s-%s" % (bank["cert"], field)})
print("shots to take: %d across %d banks" % (PLAN and len(PLAN) or 0, len(rosters)))


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
        ws = book.Worksheets("Raw_FDIC")
        ws.Activate()
        page = ws.PageSetup
        page.PrintHeadings = True
        page.Orientation = 2
        page.Zoom = False
        page.FitToPagesWide = 1
        page.FitToPagesTall = 1
        page.LeftMargin = page.RightMargin = 10
        page.TopMargin = page.BottomMargin = 10
        page.CenterHorizontally = True
        for spec in PLAN:
            letter = col_letter(spec["col"])
            ws.Columns.Hidden = False
            if spec["col"] > 2:
                ws.Range("B:%s" % col_letter(spec["col"] - 1)).EntireColumn.Hidden = True
            ws.Range("%s:ZZ" % col_letter(spec["col"] + 1)).EntireColumn.Hidden = True
            page.PrintArea = "$A$%d:$%s$%d" % (spec["header_row"], letter,
                                               spec["row"])
            out = PDFS / ("%s.pdf" % spec["name"])
            ws.ExportAsFixedFormat(0, str(out))
            done.append(spec["name"])
        ws.Columns.Hidden = False
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
    result = q.get(timeout=5400)
except queue.Empty:
    result = "blocked -- Excel did not answer"
if isinstance(result, str):
    print(result)
    raise SystemExit(1)
print("exported %d one-page PDFs" % len(result))
(SB / "bank_excel_plan.json").write_text(json.dumps(PLAN, indent=1), encoding="utf-8")
