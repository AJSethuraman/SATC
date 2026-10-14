"""Build TIE-OUT-comparability-2026-10.pdf: one document, every image embedded.

    (from threshold-engine/)
    python docs/tie-out/comparability-2026-10/scripts/build_exhibit.py --figures work/figures.json \
        --images work/images --series work/peer-series --qbp work/qbp-card.json \
        --canon CANON_DIR --chrome CHROME --out work/TIE-OUT-comparability-2026-10.pdf

FIG.json is what collect.py wrote; ../images is what capture.py wrote; CANON_DIR
holds canon's check_tie_out.py (the installed plugin, e.g.
~/.claude/plugins/cache/satc/canon/<version>). canon checks the document and
renders it: there is no other way to get the PDF.
"""
import argparse
import base64
import html
import json
import sys
from pathlib import Path

E = html.escape


def n0(v):
    return "{:,.0f}".format(v) if isinstance(v, (int, float)) else "—"


def n1(v):
    return "{:,.1f}".format(v) if isinstance(v, (int, float)) else "—"


def n2(v):
    return "{:,.2f}".format(v) if isinstance(v, (int, float)) else "—"


def pct(a, b, d=0):
    return ("{:.%df}%%" % d).format(100.0 * a / b) if b else "n/a"


def fmt(v, units):
    if v is None:
        return "—"
    if units == "$000":
        return n0(v)
    if units in ("$m", "$bn"):
        return "{:,.3f}".format(v).rstrip("0").rstrip(".") if abs(v - round(v)) > 1e-9 else n0(v)
    if units == "%":
        return "{:.4f}".format(v)
    return str(v)


class Doc:
    def __init__(self, images):
        self.images = Path(images)
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def img(self, name, alt, cite=None, caption=None, source=True, width="100%"):
        data = base64.b64encode((self.images / (name + ".png")).read_bytes()).decode()
        mark = ' data-tieout="source"' if source else ""
        chips = "".join("<span>%s</span>" % c for c in (cite or []))
        self.add('<figure><img%s src="data:image/png;base64,%s" alt="%s" style="width:%s">%s%s</figure>'
                 % (mark, data, E(alt), width,
                    ('<div class="cite">%s</div>' % chips) if chips else "",
                    ("<figcaption>%s</figcaption>" % caption) if caption else ""))


def table(head, rows, num_from=1, cls=""):
    h = "".join('<th%s>%s</th>' % (' class="num"' if i >= num_from else "", c) for i, c in enumerate(head))
    b = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i >= num_from else "", c)
                                        for i, c in enumerate(r)) for r in rows)
    return '<table class="%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (cls, h, b)


def figtable(figs):
    rows = []
    for f in figs:
        v = f["verdict"]
        rows.append(['<span class="v v-%s">%s</span>' % (v.replace(" ", ""), v), E(f["what"]),
                     fmt(f["ours"], f["units"]) + '<div class="from">%s</div>' % E(f["ours_from"]),
                     fmt(f["source"], f["units"]) + '<div class="from">%s</div>' % E(f["source_from"]),
                     ("—" if f["verdict"] == "COULD NOT" else
                      fmt(f["diff"], f["units"]) + '<div class="from">%s · tolerance %s</div>' % (E(f["units"]), E(f["tolerance_why"]))),
                     ])
        if f.get("note"):
            rows.append(["", '<div class="note">%s</div>' % E(f["note"]), "", "", ""])
    return table(["Verdict", "Figure", "Ours (the tool's side)", "Source (not ours)", "Difference"], rows, num_from=9,
                 cls="figs")


CSS = """
:root{--ink:#1b2430;--muted:#5a6573;--rule:#d5dbe2;--paper:#fff;--accent:#b00020;--code:#f2f4f7;--s1:#2a78d6;--s2:#eb6834;--ok:#1d6b3a;--warn:#8a5a00}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#e6eaef;--muted:#a3adb9;--rule:#38414c;--paper:#141a21;--accent:#ff6b7f;--code:#1e2630;--s1:#3987e5;--s2:#d95926;--ok:#5fbf7f;--warn:#e0a63a}}
:root[data-theme="dark"]{--ink:#e6eaef;--muted:#a3adb9;--rule:#38414c;--paper:#141a21;--accent:#ff6b7f;--code:#1e2630;--s1:#3987e5;--s2:#d95926;--ok:#5fbf7f;--warn:#e0a63a}
@page{size:Letter;margin:14mm 12mm}
body{background:var(--paper);color:var(--ink);font:12.5px/1.45 "Segoe UI",Arial,sans-serif;max-width:980px;margin:0 auto;padding:20px 16px}
h1{font-size:23px;margin:0 0 4px;text-wrap:balance} h2{font-size:17px;margin:26px 0 8px;border-bottom:2px solid var(--ink);padding-bottom:3px;break-after:avoid}
h3{font-size:13.5px;margin:16px 0 6px;break-after:avoid} p{margin:6px 0}
.sub{color:var(--muted);margin:0 0 12px} .lead{font-size:14px}
.gap{break-before:page}
pre,code{font-family:Consolas,"DejaVu Sans Mono",monospace;font-size:11px;background:var(--code)} pre{padding:8px;white-space:pre-wrap;word-break:break-all;margin:6px 0}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;margin:6px 0;font-size:11.5px}
td,th{border:1px solid var(--rule);padding:3px 6px;text-align:left;vertical-align:top} th{background:var(--code)} .num{text-align:right}
table.figs td:nth-child(3),table.figs td:nth-child(4),table.figs td:nth-child(5){text-align:right;white-space:nowrap}
table.figs{font-size:10.5px} .from{font-size:9.5px;color:var(--muted);white-space:normal;text-align:left;max-width:230px}
.note{font-size:10.5px;color:var(--muted)}
tr{break-inside:avoid} table[data-tieout="roster"]{break-inside:avoid}
table.figs{table-layout:fixed} table.figs th:nth-child(1){width:12%} table.figs th:nth-child(2){width:28%} table.figs th:nth-child(3){width:21%}
table.figs th:nth-child(4){width:25%} table.figs th:nth-child(5){width:14%} .from{max-width:none}
figure img.narrow{width:62%} figure{margin:8px 0;break-inside:avoid} figure img{border:1px solid var(--rule)}
figcaption{color:var(--muted);font-size:11px;margin-top:3px}
.cite{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0} .cite span{border:1px solid var(--rule);padding:1px 6px;font-size:10.5px}
.v{font-weight:700;font-size:10px;letter-spacing:.04em;padding:1px 5px;border:1.5px solid currentColor;white-space:nowrap}
.v-TIED{color:var(--ok)} .v-DIFFERS{color:var(--accent)} .v-COULDNOT{color:var(--warn)}
.answer{border-left:4px solid var(--ink);padding:4px 10px;margin:8px 0;background:var(--code)}
.fix{border-left:4px solid var(--s1);padding:4px 10px;margin:8px 0}
svg{max-width:100%;height:auto;color:var(--ink)} ol li{margin:3px 0}
.headline{font-size:15px;font-weight:600}
"""


def diagram():
    return """<svg viewBox="0 0 940 300" role="img" aria-label="Two roads: the tool's feed and the documents it does not control, meeting side by side">
 <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
 <g font-size="11.5" fill="currentColor" stroke="currentColor" font-family="Segoe UI, Arial, sans-serif">
  <text x="8" y="18" stroke="none" font-weight="700">Production road: what the tool reads and writes</text>
  <rect x="8" y="30" width="170" height="58" fill="none"/>
  <text x="93" y="52" stroke="none" text-anchor="middle">FDIC BankFind API</text>
  <text x="93" y="70" stroke="none" text-anchor="middle">/banks/financials</text>
  <line x1="178" y1="59" x2="238" y2="59" marker-end="url(#a)"/>
  <text x="208" y="50" stroke="none" text-anchor="middle" font-size="10">peers pull</text>
  <rect x="240" y="30" width="170" height="58" fill="none"/>
  <text x="325" y="52" stroke="none" text-anchor="middle">the tool's cache</text>
  <text x="325" y="70" stroke="none" text-anchor="middle">82 quarter files, q*.json</text>
  <line x1="410" y1="59" x2="470" y2="59" marker-end="url(#a)"/>
  <text x="440" y="50" stroke="none" text-anchor="middle" font-size="10">peers build</text>
  <rect x="472" y="30" width="200" height="58" fill="none"/>
  <text x="572" y="52" stroke="none" text-anchor="middle">series CSVs the workbook reads</text>
  <text x="572" y="70" stroke="none" text-anchor="middle">industry · pack · KeyBank · per bank</text>
  <line x1="672" y1="59" x2="740" y2="130" marker-end="url(#a)"/>
  <text x="8" y="292" stroke="none" font-weight="700">Check road: documents the firm does not control</text>
  <rect x="8" y="190" width="150" height="80" fill="none"/>
  <text x="83" y="212" stroke="none" text-anchor="middle">Filed Call Reports</text>
  <text x="83" y="230" stroke="none" text-anchor="middle">FFIEC CDR, 27 filings</text>
  <text x="83" y="248" stroke="none" text-anchor="middle">PDF pages + XBRL</text>
  <rect x="166" y="190" width="150" height="80" fill="none"/>
  <text x="241" y="212" stroke="none" text-anchor="middle">FDIC Quarterly</text>
  <text x="241" y="230" stroke="none" text-anchor="middle">Banking Profile 2Q26</text>
  <text x="241" y="248" stroke="none" text-anchor="middle">Table V-A + time series</text>
  <rect x="324" y="190" width="150" height="80" fill="none"/>
  <text x="399" y="212" stroke="none" text-anchor="middle">KeyCorp 10-K 2025</text>
  <text x="399" y="230" stroke="none" text-anchor="middle">and 10-Q Q2 2026</text>
  <text x="399" y="248" stroke="none" text-anchor="middle">SEC EDGAR</text>
  <rect x="482" y="190" width="150" height="80" fill="none"/>
  <text x="557" y="212" stroke="none" text-anchor="middle">Call Report</text>
  <text x="557" y="230" stroke="none" text-anchor="middle">instructions; Fed H.8</text>
  <text x="557" y="248" stroke="none" text-anchor="middle">16 Apr 2010</text>
  <line x1="632" y1="230" x2="740" y2="165" marker-end="url(#a)"/>
  <text x="688" y="222" stroke="none" text-anchor="middle" font-size="10">read, ringed</text>
  <rect x="742" y="112" width="190" height="72" fill="none" stroke-width="2"/>
  <text x="837" y="134" stroke="none" text-anchor="middle" font-weight="700">two numbers side by side</text>
  <text x="837" y="152" stroke="none" text-anchor="middle">difference, tolerance stated</text>
  <text x="837" y="170" stroke="none" text-anchor="middle">TIED · DIFFERS · COULD NOT</text>
 </g></svg>"""


