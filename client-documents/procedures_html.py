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



# ── the templates themselves, as appendix items ───────────────────────────
#
# THE FIRM'S RULE, 2 September 2026, and the second half of it is the point:
#
#     "each relevant template is included as an appendix item to the process
#      it belongs to (this is a general rule)"
#     "by template i do not mean an example, i want it printed in such a way
#      that it is the actual format we'd give a client but it has the
#      <<placeholder>> values"
#
# So this does NOT summarise a template, describe it, or render it against
# sample answers. It inlines the template file itself. The templates already
# write their merge tokens escaped -- `&lt;&lt;ClientFullName&gt;&gt;` -- so a
# browser shows `<<ClientFullName>>` on the page exactly where the client's
# name would print. The document a client receives, with the blanks showing.
#
# The markdown appendix carries the path; this expands it. One generation, one
# source: the reading copy stays a rendering of the committed markdown rather
# than a second document that can drift from it.

TEMPLATE_DIR = ROOT / "satc-handoff" / "04-TEMPLATES"

# The markdown renderer emits `<b>` and a literal em dash, so the pattern is
# written against what `blocks()` ACTUALLY produces rather than against what
# the markdown says. Checked by reading one rendered line, not by assuming.
# The `when` half may carry markup -- the conditional Records Release bullet
# ends "only when <code>PriorFirm</code> is set on the record" -- so it cannot
# be `[^<]*`. It was, and that bullet quietly fell through as plain text while
# the other eight embedded: the one template the appendix rule most needed to
# prove, missing, under a guard that only fired at zero.
TEMPLATE_REF = re.compile(
    r"<li><b>(?P<label>[^<]+?)</b>\s*[\u2014-]+\s*"
    r"<code>satc-handoff/04-TEMPLATES/(?P<file>[^<]+?\.html)</code>"
    r"(?P<when>.*?)</li>", re.S)


def template_body(filename: str) -> str:
    """One template's own markup, ready to sit inside another page.

    Everything the browser would have to fetch is removed: the stylesheet link
    (its CSS is inlined once, below) and the `doc-page` script, whose only job
    is pagination that a screen reading does not need. What is left is the
    document.
    """
    path = TEMPLATE_DIR / filename
    if not path.exists():
        raise RuntimeError(
            f"the procedures name {filename!r} as an appendix and it is not in "
            f"{TEMPLATE_DIR}. A procedure pointing at a document nobody has is "
            f"worse than one that points nowhere.")
    markup = path.read_text(encoding="utf-8")
    inner = re.search(r"<body[^>]*>(.*)</body>", markup, re.S | re.I)
    if not inner:
        raise RuntimeError(f"{filename} has no body to lift")
    body = inner.group(1)
    body = re.sub(r"<script\b.*?</script>", "", body, flags=re.S | re.I)
    body = re.sub(r"<link\b[^>]*>", "", body, flags=re.I)

    # THE DOCUMENT, NOT THE FILE. Every template carries two things: the
    # `.doc` a client receives, and a `.notes` block for whoever wires it --
    # the merge-field table, "the fee is not a field", "before this template
    # ships". Embedding the whole body put the authoring notes into the
    # firm's operating procedures, where they read as part of the letter.
    # The firm asked for "the actual format we'd give a client".
    # TWO CONVENTIONS, BOTH REAL. The estimate and the invoice wrap their
    # document in `.doc`; the ten letters use `.letter`. Neither is wrong and
    # renaming a class in twelve approved templates to tidy this up would be
    # changing a client-facing document to please the code that reads it.
    for marker in ('class="doc"', 'class="letter"'):
        doc = _balanced_div(body, marker)
        if doc is not None:
            return doc.strip()
    raise RuntimeError(
        f"{filename} wraps its client document in neither `.doc` nor "
        f"`.letter`, so this cannot tell where the document ends and the "
        f"authoring notes begin. Embedding the whole file instead would put "
        f"the merge-field table into the firm's operating procedures.")


def _balanced_div(markup: str, marker: str) -> str | None:
    """The `<div ...marker...>` element and its contents, brace-counted.

    A regex cannot do this: `.doc` contains dozens of nested divs and the
    first `</div>` is never the right one.
    """
    start = markup.find(f"<div {marker}")
    if start == -1:
        return None
    depth, i = 0, start
    for m in re.finditer(r"<div\b|</div>", markup[start:]):
        depth += 1 if m.group().startswith("<div") else -1
        if depth == 0:
            return markup[start:start + m.end()]
    return None


def _scope_selector(selector: str, scope: str) -> str:
    """One selector list, rewritten to apply only inside `scope`."""
    out = []
    for part in selector.split(","):
        head = part.strip()
        if not head:
            continue
        if head in (":root", "html", "body", "html body"):
            out.append(scope)
        elif head.startswith(("@", "%")) or head[0].isdigit():
            return selector           # keyframe stops, at-rule preludes
        else:
            out.append(f"{scope} {head}")
    return ", ".join(out)


def scope_css(css: str, scope: str = ".tpl") -> str:
    """`satc-doc.css`, rewritten to dress only the appendices.

    NESTING-AWARE ON PURPOSE. The first version split the file on "}" and
    prefixed each fragment, which mangles every `@media` block -- the output
    came out one brace short, the browser dropped every rule after the break,
    and the appendix silently lost its containment. Found by opening the page
    in a browser and reading `overflow-x: visible` off a element that had been
    told to scroll.

    Selectors inside `@keyframes` are percentages and are left alone; `:root`,
    `html` and `body` become the scope itself, because in the appendix the
    frame IS the page.
    """
    out, buf, depth, at_depths = [], [], 0, []
    i = 0
    while i < len(css):
        ch = css[i]
        if ch == "{":
            head = "".join(buf).strip()
            buf = []
            if head.startswith("@"):
                at_depths.append(depth)
                out.append(head + "{")
            else:
                inside_keyframes = any(
                    a is not None for a in at_depths) and False
                out.append(_scope_selector(head, scope) + "{"
                           if not inside_keyframes else head + "{")
            depth += 1
        elif ch == "}":
            depth -= 1
            if at_depths and at_depths[-1] == depth:
                at_depths.pop()
            out.append("".join(buf) + "}")
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return "".join(out)


