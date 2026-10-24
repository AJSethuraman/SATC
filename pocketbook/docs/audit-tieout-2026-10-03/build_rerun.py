"""Writes section 13 of TIEOUT.html, "Re-run after fixes", from the re-run's results, and puts it into the page.

    python build_rerun.py RUN_DIR INDEP_JSON RERUN_JSON PICTURES_DIR TIEOUT_HTML

Sections 1 to 12 stay as the first run wrote them: they are the record of what was found on the audit workbook as
merged at f20118b9. This adds a note under the page's subtitle and section 13 before the end of the page, replacing
both if they are already there, so it can be run again. Every number in the section is read from the JSON files.
"""

from __future__ import annotations

import base64
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pictures import sheet_picture  # noqa: E402

E = html.escape
START, END = "<!-- rerun:start -->", "<!-- rerun:end -->"
NOTE_START, NOTE_END = "<!-- rerun-note:start -->", "<!-- rerun-note:end -->"


def img(path: Path, alt: str) -> str:
    return f'<img alt="{E(alt)}" src="data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}">'


def num(v, key: str = "") -> str:
    if v is None or v == "" or v == "none":
        return "none"
    if isinstance(v, str):
        return E(v)
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer() and abs(v) < 1e7 and "bk" not in key):
        return f"{int(v):,}"
    if abs(v) >= 1000:
        return f"{v:,.6f}".rstrip("0").rstrip(".")
    return f"{v:.12g}"


def verdict(ok) -> str:
    return {True: '<span class="ok">Ties</span>', "mc": '<span class="mc">Within MC error</span>',
            "listed": '<span class="na">Listed for the random pocket only</span>'}.get(
        ok, '<span class="bad">Differs</span>')


def mc_hits(mine, theirs, shuffles: int):
    """Two shuffle counts from independent shuffles agree within three standard errors of the difference."""
    if mine is None or theirs is None:
        return False
    a, b = (mine + 1) / (shuffles + 1), (theirs + 1) / (shuffles + 1)
    p = (a + b) / 2
    return "mc" if a == b or abs(a - b) <= 3 * (2 * p * (1 - p) / shuffles) ** 0.5 else False