def ttm_chart(off_card, tool_series, qbp_series):
    """Card industry TTM net rate: the tool's series against the QBP-built one."""
    qs = sorted(q for q in tool_series if q in qbp_series)
    W, H, L, R, T, B = 900, 260, 46, 170, 14, 30
    ymax = 11.0
    x = lambda i: L + (W - L - R) * i / (len(qs) - 1)
    y = lambda v: T + (H - T - B) * (1 - v / ymax)
    def path(series):
        return " ".join(("M" if i == 0 else "L") + "%.1f,%.1f" % (x(i), y(series[q])) for i, q in enumerate(qs))
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--rule)" stroke-width="1"/>'
                   '<text x="%d" y="%.1f" font-size="10" text-anchor="end" fill="var(--muted)">%d%%</text>'
                   % (L, W - R, y(v), y(v), L - 6, y(v) + 3, v) for v in range(0, 12, 2))
    ticks = "".join('<text x="%.1f" y="%d" font-size="10" text-anchor="middle" fill="var(--muted)">%s</text>'
                    % (x(i), H - 10, q[:4]) for i, q in enumerate(qs) if q.endswith("Q4") and int(q[:4]) % 2 == 0)
    marks = ""
    for q, lab in (("2007Q3", "2006Q4 merger"), ("2012Q2", "Citi 2011"), ("2015Q3", "FIA 2014"), ("2023Q3", "Capital One 2022")):
        if q in qs:
            i = qs.index(q)
            marks += '<text x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" fill="var(--ink)">%s</text>' % (
                x(i), y(tool_series[q]) - 8, lab)
    last = qs[-1]
    return """<svg viewBox="0 0 %d %d" role="img" aria-label="Industry card net charge-off rate: tool against QBP">%s%s
      <path d="%s" fill="none" stroke="var(--s2)" stroke-width="2"/>
      <path d="%s" fill="none" stroke="var(--s1)" stroke-width="2"/>%s
      <text x="%.1f" y="%.1f" font-size="10.5" fill="var(--ink)">— tool's industry series</text>
      <text x="%.1f" y="%.1f" font-size="10.5" fill="var(--ink)">— built from the QBP</text>
      <line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="var(--s1)" stroke-width="2"/>
      <line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="var(--s2)" stroke-width="2"/>
    </svg>""" % (W, H, grid, ticks, path(qbp_series), path(tool_series), marks,
                 W - R + 18, T + 14, W - R + 18, T + 32, W - R + 4, W - R + 16, T + 10, T + 10, W - R + 4, W - R + 16, T + 28, T + 28)


