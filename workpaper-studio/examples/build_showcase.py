"""Build prototype/outputs.html: the real example outputs beside proposed screens.

Run after build_examples.py:  python3 workpaper-studio/examples/build_showcase.py
Every figure comes from out/fragments.json and the workbook, so the page shows exactly what the files contain.
"""
import html
import json
import re
import subprocess
import tempfile
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DEST = HERE.parent / "prototype" / "outputs.html"
E = html.escape
F = json.loads((OUT / "fragments.json").read_text())
CASE, QS = F["case"], F["questions"]


def scope_css(css, scope):
    """Prefix every selector in the paper stylesheet so the embedded documents keep their print look
    without leaking into the page around them."""
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, body = m.group(1).strip(), m.group(2)
        if sel.startswith("@page") or sel == "*":
            continue
        parts = []
        for s in sel.split(","):
            s = s.strip()
            parts.append(scope if s == "body" else f"{scope} {s}")
        out.append(",".join(parts) + "{" + body + "}")
    return "\n".join(out)


# ---------------------------------------------------------------- workbook: formulas and recalculated values
src = OUT / f"{CASE['id']}.xlsx"
tmp = Path(tempfile.mkdtemp())
subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(tmp), str(src)], check=True, capture_output=True, timeout=180)
wf, wv = load_workbook(src), load_workbook(tmp / src.name, data_only=True)


def fmtv(v, nf):
    if isinstance(v, float) and "%" in (nf or ""):
        return f"{v * 100:.1f}%"
    if isinstance(v, (int, float)) and "$" in (nf or ""):
        return f"${v:,.0f}"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return "" if v is None else str(v)


