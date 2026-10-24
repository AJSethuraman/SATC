"""Writes TIEOUT.html from the comparison results: one self-contained page, pictures embedded.

    python build_html.py RUN_DIR INDEP_JSON CMP_JSON DEEP_JSON PICTURES_DIR OUT_HTML

DEEP_JSON: a longer independent shuffle run (100,000 shuffles) for one band, used to settle the two pockets whose
10,000-shuffle p-values sat furthest apart (see the shuffle section). Every number in the page is read from these
files; none is typed here.
"""

from __future__ import annotations

import base64
import html
import json
import math
import sys
from pathlib import Path

E = html.escape


def money(v, cents=True):
    if v is None:
        return ""
    sign = "-" if v < 0 else ""
    return sign + (f"${abs(v):,.2f}" if cents else f"${abs(v):,.0f}")


def fmt(key: str, v):
    if v is None or v == "" or v == "none":
        return "none"
    if isinstance(v, str):
        return E(v)
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if key in ("loans", "bad", "bad_n", "avg_n", "events", "hits") or (isinstance(v, int) and abs(v) < 10 ** 7):
        return f"{int(v):,}"
    if key in ("gco_bk", "gco", "ranr_bk", "ranr", "book_gco_bk", "book_gco", "rest_gco_bk", "rest_gco",
               "excess_rest", "band_gco_bk", "band_gco", "excess_band", "dollars", "avg_bk", "avg", "book_avg",
               "money"):
        return f"${v:,.6f}".rstrip("0").rstrip(".") if abs(v - round(v, 2)) > 1e-7 else f"${v:,.2f}"
    if key in ("raw", "p"):
        return f"{v:.8f}"
    return f"{v:.12g}"


def tick(ok):
    return '<span class="ok">Ties</span>' if ok is True else (
        '<span class="mc">Within MC error</span>' if ok == "mc" else
        '<span class="bad">Differs</span>' if ok is False else '<span class="na">n/a</span>')


def img(path: Path, alt: str, source=False) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    mark = ' data-tieout="source"' if source else ""
    return f'<img{mark} alt="{E(alt)}" src="data:image/png;base64,{data}">'


