"""Render the tie-out: the Markdown source to one self-contained HTML page, every picture embedded, then to a PDF
through canon's checker (check_tie_out.render), which refuses unless the roster adds to the headline, the three
named sections are there and a source picture carries red ink.

    python3 build.py work/tallies.json     # canon's check_tie_out.py found in the installed plugin, or CANON=<dir>

The roster and the per-tab tables are written from the tallies roster.py made, never typed: <!--ROSTER--> and
<!--TABS:run--> in the Markdown are where they go, and the headline is the tallies' own total.
Needs the `markdown` package and Chrome or Chromium (CHROME=<path> if it is not where canon looks).
"""
import base64
import glob
import json
import os
import re
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
NAME = "TIE-OUT-pocketbook-every-figure-2026-09-28"
T = json.load(open(sys.argv[1]))
ORDER = ["DIFFERS", "COULD NOT", "TIED-WITHIN-SAMPLING", "TIED", "NAME", "ECHO", "NOT A FIGURE"]
CLS = {"DIFFERS": "differs", "COULD NOT": "couldnot", "TIED-WITHIN-SAMPLING": "sampling", "TIED": "tied",
       "NAME": "other", "ECHO": "other", "NOT A FIGURE": "other"}
MEANS = {
    "DIFFERS": "worked out both ways, and they disagree",
    "COULD NOT": "no independent figure could be made; the note in roster.csv names the obstacle",
    "TIED-WITHIN-SAMPLING": "both roads shuffled or sampled at random, each with its own random numbers, and the two "
                            "agree within four standard errors",
    "TIED": "worked out both ways, and they agree (to nine significant figures, or to the last digit the cell shows)",
    "NAME": "a band's or segment's name holding a digit, such as 496 - 653: made the same way from the file",
    "ECHO": "the analyst's own answer, or a fixed setting, shown back (95% sure, 20 bars): nothing to work out",
    "NOT A FIGURE": "words that hold a digit: a date in a heading, a cell name in an instruction, a file's fingerprint",
}
RUNS = {"bleed": "Where the book bleeds", "scout": "Test new variables"}


def canon_dir() -> str:
    if os.environ.get("CANON"):
        return os.environ["CANON"]
    found = sorted(glob.glob(os.path.expanduser("~/.claude/plugins/cache/*/canon/*/check_tie_out.py")),
                   key=lambda p: [int(x) for x in re.findall(r"/(\d+)\.(\d+)\.(\d+)/", p)[0]])
    if not found:
        raise SystemExit("canon's check_tie_out.py not found; set CANON to the folder that holds it")
    return str(Path(found[-1]).parent)


def chrome() -> str | None:
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return found[-1] if found else None


def embed(html: str) -> str:
    def sub(m):
        data = base64.b64encode((HERE / m.group(1)).read_bytes()).decode()
        return f'src="data:image/png;base64,{data}"'
    return re.sub(r'src="([^"]+\.png)"', sub, html)


def n(x):
    return f"{x:,}"


