"""One exhibit per bank-year: every value, beside the page it was filed on.

The firm's standard, in their words: "i want the screenshot method used for
those quarters ... it's the only way i feel like i have been able to trust this
sort of audit." So this is not a sample. Every bank-quarter value that was
compared against a filed line appears here with a photograph of that line.

**The unit is the bank-year**, not the bank and not the whole feed. A bank is
forty quarters and roughly 2,700 photographs; nobody opens that. A year is four
filings, and four filings is what somebody actually checks in a sitting.

Each document is self-contained -- every image base64'd into the HTML before
Chrome renders it -- so it survives being forwarded to an auditor who does not
have this machine. The one that isn't is the one that gets sent and can't be
read.

    python tools/tieout/build_deep_bank_exhibits.py            # all 120
    python tools/tieout/build_deep_bank_exhibits.py 17534 2026 # one
"""
import base64
import collections
import csv
import html
import json
import pathlib
import subprocess
import sys
import time

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
#: The 16-level greyscale strips, which are 36% of the colour ones and
#: indistinguishable at reading size -- a Call Report page is black text
#: on white, so the colour channels were carrying nothing. The colour
#: originals stay on disk and `--colour` still uses them.
STRIPS = SB / ("deepstrips" if "--colour" in sys.argv else "deepstrips-grey")
if not STRIPS.exists():
    STRIPS = SB / "deepstrips"
#: The exhibits live on the Forge, not in the repository. The firm, having
#: first said to store all of it: "But we can save them locally on the
#: forge instead of taking space on git." Outside the working tree rather
#: than merely gitignored inside it -- an ignored file is one
#: `git clean -xfd` away from gone, and this is 451 MB of photographed
#: regulatory filings.
#:
#: `manifest.csv` and `README.md` stay in the repository, so what exists
#: and how to rebuild it are both versioned even though the PDFs are not.
EVIDENCE = pathlib.Path(r"C:\Users\ajish\SATC-evidence")
OUT = EVIDENCE / "banks-10y-2026-09-05"
RECORD = CS / "docs" / "tie-out" / "banks-10y-2026-09-05"
RECORD.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import plain as FPLAIN             # noqa: E402

args = sys.argv[1:]

index = {e["cert"]: e["name"] for e in
         json.loads((SB / "banks" / "index.json").read_text())}

# A four-digit number was read as a YEAR and never as a certificate, so
# `build_deep_bank_exhibits.py 2270 2026` filtered for a year 2270 and built
# nothing, reporting "0 of 0" as though there were nothing to do. Five of the
# nineteen banks have four-digit certs -- 628, 639, 2270, 6560, 6672 -- and
# none of them could be selected. A KNOWN certificate wins; only a number that
# is not a certificate is read as a year.
only_cert = next((a for a in args if a in index), None)
only_year = next((a for a in args if a not in index
                  and len(a) == 4 and a.isdigit()), None)
unknown = [a for a in args if a != only_cert and a != only_year]
if unknown:
    raise SystemExit(
        "not a certificate in the peer set and not a year: %s\n"
        "certificates are %s"
        % (", ".join(unknown), ", ".join(sorted(index))))
rows = json.loads((SB / "bank_deep_rows.json").read_text())
# Every shard, not just the first file written. `deep_bank_strips.py` names
# its output after the certs it was asked for, so photographing seven banks
# separately produced `deep_strips-6672-....json` -- which this read nothing
# from. A bank whose pages were photographed and then never looked at is
# indistinguishable in the exhibit from one nobody photographed, so the
# denominator is asserted below rather than left to be noticed.
strips = json.loads((SB / "deep_strips.json").read_text())
for _shard in sorted(SB.glob("deep_strips-*.json")):
    for _cert, _quarters in json.loads(_shard.read_text()).items():
        strips.setdefault(_cert, {}).update(_quarters)
_unphotographed = sorted(set(index) - set(strips))
assert not _unphotographed, (
    "no strips for cert(s) %s -- run tools/tieout/deep_bank_strips.py for them"
    % ", ".join(_unphotographed))
print("strips loaded : %d banks, %d bank-quarters"
      % (len(strips), sum(len(v) for v in strips.values())))