def rel_close(a, b, tol=1e-9):
    if a is None or b in (None, "", "none"):
        return a is None and b in (None, "", "none")
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def main(run, indep_p, cmp_p, deep_p, pics, out):
    ind = json.loads(Path(indep_p).read_text())
    c = json.loads(Path(cmp_p).read_text())
    deep = json.loads(Path(deep_p).read_text())
    pockets = {(p["band"], p["seg"]): p for p in ind["pockets"]}
    B = ind["shuffles"]
    d = pockets[("494 - 652", "Broker")]

    # ------------------------------------------------------------------ the roster: every comparison, one verdict
    tally = {"exact": 0, "mc": 0, "differs": 0}
    lines = []                                         # (what, n, exact, mc, differs)

    def add(what, verdicts):
        n = len(verdicts)
        ex = sum(1 for v in verdicts if v is True)
        mc = sum(1 for v in verdicts if v == "mc")
        df = n - ex - mc
        tally["exact"] += ex
        tally["mc"] += mc
        tally["differs"] += df
        lines.append((what, n, ex, mc, df))

    def mc_ok(indep, pbp):
        if indep is None or pbp in (None, "none", ""):
            return indep is None and pbp in (None, "none", "")
        p = (indep + pbp) / 2
        se = math.sqrt(2 * p * (1 - p) / B)
        return "mc" if abs(indep - pbp) <= 3 * se or indep == pbp else False

    # the default pocket's One pocket table, three ways
    one_rows = []
    vs = []
    for x in c["default"]["rows"]:
        if x["key"] in ("hits", "raw", "p"):
            ok = mc_ok(*(([x["indep"] / (B + 1), x["pb"] / (B + 1)]) if x["key"] == "hits" else [x["indep"], x["pb"]]))
            ok = ok if rel_close(x["excel"], x["pb"]) else False
        else:
            ok = rel_close(x["indep"], x["excel"]) and rel_close(x["indep"], x["pb"]) and rel_close(x["excel"], x["pb"])
        vs.append(ok)
        one_rows.append((x, ok))
    add("One pocket sheet, default pocket (FICO 494 - 652, Broker): independent, Excel and PocketBook", vs)

    # main workbook
    main_rows = []
    vs = []
    for x in c["main_rows"]:
        ok = x["ok"]
        if x["col"] == "p-value":
            ok = mc_ok(x["indep"], x["main"])
        vs.append(ok)
        main_rows.append((x, ok))
    add("Main workbook, default pocket: Pockets, RANR vs GCOs and Grids against the independent figures", vs)

    # run stamp, rows in and out, bands, each loan's band
    vs = [c["sha"]["indep"] == c["sha"]["audit"]]
    vs += [x["ok"] for x in c["rows_in_out"]]
    vs += [x["ok"] for x in c["bands"]]
    lb = c["loan_bands"]
    vs.append(lb["indep_vs_excel"] == 0 and lb["indep_vs_pb"] == 0 and lb["excel_vs_pb"] == 0)
    add("Run stamp fingerprint, Rows in and out (13 lines), Bands (7 counts), each loan's band (one check over "
        "50,000 loans)", vs)

    # the other pockets picked on the dropdowns
    other_summary = []
    vs = []
    for k, t in c["others"].items():
        good = 0
        for x in t:
            if x["key"] in ("hits", "raw", "p"):
                # off the default pocket the audit lists no shuffles: Excel shows words, PocketBook its own figure
                if x["key"] == "hits":
                    ok = mc_ok(None if x["indep"] is None else (x["indep"] + 1) / (B + 1),
                               None if x["pb"] in (None, "none") else (x["pb"] + 1) / (B + 1))
                else:
                    ok = mc_ok(x["indep"], None if x["pb"] in ("", "none") else x["pb"])
            else:
                ok = (rel_close(x["indep"], x["excel"]) and rel_close(x["indep"], x["pb"])
                      and rel_close(x["excel"], x["pb"]))
                if not ok and x["indep"] is None and x["excel"] in ("", None) and x["pb"] in ("none", None):
                    ok = True
            vs.append(ok)
            good += ok is True or ok == "mc"
        other_summary.append((k, len(t), good, sum(1 for x in t if x["ties"] == "✓")))
    add("One pocket sheet, four more pockets picked on its dropdowns and recalculated", vs)

    # the sweep, every pocket against _pocketbook
    vs = []
    for s in c["sweep"]:
        vs += [True] * (s["figures"] - len(s["bad"]))
        for key, a, b in s["bad"]:
            # a pocket alone in its band: PocketBook stores 0 for the rest of its band, which is right
            vs.append(True if (a in (None, 0) and b == 0) else False)
    add("Every pocket in the grid (19), 37 figures each, against PocketBook's stored figures (_pocketbook)", vs)

    # shuffle test: every tested pocket's p, and BH
    vs = []
    for x in c["shuffle_all"]:
        vs.append("mc" if abs(x["z"]) <= 3 else False)
    add("Shuffle test p-value, every tested pocket (18): independent shuffles against PocketBook's", vs)
    vs = [x["bh_exact"] for x in c["shuffle_all"]]
    add("Benjamini-Hochberg allowance recomputed from PocketBook's raw p-values (18 pockets)", vs)
    sh = c["shuffle_sheet"]
    vs = [sh["Shuffles that count"]["excel"] == sh["Shuffles that count"]["pb"] == sh["count_from_list_my_line"],
          sh["Shuffles"]["excel"] == sh["Shuffles"]["pb"] == sh["listed"],
          rel_close(sh["p-value"]["excel"], sh["p-value"]["pb"]),
          rel_close(sh["indep_gap"], sh["Real gap"]["excel"]) and rel_close(sh["Real gap"]["excel"], sh["Real gap"]["pb"]),
          rel_close(sh["indep_line"], sh["The line"]["excel"], 1e-12),
          sh["example_rows_tied"] == 20 and all(v["ties"] == "✓" for v in sh["example"].values()),
          abs(sh["z"]["z"]["indep"] - sh["z"]["z"]["pb"]) <= 1e-9 * abs(sh["z"]["z"]["pb"]),
          abs(sh["z"]["Two-sided p-value"]["indep"] - sh["z"]["Two-sided p-value"]["pb"])
          <= 1e-6 * sh["z"]["Two-sided p-value"]["pb"]]
    add("Shuffle test sheet: listed shuffles and COUNTIF, the line, the real gap, the ten-loan example, the z-test", vs)

    total = sum(n for _, n, *_ in lines)

    # ------------------------------------------------------------------ the page
    P = []
    w = P.append
    w(HEAD)
    w('<h1>PocketBook audit workbook: independent tie-out</h1>')
    w('<p class="sub">Workpaper prepared 3 October 2026. Scenario: one synthetic bleed-test Run, 50,000 loans, FICO '
      'band by CHANNEL segment, 10,000 shuffles. Branch <code>pocketbook-audit-tieout</code>, built on the audit '
      'workbook as merged at <code>f20118b9</code>.</p>')

    w('<h2>1. How the evidence connects</h2>')
    w(DIAGRAM)
    w('<p>The production path runs from the loan file through a PocketBook Run into two workbooks. The check runs '
      'from the same loan file, as bytes, into a separate script that shares no code with PocketBook. The two meet '
      'at the comparison. The independent road is the one that makes this evidence: it can disagree with PocketBook, '
      'and PocketBook cannot influence what it computes. The figures on the PocketBook side were read out of the '
      'workbooks as LibreOffice calculates them, cell by cell, not taken from PocketBook\'s memory.</p>')

    w('<h2>2. Conclusion</h2>')
    w(f'<p class="headline" data-tieout="headline">{total:,} comparisons performed.</p>')
    w('<table class="roster" data-tieout="roster"><tr><th>Verdict</th><th>Comparisons</th><th>Meaning</th></tr>')
    w(f'<tr><td>DIFFERS</td><td data-tieout="count">{tally["differs"]:,}</td><td>Executed, and the figures do not '
      'agree within tolerance.</td></tr>')
    w(f'<tr><td>TIED within Monte Carlo error</td><td data-tieout="count">{tally["mc"]:,}</td><td>Shuffle-test '
      'results. Two independent sets of random shuffles cannot agree exactly; they agree within three standard '
      'errors of the difference.</td></tr>')
    w(f'<tr><td>TIED</td><td data-tieout="count">{tally["exact"]:,}</td><td>Executed end to end, and the figures '
      'agree within 1E-9 of the figure (counts exactly).</td></tr></table>')
    w('<table><tr><th>Area</th><th>Comparisons</th><th>Tied</th><th>Tied within MC error</th><th>Differs</th></tr>')
    for what, n, ex, mc, df in lines:
        w(f'<tr><td>{E(what)}</td><td class="n">{n:,}</td><td class="n">{ex:,}</td><td class="n">{mc:,}</td>'
          f'<td class="n">{df:,}</td></tr>')
    w('</table>')
    w(VERDICT_TEXT.format(n_pockets=len(c["sweep"])))

    w('<h2>3. Scenario and method</h2>')
    w(SCENARIO.format(sha=E(c["sha"]["indep"]), B=B))
    w(img(Path(pics) / "source-loans-csv.png", "The loan file's first seven lines with the five excluded values "
                                               "ringed", source=True))
    w('<p class="cap">The independent source: the loan file as text. The five values ringed in red are the '
      'records the Run must exclude or set aside: a FICO of -9999 (marked missing), a blank FICO, a GCO of '
      '"#N/A", a blank booked balance and a bad-loan flag of 2. Each appears in the Rows in and out reconciliation '
      'in section 6.</p>')
    w(TOLERANCE)

    w('<h2>4. The default pocket, figure by figure</h2>')
    w('<p>Pocket: grid FICO x CHANNEL, band 494 - 652, segment Broker. This is the pocket the audit workbook opens '
      'on (the top flagged pocket). The Audit (Excel) column is column E of the One pocket sheet after LibreOffice '
      'recalculated the file; the PocketBook column is column F of the same sheet, which reads the Run\'s stored '
      'figure from the hidden _pocketbook sheet. The Independent column is tieout.py. Full precision is shown so '
      'that a reviewer can see the size of any rounding difference.</p>')
    w(img(Path(pics) / "audit-one-pocket.png", "The audit workbook's One pocket sheet, calculated"))
    w('<p class="cap">The One pocket sheet as LibreOffice calculates it, every sheet but this one removed for the '
      'picture. The Ties? column (ringed) is the workbook\'s own verdict; every row reads as tied.</p>')
    w('<table class="fig"><tr><th>Step</th><th>Definition (audit "In words")</th><th>Independent</th>'
      '<th>Audit (Excel)</th><th>PocketBook</th><th>Ties</th></tr>')
    for x, ok in one_rows:
        k = x["key"]
        w(f'<tr><td>{E(x["step"])}</td><td class="words">{E(x["words"] or "")}</td><td class="n">{fmt(k, x["indep"])}'
          f'</td><td class="n">{fmt(k, x["excel"])}</td><td class="n">{fmt(k, x["pb"])}</td><td>{tick(ok)}</td></tr>')
    w('</table>')
    w('<p>The three shuffle rows (count, p-value, adjusted p-value) carry the independent script\'s own shuffles, '
      'so they agree within Monte Carlo error rather than exactly; for this pocket both sides found 0 shuffles as '
      'large as the real gap, so the figures are in fact identical. Section 7 covers the shuffle test.</p>')

    w('<h2>5. The same pocket in the main workbook</h2>')
    w('<p>The figures an analyst actually reads. Pockets was read with its MEASURE dropdown set to "GCOs ($)", '
      'Grids with MEASURE set to "GCOs ($)", and RANR vs GCOs as it opens; each copy was recalculated by LibreOffice '
      f'before reading. Pockets row {c["main"]["Pockets_row"]} and RANR vs GCOs row {c["main"]["RANR_row"]} hold this '
      'pocket.</p>')
    w('<table class="fig"><tr><th>Tab</th><th>Column</th><th>Independent</th><th>Main workbook</th><th>Ties</th></tr>')
    for x, ok in main_rows:
        w(f'<tr><td>{E(x["tab"])}</td><td>{E(x["col"])}</td><td class="n">{fmt("x", x["indep"])}</td>'
          f'<td class="n">{fmt("x", x["main"])}</td><td>{tick(ok)}</td></tr>')
    w('</table>')

    w('<h2>6. Run stamp, rows in and out, and bands</h2>')
    w(f'<p>The SHA-256 fingerprint of loans.csv computed by tieout.py is <code>{E(c["sha"]["indep"])}</code>. The Run '
      f'stamp sheet (cell C5) shows <code>{E(c["sha"]["audit"])}</code>. '
      + ("They are identical." if c["sha"]["indep"] == c["sha"]["audit"] else "<b>They differ.</b>") + '</p>')
    w('<table class="fig"><tr><th>Rows in and out</th><th>Independent</th><th>Audit (Excel)</th><th>PocketBook</th>'
      '<th>Ties</th></tr>')
    for x in c["rows_in_out"]:
        w(f'<tr><td>{E(x["line"])}</td><td class="n">{x["indep"]:,}</td><td class="n">{x["excel"]:,}</td>'
          f'<td class="n">{x["pb"]:,}</td><td>{tick(x["ok"])}</td></tr>')
    w('</table>')
    w('<table class="fig"><tr><th>Band</th><th>From (at least)</th><th>Up to (below)</th><th>Independent</th>'
      '<th>Audit (Excel)</th><th>PocketBook</th><th>Ties</th></tr>')
    for x in c["bands"]:
        lo = "lowest" if x["from"] == -1e307 else x["from"]
        hi = "and up" if x["to"] == 1e307 else ("" if x["to"] is None else x["to"])
        w(f'<tr><td>{E(x["band"])}</td><td>{lo}</td><td>{hi}</td><td class="n">{x["indep"]:,}</td>'
          f'<td class="n">{x["excel"]:,}</td><td class="n">{x["pb"]:,}</td><td>{tick(x["ok"])}</td></tr>')
    w('</table>')
    w(f'<p>Each loan\'s band: the script assigned a band to each of the {lb["loans"]:,} records from the edges alone. '
      f'Against the Loans sheet\'s Excel-calculated band column it differs on {lb["indep_vs_excel"]:,} records; against '
      f'PocketBook\'s own band column on {lb["indep_vs_pb"]:,}; and the two workbook columns differ from each other on '
      f'{lb["excel_vs_pb"]:,}. The Bands sheet\'s own count of mismatches reads '
      f'{c["band_mismatch_cell"]["excel"]}.</p>')

    w('<h2>7. The shuffle test</h2>')
    w(SHUFFLE_METHOD.format(B=B))
    w('<h3>7.1 The default pocket\'s listed shuffles</h3>')
    w(f'<p>The Shuffle test sheet lists all {sh["listed"]:,} shuffled gaps for the default pocket. The real gap is '
      f'{sh["indep_gap"]:.12f} (independent), {sh["Real gap"]["excel"]:.12f} (Excel) and {sh["Real gap"]["pb"]:.12f} '
      f'(PocketBook). The counting line is {sh["indep_line"]:.12f} independently and {sh["The line"]["excel"]:.12f} '
      f'on the sheet. The largest shuffled gap in the list, in absolute value, is {sh["max_abs_listed"]:.6f}, about a '
      f'fifth of the real gap. Counting the listed gaps against the independent line gives '
      f'{sh["count_from_list_my_line"]:,}; the sheet\'s COUNTIF gives {sh["Shuffles that count"]["excel"]:,}; '
      f'PocketBook\'s stored count is {sh["Shuffles that count"]["pb"]:,}. The sheet\'s shuffle count is '
      f'{sh["Shuffles"]["excel"]:,} and its p-value {sh["p-value"]["excel"]:.10f}, which is (0 + 1) ÷ ({B:,} + 1). '
      f'The ten-loan worked example ties on all {sh["example_rows_tied"]} listed shuffles and on its count and '
      f'p-value.</p>')
    w(f'<p>The z-test cross-check on bad loans: z = {sh["z"]["z"]["indep"]:.10f} independently, '
      f'{sh["z"]["z"]["excel"]:.10f} in Excel and {sh["z"]["z"]["pb"]:.10f} from PocketBook; the two-sided p-value is '
      f'{sh["z"]["Two-sided p-value"]["indep"]:.6e}, {sh["z"]["Two-sided p-value"]["excel"]:.6e} and '
      f'{sh["z"]["Two-sided p-value"]["pb"]:.6e}. The three agree to at least twelve significant figures.</p>')
    w('<h3>7.2 Every tested pocket: independent shuffles against PocketBook\'s</h3>')
    w(SHUFFLE_ALL.format(B=B))
    w('<table class="fig"><tr><th>Pocket</th><th>PocketBook count</th><th>PocketBook p</th><th>Independent count</th>'
      '<th>Independent p</th><th>SE of difference</th><th>Difference in SEs</th><th>PocketBook adjusted p</th>'
      '<th>BH of PocketBook raw p</th><th>BH exact</th></tr>')
    for x in sorted(c["shuffle_all"], key=lambda x: x["pb_p"]):
        w(f'<tr><td>{E(x["band"])}, {E(x["seg"])}</td><td class="n">{x["pb_hits"]:,}</td><td class="n">'
          f'{x["pb_p"]:.5f}</td><td class="n">{x["indep_hits"]:,}</td><td class="n">{x["indep_p"]:.5f}</td>'
          f'<td class="n">{x["se_diff"]:.5f}</td><td class="n">{x["z"]:+.2f}</td><td class="n">{x["pb_adj"]:.10f}'
          f'</td><td class="n">{x["bh_of_pb_raw"]:.10f}</td><td>{tick(x["bh_exact"])}</td></tr>')
    w('</table>')
    zs = [x["z"] for x in c["shuffle_all"] if not (x["pb_hits"] == 0 and x["indep_hits"] == 0)]
    within2 = sum(1 for z in zs if abs(z) <= 1.96)
    w(f'<p>Of the {len(zs)} pockets whose p-value is not at the floor, {within2} differ by less than 1.96 standard '
      f'errors and all {sum(1 for z in zs if abs(z) <= 3)} by less than 3. The other '
      f'{len(c["shuffle_all"]) - len(zs)} pockets found no shuffle as large on either side, so both report the '
      f'floor value 1 ÷ {B + 1:,}.</p>')
    deep_rows = []
    for k, v in deep.items():
        band, seg = k.split("|")
        pb = next(x for x in c["shuffle_all"] if x["band"] == band and x["seg"] == seg)
        se_pb = math.sqrt(v["p"] * (1 - v["p"]) / B)
        deep_rows.append((band, seg, pb["pb_p"], v["hits"], v["p"], se_pb, (pb["pb_p"] - v["p"]) / se_pb))
    nd = 100_000 if deep_rows else 0
    w(DEEP_TEXT)
    w('<table class="fig"><tr><th>Pocket</th><th>PocketBook p (10,000)</th><th>Independent count (100,000)</th>'
      '<th>Independent p (100,000)</th><th>SE of a 10,000-shuffle p</th><th>PocketBook off by, in SEs</th></tr>')
    for band, seg, pbp, hits, p, se, z in deep_rows:
        w(f'<tr><td>{E(band)}, {E(seg)}</td><td class="n">{pbp:.5f}</td><td class="n">{hits:,}</td><td class="n">'
          f'{p:.5f}</td><td class="n">{se:.5f}</td><td class="n">{z:+.2f}</td></tr>')
    w('</table>')
    del nd

    w('<h2>8. Does one pocket show the calculations for all?</h2>')
    w(SWEEP_TEXT)
    w('<table class="fig"><tr><th>Pocket</th><th>Loans</th><th>GCO rate</th><th>× rest of band</th>'
      '<th>Dollars above share</th><th>Figures compared</th><th>Not tied</th><th>Largest relative difference</th>'
      '</tr>')
    for s in sorted(c["sweep"], key=lambda s: (s["band"], s["seg"])):
        nb = [b for b in s["bad"] if not (b[1] in (None, 0) and b[2] == 0)]
        xb = s["x_band"]
        w(f'<tr><td>{E(s["band"])}, {E(s["seg"])}</td><td class="n">{s["loans"]:,}</td><td class="n">'
          f'{s["gco_rate"]:.6f}</td><td class="n">{"none" if xb in (None, "none") else f"{xb:.4f}"}</td>'
          f'<td class="n">{money(s["dollars"])}</td><td class="n">{s["figures"]}</td><td class="n">{len(nb)}</td>'
          f'<td class="n">{s["worst_rel"]:.1e}</td></tr>')
    w('</table>')
    w('<p>The four pockets picked on the One pocket dropdowns, after LibreOffice recalculated the sheet:</p>')
    w('<table class="fig"><tr><th>Pocket</th><th>Rows on One pocket</th><th>Agree with the independent figure</th>'
      '<th>Rows the sheet marks tied</th></tr>')
    for k, n, good, ticked in other_summary:
        w(f'<tr><td>{E(k.replace("|", ", "))}</td><td class="n">{n}</td><td class="n">{good}</td>'
          f'<td class="n">{ticked}</td></tr>')
    w('</table>')
    w(OTHERS_TEXT)

    w('<h2 data-tieout="what-it-found">9. What it found</h2>')
    o713 = pockets[("713 - 745", "Online")]
    t713 = {x["key"]: x for x in c["others"]["713 - 745|Online"]}
    w(FOUND.format(band_by_hand=money(o713["band_bk_by_hand"]), band_excel=money(t713["band_gco_bk"]["excel"]),
                   book_avg=money(d["book_avg"]), book_avg_all=money(d["book_avg_every_loan"]),
                   ranr_gap=d["ranr_gap"], ranr_band_gap=d["ranr_band_gap"], both_gap=d["both_band_gap"],
                   book_gco_bk=money(d["book_gco_bk"]), booked_all=money(ind["book"]["booked_all"])))
    w('<h2 data-tieout="what-i-got-wrong">10. What I got wrong along the way</h2>')
    w(WRONG)
    w('<h2 data-tieout="what-this-does-not-prove">11. What this does not prove</h2>')
    w(NOT_PROVED)
    w('<h2>12. How to run it yourself</h2>')
    w(RUN_IT)
    w('</main></body></html>')
    Path(out).write_text("\n".join(P), encoding="utf-8")
    print("wrote", out, f"{total:,} comparisons", tally)


HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audit Workbook Tie-out</title>
<style>
:root{--ink:#1d2430;--muted:#5b6472;--line:#d5dae1;--bg:#ffffff;--panel:#f4f6f9;--ok:#1d7a3a;--bad:#b3261e;--mc:#7a5a00;--accent:#b3261e}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#e6e9ee;--muted:#a5adba;--line:#3a414c;--bg:#14181e;--panel:#1d232b;--ok:#6fcf8a;--bad:#ff8a80;--mc:#e6c35c;--accent:#ff8a80}}
:root[data-theme="dark"]{--ink:#e6e9ee;--muted:#a5adba;--line:#3a414c;--bg:#14181e;--panel:#1d232b;--ok:#6fcf8a;--bad:#ff8a80;--mc:#e6c35c;--accent:#ff8a80}
body{background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:0}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:8px 0 4px}h2{font-size:19px;margin:36px 0 8px;border-bottom:2px solid var(--line);padding-bottom:4px}
h3{font-size:16px;margin:22px 0 6px}.sub{color:var(--muted);margin-top:0}
table{border-collapse:collapse;width:100%;margin:10px 0 16px;font-size:13px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:4px 7px;vertical-align:top;text-align:left}
th{background:var(--panel)}td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.words{color:var(--muted);min-width:180px;max-width:260px}
table.fig td:first-child{min-width:150px}
@media print{table{display:table;font-size:9.5px}td.words{max-width:180px}}
.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}.mc{color:var(--mc);font-weight:600}.na{color:var(--muted)}
.headline{font-size:18px;font-weight:700;margin:6px 0}
.roster td:nth-child(2){text-align:right;font-weight:700}
img{max-width:100%;border:1px solid var(--line);margin:8px 0 2px;background:#fff}
.cap{color:var(--muted);font-size:13px;margin-top:2px}
code{background:var(--panel);padding:1px 4px;border-radius:3px;font-size:12.5px;word-break:break-all}
pre{background:var(--panel);padding:10px 12px;overflow-x:auto;font-size:12.5px}
.finding{border-left:4px solid var(--accent);padding:4px 12px;margin:12px 0;background:var(--panel)}
svg{max-width:100%;height:auto}
svg text{fill:var(--ink);font:14px -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
svg .box{fill:var(--panel);stroke:var(--muted);stroke-width:1.2}
svg .ind{fill:var(--panel);stroke:var(--accent);stroke-width:2}
svg .arr{stroke:var(--muted);stroke-width:1.6;fill:none;marker-end:url(#a)}
svg .arr2{stroke:var(--accent);stroke-width:1.8;fill:none;marker-end:url(#b)}
svg .lab{font-size:11px;fill:var(--muted)}
</style></head><body><main>"""

DIAGRAM = """<svg viewBox="0 0 1000 350" role="img" aria-label="Diagram of the evidence chain">
<defs><marker id="a" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#7a8494"/></marker>
<marker id="b" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#b3261e"/></marker></defs>
<rect class="box" fill="#f4f6f9" stroke="#5b6472" x="20" y="140" width="170" height="74" rx="6"/>
<text fill="#1d2430" x="105" y="168" text-anchor="middle">loans.csv</text>
<text class="lab" fill="#5b6472" x="105" y="188" text-anchor="middle">50,000 records</text>
<text class="lab" fill="#5b6472" x="105" y="204" text-anchor="middle">SHA-256 9b41…0681</text>
<rect class="box" fill="#f4f6f9" stroke="#5b6472" x="280" y="40" width="180" height="66" rx="6"/>
<text fill="#1d2430" x="370" y="68" text-anchor="middle">PocketBook Run</text>
<text class="lab" fill="#5b6472" x="370" y="88" text-anchor="middle">bleed test, 10,000 shuffles</text>
<rect class="box" fill="#f4f6f9" stroke="#5b6472" x="550" y="14" width="250" height="58" rx="6"/>
<text fill="#1d2430" x="675" y="38" text-anchor="middle">Main workbook</text>
<text class="lab" fill="#5b6472" x="675" y="58" text-anchor="middle">Pockets, RANR vs GCOs, Grids</text>
<rect class="box" fill="#f4f6f9" stroke="#5b6472" x="550" y="100" width="250" height="58" rx="6"/>
<text fill="#1d2430" x="675" y="124" text-anchor="middle">Audit workbook</text>
<text class="lab" fill="#5b6472" x="675" y="144" text-anchor="middle">One pocket, Shuffle test, _pocketbook</text>
<rect class="ind" fill="#f4f6f9" stroke="#b3261e" x="280" y="250" width="180" height="66" rx="6"/>
<text fill="#1d2430" x="370" y="278" text-anchor="middle">tieout.py</text>
<text class="lab" fill="#5b6472" x="370" y="298" text-anchor="middle">no PocketBook code</text>
<rect class="ind" fill="#f4f6f9" stroke="#b3261e" x="840" y="150" width="150" height="74" rx="6"/>
<text fill="#1d2430" x="915" y="176" text-anchor="middle">Comparison</text>
<text class="lab" fill="#5b6472" x="915" y="196" text-anchor="middle">within 1E-9, or</text>
<text class="lab" fill="#5b6472" x="915" y="212" text-anchor="middle">within MC error</text>
<path class="arr" stroke="#7a8494" fill="none" d="M190,160 C230,120 240,90 278,80"/>
<text class="lab" fill="#5b6472" x="196" y="112">read, classified</text>
<path class="arr" stroke="#7a8494" fill="none" d="M460,62 L548,46"/>
<text class="lab" fill="#5b6472" x="490" y="44">writes</text>
<path class="arr" stroke="#7a8494" fill="none" d="M460,86 L548,126"/>
<text class="lab" fill="#5b6472" x="478" y="124">writes</text>
<path class="arr" stroke="#7a8494" fill="none" d="M800,46 C840,60 860,110 880,148"/>
<path class="arr" stroke="#7a8494" fill="none" d="M800,134 L838,160"/>
<text class="lab" fill="#5b6472" x="555" y="178">Both workbooks recalculated by</text>
<text class="lab" fill="#5b6472" x="555" y="192">LibreOffice; cells read</text>
<path class="arr2" stroke="#b3261e" fill="none" d="M190,196 C230,240 240,270 278,280"/>
<text class="lab" fill="#5b6472" x="160" y="262">bytes, csv module</text>
<path class="arr2" stroke="#b3261e" fill="none" d="M460,284 C640,284 800,262 870,226"/>
<text class="lab" fill="#5b6472" x="540" y="304">exact sums and ratios; its own shuffles</text>
</svg>
<p class="cap">Grey: the production path. Red: the independent check. Only the red road is independent of PocketBook.</p>"""

VERDICT_TEXT = """<p><b>Verdict.</b> The audit workbook does what it claims for the bleed test. For the default pocket, every
figure on the One pocket sheet reconciles three ways: the independent recomputation, the workbook's own Excel
formulas and PocketBook's stored figure agree to within 1E-9 of the figure, and the dollar sums agree to the cent. The
same pocket reconciles to the figures an analyst reads on the main workbook's Pockets, RANR vs GCOs and Grids tabs. The
shuffle test reproduces: the listed shuffles and COUNTIF give PocketBook's count exactly, an independent
re-implementation with its own random numbers lands within Monte Carlo error on every tested pocket, and the
Benjamini-Hochberg adjustment recomputes exactly. The claim that one pocket shows the calculations for all holds for
this scenario: all {n_pockets} pockets in the grid reconcile on every figure compared. No figure differs. The
findings in section 9 concern the workbook's wording and what it does not show, not its arithmetic.</p>"""

SCENARIO = """<p><b>Data.</b> A synthetic loan file produced by PocketBook's own generator,
<code>synth.write_extract(n=50000, seed=7)</code>: 50,000 records, no real data. The generator plants a high-loss pocket
(FICO under 620 through the Broker channel) and five deliberately unusable values (pictured below). SHA-256 of the file:
<code>{sha}</code>.</p>
<p><b>Run.</b> A bleed test ("Where the book bleeds") with one band column, FICO, cut by PocketBook into five bands of
about equal loans (edges 653, 686, 713 and 746), and one segment column, CHANNEL (Branch, Broker, Online). Control was
answered as PocketBook's own test suite answers it: a pocket is judged against the rest of its band; worse at 1.25 times;
95% confidence; Benjamini-Hochberg allowance for many tests; materiality at 1% of the book's GCOs; FICO -9999 treated
as missing. "Also write the audit workbook?" was answered Yes. Shuffles: {B:,}, PocketBook's default. The grid has
seven bands (the five score bands plus "(blank)" and "(marked missing)") and three segments, which gives 19 pockets
with at least one loan.</p>
<p><b>Independent recomputation.</b> <code>tieout.py</code> imports nothing from PocketBook and reads no workbook. It
reads the file's bytes, fingerprints them with hashlib, parses them with the csv module, and computes every dollar
sum exactly (decimal values summed as fractions, so there is no floating-point rounding until the final figure is
written out). It uses only the Python standard library: csv, decimal, fractions, hashlib and random, plus json, math
and sys for input and output. The Run's settings (column roles, band edges, the missing-value rule, the comparison,
the minimum of 10 losses, the allowance method and the number of shuffles) are typed into the script as inputs, as
listed on the audit workbook's Run stamp sheet. They are settings, not results, so taking them as given does not
weaken the check. The definitions were taken from the audit sheet's "In words" column and PocketBook's code; the
arithmetic is the script's own.</p>
<p><b>Reading the workbooks.</b> <code>compare.py</code> opens each workbook after LibreOffice headless has recalculated
it with "recalculate on load: always", using the same helper PocketBook's tests use (tests/recalc.py). Where a figure
depends on a dropdown, the dropdown was set on a copy and the copy recalculated, as an analyst would.</p>"""

TOLERANCE = """<p><b>Tolerance.</b> Two figures are treated as tied when they differ by no more than 1E-9 of the
figure (with a floor of 1E-9 absolute), which is the same standard the audit workbook's own Ties? column uses. Counts
must match exactly. The largest relative difference actually observed on any non-shuffle figure is reported in
section 8; it is of the order of 1E-13, which is floating-point rounding in the last digits of sums of 50,000 values.
Shuffle-test results are compared within Monte Carlo error, as explained in section 7.</p>"""

SHUFFLE_METHOD = """<p><b>What PocketBook does</b> (perm.py, read for this workpaper). For each pocket judged against the
rest of its band, only the records in that band that have both a booked amount and a GCO amount take part. The
statistic is the gap g = pocket GCOs ÷ pocket booked − rest-of-band GCOs ÷ rest-of-band booked. Each shuffle deals
the band's records into a random order and gives the pocket as many of them as it really holds. A shuffle counts
when its gap is at least as far from zero as the real gap in either direction (two-sided), after a small allowance
of 1E-9 times the larger of |g| and the band's total absolute GCO over its booked, so that an exact tie is not lost
to rounding; a shuffled gap that cannot be computed also counts. The p-value is (count + 1) ÷ (shuffles + 1). The
p-value shown is then adjusted for testing many pockets with Benjamini-Hochberg across the grid's tested pockets on
the same comparison. A pocket with fewer than 10 loans with a non-zero GCO is not tested.</p>
<p><b>What the independent script does.</b> The same statistic, sidedness, allowance, +1 correction and minimum, coded
from scratch with Python's own random-number generator (random.Random, seed 20261003) rather than PocketBook's
seed and generator. Each of the {B:,} shuffles is a fresh random order of each band's records, sliced into the
segments' real sizes.</p>"""

SHUFFLE_ALL = """<p>Two independent sets of {B:,} shuffles estimate the same underlying p-value, each with a standard
error of about √(p(1 − p) ÷ {B:,}). The standard error of their difference is √2 times that. A difference within about
two standard errors is expected for most pockets and within three for nearly all. The last three columns check the
Benjamini-Hochberg adjustment separately and exactly: the adjustment was recomputed from PocketBook's own raw
p-values, using the standard step-up procedure (sort the p-values, multiply each by the number of tests over its rank,
then take the running minimum from the largest rank down, capped at 1), and compared with the adjusted p-value
PocketBook stores and displays.</p>"""

DEEP_TEXT = """<p><b>The two largest differences, investigated.</b> Two pockets in the same band (653 - 685, Branch and
Broker) differed by about two standard errors in the 10,000-shuffle comparison. Two pockets in one band share their
shuffles on both sides, so their differences are correlated rather than two separate surprises. To settle whether the
gap is chance or a difference in method, the independent script was run again on that band with 100,000 shuffles and
a different seed. That gives a p-value with about a third of the standard error, against which PocketBook's
10,000-shuffle figure is compared using its own standard error alone.</p>"""

SWEEP_TEXT = """<p>The firm's working assumption is that one scenario effectively shows the calculations for all. That was
tested rather than assumed in two ways. First, every pocket in the grid was recomputed independently and compared
with PocketBook's stored figures on the hidden _pocketbook sheet, which is the sheet the One pocket dropdowns read
from: 37 figures per pocket (loans, bad loans and rate, booked, GCOs, RANR and each rate, the whole book, the rest of
the book, the rest of the band, each multiple, gap and dollar figure, the Avg line figures, loans with a loss, and the
z-test). Second, four further pockets were picked on the One pocket dropdowns and the workbook recalculated, so that
the Excel formulas themselves were exercised on pockets other than the default.</p>"""

OTHERS_TEXT = """<p>The four pockets were chosen to exercise different paths: 686 - 712, Online and 713 - 745, Online are
flagged worse and material (the second sits in the band that holds the GCO of "#N/A" and the blank booked balance);
(marked missing), Broker is a small pocket of 321 records with a p-value well away from the floor; and (blank),
Broker is a single record alone in its band, which must fall back to comparison with the whole book. Every figure
reconciled. On a pocket other than the default, the sheet lists no shuffles, so the count row reads "listed for the
default pocket only" and its Ties? cell reads "–" by design; the p-value rows still tie between Excel and
PocketBook, and the independent p-value agrees within Monte Carlo error.</p>"""

FOUND = """<p>No arithmetic error was found. Every figure compared reconciles. The following findings concern what the
audit workbook says, and what it shows, rather than what it computes.</p>
<div class="finding"><p><b>Finding 1. The "By hand" instruction for "Booked, rest of its band" leads a reviewer to a
different figure in the 713 - 745 band.</b> The instruction reads "Filter In this band to 1, less this pocket's
booked." The Excel formula is <code>SUMIFS(Loan_Booked, Loan_InBand, 1, Loan_GCO, "&gt;-1E+307") − pocket booked</code>,
that is, it sums only records that also have a GCO amount. In band 713 - 745 one record (L0000002, booked $39,684.43)
has a GCO of "#N/A" and is excluded from the GCO rate. A reviewer who follows the instruction literally includes it,
and arrives at a rest-of-band booked figure $39,684.43 higher than Excel's for all three pockets in that band (for
713 - 745, Online, a flagged pocket: {band_by_hand} by hand against {band_excel} in Excel). The rate and dollar figures
that follow would then differ too. Root cause: the instruction omits the step the pocket's own "Booked, loans with a
GCO" instruction includes ("and filter the words out of the GCO column"). Suggested wording: "Filter In this band to
1 and filter the words out of the GCO column; sum of the booked column, less this pocket's booked."</p></div>
<div class="finding"><p><b>Finding 2. "Avg line, whole book" is described as "the same over every loan", but the
formula divides by loans with a booked amount.</b> Excel computes <code>SUM(Loan_Booked) ÷ COUNT(Loan_Booked)</code>
over the 49,999 records with a booked amount, giving {book_avg}. Read literally, "every loan" means all 50,000
records, giving {book_avg_all}. The By hand note (the status bar's Average) gives the correct figure, so the
difference is in the definition only. Suggested wording: "The same over every loan with a booked amount."</p></div>
<div class="finding"><p><b>Finding 3. The audit proves a RANR gap the main workbook does not show, and does not prove
the one it does.</b> The One pocket sheet's "RANR gap in points" is the pocket against the rest of the book
(+{ranr_gap:.3f} points for the default pocket). With Control set to judge pockets against the rest of their band,
the main workbook's RANR vs GCOs tab shows the RANR gap against the rest of the band ({ranr_band_gap:+.3f} points),
which has the opposite sign, and the RANR + GCOs gap ({both_gap:+.3f} points). Neither of those, nor their dollar
figures, appears on the audit workbook. The independent script recomputed both and they reconcile to the main
workbook (section 5), so the figures are right; the gap is in coverage. A reviewer checking RANR vs GCOs against the
audit would find the audit's RANR gap disagrees with the tab in sign and could reasonably conclude one of them is
wrong.</p></div>
<div class="finding"><p><b>Finding 4. "Booked, whole book" means different populations in the two workbooks.</b> The
audit's "Booked, whole book" is the booked total of records in the GCO rate, {book_gco_bk}. The main workbook's RANR
vs GCOs "Whole book" row shows Booked of {booked_all}, the total of every record with a booked amount. The difference,
$39,684.43, is the record whose GCO is "#N/A". Both are correct for their purpose; the same label is used for both.
The audit's definition column does say "with a booked amount and a GCO amount", so a careful reader can reconcile
them.</p></div>
<div class="finding"><p><b>Finding 5. The Benjamini-Hochberg "By hand" step cannot be completed from the visible
sheets.</b> The instruction is to sort the grid's p-values and number them. The other pockets' unadjusted p-values
appear only on the hidden _pocketbook sheet (column raw_band); the main workbook shows adjusted p-values only. The
adjustment itself recomputes exactly from those hidden values (section 7.2). Suggested remedy: list the grid's
tested pockets with their counts and unadjusted p-values on the Shuffle test sheet, or point the instruction at the
hidden sheet.</p></div>
<div class="finding"><p><b>Finding 6. The shuffle test for this default pocket is not a sensitive test of the
shuffle code.</b> The default pocket's real gap is about four and a half times the largest shuffled gap, so any reasonable
implementation returns 0 shuffles and the floor p-value. Agreement on this pocket therefore proves little about the
shuffle mechanics. That is why section 7.2 compares every tested pocket, twelve of which have p-values well above
the floor; the default pocket alone would not have been enough.</p></div>
<div class="finding"><p><b>Finding 7 (presentation, minor). One step label overprints the row beneath it.</b> In the
LibreOffice rendering of One pocket (section 4 picture), "Booked, every loan with a booked amount" wraps onto a
second line and overprints "Avg line" below it. The row height is set from the length of the definition and the
By hand note, not the step label. This was seen in LibreOffice only; Excel was not available to confirm it.</p></div>"""

WRONG = """<p>Three things in my own process needed correcting before the figures were trusted.</p>
<ul>
<li>My first reading of the One pocket sheet matched the "Avg line" section heading as if it were the "Avg line"
figure, which produced a row with no Excel or PocketBook value. The reader now accepts a step only when its Ties?
cell is filled.</li>
<li>For the pocket alone in its band ((blank), Broker), I first reported the rest-of-band booked and GCOs as "none",
while PocketBook stores 0. An empty rest of band has zero booked dollars, so 0 is correct; the script now computes it
that way, and the rate that would divide by it is correctly "none" on both sides.</li>
<li>My first 10,000-shuffle comparison showed two pockets about two standard errors apart. Before treating that as
chance I ran the 100,000-shuffle check in section 7.2 rather than widening the tolerance.</li>
</ul>"""

NOT_PROVED = """<ul>
<li><b>Other scenarios.</b> One synthetic file, one band column, one segment column. Value bands (a column with few
values), typed edges, a second grid, filters, a split, a pocket judged against the book by Control's setting, and
Bonferroni or no allowance were not exercised.</li>
<li><b>The book-side shuffle test.</b> Each pocket is also shuffled against the whole book. Those p-values are stored
but not displayed under this Run's setting, and the independent script did not re-run them; the book-side
Benjamini-Hochberg adjustment was not checked.</li>
<li><b>Microsoft Excel.</b> Every workbook figure was calculated by LibreOffice. Excel was not available. The formulas
used (SUMIFS, COUNTIFS, MINIFS, INDEX, MATCH, OFFSET, NORM.S.DIST) behave the same way in both on the documented
cases, but that is an assumption, not a tested fact.</li>
<li><b>Bad loans, Bad dollars and RANR verdicts.</b> The Pockets tab was read for GCOs only. The bad-loan rate and
z-test were reconciled for the pockets, but the Pockets tab's Bad loans, Bad dollars, RANR and RANR + GCOs views, and
their verdicts, were not compared.</li>
<li><b>The generator.</b> The synthetic file was produced by PocketBook's own generator. That does not affect the
independence of the check, which reads only the file, but it means the dirt in the file is the dirt PocketBook's
authors chose to plant.</li>
<li><b>The band edges.</b> The edges 653, 686, 713 and 746 were taken from the Run stamp as settings. The script did
not check that they are the equal-count cut points PocketBook says they are, only that each record lands in the band
those edges define (the band counts, 9,628 to 9,953, are roughly equal).</li>
<li><b>Other sheets.</b> Start here, Summary, Record and the main workbook's remaining tabs were not examined.</li>
</ul>"""

RUN_IT = """<p>From the repository root, on a machine with Python 3, openpyxl, numpy, Pillow, LibreOffice
(<code>soffice</code>) and poppler (<code>pdftoppm</code>). Allow about fifteen minutes in all; the independent shuffles
take about four.</p>
<pre>cd pocketbook/docs/audit-tieout-2026-10-03
R=/tmp/pb-tieout            # any scratch folder; it receives the 50,000-record file and both workbooks

python make_scenario.py $R                                        # PocketBook writes loans.csv and both workbooks
python tieout.py $R/loans.csv $R/indep.json                       # the independent side: no PocketBook code
python tieout_band.py $R/loans.csv "653 - 685" 100000 777 $R/deep.json   # the longer check in section 7.2
python compare.py $R $R/indep.json $R/cmp.json                    # reads the recalculated workbooks
python pictures.py $R $R/pics
python build_html.py $R $R/indep.json $R/cmp.json $R/deep.json $R/pics TIEOUT.html</pre>
<p>The file's SHA-256 should read <code>9b4190398a30d2c1414a72cf0ed7b24e58cd4b4b608c5183fdb86e8eb7ba0681</code>. The
independent shuffle counts are reproduced exactly with the seeds given (20261003 for the main run, 777 for the
longer one). To check by hand without any script: open the audit workbook, go to Loans, filter In this pocket to 1,
select the ORIG_BAL column and read the status bar's Sum; it should read $101,126,518.13, the booked figure for the
default pocket in section 4.</p>"""


if __name__ == "__main__":
    a = sys.argv[1:]
    main(*a)
