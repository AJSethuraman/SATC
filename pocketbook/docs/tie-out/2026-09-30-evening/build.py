"""Render the tie-out: the Markdown source to one self-contained HTML page, every picture embedded, then to a PDF
through canon's checker (check_tie_out.render), which refuses unless the roster adds to the headline, the three
named sections are there and a source picture carries red ink. (The full tie-out's build.py, 28 Sep 2026.)

    python3 build.py work/tallies.json     # canon's check_tie_out.py found in the installed plugin, or CANON=<dir>

Every count is written from the tallies roster.py made, never typed: <!--HEADLINE-->, <!--COUNT:verdict-->,
<!--CHANGES-->, <!--ROSTER-->, <!--RERUN--> and <!--EXCERPT:name--> in the Markdown are where they go.
"""
import base64
import csv
import glob
import json
import os
import re
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
NAME = "TIE-OUT-pocketbook-evening-2026-09-30"
T = json.load(open(sys.argv[1]))
WORK = Path(sys.argv[1]).resolve().parent
ORDER = ["DIFFERS", "COULD NOT", "TIED-WITHIN-SAMPLING", "TIED", "NAME", "ECHO", "NOT A FIGURE"]
CLS = {"DIFFERS": "differs", "COULD NOT": "couldnot", "TIED-WITHIN-SAMPLING": "sampling", "TIED": "tied",
       "NAME": "other", "ECHO": "other", "NOT A FIGURE": "other"}
MEANS = {
    "DIFFERS": "worked out both ways, and they disagree",
    "COULD NOT": "no independent figure could be made; the note in roster.csv names the obstacle",
    "TIED-WITHIN-SAMPLING": "both roads shuffled at random, each with its own random numbers, and the two agree within "
                            "four standard errors",
    "TIED": "worked out both ways, and they agree (to nine significant figures, to the last digit the cell shows, or "
            "word for word)",
    "NAME": "a band's or segment's name holding a digit, such as 496 - 653: made the same way from the file",
    "ECHO": "the analyst's own answer, or a fixed setting, shown back (95% sure, 20 bars): nothing to work out",
    "NOT A FIGURE": "words that hold a digit: a date in a heading, a cell name in an instruction, a file's name",
}
CHANGE_NAMES = {"1": "1 · Grids: grey thin cells", "2": "2 · The book's figure in the heading",
                "3": "3 · Filter by: Only loans where <column> is <value>", "4": "4 · Loan size",
                "5": "5 · Look: percentiles, grey lines, short labels", "6": "6 · Borderline",
                "7": "7 · Column widths (one row a column)",
                "8": "8 · ORIG_YEAR as Split by", "9": "9 · Band labels on whole-number columns", "R": "Re-run of 29 Sep's checks on this build"}
RUN_NAMES = {"q3": "Q3", "scout": "Scouting", "flag": "Flag", "two": "Two-flag", "grey": "Grey", "year": "Year",
             "yearsplit": "Year-split", "widths-year": "Widths Year", "widths-yearsplit": "Widths Year-split",
             "bureau": "Bureau", "q3-0929": "Q3, 29 Sep's views", "flag-0929": "Flag, 29 Sep's views",
             "two-0929": "Two-flag, 29 Sep's views", "widths-q3": "Widths Q3", "widths-flag": "Widths Flag",
             "widths-two": "Widths Two-flag", "widths-grey": "Widths Grey", "widths-bureau": "Widths Bureau",
             "widths-scout": "Widths Scouting"}


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


def checked(c):
    """The figures worked out both ways: everything but names, echoes and words."""
    return sum(c[v] for v in ("DIFFERS", "COULD NOT", "TIED-WITHIN-SAMPLING", "TIED"))