def template_css() -> str:
    """`satc-doc.css`, scoped, plus what the appendix frame needs of its own."""
    path = TEMPLATE_DIR / "satc-doc.css"
    if not path.exists():
        raise RuntimeError(f"no {path.name} to dress the appendices with")
    scoped = scope_css(path.read_text(encoding="utf-8"))
    if scoped.count("{") != scoped.count("}"):
        raise RuntimeError(
            "the scoped stylesheet is unbalanced, so a browser would drop "
            "every rule after the break -- which is exactly how the appendix "
            "lost its containment the first time.")
    return scoped + """
/* THE LETTERS ARE LAID OUT FOR A PAGE, THIS IS A SCREEN. A letter-width
   table inside a 7.1in reading sheet pushed the whole document sideways --
   caught by opening it in a browser, not by any check. The template keeps its
   own proportions and scrolls inside its own frame; the page never does. */
.tpl{border:1px solid #D8D7D1;border-radius:3px;margin:0 0 22px;
  max-width:100%;overflow-x:auto;background:#fff}
.tpl > *{padding:20px}
.tpl doc-page{display:block}
.tpl img{max-width:100%;height:auto}
.tpl-note{font:500 11px/1.5 var(--mono);letter-spacing:.06em;
  text-transform:uppercase;color:#82817C;margin:0 0 8px}
"""


def embed_templates(html: str) -> tuple[str, int]:
    """Expand each appendix path into the template itself. Returns the count."""
    embedded = 0

    def one(match: re.Match) -> str:
        nonlocal embedded
        embedded += 1
        label = match.group("label").strip()
        when = re.sub(r"<[^>]+>", "", match.group("when") or "").strip(" \u2014-")
        note = f"{label} &mdash; the document itself, with its blanks showing"
        if when:
            note += f" &mdash; {H.escape(when)}"
        # THE PATH STAYS ON THE PAGE. Replacing it with the document alone
        # made `dropped()` report four words lost, and it was right to: a
        # reader who wants to edit this letter needs to know which file it is,
        # and the check that would have caught a real loss must not be taught
        # to ignore these words to make room for a nicety.
        path = f"satc-handoff/04-TEMPLATES/{H.escape(match.group('file'))}"
        return (f'<li><p class="tpl-note">{H.escape(label)} '
                f'&mdash; <code>{path}</code></p>'
                f'<div class="tpl">{template_body(match.group("file"))}</div>'
                f'<p class="tpl-note">{note}</p></li>')

    out = TEMPLATE_REF.sub(one, html)

    # EVERY ONE, NOT AT LEAST ONE. The guard below used to be `if not
    # embedded`, which fires only when the count is zero -- so when the
    # conditional Records Release bullet stopped matching (its suffix carries
    # a `<code>` tag, and the pattern ended `[^<]*`), eight of nine embedded
    # and the ninth fell through as plain text, silently. That is exactly the
    # trap `procedures.template_audit` warns about in its own comment: one
    # direction passes trivially. So this counts what the document ASKED for
    # and compares.
    asked = out.count("satc-handoff/04-TEMPLATES/")
    if embedded < _appendix_bullets(html):
        raise RuntimeError(
            f"{_appendix_bullets(html)} appendix bullet(s) name a template and "
            f"only {embedded} embedded. The rest fell through as text, which "
            f"looks finished and is not the document the firm asked for.")
    return out, embedded


def _appendix_bullets(html: str) -> int:
    """How many appendix bullets name a template, whether or not they matched.

    Deliberately a looser pattern than the one that does the work: its whole
    job is to disagree with it when the strict one drifts.
    """
    return len(re.findall(r"<li><b>[^<]+</b>[^<]*<code>satc-handoff/", html))


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
    page_body, embedded = embed_templates(chr(10).join(body))
    if not embedded:
        raise RuntimeError(
            "no appendix template was embedded. The firm's rule is that each "
            "relevant template is an appendix item to its process, and a "
            "reading copy that quietly dropped every one of them would look "
            "finished. Either the markdown stopped naming them or the pattern "
            "that finds them has drifted.")
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAT-C &mdash; operating procedures</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap">
<style>{CSS}</style>
<style>{template_css()}</style></head>
<body><div class="sheet">
  <div class="wm">SAT<span class="hy"></span>C<i>LLP</i></div>
  <div class="tg">Sethuraman Accounting, Tax &amp; Consulting</div>
  <div class="rule"></div>
  <div class="meta"><span>Internal &mdash; how the practice runs</span>
    <span>Generated from the software</span></div>
  <h1>{title}</h1>
{page_body}
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
                                 "http://", "https://", "#", "data:"))
            # AN UNFILLED MERGE TOKEN IS A BLANK, NOT A BROKEN LINK. The
            # appendices embed the templates verbatim, so the invoice arrives
            # carrying `href="<<PaymentUrl>>"` -- which is the whole point of
            # showing the template rather than an example. The browser fetches
            # nothing for it and there is no sibling file it depends on.
            and not (r.startswith("&lt;&lt;") and r.endswith("&gt;&gt;"))
            and not (r.startswith("<<") and r.endswith(">>"))]


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