FACSIMILE = ("https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx"
             "?ds=call&idType=fdiccert&id=%s&date=%s")

by_bank_year = collections.defaultdict(list)
for r in rows:
    by_bank_year[(r["cert"], r["repdte"][:4])].append(r)


def uri(name):
    p = STRIPS / name
    if not p.exists():
        return None
    return "data:image/png;base64,%s" % base64.b64encode(p.read_bytes()).decode()


def esc(x):
    return html.escape("" if x is None else str(x))


def money(v):
    """A figure as the reader should see it: exact, and no invented precision.

    An exact zero prints as `0`, not `0.0000`. A difference of nothing is the
    most important number in this document and it should not look like a
    rounding residue.
    """
    if v is None:
        return "&mdash;"
    v = float(v)
    if v == 0:
        return "0"
    return "{:,.0f}".format(v) if abs(v) >= 1000 else "{:,.4f}".format(v)


CSS = """
:root{--ink:#151515;--dim:#5c5c5c;--rule:#dcdcdc;--ok:#0a6b3d;--warn:#b00020;
--paper:#fff;--tint:#f7f8f9}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:11pt/1.5 "Source Serif 4",Georgia,serif;-webkit-print-color-adjust:exact}
.page{padding:26pt 30pt}
h1{font:600 22pt/1.2 "Inter","Segoe UI",system-ui,sans-serif;margin:0 0 4pt}
h2{font:600 13pt/1.3 "Inter","Segoe UI",system-ui,sans-serif;
margin:22pt 0 8pt;padding-bottom:4pt;border-bottom:1.5px solid var(--ink);
page-break-after:avoid}
h3{font:600 10.5pt/1.3 "Inter","Segoe UI",system-ui,sans-serif;margin:0 0 3pt}
.sub{color:var(--dim);font-size:10pt;margin:0 0 18pt}
p{margin:0 0 8pt;max-width:44em}
.mono{font-family:"Cascadia Mono",Consolas,monospace;font-size:8.6pt}
.field{border:1px solid var(--rule);border-radius:5px;padding:9pt 11pt;
margin:0 0 9pt;page-break-inside:avoid;background:var(--paper)}
.field.zero{background:var(--tint)}
.meta{color:var(--dim);font-size:8.8pt;margin:0 0 6pt}
.cmp{display:grid;grid-template-columns:auto auto auto;gap:0 18pt;
font-family:"Cascadia Mono",Consolas,monospace;font-size:9.2pt;
margin:0 0 7pt;align-items:baseline}
.cmp b{font-weight:600}
.tie{color:var(--ok);font-weight:600}
.no{color:var(--warn);font-weight:600}
.shot{border:1px solid var(--rule);border-radius:3px;margin:0 0 5pt;
overflow:hidden;background:#fff}
.shot img{display:block;width:100%;height:auto}
.hdr img{opacity:.92}
.cap{color:var(--dim);font-size:8.2pt;margin:0 0 7pt}
table{border-collapse:collapse;width:100%;font-size:9.4pt;margin:0 0 12pt}
th,td{text-align:left;padding:4pt 8pt;border-bottom:1px solid var(--rule)}
th{font:600 9pt/1.3 "Inter",system-ui,sans-serif;background:var(--tint)}
td.n{text-align:right;font-family:"Cascadia Mono",Consolas,monospace}
.note{border-left:3px solid var(--ink);padding:7pt 0 7pt 12pt;margin:0 0 12pt;
background:var(--tint)}
.quarter{page-break-before:always}
"""