def sheet_html(name):
    a, b = wf[name], wv[name]
    rows = []
    for r in range(1, a.max_row + 1):
        cells = []
        for c in range(1, min(a.max_column, 8) + 1):
            fc, vc = a.cell(r, c), b.cell(r, c)
            isf = isinstance(fc.value, str) and fc.value.startswith("=")
            val = E(fmtv(vc.value, fc.number_format))
            tag = "th" if r == 1 and name != "Cover" else "td"
            cls = ' class="f"' if isf else ""
            formula = f'<span class="fx">{E(fc.value)}</span>' if isf else ""
            cells.append(f"<{tag}{cls}>{val}{formula}</{tag}>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return '<div class="sheet"><table>' + "".join(rows) + "</table></div>"


SHEETS = ["Cover", "Testing", "Cash flow", "Collateral", "DTI", "Findings", "Review log"]

# ---------------------------------------------------------------- screens (proposals)
R_SHORT = {"Effective": ("e", "✓"), "Partially effective": ("p", "◐"), "Not effective": ("x", "✕"), "Not applicable": ("na", "–")}


def rchip(r):
    k, ic = R_SHORT.get(r, ("", "○"))
    return f'<span class="r {k}"><span aria-hidden="true">{ic}</span> {E(r)}</span>'


STAGES = ["Signed off", "Signed off", "Signed off", "In review", "Signed off", "Testing · 6 of 9", "Signed off", "Signed off",
          "Returned · 1 point", "Testing · 2 of 9", "Not started", "Not started"]


def queue_screen():
    rows = ""
    for s, st in zip(F["sample"], STAGES):
        k = "ok" if st.startswith("Signed") else "acc" if st == "In review" else "warn" if st.startswith("Returned") else ""
        mine = s["tester"] == "A. Rivera"
        rows += (f'<tr{" class=me" if s["id"] == CASE["id"] else ""}><td class="mono">{s["id"]}</td><td>{E(s["borrower"])}</td><td>{E(s["tester"])}{" <span class=cap>(you)</span>" if mine else ""}</td>'
                 f'<td><span class="chip {k}">{E(st)}</span></td><td class="num">{s["findings"] if st.startswith(("Signed", "In review", "Returned")) else "—"}</td></tr>')
    done = sum(1 for s in STAGES if s.startswith("Signed"))
    return f'''<div class="appbar"><b>Workpaper Studio</b><span>2026-Q3 sample</span><span class="sp"></span><span class="who">A. Rivera · Tester</span></div>
<div class="scr-body"><div class="hd"><div><h4>2026-Q3 sample · credit file review</h4><div class="cap">{done} of 12 signed off · due 2026-10-31</div></div><span class="sp"></span>
<div class="seg"><span class="on">My files</span><span>Waiting for review</span><span>All 12</span></div></div>
<div class="prog"><i style="width:{done / 12 * 100:.0f}%"></i></div>
<table class="t"><thead><tr><th>Case</th><th>Borrower</th><th>Tester</th><th>Where it is</th><th class="num">Findings</th></tr></thead><tbody>{rows}</tbody></table></div>'''


def testing_screen():
    nav = ""
    states = {"1.01": "Effective", "1.02": "Effective", "2.01": "Effective", "2.02": "Not effective", "3.01": "Partially effective",
              "4.01": "Effective", "5.01": "Effective", "5.02": None, "6.01": None}
    for n, s, q, _ in QS:
        st = states[n]
        k, ic = R_SHORT.get(st, ("", "○"))
        nav += f'<li class="{"cur" if n == "5.02" else ""}"><span class="ic {k}" aria-hidden="true">{ic}</span><span class="mono">{n}</span><span class="ql">{E(q)}</span></li>'
    q = next(x for x in QS if x[0] == "5.02")
    d = F["dti"]
    return f'''<div class="appbar"><b>Workpaper Studio</b><span>{CASE["id"]} · {E(CASE["borrower"])}</span><span class="sp"></span><span class="chip">Testing · 7 of 9 rated</span><span class="who">A. Rivera</span></div>
<div class="test3"><nav class="qnav" aria-label="Questions"><div class="cap" style="padding:6px 8px">Questions <b>①</b></div><ul>{nav}</ul></nav>
<section class="focus"><div class="cap">Repayment analysis · question 5.02 <span class="chip">applies: new money request = Yes</span></div>
<h5>{E(q[2])}</h5>
<details open><summary>How to test this <b>②</b></summary><p>{E(q[3])}</p></details>
<div class="evid"><b>What the file shows <b>③</b></b><div class="calcbox"><span class="cap">Debt-to-income, recomputed</span><b class="big">{d["value"] * 100:.1f}%</b><span class="chip x">above the 40% limit (fictional)</span><div class="cap">(${d["debt"]:,.0f} + ${d["proposed"]:,.0f}) ÷ ${d["inc"]:,.0f} monthly income · DTI-DEMO 1.0</div></div></div>
<div class="rate" role="radiogroup" aria-label="Rating"><b>Rating <b>④</b></b><div class="rbtns"><span><kbd>1</kbd> Effective</span><span class="sel"><kbd>2</kbd> Partially effective</span><span><kbd>3</kbd> Not effective</span><span><kbd>4</kbd> N/A</span></div></div>
<label class="cmt"><b>Comment <span class="chip warn">needed for this rating</span> <b>⑤</b></b><div class="ta">Recomputed debt-to-income is 51.3% against a 40% limit (fictional). The file does not explain the difference.<span class="caret"></span></div></label>
<div class="docs"><b>Where I looked <b>⑥</b></b> <span class="ev">Credit memo p.4</span> <span class="ev">2025 tax return, Sch. E</span> <span class="ev">Credit report</span> <span class="add">+ link</span></div>
<div class="foot"><span class="btn">← Previous <kbd>K</kbd></span><span class="sp"></span><span class="cap">Saved 11:42</span><span class="btn pri">Next unrated <kbd>J</kbd> →</span></div></section>
<aside class="facts" aria-label="File facts"><div class="cap">The file at a glance <b>⑦</b></div>
<dl><dt>Borrower</dt><dd>{E(CASE["borrower"])}</dd><dt>Facilities</dt><dd>2 · $360,000 committed</dd><dt>Security</dt><dd>Secured</dd><dt>New money</dt><dd>Yes</dd><dt>Cash left after debt</dt><dd>J. Hale $77,400<br>M. Hale $34,800</dd><dt>Collateral, adjusted</dt><dd>$325,000</dd><dt>Debt-to-income</dt><dd>51.3% <span class="chip x">above limit</span></dd></dl>
<div class="cap" style="margin-top:8px">Facts come from the supporting tables. Edit them in their own tab; they are not retyped here.</div></aside></div>'''


def review_screen():
    rows = ""
    for n, s, q, _ in QS:
        r, c = CASE["ratings"][n]
        pt = next((p for p in CASE["review_points"] if p[0] == n), None)
        act = ('<span class="chip acc">Point raised</span>' if pt else '<span class="agree">✓ Agree</span>')
        rows += f'<tr><td class="mono">{n}</td><td>{E(q)}</td><td>{rchip(r)}</td><td>{E(c) or "<span class=cap>No comment</span>"}</td><td>{act}</td></tr>'
        if pt and n == "5.02":
            rows += f'<tr class="thread"><td></td><td colspan="4"><div class="q"><b>{E(pt[1])}</b> asked: {E(pt[2])}</div><div class="a"><b>{E(pt[3])}</b> answered: {E(pt[4])}</div><div class="acts"><span class="btn">Ask again</span><span class="btn pri">Clear this point</span></div></td></tr>'
    return f'''<div class="appbar"><b>Workpaper Studio</b><span>{CASE["id"]} · {E(CASE["borrower"])}</span><span class="sp"></span><span class="chip acc">In review</span><span class="who">D. Patel · Reviewer</span></div>
<div class="scr-body"><div class="hd"><div><h4>Review: {E(CASE["borrower"])}</h4><div class="cap">Tested by {E(CASE["tester"])} · 6 effective · 2 partially · 1 not effective</div></div><span class="sp"></span><span class="btn" aria-disabled="true">Sign off · 2 points open</span></div>
<div class="note">You can read every entry and the supporting tables. You cannot change a rating. Raise a point and the tester decides. <b>①</b></div>
<table class="t"><thead><tr><th>#</th><th>Question</th><th>Tester's rating</th><th>Tester's comment</th><th>You <b>②</b></th></tr></thead><tbody>{rows}</tbody></table></div>'''


def release_screen():
    items = [("✓", "ok", "Every applicable question is rated"), ("✓", "ok", "Every rating that needs a comment has one"),
             ("✓", "ok", "Every review point is cleared"), ("✓", "ok", "The debt-to-income limit is confirmed by this organization"),
             ("✓", "ok", "Signed off by D. Patel, 2026-10-16")]
    outs = [("Workpaper (PDF)", "The signed record. Four pages: conclusion, findings, every question, supporting analysis, review log.", "Saved to the case folder"),
            ("Workbook (.xlsx)", "The same record with live formulas, so anyone can check the arithmetic in Excel.", "Saved to the case folder"),
            ("Data row", "One row: identity, every rating and comment, the recomputed ratio. Feeds the quarter roll-up.", "Written to the outbox for the database (mock)")]
    return f'''<div class="appbar"><b>Workpaper Studio</b><span>{CASE["id"]}</span><span class="sp"></span><span class="chip ok">Signed off</span></div>
<div class="scr-body rel"><div><h4>Release <b>①</b></h4><ul class="gate">{"".join(f'<li><span class="{k}">{i}</span>{E(t)}</li>' for i, k, t in items)}</ul><div class="cap">If any line fails, Release is blocked and the line says what to do.</div></div>
<div><h4>What goes out <b>②</b></h4>{"".join(f'<div class="out"><b>{E(a)}</b><div>{E(b)}</div><div class="cap">{E(c)}</div></div>' for a, b, c in outs)}<span class="btn pri" style="margin-top:8px">Release all three</span></div></div>'''


def rollup_screen():
    return f'''<div class="appbar"><b>Workpaper Studio</b><span>Quarter roll-up</span><span class="sp"></span><span class="who">Head of credit review</span></div>
<div class="scr-body"><div class="hd"><div><h4>2026-Q3 · 12 credits</h4><div class="cap">Click a question to see its findings. Click a finding to open the workpaper.</div></div><span class="sp"></span><div class="seg"><span class="on">2026-Q3</span><span>2026-Q2</span><span>Compare</span></div><div class="seg"><span class="on">All testers</span></div></div>
<div class="roll"><div class="rl-left">The table is the roll-up document's own table, live. <b>①</b><br><br>Selected: <b>2.02 Industry code</b> · 5 not effective of 12</div>
<div class="rl-right"><b>Findings for 2.02 <b>②</b></b>{"".join(f'<div class="fi"><span class="mono">{s["id"]}</span> {E(s["borrower"])}<span class="cap"> · Industry code differs between system and approval.</span></div>' for s in F["sample"][3:6])}<div class="cap">…and 2 more. Each opens the signed workpaper at question 2.02.</div></div></div></div>'''


NOTES = {
    "queue": ["One row per credit in the sample. The stage is worked out from the record, never typed.",
              "The tester sees their files first. The reviewer's default view is “Waiting for review”.",
              "Findings appear only once a file is rated, so an empty file never reads as clean."],
    "testing": ["<b>①</b> The question list shows every question's state at a glance: rated and how, waiting on an answer elsewhere, or not yet rated. Questions that do not apply drop out on their own.",
                "<b>②</b> The test steps sit with the question. They are the expert's know-how, written once in the pack.",
                "<b>③</b> Anything the supporting tables work out is shown where it is needed. It informs the rating; it never sets it.",
                "<b>④</b> Rate with one key: 1 to 4. <kbd>J</kbd> jumps to the next unrated question, <kbd>K</kbd> goes back. A tester can do a whole file without the mouse.",
                "<b>⑤</b> A comment becomes required the moment the rating calls for one, and only then.",
                "<b>⑥</b> Evidence is a reference (document, page), not a copy of the document.",
                "<b>⑦</b> The facts panel is read-only. Supporting numbers are edited in their own tab, once."],
    "review": ["<b>①</b> The reviewer reads everything and changes nothing. Their tool is the question.",
               "<b>②</b> Agree with a row in one click, or raise a point on it. Sign-off stays blocked until every point is cleared.",
               "The tester's answer sits under the question, so the record shows the conversation, not just the outcome."],
    "release": ["<b>①</b> Release is a check that blocks, not a warning. Each line names its fix.",
                "<b>②</b> The three outputs on this page are what Release produces. The data row is what the roll-up is built from."],
    "rollup": ["<b>①</b> The manager's screen is the roll-up document with clicks: every figure opens its cases.",
               "<b>②</b> A finding links back to the signed workpaper, so a number on a slide can always be traced to a file."],
}

SCREENS = [("queue", "The sample queue", "Where a tester starts the day.", queue_screen()),
           ("testing", "Testing a file", "The screen people live in. One question at a time, with the whole file one glance away.", testing_screen()),
           ("review", "Reviewing a file", "The reviewer asks; the tester decides.", review_screen()),
           ("release", "Releasing", "Nothing leaves until it passes.", release_screen()),
           ("rollup", "The quarter, on screen", "For whoever reports on the quarter.", rollup_screen())]

feed_head = "".join(f"<th>{E(c)}</th>" for c in F["feed_cols"])
feed_rows = "".join("<tr>" + "".join(f"<td>{E(str(r[c]))}</td>" for c in F["feed_cols"]) + "</tr>" for r in F["feed"])

PAGE = f'''<title>Workpaper Studio Outputs</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@600&display=swap">
<style>
/* Layout: one long page. Each output is shown as it really is (paper, workbook, data), then the screens that produce it. */
:root{{--bg:#e9edf2;--surface:#fff;--surface-2:#f4f6f9;--line:#d5dbe3;--ink:#131a23;--ink-2:#434d5a;--ink-3:#5f6a78;--accent:#1c4f8f;--accent-ink:#fff;--accent-soft:#e1ebf8;
--ok:#17673f;--ok-bg:#e0f1e8;--warn:#7f4a00;--warn-bg:#fcefcf;--err:#a1241b;--err-bg:#fbe5e2;--calc:#edf1f7;--shadow:0 6px 24px rgba(15,25,40,.14);
--sans:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0e1217;--surface:#161b22;--surface-2:#1b212a;--line:#2b3441;--ink:#e8ecf1;--ink-2:#b3bcc8;--ink-3:#8c98a8;--accent:#86b6f0;--accent-ink:#0a1a2e;--accent-soft:#1a2b43;--ok:#62d29b;--ok-bg:#12301f;--warn:#f0bb62;--warn-bg:#392a0d;--err:#ff938a;--err-bg:#3c1815;--calc:#1b2431;--shadow:0 6px 24px rgba(0,0,0,.5);color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0e1217;--surface:#161b22;--surface-2:#1b212a;--line:#2b3441;--ink:#e8ecf1;--ink-2:#b3bcc8;--ink-3:#8c98a8;--accent:#86b6f0;--accent-ink:#0a1a2e;--accent-soft:#1a2b43;--ok:#62d29b;--ok-bg:#12301f;--warn:#f0bb62;--warn-bg:#392a0d;--err:#ff938a;--err-bg:#3c1815;--calc:#1b2431;--shadow:0 6px 24px rgba(0,0,0,.5);color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:400 15px/1.5 var(--sans);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 80px}}
.wrap{{max-width:1120px;margin:0 auto}}
h1{{font-size:28px;margin:0 0 6px;font-weight:600;text-wrap:balance}} h2{{font-size:21px;margin:0;font-weight:600}} h3{{font-size:15px;margin:0}}
p{{max-width:68ch;margin:0 0 8px}} .lead{{color:var(--ink-2);font-size:16px}}
.cap{{font-size:12px;color:var(--ink-3)}} .mono{{font-family:var(--mono);font-size:12px}} .num{{text-align:right;font-variant-numeric:tabular-nums}}
nav.toc{{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 26px}} nav.toc a{{text-decoration:none;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:4px 12px;font-size:13px}}
nav.toc b{{color:var(--ink-3);font-weight:500;font-size:12px;align-self:center;margin-right:4px}}
section.blk{{margin:0 0 40px;scroll-margin-top:16px}}
.blk>header{{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin-bottom:8px}}
.meta{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--ink-2);margin-bottom:10px}} .meta b{{color:var(--ink)}}
.files{{font-size:12px;color:var(--ink-3);margin-top:8px}} .files code{{font-family:var(--mono);background:var(--surface-2);padding:1px 5px;border-radius:3px}}
.paperwrap{{background:#d9dde3;border-radius:8px;padding:22px;overflow-x:auto}}
.paperx{{background:#fff;color:#141414;max-width:800px;min-width:620px;margin:0 auto;box-shadow:0 4px 18px rgba(0,0,0,.18);padding:34px 40px;font:10.5px/1.45 var(--sans)}}
{scope_css(F["paper_css"], ".paperx")}
.tabs{{display:flex;gap:2px;flex-wrap:wrap;border-bottom:1px solid var(--line)}}
.tabs button{{border:1px solid var(--line);border-bottom:0;background:var(--surface-2);padding:5px 12px;border-radius:6px 6px 0 0;font:inherit;font-size:13px;color:var(--ink-2);cursor:pointer}}
.tabs button[aria-selected="true"]{{background:var(--surface);color:var(--ink);font-weight:500}}
.sheet{{background:var(--surface);border:1px solid var(--line);border-top:0;overflow-x:auto;padding:0}}
.sheet table{{border-collapse:collapse;font-size:12.5px;min-width:100%}}
.sheet td,.sheet th{{border:1px solid var(--line);padding:4px 8px;vertical-align:top;text-align:left;max-width:340px}}
.sheet th{{background:#1f2a37;color:#fff;font-weight:500}}
.sheet td.f{{background:var(--calc)}} .sheet .fx{{display:block;font-family:var(--mono);font-size:10.5px;color:var(--accent)}}
.data{{overflow:auto;max-height:340px;background:var(--surface);border:1px solid var(--line);border-radius:6px}}
.data table{{border-collapse:collapse;font-size:12px;white-space:nowrap}} .data th,.data td{{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left}} .data th{{position:sticky;top:0;background:var(--surface-2);font-weight:500}}
pre.json{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:12px;overflow:auto;max-height:340px;font:12px/1.5 var(--mono);margin:8px 0 0}}
/* screens */
.screen{{background:var(--surface);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);overflow:hidden}}
.scrwrap{{overflow-x:auto;padding:4px}} .scrwrap .screen{{min-width:880px}}
.appbar{{display:flex;gap:14px;align-items:center;padding:8px 14px;border-bottom:1px solid var(--line);font-size:13px;color:var(--ink-2)}} .appbar b{{color:var(--ink)}} .sp{{flex:1}}
.who{{font-size:12px;color:var(--ink-3)}}
.scr-body{{padding:14px 16px}} .hd{{display:flex;gap:12px;align-items:center;margin-bottom:10px;flex-wrap:wrap}} h4{{margin:0;font-size:16px}}
.seg{{display:inline-flex;border:1px solid var(--line);border-radius:4px;overflow:hidden;font-size:12.5px}} .seg span{{padding:3px 10px;color:var(--ink-2)}} .seg span+span{{border-left:1px solid var(--line)}} .seg .on{{background:var(--accent-soft);color:var(--accent);font-weight:500}}
.prog{{height:5px;background:var(--surface-2);border-radius:3px;overflow:hidden;margin-bottom:10px}} .prog i{{display:block;height:100%;background:var(--accent)}}
table.t{{border-collapse:collapse;width:100%;font-size:13px}} .t th{{text-align:left;font-weight:500;font-size:12px;color:var(--ink-3);padding:6px 8px;border-bottom:1px solid var(--line);background:var(--surface-2)}} .t td{{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}}
.t tr.me td{{background:var(--accent-soft)}}
.chip{{display:inline-flex;font-size:12px;line-height:18px;padding:0 8px;border-radius:9px;background:var(--surface-2);color:var(--ink-2);white-space:nowrap;border:1px solid var(--line)}}
.chip.ok{{background:var(--ok-bg);color:var(--ok);border-color:transparent}} .chip.warn{{background:var(--warn-bg);color:var(--warn);border-color:transparent}} .chip.acc{{background:var(--accent-soft);color:var(--accent);border-color:transparent}} .chip.x{{background:var(--err-bg);color:var(--err);border-color:transparent}}
.r{{font-size:12px;white-space:nowrap;font-weight:500}} .r.e{{color:var(--ok)}} .r.p{{color:var(--warn)}} .r.x{{color:var(--err)}} .r.na{{color:var(--ink-3)}}
.btn{{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--line);border-radius:4px;padding:4px 12px;font-size:13px;font-weight:500;background:var(--surface)}} .btn.pri{{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}} .btn[aria-disabled]{{opacity:.6}}
kbd{{font:11px var(--mono);border:1px solid var(--line);border-bottom-width:2px;border-radius:3px;padding:0 4px;background:var(--surface-2);color:var(--ink-2)}} .btn.pri kbd{{background:transparent;color:inherit;border-color:rgba(255,255,255,.5)}}
.test3{{display:grid;grid-template-columns:250px 1fr 230px;min-height:520px}}
.qnav{{border-right:1px solid var(--line);background:var(--surface-2)}} .qnav ul{{list-style:none;margin:0;padding:0 6px 10px}} .qnav li{{display:grid;grid-template-columns:20px 38px 1fr;gap:4px;padding:6px;border-radius:4px;font-size:12.5px;align-items:start}} .qnav li.cur{{background:var(--accent-soft)}}
.qnav .ql{{color:var(--ink-2);overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}}
.ic{{width:18px;height:18px;border-radius:50%;display:grid;place-items:center;font-size:11px;border:1.5px solid var(--line);color:var(--ink-3)}} .ic.e{{background:var(--ok);border-color:var(--ok);color:var(--surface)}} .ic.p{{border-color:var(--warn);color:var(--warn)}} .ic.x{{background:var(--err);border-color:var(--err);color:var(--surface)}}
.focus{{padding:16px 20px;display:grid;gap:12px;align-content:start}} .focus h5{{font-size:19px;margin:0;line-height:1.3;font-weight:600}}
.focus details p{{font-size:13.5px;color:var(--ink-2);margin:4px 0 0}} .focus summary{{font-size:13px;color:var(--accent);cursor:pointer}}
.calcbox{{background:var(--calc);border-radius:6px;padding:8px 10px;margin-top:4px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}} .big{{font-size:22px;font-variant-numeric:tabular-nums}}
.rbtns{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:4px}} .rbtns span{{border:1px solid var(--line);border-radius:6px;padding:8px;font-size:13.5px;text-align:center}} .rbtns .sel{{border:2px solid var(--warn);background:var(--warn-bg);color:var(--warn);font-weight:600}}
.ta{{border:1px solid var(--line);border-radius:6px;padding:8px 10px;font-size:13.5px;margin-top:4px;min-height:60px}} .caret{{display:inline-block;width:1px;height:15px;background:var(--ink);vertical-align:-2px;margin-left:1px}}
.ev{{font-family:var(--mono);font-size:12px;background:var(--accent-soft);color:var(--accent);padding:1px 7px;border-radius:3px}} .add{{font-size:12px;color:var(--accent)}}
.foot{{display:flex;gap:10px;align-items:center;border-top:1px solid var(--line);padding-top:10px}}
.facts{{border-left:1px solid var(--line);padding:12px 14px;background:var(--surface-2)}} .facts dl{{margin:6px 0 0;display:grid;gap:2px}} .facts dt{{font-size:11.5px;color:var(--ink-3)}} .facts dd{{margin:0 0 6px;font-size:13px;font-variant-numeric:tabular-nums}}
.note{{background:var(--accent-soft);border-radius:6px;padding:8px 12px;font-size:13px;margin-bottom:10px}}
.agree{{font-size:12.5px;color:var(--ok)}} tr.thread td{{background:var(--surface-2)}} .thread .q,.thread .a{{font-size:13px;margin:2px 0}} .thread .acts{{display:flex;gap:6px;margin-top:6px}}
.rel{{display:grid;grid-template-columns:1fr 1.2fr;gap:24px}} .gate{{list-style:none;padding:0;margin:8px 0}} .gate li{{display:flex;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13.5px}} .gate .ok{{color:var(--ok);font-weight:700}}
.out{{border:1px solid var(--line);border-radius:6px;padding:8px 10px;margin-top:8px;font-size:13.5px}}
.roll{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .rl-left{{background:var(--surface-2);border-radius:6px;padding:12px;font-size:13.5px}} .fi{{font-size:13px;padding:6px 0;border-bottom:1px solid var(--line)}}
.how{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));gap:6px 22px;margin:12px 0 0;padding:0;list-style:none;font-size:14px;color:var(--ink-2)}} .how li{{padding-left:0}} .how b{{color:var(--accent)}}
.screen h5 b,.screen h4 b,.screen summary b,.screen .cap b,.screen label b b,.screen .evid>b b,.screen .rate>b b,.screen .docs>b b,.screen th b,.screen .note b,.screen .rl-left b:last-child{{color:var(--accent)}}
@media (max-width:760px){{.paperwrap{{padding:10px}}}}
</style>
<div class="wrap">
<header><h1>What comes out, and how people get there</h1>
<p class="lead">One finished credit file review and a quarter's sample of twelve, all synthetic. First the four outputs exactly as the files contain them, then the screens that produce them. The methods and limits are fictional, and the wording is example text, not any organization's policy.</p>
<nav class="toc" aria-label="On this page"><b>Outputs</b><a href="#workpaper">The signed workpaper</a><a href="#workbook">The workbook</a><a href="#feed">The data feed</a><a href="#rollup">The quarter roll-up</a><b>Screens</b>{"".join(f'<a href="#scr-{k}">{E(t)}</a>' for k, t, _, _ in SCREENS)}</nav></header>

<section class="blk" id="workpaper"><header><h2>The signed workpaper</h2><span class="chip">PDF</span></header>
<div class="meta"><span><b>Who gets it</b> the file, the reviewer, an examiner</span><span><b>When</b> at sign-off</span><span><b>What it is for</b> the record of what was tested, found and agreed</span></div>
<div class="paperwrap"><div class="paperx">{F["workpaper"]}</div></div>
<div class="files">In the repository: <code>workpaper-studio/examples/out/{CASE["id"]}-workpaper.pdf</code> (2 pages) and the same as HTML.</div></section>

<section class="blk" id="workbook"><header><h2>The workbook</h2><span class="chip">.xlsx</span></header>
<div class="meta"><span><b>Who gets it</b> anyone who wants to check the arithmetic</span><span><b>When</b> at sign-off</span><span><b>What it is for</b> the same record, with live formulas</span></div>
<p class="cap">Tinted cells are formulas. The blue line under each is the formula itself; the value above it is what LibreOffice calculated when it opened the file.</p>
<div class="tabs" role="tablist">{"".join(f'<button type="button" role="tab" aria-selected="{str(i == 0).lower()}" data-sheet="{i}">{E(n)}</button>' for i, n in enumerate(SHEETS))}</div>
{"".join(f'<div class="sheetpane" data-pane="{i}"{"" if i == 0 else " hidden"}>{sheet_html(n)}</div>' for i, n in enumerate(SHEETS))}
<div class="files">In the repository: <code>workpaper-studio/examples/out/{CASE["id"]}.xlsx</code>. <code>check_workbook.py</code> recalculates it in LibreOffice and compares 12 results with independent arithmetic.</div></section>

<section class="blk" id="feed"><header><h2>The data feed</h2><span class="chip">CSV</span><span class="chip">JSON</span></header>
<div class="meta"><span><b>Who gets it</b> the database behind the roll-up</span><span><b>When</b> at release</span><span><b>What it is for</b> counting across files without opening them</span></div>
<p class="cap">One row per credit, one column per question. Adding a question to the pack adds a column. Not applicable is written as such, never as effective.</p>
<div class="data" tabindex="0" aria-label="Feed rows"><table><thead><tr>{feed_head}</tr></thead><tbody>{feed_rows}</tbody></table></div>
<p class="cap" style="margin-top:12px">The same credit as a full record, with every value's state spelled out:</p>
<pre class="json" tabindex="0">{E(json.dumps(F["record"], indent=2))}</pre>
<div class="files">In the repository: <code>out/feed-2026-Q3.csv</code> and <code>out/{CASE["id"]}.record.json</code>. The format is a proposal until the receiving system's owner confirms it.</div></section>

<section class="blk" id="rollup"><header><h2>The quarter roll-up</h2><span class="chip">PDF</span></header>
<div class="meta"><span><b>Who gets it</b> the head of credit review, a committee</span><span><b>When</b> at quarter end</span><span><b>What it is for</b> where the weaknesses are, and the findings behind each</span></div>
<div class="paperwrap"><div class="paperx">{F["rollup"]}</div></div>
<div class="files">In the repository: <code>out/rollup-2026-Q3.pdf</code>. Built from the feed rows above, so every figure traces to a signed workpaper.</div></section>

{"".join(f'<section class="blk" id="scr-{k}"><header><h2>{E(t)}</h2><span class="chip acc">Proposed screen</span></header><p class="cap">{E(sub)}</p><div class="scrwrap"><div class="screen">{body}</div></div><ul class="how">{"".join(f"<li>{n}</li>" for n in NOTES[k])}</ul></section>' for k, t, sub, body in SCREENS)}
</div>
<script>
document.querySelectorAll('.tabs button').forEach(function(b){{b.addEventListener('click',function(){{
  document.querySelectorAll('.tabs button').forEach(function(x){{x.setAttribute('aria-selected',String(x===b))}});
  document.querySelectorAll('.sheetpane').forEach(function(p){{p.hidden=p.dataset.pane!==b.dataset.sheet}});
}})}});
</script>
'''
DEST.write_text(PAGE)
print("wrote", DEST, len(PAGE), "bytes")
