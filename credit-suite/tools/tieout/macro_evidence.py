"""A picture of every macro source document, with the proved rows ringed.

The firm, on the macro side's weaker provenance: "I can become okay with this if
you actually screenshotted something to show it matched. like for instance if
this is FRED info i know you can visually see stuff like charge-offs,
delinquencies, etc."

So each publisher's own page is photographed with the row marked, and every
series is mapped to the shot that shows where its numbers live. That does not
turn 11,341 programmatic comparisons into 11,341 photographs -- it shows the
document each comparison was made against, so a reader can see the table rather
than take the word "verified" for it.
"""
import html
import json
import pathlib
import re
import subprocess
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
C = SB / "sources"
OUT = SB / "macroshots"
WORK = SB / "srcwork"
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

MARKER = """
<style>
  .tieout-ring { outline: 4px solid #d40000 !important; outline-offset: 1px !important;
                 background: #ffe9e9 !important; }
  .tieout-ring > * { background: #ffe9e9 !important; }
  .tieout-note { position: fixed !important; top: 0 !important; left: 0 !important;
                 right: 0 !important; z-index: 2147483647 !important;
                 background: #d40000 !important; color: #fff !important;
                 font: 700 15px/1.5 system-ui, sans-serif !important;
                 padding: 9px 14px !important; }
  body { padding-top: 46px !important; }
</style>
<script>
(function () {
  var wants = %s, note = %s, hits = 0;
  var b = document.createElement("div");
  b.className = "tieout-note"; b.textContent = note;
  document.body.appendChild(b);
  var rows = document.querySelectorAll("tr");
  var first = null;
  for (var i = 0; i < rows.length; i++) {
    var t = (rows[i].textContent || "").replace(/\\u00a0/g, " ")
              .replace(/[\\s]+/g, " ").trim();
    for (var j = 0; j < wants.length; j++) {
      if (t.indexOf(wants[j]) === 0) {
        rows[i].classList.add("tieout-ring"); hits++;
        if (!first) first = rows[i];
        break;
      }
    }
  }
  b.textContent = note + "   [" + hits + " row(s) ringed]";
  if (first) {
    var off = first.getBoundingClientRect().top - 190;
    if (off > 0) { document.body.style.position = "relative";
                   document.body.style.top = (-off) + "px"; }
  }
})();
</script>
"""

#: name -> (cached page, the row labels to ring, caption, series it covers)
PAGES = {
    "fed-delinquency-all-banks": (
        "fed_delallsa.html", ["2026:2", "2026:1", "2025:4", "2025:3"],
        "Federal Reserve Board -- delinquency rates on loans at ALL commercial "
        "banks. Eleven loan categories across the row; the four most recent "
        "quarters are ringed.",
        ["DRREACBS", "DRSFRMACBS", "DRCRELEXFACBS", "DRCLACBS", "DRCCLACBS",
         "DROCLACBS", "DRLFRACBS", "DRBLACBS", "DRAGACBS", "DRALACBS"]),
    "fed-chargeoff-all-banks": (
        "fed_chgallsa.html", ["2026:2", "2026:1", "2025:4", "2025:3"],
        "Federal Reserve Board -- charge-off rates on loans at ALL commercial "
        "banks, same four quarters.",
        ["CORREACBS", "CORSFRMACBS", "CORCREXFACBS", "CORCACBS", "CORCCACBS",
         "COROCACBS", "CORLFRACBS", "CORBLACBS", "CORAGACBS", "CORALACBS"]),
    "fed-delinquency-top-100": (
        "fed_deltop100sa.html", ["2026:2", "2026:1", "2025:4", "2025:3"],
        "The same delinquency measure for the 100 largest banks.",
        ["DRCCLT100S", "DROCLT100S", "DRCLT100S", "DRBLT100S", "DRSFRMT100S",
         "DRCRELEXFT100S"]),
    "fed-delinquency-other-banks": (
        "fed_delothersa.html", ["2026:2", "2026:1", "2025:4", "2025:3"],
        "And for every bank outside the largest 100.",
        ["DRCCLOBS", "DROCLOBS", "DRCLOBS", "DRBLOBS", "DRSFRMOBS",
         "DRCRELEXFOBS", "CORCCOBS", "COROCOBS", "CORCOBS"]),
    "fed-chargeoff-top-100": (
        "fed_chgtop100sa.html", ["2026:2", "2026:1", "2025:4", "2025:3"],
        "Charge-off rates, 100 largest banks.", ["CORCCT100S", "COROCT100S"]),
    "g19-consumer-credit": (
        "g19_hist_sa.csv", ["Jun 2026", "May 2026", "Apr 2026", "Mar 2026"],
        "Federal Reserve Board -- G.19 consumer credit outstanding, seasonally "
        "adjusted, in MILLIONS of dollars. Total, revolving, nonrevolving.",
        ["TOTALSL", "REVOLSL", "NONREVSL"]),
    "debt-service-ratios": (
        "dsr_new.htm", ["2026:1", "2025:4", "2025:3", "2025:2"],
        "Federal Reserve Board -- household debt service ratios, on the "
        "credit-bureau methodology in force since the 2024 Q2 publication.",
        ["TDSP", "MDSP", "CDSP"]),
    "loan-officer-survey": (
        "sloos_chartdata.htm", ["2026:3", "2026:2", "2026:1", "2025:4"],
        "Federal Reserve Board -- Senior Loan Officer Opinion Survey, net "
        "percentage of banks tightening or reporting stronger demand.",
        ["DRTSCILM", "DRTSCIS", "DRSDCILM", "DRSDCIS", "SUBLPDRCSC",
         "SUBLPDRCSN", "SUBLPDRCSM", "DRTSSP", "SUBLPDHMSENQ", "DRTSCLCC",
         "STDSAUTO", "STDSOTHCONS"]),
}