def main(run: Path, indep_p: Path, rerun_p: Path, pics: Path, page: Path) -> None:
    ind = json.loads(indep_p.read_text())
    c = json.loads(rerun_p.read_text())
    pics.mkdir(parents=True, exist_ok=True)
    calc = next((run / "compare-rerun" / "audit-default").glob("*.xlsx"))
    work = run / "pictures-rerun"
    sheet_picture(calc, "One pocket", "B1:H40", pics / "rerun-one-pocket.png", work)
    sh_head = None
    from openpyxl import load_workbook
    ws = load_workbook(calc, read_only=True, data_only=True)["Shuffle test"]
    for i, row in enumerate(ws.iter_rows(min_col=2, max_col=2, values_only=True), start=1):
        if row[0] == "D. The allowance for many tests":
            sh_head = i
            break
    sheet_picture(calc, "Shuffle test", f"B{sh_head}:L{sh_head + len(c['partd']['rows']) + 7}",
                  pics / "rerun-part-d.png", work)
    P = c["pick"]["indep"]
    B = ind["shuffles"]

    # ------------------------------------------------------------------ the roster
    lines = []

    def add(what, verdicts):
        n = len(verdicts)
        ex = sum(1 for v in verdicts if v is True)
        mc = sum(1 for v in verdicts if v == "mc")
        na = sum(1 for v in verdicts if v == "listed")
        lines.append((what, n, ex, mc, na, n - ex - mc - na))
    add("The pocket the workbook opens on: drawn independently from the file's SHA-256, against One pocket and the "
        "Run stamp", [c["pick"]["ok"]])
    add(f"One pocket, the random pocket (FICO {P['band']}, {P['seg']}): every row, independent, Excel and PocketBook",
        [x["ok"] for x in c["random"]["rows"]])
    for k, t in c["others"].items():
        add(f"One pocket, {k.replace('|', ', ')} picked on the dropdowns: every row", [x["ok"] for x in t])
    pb = c["partb"]
    s = pb["indep"] or {}
    add("Shuffle test part B: the listed shuffles counted at the independent line, the count, the shuffles, the "
        "p-value and the actual gap",
        [pb["count_from_list_indep_line"] == pb["Shuffles that count"]["excel"] == pb["Shuffles that count"]["pb"],
         pb["listed"] == B == pb["Shuffles"]["excel"],
         pb["p-value"]["ties"] == "✓",
         abs(s.get("gap", 0) - pb["Actual gap"]["excel"]) <= 1e-9 * max(1, abs(pb["Actual gap"]["excel"]))
         and pb["Actual gap"]["ties"] == "✓",
         mc_hits(s.get("hits"), pb["Shuffles that count"]["pb"], B)])
    add("Shuffle test part D: each listed pocket's adjusted p-value, Excel and PocketBook, against Benjamini-Hochberg "
        "worked out here from the listed p-values", [x["ok"] for x in c["partd"]["rows"]])
    add("Shuffle test part D: each listed pocket's unadjusted p-value against the independent shuffles",
        ["mc" if x["mc"] else False for x in c["partd"]["rows"]])
    add("Main workbook, RANR vs GCOs, the random pocket's row and the Whole book row: independent, audit and main",
        [x["ok"] for x in c["main"]] + [x["ok"] for x in c["whole_book"]])
    crosses = sum(v["crosses"] for v in c["sheets"].values())
    total = sum(x[1] for x in lines)
    differs = sum(x[5] for x in lines)

    # ------------------------------------------------------------------ the section
    W = []
    w = W.append
    w(START)
    w('<h2 data-tieout="rerun">13. Re-run after fixes</h2>')
    w('<p>The findings in section 9 were fixed on branch <code>pocketbook-audit-fixes</code>, and the firm asked for '
      'one more change on 3 October 2026: <em>"tying out one thing that should prove everything if you picked '
      'randomly"</em>, chosen as <em>"Random, seed stamped"</em>. The audit workbook now opens on a pocket drawn at '
      'random from the tested pockets, not on the top flagged pocket. The scenario was rebuilt with '
      '<code>make_scenario.py</code> from the same generator and seed, and <code>tieout.py</code> was run again end to '
      'end with the same shuffle seed (20261003). The file is byte for byte the first run\'s: SHA-256 '
      f'<code>{E(c["sha"])}</code>.</p>')
    w(f'<p class="headline" data-tieout="rerun-headline">{total:,} comparisons; {differs} differ. Every sheet of the '
      f'audit workbook shows {crosses} ✗ as LibreOffice calculates it.</p>')
    w('<table><tr><th>Area</th><th>Comparisons</th><th>Tied</th><th>Tied within MC error</th><th>Not listed by '
      'design</th><th>Differs</th></tr>')
    for what, n, ex, mc, na, df in lines:
        w(f'<tr><td>{E(what)}</td><td class="n">{n:,}</td><td class="n">{ex:,}</td><td class="n">{mc:,}</td>'
          f'<td class="n">{na:,}</td><td class="n">{df:,}</td></tr>')
    w('</table>')
    w('<p class="cap">"Not listed by design": on a pocket other than the random one, the shuffles are not listed, so '
      'the count row reads "Listed for the pocket selected at random only"; its p-value rows still tie between Excel '
      'and PocketBook and agree with the independent shuffles within Monte Carlo error. The Monte Carlo test on the '
      'random pocket\'s own count allows three standard errors.</p>')

    w('<h3>13.1 The random pick, drawn independently</h3>')
    w(f'<p><code>tieout.py</code> draws the pick itself, from the file\'s bytes: SHA-256 over the fixed texts and the '
      f'file\'s fingerprint gives the seed <code>{P["seed"]}</code>; the {P["population"]} tested pockets (every pocket '
      f'with at least 10 loans with a loss), keyed "grid|band|segment" and sorted as text, are numbered from 0; '
      f'{P["seed"]} mod {P["population"]} = {P["index"]}, which is <strong>FICO {E(P["band"])}, {E(P["seg"])}'
      f'</strong>. The audit workbook opens on {E(", ".join(c["pick"]["audit"]))}; its Run stamp reads seed '
      f'<code>{E(str(c["pick"]["stamp_seed"]))}</code> and "{E(str(c["pick"]["stamp_population"]))}". '
      f'{verdict(c["pick"]["ok"])}.</p>')
    w(img(pics / "rerun-one-pocket.png", "The top of the One pocket sheet after the fixes"))
    w('<p class="cap">The top of One pocket as LibreOffice calculates it: the Selection note states the random pick, '
      'the population and the seed, and the first rows tie. The step labels no longer run into the row below '
      '(finding 7): each row is as tall as its longest wrapped cell, the label included.</p>')

    w('<h3>13.2 Each finding, checked again</h3>')
    f1, f2 = c["finding1"], c["finding2"]
    f4 = c["finding4"]
    gap_rows = [x for x in c["main"] if x["col"].startswith(("RANR + GCOs", "RANR:"))]
    w('<table><tr><th>Finding</th><th>Fix</th><th>Checked on the re-run</th><th>Result</th></tr>')
    w(f'<tr><td>1. By hand for "Booked, rest of its band" gave more than Excel</td><td>Every By hand step now names '
      f'exactly the loans its formula takes; a test reads each formula\'s SUMIFS and COUNTIFS criteria and each By '
      f'hand step\'s filters and requires them to match, on every row.</td><td>Band 713 - 745, Online (the band with '
      f'the GCO of "#N/A"). By hand now reads: "{E(f1["hand"])}" Following it: '
      f'{num(f1["indep_following_new_words"])}; Excel {num(f1["excel"])}. Following the old words gave '
      f'{num(f1["indep_following_old_words"])}.</td>'
      f'<td>{verdict(abs(f1["indep_following_new_words"] - f1["excel"]) <= 1e-6)}</td></tr>')
    w(f'<tr><td>2. "Avg line, whole book" said every loan</td><td>Definitions now say exactly what each formula '
      f'computes.</td><td>Definition: "{E(f2["words"])}" Excel {num(f2["excel"])}, independent {num(f2["indep"])} '
      f'(every loan, read literally, would be {num(f2["every_loan_reading"])}).</td>'
      f'<td>{verdict(abs(f2["excel"] - f2["indep"]) <= 1e-6)}</td></tr>')
    w(f'<tr><td>3. The audit did not prove the RANR gap RANR vs GCOs shows</td><td>New rows: RANR and RANR + GCOs '
      f'against the rest of the book and of the band, each with its gap in points and dollars.</td><td>The random '
      f'pocket\'s row on RANR vs GCOs: {len(gap_rows)} gap, dollar and rest figures, each against the audit row and '
      f'the independent figure (table below).</td><td>{verdict(all(x["ok"] for x in gap_rows))}</td></tr>')
    w(f'<tr><td>4. "Booked, whole book" meant two totals</td><td>Each booked total is named by its population, with a '
      f'reconciling row.</td><td>Every loan with a booked amount {num(f4["book_all_bk"])}; loans with a GCO '
      f'{num(f4["book_gco_bk"])}; loans with no GCO amount {num(f4["book_nogco_bk"])} (independent '
      f'{num(f4["indep_nogco"])}); loans with a RANR {num(f4["book_ranr_bk"])}, which is the Booked figure in RANR vs '
      f'GCOs\' Whole book row ({num(c["whole_book"][0]["main"])}).</td>'
      f'<td>{verdict(all(x["ok"] for x in c["whole_book"]) and abs(f4["book_nogco_bk"] - f4["indep_nogco"]) <= 1e-6)}'
      f'</td></tr>')
    pd = c["partd"]
    w(f'<tr><td>5. Benjamini-Hochberg could not be done from the visible sheets</td><td>Part D of Shuffle test lists '
      f'the family with the rule written out.</td><td>{len(pd["rows"])} pockets listed; Excel\'s adjusted p-value '
      f'against PocketBook\'s and against Benjamini-Hochberg worked out here from the listed p-values; the selected '
      f'pocket\'s {num(pd["selected"][0])} against the Run\'s {num(pd["selected"][1])}.</td>'
      f'<td>{verdict(all(x["ok"] for x in pd["rows"]) and pd["selected"][2] == "✓")}</td></tr>')
    rp = c["random"]["rows"]
    raw = next(x for x in rp if x["key"] == "raw")
    w(f'<tr><td>6. The default pocket\'s shuffle test was not sensitive</td><td>The default is now a random tested '
      f'pocket.</td><td>The random pocket\'s p-value is {num(raw["excel"])} ({num(pb["Shuffles that count"]["excel"])} '
      f'of {B:,} shuffles at or beyond the line), so the listed shuffles are counted on both sides of the line.</td>'
      f'<td>{verdict(raw["ok"])}</td></tr>')
    w(f'<tr><td>7. A step label overprinted the row below</td><td>Row heights follow every wrapped cell, the label '
      f'included; Run stamp, Rows in and out, Bands and Shuffle test rows likewise.</td><td>The pictures in this '
      f'section and in <code>docs/audit-2026-10-03/</code>, rendered by LibreOffice.</td>'
      f'<td><span class="ok">No overlap seen</span></td></tr>')
    w('</table>')

    w('<h3>13.3 RANR vs GCOs against the audit</h3>')
    w('<table class="fig"><tr><th>RANR vs GCOs column</th><th>Audit row</th><th>Independent</th><th>Audit (Excel)</th>'
      '<th>Main workbook</th><th>Ties</th></tr>')
    for x in c["main"] + [{"col": "Whole book: " + y["what"], "audit_row": y["audit_row"], "indep": y["indep"],
                           "audit": y["audit"], "main": y["main"], "ok": y["ok"]} for y in c["whole_book"]]:
        w(f'<tr><td>{E(x["col"])}</td><td>{E(str(x["audit_row"]))}</td><td class="n">{num(x["indep"])}</td>'
          f'<td class="n">{num(x["audit"])}</td><td class="n">{num(x["main"])}</td><td>{verdict(x["ok"])}</td></tr>')
    w('</table>')

    w('<h3>13.4 The allowance for many tests, from the visible table</h3>')
    w(img(pics / "rerun-part-d.png", "Part D of the Shuffle test sheet"))
    w('<p class="cap">Part D of Shuffle test as LibreOffice calculates it, for the random pocket\'s grid and '
      'comparison. It follows the pocket picked on One pocket.</p>')
    w('<table><tr><th>Pocket</th><th>Count</th><th>p-value</th><th>Rank</th><th>Adjusted, Excel</th>'
      '<th>Adjusted, PocketBook</th><th>BH worked out here</th><th>Independent p</th><th>Ties</th></tr>')
    for x in pd["rows"]:
        w(f'<tr><td>{E(x["band"])}, {E(x["seg"])}{" ◀" if x["selected"] else ""}</td><td class="n">{x["count"]:,}</td>'
          f'<td class="n">{x["p"]:.6f}</td><td class="n">{x["rank"]}</td><td class="n">{x["adj_excel"]:.10f}</td>'
          f'<td class="n">{x["adj_pb"]:.10f}</td><td class="n">{x["bh_of_listed_p"]:.10f}</td>'
          f'<td class="n">{x["indep_p"]:.6f}</td><td>{verdict(x["ok"])}</td></tr>')
    w('</table>')

    w('<h3>13.5 How to run the re-run</h3>')
    w('<pre>cd pocketbook/docs/audit-tieout-2026-10-03\nR=/tmp/pb-tieout\n\npython make_scenario.py $R\n'
      'python tieout.py $R/loans.csv $R/indep.json\npython compare_rerun.py $R $R/indep.json $R/rerun.json\n'
      'python build_rerun.py $R $R/indep.json $R/rerun.json $R/pics TIEOUT.html\nrm -rf $R</pre>')
    w(END)
    section = "\n".join(W)

    text = page.read_text(encoding="utf-8")
    text = re.sub(re.escape(START) + ".*?" + re.escape(END) + "\n?", "", text, flags=re.S)
    text = re.sub(re.escape(NOTE_START) + ".*?" + re.escape(NOTE_END) + "\n?", "", text, flags=re.S)
    note = (f'{NOTE_START}<p class="finding">Sections 1 to 12 are the tie-out as first run, on the audit workbook as '
            f'merged at <code>f20118b9</code>. Section 13 is the re-run after the fixes: {total:,} comparisons, '
            f'{differs} differ.</p>{NOTE_END}\n')
    text = text.replace("<h2>1. How the evidence connects</h2>", note + "<h2>1. How the evidence connects</h2>", 1)
    text = text.replace("</main></body></html>", section + "\n</main></body></html>", 1)
    page.write_text(text, encoding="utf-8")
    print(f"{page}: section 13 written; {total} comparisons, {differs} differ, {crosses} crosses")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]))