def main():
    ap = argparse.ArgumentParser()
    for a in ("--figures", "--images", "--canon", "--chrome", "--out", "--series", "--qbp"):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    F = json.loads(Path(a.figures).read_text("utf-8"))
    figs = F["figures"]
    by_gap = {g: [f for f in figs if f["gap"] == g] for g in range(1, 8)}
    counts = F["counts"]
    total = len(figs)
    d = Doc(a.images)
    sys.path.insert(0, str(Path(__file__).parent))
    import sources as S

    g1, g2, g3, g4, g5, g6, g7 = (F["gap%d" % i] for i in range(1, 8))
    bank = {b["bank"]: b for b in g1["banks"]}
    kb1 = bank["KeyBank"]
    acq = g5["acquisitions"]
    mat = [r for r in acq["groups"] if r["material"]]
    miss = sorted([r for r in mat if not r["caught"]], key=lambda r: -(r["share"] or 0))
    hist4 = g4["qbp_hist"]
    ttm_off_card = hist4["credit-card"]["off"]
    worst_card = max(ttm_off_card.items(), key=lambda kv: kv[1][0] - kv[1][1])
    kq = F["gap1"]["keycorp_10q_gnma"]

    # ------------------------------------------------------------------ front
    d.add("<h1>Seven comparability questions, tied out against the filings</h1>")
    d.add('<p class="sub">threshold-engine · KeyBank, N.A. (FDIC cert 17534) against its 15 peers and the industry · '
          'public data only · run 14 October 2026 · KeyBank\'s internal books were not used anywhere</p>')
    d.add('<p class="headline"><span data-tieout="headline">%d figures</span> were put beside a document the firm does not '
          'control: <b>%d DIFFERS</b>, <b>%d COULD NOT</b>, %d TIED.</p>'
          % (total, counts.get("DIFFERS", 0), counts.get("COULD NOT", 0), counts.get("TIED", 0)))

    d.add("<h2>The answer, gap by gap</h2>")
    d.add(table(["Gap", "Verdict on the gap", "How big", "What to do"], [
        ["1 · Government-guaranteed loans in 90+",
         "<b>Real at KeyBank, about a third of its first-lien 90+. At the peers it could be most of mortgage 90+, but the filings only bound it.</b> The lines are RC-N items 11, 11.a and 11.b on today's form, not 10 and 10.a.",
         "Rebooked GNMA loans 90+ come to %s of first-lien 90+ accruing at U.S. Bank, %s at Citizens, %s at Wells Fargo; %s industry-wide. These are upper bounds: the GNMA line also holds commercial loans. KeyBank, the one split that is public: about $%dm of its $15.0m (one third), from KeyCorp's 10-Q." % (
             pct(bank["U.S. Bank"]["gnma_90"], bank["U.S. Bank"]["first_90"]), pct(bank["Citizens"]["gnma_90"], bank["Citizens"]["first_90"]),
             pct(bank["Wells Fargo"]["gnma_90"], bank["Wells Fargo"]["first_90"]), pct(g1["industry_gnma_90"], g1["industry_first_90"]), kq[1]),
         "Compare mortgage across banks on nonaccrual and charge-offs, not 90+ accruing. Do not subtract rebooked GNMA from a peer's mortgage 90+: the line is not split by loan type and can hold commercial loans. Where a 90+ figure is shown, put the GNMA share beside it as an upper bound."],
        ["2 · Nonaccrual is partly policy (cards)",
         "<b>Real.</b> The Call Report lets a bank keep a late consumer loan accruing.",
         "At 30 Jun 2026, 10 of 16 banks file zero card nonaccrual; Citizens has filed zero card 90+ accruing in every one of its 76 quarters and puts it all in nonaccrual.",
         "Compare cards across banks on 90+ including nonaccrual (and 30+ including nonaccrual). Show nonaccrual alone and 90+ accruing alone only for KeyBank's own history."],
        ["3 · Card securitizations back on balance sheet, 2010Q1",
         "<b>Real in the industry card series; not visible in the roster banks' own series.</b>",
         "Industry card balances +%s in one quarter ($%sbn to $%sbn). About +%.1f pts on the industry card rate from the change in mix alone." % (
             pct(g3["qbp"]["2010Q1"]["bal"] - g3["qbp"]["2009Q4"]["bal"], g3["qbp"]["2009Q4"]["bal"], 1), n1(g3["qbp"]["2009Q4"]["bal"] / 1000),
             n1(g3["qbp"]["2010Q1"]["bal"] / 1000), g3["mix_effect"]),
         "Treat 2010Q1 as a break in the industry card series: use it from 2010Q4, or label 2006 to 2010Q3 as excluding securitized cards. The pack composite already starts at 2010Q4."],
        ["4 · Industry total against peer median",
         "<b>Real, and it depends on the product.</b> The tool's industry total is the FDIC's own (ties to the QBP).",
         "Card and other consumer: within about 0.15 pts on average, but up to 1.3 pts apart in the 2009–11 stress. Auto: the industry is higher in every quarter, typically twice the median (1.3 to 2.9 times; %.2f%% against %.2f%% now). Home equity: 2.2 times the median at the 2009 peak." % (
             g4["products"]["Auto"]["rows"]["2026Q2"]["ind"], g4["products"]["Auto"]["rows"]["2026Q2"]["med"]),
         "Show both, as decided. For auto, anchor on the peer median and say why. Build the median in the tool: the band has no p50 yet."],
        ["5 · Mergers and acquired loans",
         "<b>Real, two ways.</b> (a) The 25% jump rule misses smaller acquisitions. (b) The tool's industry series counts charge-offs twice when one bank absorbs an affiliate.",
         "(a) %d of %d material acquisitions since 2006 (counted by acquirer, quarter and product) are not left out, up to %s of a book (PNC buying BBVA USA, auto). (b) Six card quarters overcounted by $74m to $4.8bn; the industry card rate is up to +%.2f pts high for four quarters after each." % (
             len(miss), len(mat), pct(miss[0]["share"], 1), worst_card[1][0] - worst_card[1][1]),
         "(a) Leave out windows around every quarter whose recorded acquisitions, added together, are 5% or more of the product. (b) In the merger quarter, take the absorbed bank's last year-to-date figure off the survivor's flow; test against the QBP's quarterly totals."],
        ["6 · Entity: KeyCorp 10-K against KeyBank's Call Report",
         "<b>Small and fully explained</b>, with one definition gap.",
         "Balances and charge-offs tie within $1m at both dates once two named items are added: education loans in discontinued operations ($%dm, $%dm) and residential mortgages held for sale ($%dm, $%dm). KeyCorp's \"home equity\" is $%sbn larger than the Call Report's home equity lines." % (
             g6["31 Dec 2025"]["disc"], g6["30 Jun 2026"]["disc"], g6["31 Dec 2025"]["hfs"], g6["30 Jun 2026"]["hfs"],
             n2((g6["30 Jun 2026"]["he"] * 1000 - g6["30 Jun 2026"]["heloc"]) / 1e6)),
         "In the internal import, name the two items as exclusions, and either split internal home equity into lines and loans or compare mortgage plus home equity together."],
        ["7 · Auto",
         "<b>RC-C 6.c ties at 62,212; where the rest of direct auto is filed COULD NOT be settled from public data.</b>",
         "6.c holds every consumer car-purchase loan, direct or indirect. KeyBank sold its indirect book in 2021Q3 (6.c fell from $3.80bn to $0.15bn; it kept $2.82bn of the notes). Only two peers file consumer leases: U.S. Bank (at most %s of its consumer auto) and Bank of America (at most %s); the lease line is not split by asset, so these are upper bounds." % (
             pct([x for x in g7["leases"] if x["bank"] == "U.S. Bank"][0]["leases"], [x for x in g7["leases"] if x["bank"] == "U.S. Bank"][0]["leases"] + [x for x in g7["leases"] if x["bank"] == "U.S. Bank"][0]["auto"]),
             pct([x for x in g7["leases"] if x["bank"] == "Bank of America"][0]["leases"], [x for x in g7["leases"] if x["bank"] == "Bank of America"][0]["leases"] + [x for x in g7["leases"] if x["bank"] == "Bank of America"][0]["auto"])),
         "On site, compare internal direct auto at 30 Jun 2026 with 62,212. If it is larger, map the internal segment's composition and entity before assigning the difference to any filed line: it may be loans the Call Report files in 6.d (boats, RVs, cash loans against a car already owned), or a difference of entity or internal definition. Set direct auto's thresholds on internal data, with peers as context only."],
    ], num_from=9))

    d.add("<h2>How the dots connect</h2>")
    d.add("<figure>%s<figcaption>Every figure travels two roads. The top road is how a number reaches the files the firm reads. "
          "The bottom road ends at a document the firm does not produce and cannot change: a bank's filed Call Report, the FDIC's "
          "published industry totals, KeyCorp's SEC filings, the regulators' own instructions. Only the bottom road makes this "
          "evidence rather than a second reading of the same feed.</figcaption></figure>" % diagram())

    d.add("<h2>The roster: %d figures, by gap and verdict</h2>" % total)
    rows = []
    names = {1: "Government-guaranteed loans", 2: "Card nonaccrual policy", 3: "2010 securitizations", 4: "Industry against median",
             5: "Mergers", 6: "KeyCorp against KeyBank", 7: "Auto"}
    for g in range(1, 8):
        c = {v: sum(1 for f in by_gap[g] if f["verdict"] == v) for v in ("DIFFERS", "COULD NOT", "TIED")}
        rows.append(["%d · %s" % (g, names[g])] + ['<span data-tieout="count">%d</span>' % c[v] for v in ("DIFFERS", "COULD NOT", "TIED")]
                    + [str(len(by_gap[g]))])
    rows.append(["<b>All</b>"] + ["<b>%d</b>" % counts.get(v, 0) for v in ("DIFFERS", "COULD NOT", "TIED")] + ["<b>%d</b>" % total])
    d.add(table(["Gap", "DIFFERS", "COULD NOT", "TIED", "Figures"], rows).replace("<table", '<table data-tieout="roster"', 1))
    d.add("<p>Each figure is one comparison: the value on the tool's side, read where it says, against the value in an independent "
          "document. The DIFFERS and COULD NOT figures are the ones worth reading:</p>")
    d.add(figtable([f for f in figs if f["verdict"] != "TIED"]))
    d.add('<p>The %d TIED figures are listed in full at the end. A TIED figure means the tool reads the public data correctly; '
          'it does not mean the gap it belongs to is small.</p>' % counts.get("TIED", 0))

    # ------------------------------------------------------------------ gap 1
    d.add('<h2 class="gap">Gap 1 · Government-guaranteed loans counted as 90+ days late</h2>')
    d.add('<p><b>The question.</b> FHA and VA mortgages and federally guaranteed student loans can sit 90+ days late with little '
          'loss to the bank, because the government pays. Does that inflate the 90+ measures, and by how much?</p>')
    d.add('<div class="answer"><b>Real. At KeyBank about a third of first-lien 90+ is government-insured; at the peers it could be most of it, but the '
          'filings give only an upper bound.</b> On today\'s form the lines are RC-N <b>item 11</b> '
          '(loans wholly or partially guaranteed by the U.S. Government), <b>11.a</b> (the guaranteed portion, excluding rebooked GNMA '
          'loans) and <b>11.b</b> (rebooked GNMA loans: Ginnie Mae pool loans the bank may buy back, which come back onto its books). '
          'Item 10 is now "Debt securities and other assets". The brief\'s "items 10 and 10.a" is the older numbering.</div>')
    d.add("<h3>KeyBank's filing, 30 June 2026</h3>")
    d.img("g1-keybank-rcn-11", "KeyBank RC-N rows 1.c.(2)(a) and 11 to 11.b",
          ["KeyBank National Association", "FFIEC 031", "Report date 6/30/2026", "Schedule RC-N, report page 45", "Column B: 90+ days, still accruing",
           "1.c.(2)(a) RCONC237 = 15,000", "11 RCFDK037 = 69,414", "11.a RCFDK040 = 0", "11.b RCFDK043 = 69,414", "$ thousands"])
    d.add("<p>All of KeyBank's guaranteed 90+ is rebooked GNMA loans (11.b), and 11.a is zero, so no guaranteed student loans are 90+ late. "
          "The rebooked GNMA amount (69,414) is more than four times KeyBank's whole first-lien 90+ line (15,000), so most of it "
          "cannot be residential. KeyCorp's 10-Q says which:</p>")
    d.img("g1-10q-gnma-note", "KeyCorp 10-Q note on GNMA loans", ["KeyCorp 10-Q, quarter ended 30 Jun 2026", "Note 4 aging table, footnote (c)",
          "$54m commercial mortgage", "$5m residential mortgage", "$ millions"], width="90%")
    d.add("<p>So about $5m of KeyBank's $15.0m first-lien 90+ is government-insured residential loans. KeyCorp's own aging table counts "
          "these loans as <i>current</i> (footnote (c) sits on the Current column), while the Call Report counts them as 90+ and still accruing. "
          "Internal 90+ therefore excludes them and filed 90+ includes them. At 31 December 2025 the two tie ($66m + $6m against 72,321); "
          "at 30 June 2026 they differ by about $10m, which is not explained here:</p>")
    d.img("g1-keybank-rcn-11-dec25", "KeyBank RC-N 11.b at 31 Dec 2025", ["KeyBank", "Report date 12/31/2025", "RC-N 11.b col B RCFDK043 = 72,321"])
    d.img("g1-10k-gnma-note", "KeyCorp 10-K note on GNMA loans", ["KeyCorp 10-K 2025", "footnote (c)", "$66m + $6m"], width="90%")
    d.add("<h3>The peers: rebooked GNMA 90+ against first-lien mortgage 90+ (30 Jun 2026, $000, as filed)</h3>")
    rows = []
    for b in g1["banks"]:
        rows.append([b["bank"], n0(b["first_90"]), n0(b["gnma_90"]), pct(b["gnma_90"], b["first_90"]) if b["first_90"] else "n/a",
                     n0(b["first_30"]), n0(b["gnma_30"]), pct(b["gnma_30"], b["first_30"]) if b["first_30"] else "n/a", n0(b["part_90"])])
    rows.append(["<b>Industry (4,313 filers)</b>", n0(g1["industry_first_90"]), n0(g1["industry_gnma_90"]),
                 pct(g1["industry_gnma_90"], g1["industry_first_90"]), "", "", "", ""])
    d.add(table(["Bank", "First-lien 90+ (1.c.(2)(a) B)", "Rebooked GNMA 90+ (11.b B)", "GNMA ÷ first-lien (upper bound)", "First-lien 30–89",
                 "GNMA 30–89 (11.b A)", "GNMA ÷ 30–89", "Guaranteed portion 90+ (11.a B)"], rows))
    d.add("<p>Item 11 is not split by loan type, so \"GNMA ÷ first-lien\" is an upper bound: a ratio over 100%% (KeyBank, Wells Fargo) means some "
          "GNMA loans are commercial (FHA multifamily) rather than 1-4 family. The FDIC's QBP files rebooked GNMA loans under closed-end first liens, "
          "and its industry figure ties to the FDIC API to the dollar (figure G1-35), but that is the same unsplit item 11.b. So the filings show that "
          "government-insured loans <i>could</i> be most of the 90+ accruing mortgage measure at most mortgage lenders on the roster, not that they are: "
          "KeyBank, the one bank whose split is public, has most of its GNMA in commercial loans. A split for each peer would need its own holding-company "
          "filings, which were not read here. On the 90+ including nonaccrual measure the industry share is at most %s.</p>"
          % pct(g1["industry_gnma_90"], g1["industry_first_90"] + g1["industry_first_na"]))
    d.img("g1-usbank-rcn-11", "U.S. Bank RC-N rows", ["U.S. Bank National Association", "Report date 6/30/2026", "1.c.(2)(a) col B = 4,181,884",
                                                    "11.b col B = 3,945,459"])
    hi = g1["industry_hist"]
    d.add("<p>Industry over time (QBP, $m): " + "; ".join("%s %s of %s (%s)" % (q, n0(v[0]), n0(v[1]), pct(v[0], v[1])) for q, v in sorted(hi.items())) + ".</p>")
    d.add('<p><b>A field-name trap, found on the way.</b> The FDIC API\'s names read the wrong way round. <code>P9GTYPAR</code> ("part '
          'guaranteed") is item 11, all wholly or partially guaranteed loans; <code>P9GTY</code> is 11.a, the guaranteed portion; '
          '<code>P9GTYGNM</code> is 11.b. The same holds for the 30–89 (<code>P3</code>) and nonaccrual (<code>NA</code>) twins. It was settled by '
          'reading the 16 filings, not the dictionary.</p>')
    d.add('<div class="fix"><b>Recommended fix.</b> For mortgage, compare banks on nonaccrual and charge-offs, where guaranteed loans barely '
          'register. Do not subtract rebooked GNMA (P9GTYGNM) from a peer\'s first-lien 90+ (P9RERSFM): item 11.b is not split by loan type, '
          'so the subtraction can take out commercial loans. KeyBank shows it: 15,000 − 69,414 is below zero, while about $10m of its first-lien 90+ '
          'is not government-insured. If a 90+ mortgage figure is shown, put "rebooked GNMA ÷ first-lien 90+" beside it, labelled as an upper bound '
          'on the insured share. For KeyBank use the 10-Q\'s residential figure each quarter. When internal 90+ is compared with filed 90+, take the residential GNMA '
          'amount off the filed side, because KeyCorp counts those loans as current. Other consumer: KeyBank has none (11.a is 0); for peers, item 11.a '
          'mixes SBA, student and other guarantees and cannot be pinned to a product.</div>')
    d.add("<h3>Figures</h3>" + figtable(by_gap[1][:4] + by_gap[1][34:]))
    d.add("<p>The other 30 gap-1 figures are the 15 peers' rebooked GNMA 90+ and first-lien 90+, API (or the tool's cache) against each filing: all TIED; "
          "see the full list at the end.</p>")

    # ------------------------------------------------------------------ gap 2
    d.add('<h2 class="gap">Gap 2 · Nonaccrual is partly bank policy</h2>')
    d.add("<p><b>The question.</b> Card issuers often charge a card off at 180 days without ever putting it on nonaccrual. Is card "
          "nonaccrual comparable across the peers?</p>")
    d.add('<div class="answer"><b>No. It is policy, and the Call Report allows it.</b> Any consumer loan or 1-4 family mortgage "need not be placed in '
          'nonaccrual status"; if a bank elects to, it must report it in column C.</div>')
    d.img("g2-glossary-nonaccrual", "Call Report glossary, Nonaccrual Status", ["FFIEC 031 and 041 instructions, Glossary, 'Nonaccrual Status'",
          "page A-92 (3-24), in the September 2026 set", "Exceptions to the general rule, (1)"])
    d.img("g2-glossary-nonaccrual-cont", "Call Report glossary, Nonaccrual Status continued", ["Glossary page A-93"])
    d.add("<h3>As filed, 30 June 2026</h3>")
    for nm, cap in (("keybank", "KeyBank files both: 9,346 90+ accruing and 6,401 nonaccrual."),
                    ("citizens", "Citizens files no card 90+ accruing; everything 90+ is nonaccrual (19,453)."),
                    ("wellsfargo", "Wells Fargo files 758,000 90+ accruing and no card nonaccrual.")):
        d.img("g2-%s-rcn-5a" % nm, "RC-N 5.a", ["RC-N line 5.a Credit cards", "col B RCFDB576 · col C RCFDB577", "$ thousands", "6/30/2026"], caption=cap)
    rows = []
    for b in g2["banks"]:
        L = b["bal"]
        rows.append([b["bank"], n0(L), n0(b["na"]), n0(b["p9"]), pct(b["na"], L, 2) if L else "n/a", pct(b["p9"], L, 2) if L else "n/a",
                     pct(b["na"] + b["p9"], L, 2) if L else "n/a"])
    d.add(table(["Bank", "Card balance", "Nonaccrual (5.a C)", "90+ accruing (5.a B)", "Nonaccrual %", "90+ accruing %", "90+ incl. nonaccrual %"], rows))
    rows = [[h["bank"], str(h["quarters"]), str(h["na_quarters"]), str(h["p9_zero_quarters"])] for h in g2["history"]]
    d.add("<h3>Over 82 quarters, 2006Q1 to 2026Q2 (the tool's cache)</h3>")
    d.add(table(["Bank", "Quarters with a card book", "…filing any card nonaccrual", "…filing zero 90+ accruing"], rows))
    d.add("<p>The pattern holds in the filings ten years earlier too: Citizens at 31 Dec 2015 filed 0 card 90+ accruing and 14,034 nonaccrual; "
          "Wells Fargo filed 320,000 and 0 (figures G2-33 to G2-36).</p>")
    d.img("g2-citizens-2015-rcn-5a", "Citizens RC-N 5.a 2015", ["Citizens Bank, N.A.", "Report date 12/31/2015", "RC-N 5.a"])
    ind = g2["industry"]
    d.add("<p>Industry-wide, nonaccrual is " + ", ".join("%s%% of card 90+ including nonaccrual in %s" % (n1(v["na_share"]), q[:4]) for q, v in sorted(ind.items())) + ".</p>")
    d.add('<div class="fix"><b>Recommended fix.</b> Compare cards across banks only on <b>90+ including nonaccrual</b> and <b>30+ including nonaccrual</b> '
          '(30–89 is unaffected). A bank that moves a loan to nonaccrual at 90 days and one that keeps it accruing to 180 days both count it there. '
          'Show nonaccrual alone and 90+ accruing alone only for KeyBank\'s own history. The same exception covers every consumer product and 1-4 family '
          'mortgage; the other products\' nonaccrual practice was not measured here (see "What this does not prove").</div>')
    d.add("<h3>Figures</h3><p>36 figures, every one TIED: for each of the 16 banks, card nonaccrual and card 90+ accruing in the tool's cache against "
          "the filing (32), and the two 2015 filings (4). Listed at the end.</p>")

    # ------------------------------------------------------------------ gap 3
    d.add('<h2 class="gap">Gap 3 · Card securitizations back on balance sheet in 2010 (FAS 166/167)</h2>')
    d.add("<p><b>The question.</b> From 2010Q1, accounting standards FAS 166 and 167 brought securitized card receivables back onto banks' balance "
          "sheets. Is there a break in card balances or rates, for the industry and the peers?</p>")
    q3 = g3["qbp"]
    d.add('<div class="answer"><b>Yes in the industry series; not in the roster banks\' own series.</b> Industry card balances rose from $%sbn to $%sbn '
          'in one quarter (+%s). %s of the rise came in four separate card charters that are not on the roster: Citibank (South Dakota), '
          'FIA Card Services, Chase Bank USA and Capital One Bank (USA). Each was later merged into its roster parent (2011, 2014, 2019 and 2022).</div>'
          % (n1(q3["2009Q4"]["bal"] / 1000), n1(q3["2010Q1"]["bal"] / 1000), pct(q3["2010Q1"]["bal"] - q3["2009Q4"]["bal"], q3["2009Q4"]["bal"], 1),
             pct(g3["four_share"], 1, 1)))
    gr = g3["groups"]
    d.add(table(["Group", "2009Q4 balance ($000)", "2010Q1 balance", "Quarterly rate 2009Q4", "Quarterly rate 2010Q1"], [
        ["The four card charters", n0(gr["four"]["20091231"]["bal"]), n0(gr["four"]["20100331"]["bal"]), "%.2f%%" % gr["four"]["20091231"]["rate"], "%.2f%%" % gr["four"]["20100331"]["rate"]],
        ["Rest of the industry", n0(gr["rest"]["20091231"]["bal"]), n0(gr["rest"]["20100331"]["bal"]), "%.2f%%" % gr["rest"]["20091231"]["rate"], "%.2f%%" % gr["rest"]["20100331"]["rate"]],
    ]))
    d.add("<p>The four charters' own loss rate barely moved across the break, and the rest of the industry eased. The industry rate rose because the "
          "higher-loss issuers' share of the book jumped: holding each group at its 2010Q1 rate, the 2009Q4 weights give %.2f%% and the 2010Q1 weights "
          "%.2f%%, a mix effect of <b>+%.2f pts</b> (quarterly, annualised, on quarter-end balances). The tool's industry TTM series goes %s.</p>"
          % (g3["mix_before"], g3["mix_after"], g3["mix_effect"],
             ", ".join("%s %.2f" % (q, v) for q, v in sorted(g3["tool_ttm"].items()) if v)))
    d.add("<p>The QBP's own quarterly rate jumps from %.2f%% to %.2f%% at 2010Q1, an artefact of averaging a pre-consolidation balance with a "
          "post-consolidation one under post-consolidation losses. How a series averages its balance decides how the break shows.</p>"
          % (100 * q3["2009Q4"]["rate"], 100 * q3["2010Q1"]["rate"]))
    rows = [[m["bank"], n0(m["q4"]) if m["q4"] is not None else "—", n0(m["q1"]) if m["q1"] is not None else "—",
             pct(m["q1"] - m["q4"], m["q4"], 1) if m["q4"] else "n/a",
             "left out" if (m["q4"] and abs(m["q1"] / m["q4"] - 1) > 0.25) else ""] for m in g3["moves"]]
    d.add("<h3>The roster banks at the break (card balance, $000)</h3>")
    d.add(table(["Bank", "2009Q4", "2010Q1", "Change", "25% jump rule"], rows))
    d.add("<p>Only PNC (+67%) and Bank of America's tiny card book moved more than 25%, and the jump rule leaves both out. The pack composite for "
          "cards starts at 2010Q4 regardless (earlier quarters fall to breaks or to fewer than five banks).</p>")
    d.add("<h3>The Federal Reserve's own account of the consolidation</h3>")
    d.img("g3-fed-h8-release", "H.8 release date", ["Federal Reserve H.8", "Release date April 16, 2010"])
    d.img("g3-fed-h8-notes", "H.8 notes on the data", ["Notes on the Data (billions of dollars)", "commercial banks consolidated $378.1bn",
                                                       "credit cards and other revolving plans $322.3bn"])
    d.add("<p>The H.8 counts what was consolidated: $322.3bn of cards and other revolving plans at domestically chartered commercial banks. The same "
          "banks' cards plus other revolving rose $%sbn on the Call Reports (figure G3-03). These are not the same quantity: the quarter's change also nets "
          "off that quarter's charge-offs and paydowns. They agree in scale only, so the figure reads DIFFERS.</p>" % n1(g3["rev_change"] / 1e6))
    d.add('<div class="fix"><b>Recommended fix.</b> Mark 2010Q1 as a break in the industry card series. Either use it from 2010Q4, the first TTM '
          'window entirely after the break, or keep 2006 to 2010Q3 labelled "on-balance-sheet only: excludes securitized cards, about 40% of the book". '
          'Do not calibrate the card crisis (the High line) on pre-2010 industry levels without saying so. The roster banks\' own card histories before '
          'each charter merger are a separate problem: see gap 5.</div>')
    d.add("<h3>Figures</h3>" + figtable(by_gap[3]))

    # ------------------------------------------------------------------ gap 4
    d.add('<h2 class="gap">Gap 4 · The dollar-weighted industry total against the peer median</h2>')
    d.add("<p><b>The question.</b> How far apart are the industry total and the peer median, product by product?</p>")
    d.add('<div class="answer"><b>First, the industry total is right.</b> The tool\'s cache, summed over every filer, gives the FDIC\'s own published '
          'figures: card balances, card delinquency and charge-off rates, home equity, 1-4 family and other consumer balances (8 figures). The tool\'s '
          'TTM industry series also equals a TTM built from the QBP alone at 2026Q2, for card, mortgage, home equity and auto. <b>Then, the gap is real '
          'and it depends on the product.</b></div>')
    d.img("g4-qbp-table-va", "QBP Table V-A", ["FDIC Quarterly Banking Profile, 2026 Q2", "Table V-A, Loan Performance", "All FDIC-Insured Institutions",
          "June 30, 2026", "rates %; balances $bn"], width="60%")
    rows = []
    for prod, p in g4["products"].items():
        r = p["rows"].get("2026Q2", {})
        rows.append([prod, "%s–%s" % (p["first"], p["last"]), "%+.2f" % p["mean"], "%+.2f to %+.2f" % (p["min"], p["max"]),
                     "%.2f (%.2f–%.2f)" % (p["ratio_median"], p["ratio_min"], p["ratio_max"]),
                     n2(r.get("ind")), n2(r.get("med")), n2(r.get("pack")), n2(r.get("kb"))])
    d.add("<h3>TTM net charge-off rate, industry against the median of the 15 peers (pts)</h3>")
    d.add(table(["Product", "Quarters", "Industry − median, mean", "Range", "Industry ÷ median, median (range)", "Industry 2026Q2", "Median",
                 "Pack (dollar-weighted peers)", "KeyBank"], rows))
    for prod in ("Credit card", "Home equity", "Mortgage", "Auto"):
        p = g4["products"][prod]
        d.add("<p><b>%s</b>, selected quarters: %s.</p>" % (prod, "; ".join(
            "%s industry %.2f, median %.2f (%d banks)" % (q, v["ind"], v["med"], v["n"]) for q, v in sorted(p["rows"].items()))))
    d.add("<p>The median is the median of the peers' kept rates, computed here with the tool's own <code>bank_book</code> under the build's rules "
          "(jump 0.25, minimum book $1bn, at least 5 banks). The tool does not build a median yet: its band gives the 10th, 25th, 75th and 90th percentiles. "
          "No independent source publishes a median of this roster, so the median itself is COULD NOT (G4-18). Its inputs are per-bank rates, and one of "
          "them, KeyBank's card rate, was rebuilt from five filings and ties to the tool's file to six decimals (G4-17).</p>")
    d.add('<div class="fix"><b>Recommended fix.</b> Show both, as the firm decided. For auto, anchor on the peer median and say why: the industry auto rate '
          'is about twice the median because the dollar-weighted total leans on the large higher-loss lenders. Add p50 to the band. And fix the double count '
          'in gap 5 before using any industry history: the card series is up to %.2f pts high in the quarters after affiliated-charter mergers.</div>'
          % (worst_card[1][0] - worst_card[1][1]))
    d.add("<h3>Figures</h3>" + figtable(by_gap[4]))

    # ------------------------------------------------------------------ gap 5
    d.add('<h2 class="gap">Gap 5 · Mergers and acquired loans</h2>')
    d.add("<p><b>The question.</b> Which quarters carry a jump from an acquisition, and do the roster's rules catch them?</p>")
    d.add('<div class="answer"><b>Two problems, both real.</b> (a) The rules leave a rate window out only when a product\'s book moves more than 25% in a '
          'quarter. The FDIC merger record is pulled, but it feeds only the Balances tab, never the rates. (b) When a bank absorbs an affiliate, the '
          'survivor\'s year-to-date charge-offs include the affiliate\'s earlier quarters. The tool takes a quarter\'s flow as year-to-date less the previous '
          'quarter, so those quarters are counted twice.</div>')
    d.add("<h3>(a) Acquisitions the 25% rule does not catch</h3>")
    d.add("<p>%d acquisitions by roster banks since October 2005 (FDIC history, the tool's own list of acquisition codes); %d with no filing in the cache. "
          "Measured for each acquirer, quarter and product: the books of every bank it absorbed that quarter, each at its last filing, added together "
          "against the acquirer's own book the quarter before. Of %d such cases, %d are material "
          "(5%% or more of a book over $1bn, or $1bn or more into a smaller one). %d are caught by the jump rule and <b>%d are not</b>. The largest misses:</p>"
          % (acq["events"], len(acq["no_filing"]), len(acq["groups"]), len(mat), len(mat) - len(miss), len(miss)))
    rows = [[r["acquirer"], r["quarter"][:4] + "Q%d" % ((int(r["quarter"][4:6]) - 1) // 3 + 1), r["product"], E(r["banks"][0][0] if len(r["banks"]) == 1 else "%s and %d other%s" % (r["banks"][0][0], len(r["banks"]) - 1, "s" if len(r["banks"]) > 2 else "")), n0(r["acquired"]),
             n0(r["before"]), pct(r["share"], 1, 1), "%+.1f%%" % (100 * r["jump"])] for r in miss[:20]]
    d.add(table(["Acquirer", "Quarter", "Product", "Acquired bank(s), largest first", "Acquired book ($000)", "Acquirer's book before", "Share", "Quarter's move"], rows))
    d.add("<p>The quarter's move stays under 25% because the acquirer's own book shrank or the acquisition was under a quarter of the book. Some misses are a group "
          "merging its own charters: Citizens Bank of Pennsylvania into Citizens (2019Q1), Wachovia's card bank into Wells Fargo (2010Q2), Fifth Third's "
          "Michigan charter (2009Q3). Before such a date the roster bank's history is only part of its group's book. PNC's eleven 2007Q3 mortgage "
          "acquisitions are each under 5% of its book and 16.5% together, which is why the count is by quarter, not by charter.</p>")
    d.add("<h3>(b) The double count, measured against the QBP</h3>")
    off = hist4["credit-card"]["off"]
    tool_s = {q: v[0] for q, v in off.items()}
    d.add(table(["Quarter", "Tool's industry card charge-offs ($m)", "QBP ($m)", "Difference", "Absorbed charter(s)", "Their last year-to-date"],
                [[e["q"], n1(e["tool"]), n1(e["qbp"]), n1(e["tool"] - e["qbp"]), E(", ".join(e["names"])), n1(e["absorbed"])] for e in g5["events"]]))
    d.add("<p>Each overcount equals, to within a few $m, the absorbed charter's own year-to-date card charge-offs at its last filing. The filings show why. "
          "Citibank NA's September 2011 year-to-date figure carries Citibank (South Dakota)'s first-half losses:</p>")
    d.img("g5-citi-jun11-rib-5a", "Citibank NA RI-B 5.a June 2011", ["Citibank, N.A.", "Quarter end 6/30/2011", "RI-B 5.a col A RIADB514 = 1,157,000"])
    d.img("g5-citi-sep11-rib-5a", "Citibank NA RI-B 5.a September 2011", ["Citibank, N.A.", "Quarter end 9/30/2011", "RI-B 5.a col A = 8,515,000"])
    d.img("g5-csd-jun11-rib-5a", "Citibank South Dakota RI-B 5.a June 2011", ["Citibank (South Dakota), N.A.", "FFIEC 041", "6/30/2011", "RI-B 5.a = 4,846,242"])
    d.add("<p>8,515,000 − 1,157,000 = 7,358,000, of which 4,846,242 was already counted in South Dakota's own filing. The Call Report requires it:</p>")
    d.img("g5-glossary-common-control", "Glossary, Business Combinations", ["FFIEC 031 and 041 instructions, Glossary", "Business Combinations",
          "Transactions between entities under common control"])
    # chart
    q = json.loads(Path(a.qbp).read_text("utf-8"))
    tool_full = S.series(Path(a.series) / "credit-card_industry_net.csv")
    qq = sorted(q["card"])
    qbp_full = {}
    for at in tool_full:
        i = qq.index(at)
        w = qq[i - 3:i + 1]
        qbp_full[at] = 100 * sum(q["card"][x][0] for x in w) / (sum(q["card"][x][1] for x in w) / 4)
    d.add("<figure>%s<figcaption>Industry card net charge-off rate, trailing four quarters, %%. Blue: the tool's series "
          "(credit-card_industry_net.csv). Orange: the same arithmetic on the QBP's published quarterly charge-offs and balances. "
          "The lines part for four quarters after each affiliated-charter merger. %d of %d quarters differ by 0.01 pts or more.</figcaption></figure>"
          % (ttm_chart(off, tool_full, qbp_full), len(off), hist4["credit-card"]["n"]))
    d.add("<p>Mortgage and home equity run the other way in 2008–09 (up to %.2f and %.2f pts low): the WaMu and Wachovia acquisitions fit by size and "
          "date, but that cause was not traced here. Auto agrees in all %d quarters compared.</p>"
          % (min(v[0] - v[1] for v in hist4["mortgage"]["off"].values()), min(v[0] - v[1] for v in hist4["home-equity"]["off"].values()), hist4["auto"]["n"]))
    d.add("<p>A peer's own series is protected only when the jump rule fires. Citi's 2011Q3 card book moved +302%%, so its windows are left out. Wells Fargo's "
          "2010Q2 card book moved −2.2%%, so its windows stay in, carrying Wachovia Card Services' first-quarter charge-offs twice ($%sm net). "
          "Wells' own card rate, as the tool computes it, against the same rate without them: %s. These windows are in the pack composite.</p>"
          % (n1(g5["wcs_q1"] / 1000), "; ".join("%s %.2f%% against %.2f%%" % (w["q"], w["net"], w["without"]) for w in g5["wells"])))
    d.add('<div class="fix"><b>Recommended fix.</b> (a) Leave out rate windows that touch any quarter whose recorded acquisitions, added together, are 5% or more of the '
          'acquirer\'s product book. Both banks are in the cache, so the share can be computed rather than guessed. (b) In a merger quarter under common control, '
          'take the absorbed bank\'s last year-to-date flows off the survivor\'s flow (same calendar year), in <code>quarterly_flows</code> and <code>industry</code> '
          'alike, and hold the industry series to the QBP\'s published quarterly totals as a test.</div>')
    d.add("<h3>Figures</h3>" + figtable(by_gap[5]))

    # ------------------------------------------------------------------ gap 6
    d.add('<h2 class="gap">Gap 6 · Entity: KeyCorp\'s 10-K against KeyBank, N.A.\'s Call Report</h2>')
    d.add("<p><b>The question.</b> The firm's internal data is KeyCorp's; the Call Report is the bank's. How far apart are their consumer balances and "
          "charge-offs on the same dates?</p>")
    e25, e26 = g6["31 Dec 2025"], g6["30 Jun 2026"]
    d.add('<div class="answer"><b>Small and fully explained, at both dates.</b> Two items account for every difference beyond rounding. '
          '(1) KeyCorp reports its old education loans ($%dm at Dec 2025, $%dm at Jun 2026; government-guaranteed and private student loans, a business '
          'discontinued in 2009) as "discontinued assets", outside "other consumer loans"; the bank files them in RC-C 6.d with every other student loan. '
          '(2) KeyCorp\'s loan totals exclude loans held for sale; the Call Report includes them (residential: $%dm, $%dm). <b>One definition gap remains:</b> '
          'KeyCorp\'s "home equity" includes closed-end home equity loans that the Call Report files with mortgages.</div>' % (e25["disc"], e26["disc"], e25["hfs"], e26["hfs"]))
    d.img("g6-10k-cover", "KeyCorp 10-K cover", ["KeyCorp", "Form 10-K", "fiscal year ended December 31, 2025"], width="70%")
    d.img("g6-10k-figure9", "KeyCorp 10-K Figure 9", ["10-K Figure 9, Composition of Loans", "December 31, 2025", "$ millions"])
    d.img("g6-10k-figure9-note-c", "10-K footnote (c)", ["footnote (c): education loans in discontinued operations"], width="90%")
    d.img("g6-10k-hfs-note", "10-K balance sheet footnote", ["balance sheet footnote (a): residential mortgage loans held for sale"], width="90%")
    d.img("g6-keybank-rcc-12312025", "KeyBank RC-C 31 Dec 2025", ["KeyBank", "FFIEC 031", "Report date 12/31/2025", "Schedule RC-C Part I", "col A", "$ thousands"])
    d.img("g6-10k-figure32", "10-K Figure 32", ["10-K Figure 32, Summary of Loan and Lease Loss Experience", "year 2025, charged off and recovered"])
    d.img("g6-10q-cover", "KeyCorp 10-Q cover", ["KeyCorp", "Form 10-Q", "quarter ended June 30, 2026"], width="70%")
    d.img("g6-10q-figure8", "KeyCorp 10-Q Figure 8", ["10-Q Figure 8, Composition of Loans at June 30, 2026"])
    d.img("g6-10q-figure8-note-b", "10-Q footnote (b)", ["footnote (b): $182m education loans in discontinued operations"], width="90%")
    d.img("g6-10q-hfs-note", "10-Q balance sheet footnote", ["balance sheet footnote (a): $204m residential held for sale"], width="90%")
    d.img("g6-keybank-rcc-06302026", "KeyBank RC-C 30 Jun 2026", ["KeyBank", "Report date 6/30/2026", "Schedule RC-C Part I"])
    d.img("g6-10q-figure29", "KeyCorp 10-Q Figure 29", ["10-Q Figure 29", "six months ended June 30, 2026 column"])
    d.add("<h3>The definition gap: home equity</h3>")
    d.add(table(["Date", "KeyCorp home equity ($m)", "Call Report home equity lines, 1.c.(1) ($000)", "Difference ($m)", "Call Report junior liens, 1.c.(2)(b)"],
                [[k, n0(v["he"]), n0(v["heloc"]), n1(v["he"] - v["heloc"] / 1000), n0(v["junior"])] for k, v in (("31 Dec 2025", e25), ("30 Jun 2026", e26))]))
    d.add("<p>The difference is closed-end home equity loans. Junior liens on the whole Call Report are only $%sm, so at least $%sbn of KeyCorp's home equity "
          "loans are first liens, filed in 1.c.(2)(a) with residential mortgages. The tool's \"Home equity\" is lines only, and its \"Mortgage\" is first liens "
          "including those loans. Internal home equity on KeyCorp's definition will not match either public series.</p>"
          % (n0(e26["junior"] / 1000), n2((e26["he"] * 1000 - e26["heloc"] - e26["junior"]) / 1e6)))
    d.add('<div class="fix"><b>Recommended fix.</b> In the internal import (docs/INTERNAL-IMPORT.md, on the design branch), name the two reconciling items as exclusions: '
          'discontinued education loans and residential loans held for sale. That is exactly the "filed, less named exclusions, against internal" check the firm described. '
          'For home equity, either supply internal home equity split into lines and loans (lines compare with 1.c.(1)), or compare internal mortgage plus home equity '
          'with filed 1.c.(1) + 1.c.(2)(a) + 1.c.(2)(b) + residential held for sale. The entity gap itself is not worth a separate adjustment: cards tie directly, '
          'and the rest ties once the two items are added.</div>')
    d.add("<h3>Figures</h3>" + figtable(by_gap[6]))

    # ------------------------------------------------------------------ gap 7
    d.add('<h2 class="gap">Gap 7 · Auto</h2>')
    d.add("<p><b>The question.</b> KeyBank files 62,212 ($000) of auto loans. The firm says KeyBank has direct auto inside internal other consumer. Where "
          "is direct auto filed, and do auto leases matter for the peers?</p>")
    d.add('<div class="answer"><b>RC-C 6.c ties at 62,212, and by the instructions it must hold every direct and indirect consumer loan to buy a car.</b> '
          'Where any larger direct-auto book sits <b>COULD NOT</b> be settled from public data: KeyCorp never states a direct auto balance. What the instructions '
          'do settle is what belongs where: boats, RVs, motorcycles, cash loans against a car the borrower already owns, and loans not mainly for buying a car '
          'go in 6.d, not 6.c. That is one possible home for the firm\'s "some random other stuff" (KeyCorp\'s 10-K says its consumer collateral includes '
          '"automobiles, boats, and RVs"), but it is not the only explanation for an internal figure above 62,212: the internal data is KeyCorp\'s and was not '
          'examined here, so entity scope or an internal definition could account for a difference too.</div>')
    d.img("g7-instr-rcc-6c", "RC-C instructions item 6.c", ["FFIEC 031 and 041 instructions", "Schedule RC-C Part I, item 6.c", "page RC-C-13 (3-17)"])
    d.img("g7-keybank-rcc-6c-10a", "KeyBank RC-C 6.c and 10.a", ["KeyBank", "Report date 6/30/2026", "6.c RCFDK137 = 62,212", "10.a RCFDF162 = 0"])
    d.img("g7-10k-collateral", "KeyCorp 10-K collateral sentence", ["KeyCorp 10-K 2025", "Note 4: consumer loan collateral"], width="90%")
    d.add("<h3>What happened to KeyBank's filed auto book</h3>")
    kh = [r for r in g7["keybank_history"] if r["q"][4:] == "1231" or r["q"] in ("20210630", "20210930", "20260630")]
    d.add(table(["Quarter", "Auto 6.c ($000)", "Other consumer 6.d", "Other revolving 6.b", "All consumer"],
                [[r["q"][:4] + "Q%d" % ((int(r["q"][4:6]) - 1) // 3 + 1), n0(r["auto"]), n0(r["other"]), n0(r["rev"]), n0(r["con"])] for r in kh]))
    d.add("<p>The auto line ran from $2.7bn (2016, after First Niagara) to $5.1bn, then fell from $3.80bn to $0.15bn in 2021Q3. KeyBank securitized and "
          "sold the indirect book and kept $%sbn of the asset-backed notes as held-to-maturity securities. The 10-K's \"senior notes from a securitization "
          "collateralized by sold indirect auto loans\" are down to $74m (Dec 2025) and $16m (Jun 2026). What is left in 6.c is a run-off book of $62m.</p>"
          % n2(g7["abs_auto_2021q3"] / 1e6))
    d.img("g7-keybank-rcc-6c-jun21", "KeyBank RC-C 6.c June 2021", ["KeyBank", "Report date 6/30/2021", "6.c = 3,804,433"])
    d.img("g7-keybank-rcc-6c-sep21", "KeyBank RC-C 6.c September 2021", ["KeyBank", "Report date 9/30/2021", "6.c = 152,093"])
    d.img("g7-keybank-rcb-m5c-sep21", "KeyBank RC-B M.5.c", ["KeyBank", "Report date 9/30/2021", "Schedule RC-B Memoranda 5.c", "ABS: automobile loans, HTM = 2,824,525"])
    d.add("<h3>Consumer leases (RC-C 10.a) across the roster, 30 June 2026 ($000, as filed)</h3>")
    d.add(table(["Bank", "Auto loans 6.c", "Consumer leases 10.a", "Leases ÷ (loans + leases), upper bound", "Lease charge-offs YTD (RI-B 8.a)", "Auto charge-offs YTD (RI-B 5.b)"],
                [[x["bank"], n0(x["auto"]), n0(x["leases"]), pct(x["leases"], x["auto"] + x["leases"]) if x["auto"] + x["leases"] else "n/a",
                  n0(x["lease_co"]), n0(x["auto_co"])] for x in g7["leases"]]))
    d.img("g7-usbank-rcc-6c-10a", "U.S. Bank RC-C 6.c and 10.a", ["U.S. Bank", "Report date 6/30/2026", "6.c = 3,248,165", "10.a = 4,087,388"])
    d.add("<p>Only U.S. Bank and Bank of America file consumer leases. Item 10.a holds every lease to an individual for personal use, not only cars, "
          "and neither filing splits it, so the share is an upper bound on auto leasing. The other 14 file zero, and since consumer auto leases belong in 10.a, "
          "they have none. The auto rate stays internally consistent: lease charge-offs are on RI-B 8.a, "
          "outside the rate's top line, just as leases are outside its bottom line. The FDIC API has no field for 10.a (searched: 2,378 fields), so the tool "
          "cannot carry it. Separately, KeyBank's filed auto is a $62m run-off book, while 12 of the 15 peers hold auto books of $1.3bn to $89bn (Regions, Zions and Citi hold little or none). Peer "
          "and industry auto rates describe a different business from KeyBank's direct auto, and KeyBank's own filed auto history is three different books "
          "in sequence.</p>")
    d.add('<div class="fix"><b>Recommended fix.</b> On site, put internal direct auto at 30 Jun 2026 beside 62,212. If it is larger, list what the internal segment holds '
          '(car-purchase loans, boats and RVs, cash loans against owned cars, anything booked outside KeyBank, N.A.) before assigning the difference to a filed line; '
          'only the car-purchase loans of KeyBank, N.A. belong in 6.c. Set direct auto\'s thresholds on internal data, '
          'with peers and industry as context only, and do not use KeyBank\'s filed auto history before 2021Q4. Note on the peer view that U.S. Bank\'s and Bank '
          'of America\'s auto figures leave out any car leases, which sit in their consumer lease lines (10.a, not split by asset).</div>')
    d.add("<h3>Figures</h3>" + figtable(by_gap[7][:3] + by_gap[7][18:]))
    d.add("<p>The other 15 gap-7 figures are the peers' auto loans, the tool's cache against each filing: all TIED.</p>")

    # ------------------------------------------------------------------ run it
    d.add('<h2 class="gap">How to run it yourself</h2>')
    d.add("<p>Every step uses the real values. <b>Run every command from the <code>threshold-engine/</code> folder</b>, with the package installed "
          "(<code>pip install -e .</code>); every output goes under <code>work/</code>. The scripts need Python 3.11+, <code>openpyxl</code>, "
          "<code>pdfplumber</code>, <code>Pillow</code>, <code>playwright</code> and poppler's <code>pdftoppm</code>. Steps 1, 2 and 4 re-derive every "
          "figure; step 5 rebuilds this document; steps 3 and 6 are checks by hand.</p>")
    d.add("""<ol>
<li>The tool's own data, with the commands the README gives (Auto added):
<pre>threshold-engine peers pull --cache work/fdic-cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --mergers 2005-10-01 --delinquency yes
threshold-engine peers build work/peers.xlsx --cache work/fdic-cache --roster config/peers.json --series-dir work/peer-series --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --mergers work/fdic-cache/mergers.json --extra-acquisitions 6672=2022Q2 --delinquency yes --industry-combined --jump 0.25 --min-book 1000000 --exempt-self yes --pack all --min-banks 5 --rank-by net --last-n 20 --min-obs 12 --base-quarter 2019Q4 --index-min-book 500000 --lagged-years 2019 2025 --lag-years 2 --normalisation-years 2019 2025 --mix-base-year 2019</pre></li>
<li>The independent sources (27 filed Call Reports from the FFIEC CDR, FDIC API responses, KeyCorp's 10-K and 10-Q, the QBP, the instructions, the H.8):
<pre>python docs/tie-out/comparability-2026-10/scripts/fetch_sources.py --sources work/sources --user-agent "Firm name you@example.com"</pre>
The SEC refuses an automated request that does not name a contact, so the runner supplies their own.
Every URL is written to <code>work/sources/urls.txt</code>. One filing by hand: open
<code>https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call&amp;idType=fdiccert&amp;id=17534&amp;date=06302026</code>, press <i>Download PDF</i>,
go to Schedule RC-N on report page 45, and read item 11.b column B: <b>69,414</b>.</li>
<li>One API call by hand, the guaranteed-loan fields for KeyBank:
<pre>curl -s "https://api.fdic.gov/banks/financials?filters=CERT:17534%20AND%20REPDTE:20260630&amp;fields=CERT,REPDTE,P9GTYPAR,P9GTY,P9GTYGNM,P9RERSFM&amp;format=json"</pre>
It returns <code>P9GTYPAR 69414, P9GTY 0, P9GTYGNM 69414, P9RERSFM 15000</code>.</li>
<li>Every figure and verdict:
<pre>python docs/tie-out/comparability-2026-10/scripts/collect.py --sources work/sources --cache work/fdic-cache --series work/peer-series --roster config/peers.json --engine src --out work/figures.json</pre>
It prints <code>figures: 147  {'TIED': 131, 'DIFFERS': 13, 'COULD NOT': 3}</code> and lists the 16 that are not TIED.</li>
<li>The photographs, then this document (canon checks it on the way through and refuses an unmarked source picture):
<pre>python docs/tie-out/comparability-2026-10/scripts/capture.py --sources work/sources --out work/images --chrome "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
python docs/tie-out/comparability-2026-10/scripts/build_exhibit.py --figures work/figures.json --images work/images --series work/peer-series --qbp work/qbp-card.json --canon %USERPROFILE%\\.claude\\plugins\\cache\\satc\\canon\\1.22.0 --chrome "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --out work/TIE-OUT-comparability-2026-10.pdf</pre>
<code>work/qbp-card.json</code> is written by <code>collect.py</code> beside <code>work/figures.json</code>.</li>
<li>Check one KeyCorp figure by hand: in the 10-K at <code>https://www.sec.gov/Archives/edgar/data/91576/000162828026010546/key-20251231.htm</code>, find
"Figure 9. Composition of Loans": other consumer loans 4,644. Add footnote (c)'s $205 million: 4,849. KeyBank's 31 Dec 2025 Call Report, RC-C 6.b + 6.c + 6.d:
288,376 + 65,960 + 4,493,814 = <b>4,848,150</b> ($000).</li>
</ol>""")

    # ------------------------------------------------------------------ found / wrong / not proven
    d.add('<h2 data-tieout="what-it-found">What it found</h2>')
    d.add("""<ul>
<li><b>A defect in the tool's industry series.</b> Year-to-date differencing counts an absorbed affiliate's charge-offs twice in the merger quarter: six card
quarters, $74m to $4.8bn each, and the industry card rate up to 0.71 pts high for four quarters after each. The same mechanism lifts
Wells Fargo's own card rate by about 0.4 pts for four quarters of 2010–11, inside the pack composite. No test could catch it, because every input value is right. Only putting the series beside the
FDIC's own totals showed it.</li>
<li><b>The jump rule misses 60 material acquisition quarters</b>, up to 27% of a book. The merger record is pulled but used only for the Balances index.</li>
<li><b>Right value, wrong citation, twice.</b> The government-guaranteed lines are RC-N items 11 to 11.b, not 10 and 10.a. The FDIC's field names for them read
the wrong way round (P9GTYPAR is item 11; P9GTY is 11.a).</li>
<li><b>KeyCorp counts rebooked GNMA loans as current; the Call Report counts them as 90+ accruing.</b> Internal and filed 90+ differ by design, by about $5m
for residential at June 2026.</li>
<li><b>KeyCorp's "home equity" is not the Call Report's.</b> About $2.5bn of closed-end home equity loans are filed with mortgages, so the internal import cannot
map home equity one-to-one.</li>
<li><b>KeyBank's filed auto line was emptied by a sale in 2021Q3</b> (6.c down $3.65bn in the quarter; $2.82bn of auto asset-backed notes kept). 62,212 is a run-off book.</li>
<li><b>The tool's industry total is the FDIC's own</b>, to the published precision on every figure tried, and the tool reads every filed value it was set beside
correctly: 131 of 131 TIED figures.</li>
</ul>""")
    d.add('<h2 data-tieout="what-i-got-wrong">What I got wrong</h2>')
    d.add("""<ul>
<li><b>I first read the QBP's rebooked-GNMA rows wrong.</b> The block below it reuses the same row labels, and my parser let the next block overwrite them: it
reported 49.9 ($m) where the sheet says 11,701.511. The composition table in the same sheet (GNMA 9.5% of noncurrent loans, about $12bn) disagreed, which is what
caught it. The parser now refuses a label that appears twice in one block.</li>
<li><b>My first count of uncaught acquisitions was 57, and one was an artefact.</b> Capital One's 2007 card row: the acquired card book never reached the
acquirer's card line, so nothing entered its rate. I also briefly narrowed the definition of "material" in the script, which dropped ten caught cases from the
denominator; restored, the count was 149, with 93 caught.</li>
<li><b>I then tested each absorbed bank on its own, and the review caught it.</b> An acquirer that absorbs several banks in one quarter takes in their
combined book: PNC's eleven 2007Q3 mortgage acquisitions are each under 5% and 16.5% together. Counted by acquirer, quarter and product, 130 cases are
material and 60 slip the rule, against 149 and 56 counted bank by bank.</li>
<li><b>My first guess at the 2019 card overcount's size was 0.13 pts. It is 0.09.</b> I reasoned from memory of Chase Bank USA's size before measuring;
the measured number is what is reported.</li>
<li><b>I first blocked on the network and nearly used the repository's saved FDIC data as a stand-in.</b> That would have tied the tool's copy against an
earlier copy of the same feed. The firm opened the network instead, and nothing from the repository's saved data is used as a source here.</li>
<li><b>The gap-6 photographs of KeyCorp's figures are cut from the HTML filing</b>, rendered in Chromium, not from a printed PDF. The numbers were read twice,
from the rendered table and from the filing's text, and agree.</li>
</ul>""")
    d.add('<h2 data-tieout="what-this-does-not-prove">What this does not prove</h2>')
    d.add("""<ul>
<li><b>The workbook was not opened.</b> The tool's side of every figure is its cache (<code>peers pull</code>) or its series CSVs (<code>peers build</code>), not
cells in <code>peers.xlsx</code> or the main workbook. The CSVs are what <code>workbook</code> reads; the hop into Excel was tied once, on 12 Oct 2026, for one card
figure, and is assumed here. The build ran in a Linux container, not on the firm's Windows machine with Excel.</li>
<li><b>The guaranteed-loan fields (P9GTY…) are not in the tool's cache.</b> Those comparisons are FDIC API against filing, because the tool does not pull them.</li>
<li><b>Item 11 is not split by loan type</b>, so the peers' GNMA share of mortgage 90+ is an upper bound. Only KeyBank's split is known, from KeyCorp's 10-Q.</li>
<li><b>Item 10.a is not split by asset</b>, so U.S. Bank's and Bank of America's lease shares are upper bounds on auto leasing, not measures of it.</li>
<li><b>Nonaccrual practice was measured for cards only.</b> The same exception covers every consumer product and 1-4 family mortgage; other consumer, auto and
mortgage nonaccrual may be just as policy-driven, and were not tested.</li>
<li><b>The 2010 mix effect (+%.2f pts) is an estimate</b> on quarterly, quarter-end balances. It holds each group's rate fixed, which is a modelling choice.</li>
<li><b>The 2008–09 mortgage and home-equity understatement was measured, not explained.</b> WaMu and Wachovia fit the timing; no filing was read to prove it.</li>
<li><b>KeyBank's June 2026 GNMA difference (~$10m) is not explained.</b> The two documents define the population differently; the reconciliation was not done.</li>
<li><b>The peer median is not tied</b>: no one publishes it. Its inputs were tied for one bank and one product.</li>
<li><b>Where direct auto beyond 62,212 is filed</b> needs the internal figure, which this tie-out may not use.</li>
<li><b>Delinquency against the median was not compared</b>, only TTM net charge-off rates. The acquisition analysis covers the 16 roster banks since October 2005 only.</li>
<li><b>Seven acquisitions had no filing in the cache</b> (acquired banks that filed no Call Report the tool pulled, such as thrifts before 2012) and were not measured.</li>
</ul>""" % g3["mix_effect"])

    # ------------------------------------------------------------------ appendix
    d.add('<h2 class="gap">Every figure (%d)</h2>' % total)
    d.add(figtable(figs))

    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Comparability Tie-Out</title><style>%s</style></head><body>%s</body></html>' % (CSS, "\n".join(d.parts)))
    sys.path.insert(0, a.canon)
    import check_tie_out
    import tempfile
    with tempfile.TemporaryDirectory() as scratch:      # canon writes the page it renders here, not beside the PDF
        check_tie_out.render(page, Path(a.out).resolve(), what="the comparability tie-out", chrome=a.chrome, scratch=scratch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
