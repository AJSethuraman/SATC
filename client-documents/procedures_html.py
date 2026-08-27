"""The generated procedures, in the firm's house style, as one file.

WHY THIS IS IN THE REPOSITORY. It was written as a throwaway in a session
scratchpad, sent to the firm, and would have been lost with the container --
leaving only the markdown, which they had already read and called unpleasant.
A rendering nobody can regenerate is a rendering that exists once.

The markdown stays the source of truth: `procedures.py` generates it from the
software that performs each step, and `procedures --check` fails when the
committed copy drifts. This turns that same text into something a person will
actually read, and adds nothing to it.

ONE FILE, NOTHING BESIDE IT. The palette and the type are lifted verbatim from
`satc-handoff/04-TEMPLATES/satc-doc.css` -- navy #132437, oxblood #6A2833, IBM
Plex Sans and Mono -- so it sits in the same family as the client letters
rather than merely near them.

It is deliberately NOT the letter chrome. A letter has an addressee, a subject
line and a signature; a procedure has none of those, and forcing one into the
other's shape would be dressing a document as something it is not.
"""

from __future__ import annotations

import html as H
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "OPERATING-PROCEDURES.md"

BULLET = re.compile(r"^\s*[-*] ")
ORDERED = re.compile(r"^\s*\d+\. ")
BLOCK = re.compile(r"^(#{1,3} |>|```|\s*[-*] |\s*\d+\. |\s*\|)")


def inline(s: str) -> str:
    """Escape first, then mark up.

    The other order lets the document's own angle brackets -- `<REF>` appears
    eleven times -- turn into tags and vanish.
    """
    s = H.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def blocks(raw: str) -> tuple[str, list[str]]:
    """(title, HTML blocks) for one markdown document."""
    lines = raw.splitlines()
    out: list[str] = []
    title = "Operating procedures"
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        if line.startswith("# "):
            title = inline(line[2:].strip())
            i += 1
            continue

        if line.startswith("## "):
            text = line[3:].strip()
            # The generator numbers its own sections ("1 · Taking on a new
            # client"). Keep ITS number rather than counting again here: two
            # numberings of one list is two answers waiting to disagree.
            m = re.match(r"^(\d+)\s*·\s*(.+)$", text)
            num, text = (m.group(1), m.group(2)) if m else ("", text)
            n = f'<span class="n">{int(num):02d}</span>' if num else ""
            out.append(f"<h2>{n}<span>{inline(text)}</span></h2>")
            i += 1
            continue

        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:].strip())}</h3>")
            i += 1
            continue

        if line.startswith("```"):
            block, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            out.append("<pre>" + H.escape("\n".join(block)) + "</pre>")
            continue

        if line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i].lstrip(">").strip())
                i += 1
            paras = [p.strip() for p in "\n".join(block).split("\n\n")]
            out.append("<blockquote>"
                       + "".join(f"<p>{inline(p)}</p>" for p in paras if p)
                       + "</blockquote>")
            continue

        if line.lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = [[c.strip() for c in r.strip("|").split("|")] for r in block]
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            head, rest = rows[0], rows[1:]
            out.append('<div class="scroll"><table><thead><tr>'
                       + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>"
                                                  for c in r) + "</tr>"
                                 for r in rest)
                       + "</tbody></table></div>")
            continue

        marker, tag = ((BULLET, "ul") if BULLET.match(line)
                       else (ORDERED, "ol") if ORDERED.match(line)
                       else (None, None))
        if marker is not None:
            items = []
            while i < len(lines) and marker.match(lines[i]):
                parts = [marker.sub("", lines[i])]
                i += 1
                # A LIST ITEM CAN WRAP. The generator wraps at about seventy
                # columns, so half its bullets continue on an indented line.
                # Taking only the first line broke them apart on the page --
                # "the hard-no list in" as a bullet, "firm-settings.yaml,
                # refused before anything is composed" as a loose paragraph
                # beneath it. Every word was present, in the wrong shape, and
                # no word count would ever have said so. Found by reading it.
                while (i < len(lines) and lines[i].strip()
                       and not BLOCK.match(lines[i])):
                    parts.append(lines[i].strip())
                    i += 1
                items.append("<li>" + inline(" ".join(parts)) + "</li>")
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue

        para = [line]
        i += 1
        while (i < len(lines) and lines[i].strip()
               and not BLOCK.match(lines[i])):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")

    return title, out