def shoot(name, body, width=1500, height=1100):
    page = WORK / ("macro-%s.html" % name)
    page.write_text(body, encoding="utf-8")
    png = OUT / (name + ".png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--virtual-time-budget=30000",
                    "--window-size=%d,%d" % (width, height),
                    "--screenshot=%s" % png, page.resolve().as_uri()],
                   check=False, capture_output=True, timeout=240)
    return png


series_to_shot = {}
made = []
for name, (fname, wants, caption, covers) in PAGES.items():
    path = C / fname
    if not path.exists():
        print("%-28s MISSING %s" % (name, fname))
        continue
    body = path.read_text(encoding="utf-8", errors="replace")
    body += MARKER % (json.dumps(wants), json.dumps(caption))
    png = shoot(name, body)
    ok = png.exists() and png.stat().st_size > 20000
    made.append((name, png, caption, covers))
    for s in covers:
        series_to_shot[s] = name
    print("%-28s %-4s %7d bytes  covers %d series"
          % (name, "ok" if ok else "THIN", png.stat().st_size if png.exists() else 0,
             len(covers)))

# ---- the file-based sources get a rendered excerpt of their own bytes ------
FILES = {
    "fhfa-house-prices-state": (
        "fhfa_state.csv", r"^state,|^(AK|CA|GA|NY|TX),2026,2,",
        "FHFA -- hpi_at_state.csv, the agency's own quarterly file. Header row "
        "plus five states at 2026 Q2. Every state series is a row of this file.",
        [s for s in [] ]),
    "fhfa-house-prices-metro": (
        "fhfa_metro.csv", r"^place_name,|,35614,2026,2,|,16980,2026,2,",
        "FHFA -- hpi_at_metro.csv. Each metro series is one CBSA code in this "
        "file.", []),
}
for name, (fname, pattern, caption, covers) in FILES.items():
    path = C / fname
    if not path.exists():
        print("%-28s MISSING %s" % (name, fname))
        continue
    rx = re.compile(pattern)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    keep = [(i + 1, l) for i, l in enumerate(lines) if rx.search(l)][:10]
    rows = "\n".join(
        '<tr class="%s"><td class="n">%d</td><td>%s</td></tr>'
        % ("" if i == 1 else "tieout-ring", i, html.escape(l))
        for i, l in keep)
    doc = ("<style>body{font:14px/1.6 ui-monospace,Consolas,monospace;margin:0;"
           "padding-top:56px}table{border-collapse:collapse;width:100%%}"
           "td{padding:6px 10px;border-bottom:1px solid #ddd;white-space:pre}"
           ".n{color:#888;text-align:right;width:74px;background:#f6f6f6}"
           ".tieout-ring{outline:3px solid #d40000;background:#fff3f3}"
           ".hdr{position:fixed;top:0;left:0;right:0;background:#d40000;color:#fff;"
           "font:700 15px/1.4 system-ui;padding:9px 14px}</style>"
           '<div class="hdr">%s<br><span style="font-weight:400;font-size:12px">'
           "file %s &mdash; line numbers are the file's own</span></div>"
           "<table>%s</table>" % (html.escape(caption), html.escape(fname), rows))
    png = shoot(name, doc, 1500, 420)
    made.append((name, png, caption, covers))
    print("%-28s %-4s %d matching line(s)"
          % (name, "ok" if png.exists() else "FAIL", len(keep)))

(SB / "macro_series_to_shot.json").write_text(json.dumps(series_to_shot, indent=1),
                                              encoding="utf-8")
print("\n%d source images in %s" % (len(made), OUT))
print("series mapped to an image: %d" % len(series_to_shot))