DIAGRAM = """
<figure style="margin:0 0 16pt">
<svg viewBox="0 0 720 200" role="img" width="100%"
 aria-label="Two roads to the same number: the FDIC's feed into this workbook,
 and the bank's own filed Call Report page, meeting at difference zero.">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
 markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z"
 fill="currentColor"/></marker></defs>
<g fill="none" stroke="currentColor" stroke-width="1.2">
<rect x="8" y="16" width="150" height="40" rx="4"/>
<rect x="230" y="16" width="150" height="40" rx="4"/>
<rect x="452" y="16" width="160" height="40" rx="4"/>
<rect x="8" y="132" width="150" height="40" rx="4"/>
<rect x="230" y="132" width="150" height="40" rx="4"/>
<rect x="452" y="132" width="160" height="40" rx="4"/>
<line x1="160" y1="36" x2="226" y2="36" marker-end="url(#a)"/>
<line x1="382" y1="36" x2="448" y2="36" marker-end="url(#a)"/>
<line x1="160" y1="152" x2="226" y2="152" marker-end="url(#a)"/>
<line x1="382" y1="152" x2="448" y2="152" marker-end="url(#a)"/>
<line x1="532" y1="58" x2="532" y2="86" marker-end="url(#a)"/>
<line x1="532" y1="130" x2="532" y2="102" marker-end="url(#a)"/>
<rect x="452" y="84" width="160" height="20" rx="10"/>
</g>
<g font-family="Inter,system-ui,sans-serif" font-size="10" fill="currentColor">
<text x="20" y="32">FDIC BankFind API</text>
<text x="20" y="47" font-size="8.6" opacity=".72">one request per bank</text>
<text x="242" y="32">bank-values.csv</text>
<text x="242" y="47" font-size="8.6" opacity=".72">the file you open</text>
<text x="464" y="41" font-weight="600">what we say</text>
<text x="20" y="148">the bank's Call Report</text>
<text x="20" y="163" font-size="8.6" opacity=".72">cdr.ffiec.gov facsimile</text>
<text x="242" y="148">the MDRM line</text>
<text x="242" y="163" font-size="8.6" opacity=".72">photographed below</text>
<text x="464" y="157" font-weight="600">what the bank filed</text>
<text x="474" y="98" font-size="9" font-weight="600">difference 0</text>
<text x="176" y="102" font-size="8.6" opacity=".72">the lower road touches a document</text>
<text x="176" y="114" font-size="8.6" opacity=".72">nobody here controls -- that is what makes this evidence</text>
</g></svg>
<figcaption style="color:#5c5c5c;font-size:8.6pt">The same figure travels two
roads. Only the lower one goes through a document this firm does not
control.</figcaption></figure>
"""