def roster_html():
    rows = []
    for v in ORDER:
        c = T["by_verdict"][v]
        if not c:
            continue
        b, s = T["by_run"]["bleed"][v], T["by_run"]["scout"][v]
        rows.append(f'<tr><td><span class="v {CLS[v]}">{v}</span></td><td class="r" data-tieout="count">{n(c)}</td>'
                    f'<td class="r">{n(b)}</td><td class="r">{n(s)}</td><td>{MEANS[v]}</td></tr>')
    return ('<table data-tieout="roster"><thead><tr><th>Verdict</th><th class="r">Cells</th>'
            '<th class="r">Bleed run</th><th class="r">New-variable run</th><th>Meaning</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def tabs_html(run):
    used = [v for v in ORDER if any(T["by_tab"].get(k, {}).get(v) for k in T["by_tab"] if k.startswith(run + "|"))]
    head = "".join(f'<th class="r">{v.replace("TIED-WITHIN-SAMPLING", "WITHIN SAMPLING")}</th>' for v in used)
    rows = []
    tot = {v: 0 for v in used}
    for k, c in T["by_tab"].items():
        r, tab = k.split("|")
        if r != run:
            continue
        cells = "".join(f'<td class="r">{n(c.get(v, 0)) if c.get(v, 0) else "·"}</td>' for v in used)
        rows.append(f"<tr><td>{tab}</td>{cells}<td class=\"r\"><b>{n(sum(c.values()))}</b></td></tr>")
        for v in used:
            tot[v] += c.get(v, 0)
    rows.append("<tr><td><b>All</b></td>" + "".join(f'<td class="r"><b>{n(tot[v])}</b></td>' for v in used)
                + f'<td class="r"><b>{n(sum(tot.values()))}</b></td></tr>')
    return (f'<table class="tabs"><thead><tr><th>Tab</th>{head}<th class="r">All</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


CSS = (Path(__file__).resolve().parent.parent / "2026-09-28" / "build.py").read_text().split('CSS = """')[1] \
    .split('"""')[0] + """
.v.sampling { color:#1f4f7a; background:#eef3f9; border:1px solid #b8cbe0; }
.v.other { color:#525a64; background:#f3f2ef; border:1px solid #d8d3ca; }
table.tabs td, table.tabs th { font-size:8pt; padding:3px 6px 3px 0; }
"""


# side-by-side blocks, filled from roster.csv: (run, cell as roster.csv writes it) for each line
EXCERPTS = {
    "start": [("bleed", "Start here!D17"), ("bleed", "Start here!E20"), ("bleed", "Start here!F20"),
              ("bleed", "Start here!F17")],
    "pockets": [("bleed", "Pockets!G21 [view-00]"), ("bleed", "Pockets!H21 [view-00]"),
                ("bleed", "Pockets!I21 [view-00]"), ("bleed", "Pockets!J21 [view-00]"),
                ("bleed", "Pockets!L21 [view-00]"), ("bleed", "Pockets!N21 [view-00]"),
                ("bleed", "Pockets!L21 [view-02]"), ("bleed", "Pockets!L23 [view-03]"),
                ("bleed", "Pockets!K23 [view-03]")],
    "grids": [("bleed", "Grids!D17 [view-00]"), ("bleed", "Grids!O17 [view-00]"), ("bleed", "Grids!D28 [view-00]"),
              ("bleed", "Grids!Q35 [view-00]"), ("bleed", "Grids!G45 [view-00]"), ("bleed", "Grids!F64 [view-00]"),
              ("bleed", "Grids!E17 [view-23]"), ("bleed", "Grids!E28 [view-23]")],
    "split": [("bleed", "Split!E18 [view-00]"), ("bleed", "Split!F18 [view-00]"), ("bleed", "Split!G18 [view-00]"),
              ("bleed", "Split!H18 [view-00]"), ("bleed", "Split!I18 [view-00]"), ("bleed", "Split!G19 [view-00]"),
              ("bleed", "Split!J30 [view-00]")],
    "pck": [("bleed", "Paid, cost, kept!E20 [view-00]"), ("bleed", "Paid, cost, kept!F20 [view-00]"),
            ("bleed", "Paid, cost, kept!I20 [view-00]"), ("bleed", "Paid, cost, kept!J20 [view-00]"),
            ("bleed", "Paid, cost, kept!K20 [view-00]"), ("bleed", "Paid, cost, kept!K21 [view-00]")],
    "record": [("bleed", "Record!C16"), ("bleed", "Record!C31"), ("bleed", "Record!C34"), ("bleed", "Record!C43"),
               ("bleed", "Record!F43"), ("bleed", "Record!C69"), ("bleed", "Control!P16")],
    "look": [("bleed", "Look!C16"), ("bleed", "Look!C17"), ("bleed", "Look!C70"), ("bleed", "Look!_look!H7"),
             ("scout", "Look!_look!BU7"), ("scout", "Look!_look!BU8")],
    "newvar": [("scout", "New variables!I45"), ("scout", "New variables!J45"), ("scout", "New variables!M120"),
               ("scout", "New variables!N171"), ("scout", "New variables!F104"), ("scout", "New variables!H33"),
               ("scout", "New variables!I33"), ("scout", "New variables!K34"), ("scout", "New variables!L34"),
               ("scout", "New variables!L45"), ("scout", "New variables!C17")],
    "scouting": [("scout", "Scouting!C8"), ("scout", "Scouting!C9"), ("scout", "New variables!C29"),
                 ("scout", "Scouting!D24"), ("scout", "Scouting!E24"), ("scout", "Scouting!C26"),
                 ("scout", "Scouting!D66"), ("scout", "Scouting!G19")],
}


def excerpt(name, roster):
    by = {(r["run"], r["cell"]): r for r in roster}
    out = [f"{'cell':<34} {'workbook (ours)':>24} {'loan file (source)':>24}  verdict"]
    for run, cell in EXCERPTS[name]:
        r = by.get((run, cell))
        if r is None:
            raise SystemExit(f"excerpt {name}: {run} {cell} is not in roster.csv")
        ours, src = r["ours"], r["source"]
        ours = ours if len(ours) <= 24 else ours[:22] + "…"
        src = src if len(src) <= 24 else src[:22] + "…"
        out.append(f"{cell.replace(' [view-', ' [v'):<34} {ours:>24} {src:>24}  {r['verdict']}")
    return "```\n" + "\n".join(out) + "\n```"


def main():
    sys.path.insert(0, canon_dir())
    import csv
    roster = list(csv.DictReader(open(HERE / "roster.csv", newline="", encoding="utf-8")))
    import check_tie_out

    src = (HERE / f"{NAME}.md").read_text(encoding="utf-8")
    src = src.replace("<!--HEADLINE-->", n(T["total"]))
    src = src.replace("<!--ROSTER-->", roster_html())
    for run in RUNS:
        src = src.replace(f"<!--TABS:{run}-->", tabs_html(run))
    for name in EXCERPTS:
        src = src.replace(f"<!--EXCERPT:{name}-->", excerpt(name, roster))
    for v in ORDER:
        src = src.replace(f"<!--COUNT:{v}-->", n(T["by_verdict"][v]))
        for run in RUNS:
            src = src.replace(f"<!--COUNT:{run}:{v}-->", n(T["by_run"][run][v]))
    left = re.findall(r"<!--[A-Z]+[:A-Z a-z-]*-->", src)
    if left:
        raise SystemExit(f"placeholders left unfilled: {left}")
    body = markdown.markdown(src, extensions=["tables", "fenced_code", "md_in_html"])
    html = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>PocketBook full tie-out</title><style>{CSS}</style></head>"
            f'<body><div class="sheet">{embed(body)}</div></body></html>\n')
    (HERE / f"{NAME}.html").write_text(html, encoding="utf-8")
    check_tie_out.render(html, HERE / f"{NAME}.pdf", what="the PocketBook full tie-out", chrome=chrome())


if __name__ == "__main__":
    main()