CSS = """
/* Tokens lifted verbatim from satc-doc.css so this is the same family as the
   client letters, not an approximation of it. */
:root{--navy:#132437;--oxblood:#6A2833;--ink:#242C36;--ink-2:#4A5360;
  --mute:#82817C;--hairline:#D8D7D1;--hairline-2:#E6E5E0;--paper:#FFFFFF;
  --sunk:#F4F3EF;
  --sans:"IBM Plex Sans",Helvetica,Arial,sans-serif;
  --mono:"IBM Plex Mono","Courier New",monospace}
*{box-sizing:border-box}
body{margin:0;background:#EFEEE9;color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.62;-webkit-font-smoothing:antialiased}
.sheet{max-width:7.1in;margin:0 auto;background:var(--paper);
  padding:0.62in clamp(18px,5vw,0.72in) 0.6in}
@media (min-width:820px){.sheet{margin:24px auto;
  box-shadow:0 1px 3px rgba(19,36,55,.10),0 12px 34px rgba(19,36,55,.07)}}
a{color:var(--oxblood)}
/* masthead — the same lockup the letters carry */
.wm{display:flex;align-items:flex-end;font-size:25px;font-weight:700;
  letter-spacing:-.04em;line-height:.74;color:var(--navy)}
.wm .hy{width:.3em;height:.3em;flex:none;background:var(--oxblood);
  margin:0 .18em .2em}
.wm i{font-style:normal;font-weight:500;letter-spacing:0;margin-left:.22em}
.tg{font-family:var(--mono);font-size:9px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-2);margin-top:7px}
.rule{height:1.6px;background:var(--navy);margin:13px 0 0}
.meta{display:flex;flex-wrap:wrap;gap:6px 22px;justify-content:space-between;
  margin-top:15px;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--mute)}
h1{font-size:23px;font-weight:600;color:var(--navy);letter-spacing:-.015em;
  margin:20px 0 0;line-height:1.2;text-wrap:balance}
h2{display:flex;align-items:baseline;gap:13px;font-size:15px;font-weight:600;
  color:var(--navy);padding-bottom:7px;margin:34px 0 13px;
  border-bottom:.5px solid var(--hairline-2);text-wrap:balance}
h2 .n{font-family:var(--mono);font-size:11.5px;font-weight:500;
  color:var(--oxblood);letter-spacing:.1em;flex:none}
h3{font-size:14px;font-weight:600;color:var(--navy);margin:22px 0 8px}
p{margin:11px 0 0}
b,strong{color:var(--navy);font-weight:600}
code{font-family:var(--mono);font-size:.85em;background:var(--sunk);
  padding:1px 5px;border-radius:2px;color:var(--ink);word-break:break-word}
pre{font-family:var(--mono);font-size:12.5px;line-height:1.72;
  background:var(--sunk);border-left:2px solid var(--hairline);
  padding:12px 15px;margin:13px 0 0;overflow-x:auto;color:var(--ink-2)}
blockquote{margin:14px 0 0;padding:11px 16px;background:var(--sunk);
  border-left:2px solid var(--oxblood)}
blockquote p{margin:0;font-size:14px;color:var(--ink-2)}
blockquote p+p{margin-top:8px}
ul,ol{margin:11px 0 0;padding-left:21px}
li{margin-bottom:6px}li:last-child{margin-bottom:0}
.scroll{overflow-x:auto;margin:13px 0 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th{text-align:left;font-family:var(--mono);font-size:10px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--mute);font-weight:600;
  padding:0 12px 6px 0;border-bottom:1px solid var(--navy);white-space:nowrap}
td{padding:8px 12px 8px 0;border-bottom:.5px solid var(--hairline-2);
  vertical-align:top;color:var(--ink-2)}
td:first-child{color:var(--ink)}
.foot{margin-top:34px;padding-top:12px;border-top:.5px solid var(--hairline);
  font-family:var(--mono);font-size:10px;letter-spacing:.05em;color:var(--mute);
  line-height:1.8}
@media print{body{background:#fff}
  .sheet{box-shadow:none;margin:0;max-width:none;padding:0.5in}
  h2{break-after:avoid}pre,table,blockquote{break-inside:avoid}}
"""