def build(cert, year):
    name = index.get(cert, cert)
    recs = sorted(by_bank_year[(cert, year)],
                  key=lambda r: (r["repdte"], r["field"]))
    quarters = sorted({r["repdte"] for r in recs})
    tied = sum(1 for r in recs if r["verdict"] == "TIES")
    shot = 0

    parts = ["<style>%s</style><div class='page'>" % CSS]
    parts.append("<h1>%s &mdash; %s</h1>" % (esc(name), esc(year)))
    parts.append("<p class='sub'>FDIC certificate %s &middot; %d values across "
                 "%d quarter(s) &middot; every one shown beside the line the "
                 "bank filed it on</p>" % (esc(cert), len(recs), len(quarters)))
    parts.append(DIAGRAM)
    parts.append("<div class='note'><p><b>What this document is.</b> The left "
                 "number in each pair is read out of "
                 "<span class='mono'>verified-data/bank-values.csv</span>, the "
                 "file the firm opens. The right number is read off the bank's "
                 "own Call Report as the regulator serves it. The photograph "
                 "beneath them is that page, cropped to the row, with the "
                 "filing's own header above it so you can see whose filing it "
                 "is and for which period.</p>"
                 "<p><b>To check any of it yourself:</b> open the filing link "
                 "under a quarter heading, search the page for the eight-"
                 "character code (an <i>MDRM code</i> &mdash; the Federal "
                 "Reserve's permanent name for one line on the form), and read "
                 "the number beside it.</p></div>")

    parts.append("<h2>This year at a glance</h2><table><tr><th>Quarter</th>"
                 "<th>Values</th><th>Tied to the filing</th>"
                 "<th>Not compared, and why</th><th>The filing</th></tr>")
    for q in quarters:
        qr = [r for r in recs if r["repdte"] == q]
        qt = sum(1 for r in qr if r["verdict"] == "TIES")
        other = collections.Counter(r["verdict"] for r in qr
                                    if r["verdict"] != "TIES")
        why = "; ".join("%d %s" % (v, k.lower()) for k, v in other.most_common())
        mmdd = q[5:7] + q[8:10] + q[:4]
        parts.append("<tr><td>%s</td><td class='n'>%d</td><td class='n'>%d</td>"
                     "<td>%s</td><td><span class='mono'>%s</span></td></tr>"
                     % (esc(q), len(qr), qt, esc(why or "&mdash;"),
                        FACSIMILE % (cert, mmdd)))
    parts.append("</table>")

    for q in quarters:
        mmdd = q[5:7] + q[8:10] + q[:4]
        qr = [r for r in recs if r["repdte"] == q]
        parts.append("<div class='quarter'><h2>Quarter ending %s</h2>" % esc(q))
        parts.append("<p class='cap'>Filed Call Report: <span class='mono'>%s"
                     "</span></p>" % (FACSIMILE % (cert, mmdd)))
        qshots = (strips.get(cert) or {}).get(q) or {}
        for r in qr:
            zero = float(r["ours"] or 0) == 0.0
            parts.append("<div class='field%s'>" % (" zero" if zero else ""))
            parts.append("<h3>%s</h3>" % esc(r["field"]))
            desc = FPLAIN.describe(r["field"]) or ""
            parts.append("<p class='meta'>%s%s%s</p>"
                         % (esc(desc), " &middot; " if desc else "",
                            esc(r.get("schedule") or "")))
            verdict_cls = "tie" if r["verdict"] == "TIES" else "no"
            parts.append("<div class='cmp'>"
                         "<span>ours &nbsp;(bank-values.csv)</span>"
                         "<b>%s</b><span class='%s'>%s</span>"
                         "<span>filed (%s)</span><b>%s</b><span></span>"
                         "<span>difference</span><b>%s</b><span></span></div>"
                         % (money(r["ours"]), verdict_cls, esc(r["verdict"]),
                            esc(r.get("cited") or ""), money(r.get("theirs")),
                            money(None if r.get("theirs") is None
                                  else float(r["ours"]) - float(r["theirs"]))))
            if r.get("how"):
                parts.append("<p class='cap'>%s</p>" % esc(r["how"]))
            # The header identifies the filing -- bank, form, period. Several
            # codes for one field usually sit on the SAME page, and repeating
            # the same header strip under each of them doubles the file and
            # reads as noise. Show it once per page inside a field block.
            seen_header = set()
            for comp in qshots.get(r["field"], []):
                if not comp.get("png"):
                    parts.append("<p class='cap'>%s: %s</p>"
                                 % (esc(comp.get("code")),
                                    esc(comp.get("why", "no image"))))
                    continue
                h = uri(comp["header"]) if comp["header"] not in seen_header else None
                seen_header.add(comp["header"])
                img = uri(comp["png"])
                if h:
                    parts.append("<div class='shot hdr'><img src='%s'></div>" % h)
                if img:
                    parts.append("<div class='shot'><img src='%s'></div>" % img)
                    shot += 1
                parts.append("<p class='cap'>%s &middot; page %s &middot; "
                             "row as filed: <span class='mono'>%s</span></p>"
                             % (esc(comp["code"]), esc(comp.get("page")),
                                esc((comp.get("row") or "")[:170])))
            parts.append("</div>")
        parts.append("</div>")

    parts.append("<h2>What this does not prove</h2>")
    parts.append("<p>That the bank was right. A value can match its filing to "
                 "the dollar and the filing can still be wrong; this proves "
                 "faithful copying and nothing beyond it.</p>")
    parts.append("<p>Anything shaded grey is a value of exactly zero &mdash; a "
                 "category where this bank has no exposure. It ties, and it is "
                 "the weakest form of agreement there is.</p>")
    parts.append("<p>Ratios the FDIC computes have no line on the form to "
                 "photograph, so they carry no picture here. The lines they "
                 "are computed from do.</p>")
    parts.append("<p>Nothing in this document was checked by a second "
                 "person.</p></div>")

    stem = "%s-%s-%s" % (cert, name.replace(" ", "-").replace(",", ""), year)
    html_path = SB / ("exh-%s.html" % stem)
    html_path.write_text("".join(parts), encoding="utf-8")
    pdf = OUT / ("TIE-OUT-%s.pdf" % stem)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                    "--no-pdf-header-footer", "--print-to-pdf=%s" % pdf,
                    html_path.as_uri()], capture_output=True, timeout=900)
    ok = pdf.exists() and pdf.stat().st_size > 20000
    return {"cert": cert, "bank": name, "year": year, "values": len(recs),
            "tied": tied, "images": shot, "pdf": pdf.name if ok else None,
            "mb": round(pdf.stat().st_size / 1e6, 1) if ok else 0}


