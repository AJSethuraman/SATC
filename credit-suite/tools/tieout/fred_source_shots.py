"""Photograph each publisher's own document, with the proved row ringed.

The rule this serves: writing "the source agrees" is something a person can do
while believing it. Pasting the picture and pointing at the row is not -- either
the number is on it or it is not, and you find that out when you look rather
than when somebody else does.

Every shot below is the agency's own page, taken from the copy fetched during
the tie-out, opened in a real browser. The only thing added is a red ring around
the row being proved and a scroll to bring it into view. Nothing is retyped and
no table is rebuilt, because a rebuilt table proves the rebuild.

For sources that are data files rather than pages -- FHFA's CSVs, the Z.1
package -- the shot is of the file's own bytes, in a monospaced view that keeps
the delimiters visible, so a reader can grep the same file and land on the same
line.
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
OUT = SB / "srcshots"
WORK = SB / "srcwork"
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

MARKER = """
<style>
  .tieout-ring { outline: 4px solid #d40000 !important;
                 outline-offset: 1px !important;
                 background: #ffe9e9 !important; }
  .tieout-ring > * { background: #ffe9e9 !important; }
  .tieout-note { position: fixed !important; top: 0 !important; left: 0 !important;
                 right: 0 !important; z-index: 2147483647 !important;
                 background: #d40000 !important; color: #ffffff !important;
                 font: 700 15px/1.5 system-ui, sans-serif !important;
                 padding: 9px 14px !important; margin: 0 !important; }
  .tieout-head { position: fixed !important; left: 0 !important; right: 0 !important;
                 z-index: 2147483646 !important; background: #fffbe6 !important;
                 border-bottom: 2px solid #d40000 !important;
                 padding: 4px 14px 8px !important; overflow-x: hidden !important; }
  .tieout-head .tieout-cap { font: 700 11px/1.6 system-ui, sans-serif !important;
                             color: #8a6d00 !important; letter-spacing: .04em; }
</style>
<script>
(function () {
  var want = %s, note = %s;

  var banner = document.createElement("div");
  banner.className = "tieout-note";
  banner.textContent = note;
  document.body.appendChild(banner);

  // The row being proved: a row that contains no rows of its own, whose text
  // begins with the period label. A wrapper that merely contains the text is
  // not the row.
  function pick(selector) {
    var els = document.querySelectorAll(selector), best = null;
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.querySelector("tr, table")) continue;
      var t = (el.textContent || "").replace(/\\u00a0/g, " ")
                                    .replace(/[\\s]+/g, " ").trim();
      if (t.indexOf(want) === 0) return el;
      if (best === null && t.indexOf(want) !== -1) best = el;
    }
    return best;
  }
  var hit = pick("tr") || pick("pre");
  if (!hit) {
    banner.textContent = note + "   [ROW NOT LOCATED -- do not trust this shot]";
    return;
  }
  hit.classList.add("tieout-ring");

  // Bring the table's own column headings along, so the number in the shot has
  // a heading over it. Marked as a copy rather than passed off as adjacency.
  var headTop = 46;
  var table = hit.closest ? hit.closest("table") : null;
  if (table) {
    var heads = [];
    var all = table.querySelectorAll("tr");
    for (var j = 0; j < all.length && heads.length < 3; j++) {
      if (all[j] === hit) break;
      if (all[j].querySelectorAll("th").length) heads.push(all[j]);
    }
    if (heads.length) {
      var strip = document.createElement("div");
      strip.className = "tieout-head";
      strip.style.top = "46px";
      var cap = document.createElement("div");
      cap.className = "tieout-cap";
      cap.textContent = "COLUMN HEADINGS, COPIED FROM THE TOP OF THIS SAME TABLE";
      strip.appendChild(cap);
      var t2 = document.createElement("table");
      t2.setAttribute("style", "border-collapse:collapse");
      for (var k = 0; k < heads.length; k++) {
        t2.appendChild(heads[k].cloneNode(true));
      }
      strip.appendChild(t2);
      document.body.appendChild(strip);
      headTop = 46 + strip.getBoundingClientRect().height;
    }
  }

  // CSS shift, never scrollBy: scrollBy screenshots blank in headless mode.
  var off = hit.getBoundingClientRect().top - (headTop + 140);
  if (off > 0) {
    document.body.style.position = "relative";
    document.body.style.top = (-off) + "px";
  }
})();
</script>
"""

#: name -> (cached file, the text that identifies the row, the caption)
PAGES = {
    "fed-delallsa": (
        "fed_delallsa.html", "2026:2",
        "Federal Reserve Board -- Delinquency rates, all commercial banks "
        "(delallsa) -- row 2026:2"),
    "fed-chgallsa": (
        "fed_chgallsa.html", "2026:2",
        "Federal Reserve Board -- Charge-off rates, all commercial banks "
        "(chgallsa) -- row 2026:2"),
    "fed-deltop100sa": (
        "fed_deltop100sa.html", "2026:2",
        "Federal Reserve Board -- Delinquency rates, 100 largest banks "
        "(deltop100sa) -- row 2026:2"),
    "fed-delothersa": (
        "fed_delothersa.html", "2026:2",
        "Federal Reserve Board -- Delinquency rates, other banks "
        "(delothersa) -- row 2026:2"),
    "g19-hist-sa": (
        "g19_hist_sa.csv", "Jun 2026",
        "Federal Reserve Board -- G.19 Consumer Credit, historical seasonally "
        "adjusted levels -- row Jun 2026"),
    "g19-current": (
        "g19_current_default.htm", "Total outstanding",
        "Federal Reserve Board -- G.19 Consumer Credit, current release -- "
        "row 'Total outstanding', last column is June 2026"),
    "dsr-current": (
        "dsr_new.htm", "2026:1",
        "Federal Reserve Board -- Household Debt Service Ratio (credit-bureau "
        "methodology) -- row 2026:1"),
    "dsr-archived": (
        "dsr.htm", "Last update",
        "Federal Reserve Board -- the ARCHIVED debt service page, frozen at "
        "2024:1. Reading this one would have compared a 2026 figure against a "
        "discontinued series."),
    "sloos-chartdata": (
        "sloos_chartdata.htm", "2026:3",
        "Federal Reserve Board -- Senior Loan Officer Opinion Survey, chart "
        "data -- row 2026:3"),
    "sloos-table1": (
        "sloos_t1.htm", "Tightened somewhat",
        "Federal Reserve Board -- SLOOS Table 1, question 1: standards on C&I "
        "loans to large and middle-market firms, by bank size"),
}

#: name -> (file, a regex selecting the lines to show, caption, how many lines)
FILES = {
    "fhfa-state": (
        "fhfa_state.csv", r"^state,|^AK,2026,2,|^GA,2026,2,|^CA,2026,2,",
        "FHFA -- hpi_at_state.csv, the agency's own quarterly file: header row "
        "plus three states at 2026 Q2", 4),
    "fhfa-us": (
        "fhfa_us.csv", r"^USA,2026,2,",
        "FHFA -- hpi_at_us_and_census.csv, row USA 2026 Q2", 2),
}


def shoot(name, source_html, width=1500, height=1000):
    page = WORK / (name + ".html")
    page.write_text(source_html, encoding="utf-8")
    png = OUT / (name + ".png")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--virtual-time-budget=30000",
         "--window-size=%d,%d" % (width, height),
         "--screenshot=%s" % png, page.resolve().as_uri()],
        check=False, capture_output=True, timeout=180)
    return png


made = []
for name, (fname, want, caption) in PAGES.items():
    path = C / fname
    if not path.exists():
        print("%-18s MISSING %s" % (name, fname))
        continue
    body = path.read_text(encoding="utf-8", errors="replace")
    body += MARKER % (json.dumps(want), json.dumps(caption))
    png = shoot(name, body)
    made.append((name, png, caption))
    print("%-18s %s  %s" % (name, "ok" if png.exists() else "FAILED",
                            png.stat().st_size if png.exists() else 0))

for name, (fname, pattern, caption, _n) in FILES.items():
    path = C / fname
    if not path.exists():
        print("%-18s MISSING %s" % (name, fname))
        continue
    rx = re.compile(pattern)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    keep = [(i + 1, ln) for i, ln in enumerate(lines) if rx.match(ln)]
    rows = "\n".join(
        '<tr class="%s"><td class="n">%d</td><td>%s</td></tr>'
        % ("tieout-ring" if not ln.lower().startswith(("state", "place")) else "",
           i, html.escape(ln))
        for i, ln in keep[:12])
    doc = ("<style>body{font:14px/1.6 ui-monospace,Consolas,monospace;margin:0;"
           "padding-top:52px}table{border-collapse:collapse;width:100%%}"
           "td{padding:6px 10px;border-bottom:1px solid #ddd;white-space:pre}"
           ".n{color:#888;text-align:right;width:70px;background:#f6f6f6}"
           ".tieout-ring{outline:3px solid #d40000;background:#fff3f3}"
           ".hdr{position:fixed;top:0;left:0;right:0;background:#d40000;"
           "color:#fff;font:15px/1.5 system-ui;padding:8px 14px}</style>"
           '<div class="hdr">%s &mdash; file %s, line numbers as in the file'
           "</div><table>%s</table>"
           % (html.escape(caption), html.escape(fname), rows))
    png = shoot(name, doc, 1500, 320)
    made.append((name, png, caption))
    print("%-18s %s  %d matching line(s)" % (name, "ok" if png.exists() else "FAILED",
                                             len(keep)))

print("\nsource shots written: %d in %s" % (len(made), OUT))