def render(src: Path | str = SOURCE) -> str:
    """The markdown at `src` as one self-contained HTML document."""
    title, body = blocks(Path(src).read_text(encoding="utf-8"))
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAT-C &mdash; operating procedures</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap">
<style>{CSS}</style></head>
<body><div class="sheet">
  <div class="wm">SAT<span class="hy"></span>C<i>LLP</i></div>
  <div class="tg">Sethuraman Accounting, Tax &amp; Consulting</div>
  <div class="rule"></div>
  <div class="meta"><span>Internal &mdash; how the practice runs</span>
    <span>Generated from the software</span></div>
  <h1>{title}</h1>
{chr(10).join(body)}
  <div class="foot">Generated by <code>python cli.py procedures --html</code>.
  Do not edit this document by hand &mdash; every step is read out of the code
  that performs it, and an edit here is undone the next time it is made.</div>
</div></body></html>
"""
    stranded = external_references(doc)
    if stranded:
        raise RuntimeError(
            f"not self-contained -- the page still points at {stranded}. "
            f"A file that only renders while its siblings happen to sit "
            f"beside it is the bug this exists to avoid.")
    return doc


def external_references(doc: str) -> list[str]:
    """Anything the browser would have to fetch besides the font stylesheet.

    Reads MARKUP, not code: a scan of the whole document counts `src="..."`
    inside a script's own string literals, which the browser never fetches.
    """
    markup = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", doc,
                    flags=re.S | re.I)
    return [r for r in re.findall(r'(?:href|src)="([^"]+)"', markup)
            if not r.startswith(("https://fonts.googleapis.com",
                                 "https://fonts.gstatic.com",
                                 "http://", "https://", "#", "data:"))]


# ── did the rendering drop anything? ──────────────────────────────────────

# Two differences between the markdown and the page are deliberate, and are
# declared here rather than tolerated silently: the section numbers are
# reformatted 1..8 -> 01..08, and `<REF>` survives as text on the page while
# looking like a tag in the markdown. Anything else is a real loss.
EXPECTED_DIFFERENCE = ({str(n) for n in range(1, 20)}
                       | {"ref", "period", "year", "last", "s"})


def words(text: str) -> list[str]:
    text = re.sub(r"<[^>]+>", " ", text)
    text = H.unescape(text)
    text = re.sub(r"[*_`>|#\\]", " ", text)
    return re.findall(r"[a-z0-9]+", text.lower())


def dropped(markdown: str, doc: str) -> dict[str, int]:
    """Words in the markdown that did not reach the page.

    BOTH SIDES THROUGH ONE FUNCTION. A first version stripped markdown syntax
    from one side and HTML tags from the other with different rules, so
    `--force` came out as two different tokens and was reported missing from a
    page it was on. A comparison whose two halves are normalised differently
    is not a comparison.
    """
    import collections
    body = doc.split("<h1>", 1)[1].rsplit('<div class="foot">', 1)[0]
    a = collections.Counter(words(markdown))
    b = collections.Counter(words(body))
    return {w: n - b.get(w, 0) for w, n in a.items()
            if n > b.get(w, 0) and w not in EXPECTED_DIFFERENCE}