def changes_html():
    heads = "".join(f'<th class="r">{v.replace("TIED-WITHIN-SAMPLING", "WITHIN SAMPLING")}</th>'
                    for v in ("TIED", "TIED-WITHIN-SAMPLING", "DIFFERS", "COULD NOT"))
    rows = []
    for c, name in CHANGE_NAMES.items():
        t = T["by_change"][c]
        den = checked(t)
        cells = "".join(f'<td class="r">{n(t[v]) if t[v] else "·"}</td>'
                        for v in ("TIED", "TIED-WITHIN-SAMPLING", "DIFFERS", "COULD NOT"))
        other = t["NAME"] + t["ECHO"] + t["NOT A FIGURE"]
        rows.append(f'<tr><td>{name}</td>{cells}<td class="r"><b>{n(den)}</b></td><td class="r">{n(other)}</td></tr>')
    tot = {v: sum(T["by_change"][c][v] for c in CHANGE_NAMES) for v in ORDER}
    rows.append("<tr><td><b>All</b></td>" + "".join(f'<td class="r"><b>{n(tot[v])}</b></td>' for v in
                ("TIED", "TIED-WITHIN-SAMPLING", "DIFFERS", "COULD NOT")) +
                f'<td class="r"><b>{n(checked(tot))}</b></td><td class="r">{n(tot["NAME"] + tot["ECHO"] + tot["NOT A FIGURE"])}'
                f"</td></tr>")
    return (f'<table class="tabs"><thead><tr><th>Change</th>{heads}<th class="r">Worked out both ways</th>'
            f'<th class="r">Names, echoes, words</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def roster_html():
    runs = list(T["by_run"])
    rows = []
    for v in ORDER:
        c = T["by_verdict"][v]
        if not c:
            continue
        per = "".join(f'<td class="r">{n(T["by_run"][r][v]) if T["by_run"][r][v] else "·"}</td>' for r in runs)
        rows.append(f'<tr><td><span class="v {CLS[v]}">{v}</span></td><td class="r" data-tieout="count">{n(c)}</td>'
                    f'{per}<td>{MEANS[v]}</td></tr>')
    heads = "".join(f'<th class="r">{RUN_NAMES.get(r, r)}</th>' for r in runs)
    return ('<table data-tieout="roster" class="tabs"><thead><tr><th>Verdict</th><th class="r">Cells</th>' + heads +
            "<th>Meaning</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def rerun_html():
    R = json.load(open(WORK / "rerun.json"))
    rows = []
    for run, name in (("q3", "Consumer book Q3"), ("flag", "Flag book"), ("two", "Two-flag book"),
                      ("bureau", "Bureau book"), ("scout", "Scouting book (new variables)")):
        d = R[run]
        t = d["tally"]
        same = t.get("same figure, same verdict", 0)
        moved_verdict = sum(v for k, v in t.items() if "->" in k)
        moved_fig = sum(v for k, v in t.items() if k.startswith("figure moved"))
        rows.append(f"<tr><td>{name}</td><td class='r'>{n(d['cells read on 28 Sep'])}</td><td class='r'>{n(same)}</td>"
                    f"<td class='r'>{n(moved_fig)}</td><td class='r'>{n(moved_verdict)}</td>"
                    f"<td class='r'>{n(t.get('not read on this build', 0))}</td>"
                    f"<td class='r'><b>{n(len(d['tied then, not now']))}</b></td></tr>")
    return ("<table class='tabs'><thead><tr><th>Book</th><th class='r'>Cells read on 29 Sep</th>"
            "<th class='r'>Same figure, same verdict</th><th class='r'>Figure moved</th>"
            "<th class='r'>Verdict moved</th><th class='r'>Not on this build</th>"
            "<th class='r'>Tied then, not now</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


CSS = (HERE.parent / "2026-09-28" / "build.py").read_text().split('CSS = """')[1].split('"""')[0] + """
.v.sampling { color:#1f4f7a; background:#eef3f9; border:1px solid #b8cbe0; }
.v.other { color:#525a64; background:#f3f2ef; border:1px solid #d8d3ca; }
table.tabs td, table.tabs th { font-size:8pt; padding:3px 6px 3px 0; }
"""

EXCERPTS = json.load(open(HERE / "excerpts.json")) if (HERE / "excerpts.json").exists() else {}


def excerpt(name, roster):
    by = {(r["run"], r["cell"]): r for r in roster}
    out = [f"{'cell':<30} {'workbook (ours)':>26} {'loan file (source)':>26}  verdict"]
    for run, cell in EXCERPTS[name]:
        r = by.get((run, cell))
        if r is None:
            raise SystemExit(f"excerpt {name}: {run} {cell} is not in roster.csv")
        ours, src = r["ours"], r["source"]
        ours = ours if len(ours) <= 26 else ours[:24] + "…"
        src = src if len(src) <= 26 else src[:24] + "…"
        out.append(f"{cell.replace(' [view-', ' [v'):<30} {ours:>26} {src:>26}  {r['verdict']}")
    return "```\n" + "\n".join(out) + "\n```"


def main():
    sys.path.insert(0, canon_dir())
    roster = list(csv.DictReader(open(HERE / "roster.csv", newline="", encoding="utf-8")))
    import check_tie_out

    src = (HERE / f"{NAME}.md").read_text(encoding="utf-8")
    src = src.replace("<!--HEADLINE-->", n(T["total"]))
    src = src.replace("<!--CHANGES-->", changes_html())
    src = src.replace("<!--ROSTER-->", roster_html())
    src = src.replace("<!--RERUN-->", rerun_html())
    for name in EXCERPTS:
        src = src.replace(f"<!--EXCERPT:{name}-->", excerpt(name, roster))
    for v in ORDER:
        src = src.replace(f"<!--COUNT:{v}-->", n(T["by_verdict"][v]))
    left = re.findall(r"<!--[A-Z]+[:A-Z a-z-]*-->", src)
    if left:
        raise SystemExit(f"placeholders left unfilled: {left}")
    body = markdown.markdown(src, extensions=["tables", "fenced_code", "md_in_html"])
    html = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>PocketBook evening tie-out</title><style>{CSS}</style></head>"
            f'<body><div class="sheet">{embed(body)}</div></body></html>\n')
    (HERE / f"{NAME}.html").write_text(html, encoding="utf-8")
    check_tie_out.render(html, HERE / f"{NAME}.pdf", what="the PocketBook evening tie-out", chrome=chrome())


if __name__ == "__main__":
    main()