pairs = sorted(by_bank_year)
if only_cert:
    pairs = [p for p in pairs if p[0] == only_cert]
if only_year:
    pairs = [p for p in pairs if p[1] == only_year]

started = time.time()
built, failed, blind = [], [], []
for cert, year in pairs:
    got = build(cert, year)
    (built if got["pdf"] else failed).append(got)
    if got["pdf"] and got["values"] and not got["images"]:
        blind.append(got)
    print("  %-26s %s  %4d values, %4d images, %4.1f MB  %s"
          % (got["bank"][:26], year, got["values"], got["images"], got["mb"],
             got["pdf"] or "FAILED TO RENDER"), flush=True)

# An exhibit whose pictures did not embed renders perfectly and proves
# nothing, and it is indistinguishable from one that worked until somebody
# opens it. That is tenet one, and it happened again on 7 September 2026: the
# builder prefers the SHRUNK strips, `deepstrips-grey`, and seven banks had
# only been photographed into `deepstrips`. Every page said "0 images" and the
# run went on to completion.
if blind:
    banks = sorted({("%s %s" % (b["bank"], b["year"])) for b in blind})
    raise SystemExit(
        "REFUSING: %d exhibit(s) carry values and NO photographs.\n"
        "  %s\n"
        "The pages were cut into %s but this build reads %s. Run\n"
        "  python tools/tieout/shrink_strips.py\n"
        "and build again. An exhibit without its pictures is not evidence."
        % (len(blind), "\n  ".join(banks[:12]), SB / "deepstrips", STRIPS))

(SB / "deep_exhibits.json").write_text(json.dumps(built, indent=1),
                                       encoding="utf-8")

# The manifest is the versioned record of an unversioned folder, written by
# the run that writes the PDFs so the two cannot drift.
#
# MERGED, not overwritten. The first version wrote only the exhibits this
# run produced, which is right for a full rebuild and truncated a 132-row
# record to one row the first time somebody built a single bank-year -- and
# building one quarter at a time is the whole point of the schedule this
# implements. Rows this run rebuilt are replaced; rows it did not touch are
# kept; a row whose PDF is no longer on the Forge is dropped, because a
# record listing a file nobody can open is worse than no record.
HEADER = ["cert", "bank", "year", "values", "tied_to_the_filing",
          "photographs", "megabytes", "pdf"]
rows = {}
if (RECORD / "manifest.csv").exists():
    with (RECORD / "manifest.csv").open(encoding="utf-8") as fh:
        for _r in csv.DictReader(fh):
            rows[(_r["cert"], _r["year"])] = [_r.get(k, "") for k in HEADER]
kept = len(rows)
for _e in built:
    rows[(_e["cert"], _e["year"])] = [_e["cert"], _e["bank"], _e["year"],
                                      _e["values"], _e["tied"], _e["images"],
                                      _e["mb"], _e["pdf"]]
gone = [k for k, v in rows.items() if not (OUT / v[7]).exists()]
for k in gone:
    del rows[k]
with (RECORD / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
    _w = csv.writer(fh)
    _w.writerow(HEADER)
    for _k in sorted(rows, key=lambda k: (rows[k][1], rows[k][2])):
        _w.writerow(rows[_k])
print("manifest    : %d rows (%d rebuilt now, %d kept, %d dropped as missing)"
      % (len(rows), len(built), kept - len(built) - len(gone), len(gone)))
print("exhibits in : %s" % OUT)
print("manifest    : %s" % (RECORD / "manifest.csv"))
print("\nexhibits built : %d of %d" % (len(built), len(pairs)))
if failed:
    print("FAILED         : %d -- %s"
          % (len(failed), [f["bank"] + " " + f["year"] for f in failed]))
print("total size     : %.0f MB" % sum(b["mb"] for b in built))
print("elapsed        : %.0f min" % ((time.time() - started) / 60))
