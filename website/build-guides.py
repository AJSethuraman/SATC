#!/usr/bin/env python3
"""Generate website/guides/*.html from the drafts in docs/guides/.

    cd website && python3 build-guides.py
    cd website && python3 build-guides.py --check     # fails if the pages drift

Same shape as build-pricing-config.py, and for the same reason. The guides are
written and reviewed as Markdown in docs/guides/, which is where their sources
file and their tenet checker already live. Hand-porting them into HTML would
give the site a second copy that drifts from the reviewed one the first time a
sentence changes -- so the site's copy is generated and diffed instead.

WHAT THIS DELIBERATELY STRIPS

HTML comments. The drafts carry `[CONFIRM: ...]` markers inside them, which are
questions for the firm and must never reach a visitor. They are removed here
AND asserted absent by the check below, because a marker leaking onto a public
page is the one failure in this file that would actually embarrass anybody.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "docs" / "guides"
OUT = HERE / "guides"

# Source file -> published slug. Only these three are pages; PLAN.md and the
# SOURCES files are working documents and stay in docs/.
PAGES = [
    ("good-records-individuals.md", "records.html",
     "What to have ready before a return, and what turns a short one into a long one."),
    ("good-records-business.md", "business-records.html",
     "What a business return starts from, and how to keep books a return can be prepared from."),
    ("entity-choice.md", "s-corp.html",
     "What an LLC is, what electing S corporation commits an owner to, and when it is the wrong answer."),
]

NBH = "‑"


def inline(text: str) -> str:
    """Markdown inline -> HTML, on escaped text.

    Escaping first means a stray < or & in a draft cannot open a tag; the
    handful of constructs the drafts actually use are then put back by hand.
    Anything not listed here renders as literal text, which is the right
    failure: a new construct shows up visibly rather than silently vanishing.
    """
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def render_body(md: str) -> tuple[str, str, str]:
    """Return (title, lede, body-html) for one draft."""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)      # the CONFIRM markers
    # The drafts end with the not-advice line, and the shell below places it in
    # its own slot under the call to action. Left in both, it printed twice --
    # caught by copy.spec.py the first time these pages were checked. The shell
    # owns it, so it comes out of the body here.
    # Anchored to the end at first, which missed it: the S-corp draft puts the
    # line above its call to action, not below. Matched as its own line
    # wherever it sits -- the sentence is distinctive enough that this cannot
    # take anything else with it.
    md = re.sub(r"^This is general information,? not advice about a particular [a-z]+\.?\s*$",
                "", md, flags=re.M)
    lines = md.split("\n")

    title = ""
    lede_parts: list[str] = []
    out: list[str] = []
    para: list[str] = []
    bullets: list[str] = []
    seen_h2 = False

    def flush_para():
        nonlocal para
        if para:
            joined = " ".join(x.strip() for x in para).strip()
            if joined:
                if not seen_h2 and not out:
                    lede_parts.append(inline(joined))
                else:
                    out.append("<p>" + inline(joined) + "</p>")
            para = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            out.append("<ul>" + "".join(
                "<li>" + inline(" ".join(b)) + "</li>" for b in bullets) + "</ul>")
            bullets = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("# "):
            flush_para(); flush_bullets()
            title = line[2:].strip()
            continue
        if line.strip() == "---":
            flush_para(); flush_bullets()
            continue
        m = re.match(r"^## (.+)$", line)
        if m:
            flush_para(); flush_bullets()
            seen_h2 = True
            head = m.group(1).strip()
            # "01 · Heading" -- the number is a marker, not part of the sentence,
            # so it is set apart rather than left inside the heading text.
            n = re.match(r"^(\d+)\s*·\s*(.+)$", head)
            if n:
                out.append('<h2><span class="n">' + n.group(1) + "</span>" +
                           inline(n.group(2)) + "</h2>")
            else:
                out.append("<h2>" + inline(head) + "</h2>")
            continue
        if line.startswith("- "):
            flush_para()
            bullets.append([line[2:].strip()])
            continue
        if bullets and line.startswith("  ") and line.strip():
            bullets[-1].append(line.strip())
            continue
        if not line.strip():
            flush_para(); flush_bullets()
            continue
        para.append(line)

    flush_para(); flush_bullets()
    return title, " ".join(lede_parts), "\n  ".join(out)


SHELL = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_esc} &mdash; SATC</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#132437">
<link rel="canonical" href="https://satcllp.com/guides/{slug}" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="SAT-C LLP" />
<meta property="og:title" content="{title_esc}" />
<meta property="og:description" content="{desc}" />
<meta property="og:url" content="https://satcllp.com/guides/{slug}" />
<meta property="og:image" content="https://satcllp.com/og-image.png" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="https://satcllp.com/og-image.png" />
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E%3Crect%20width='32'%20height='32'%20fill='%23132437'/%3E%3Cpath%20d='M6%206%20H20%20V13%20H13%20V20%20H6%20Z'%20fill='none'%20stroke='%23fff'%20stroke-width='3'/%3E%3Crect%20x='21'%20y='21'%20width='6'%20height='6'%20fill='%23C0A265'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="guide.css">
</head>
<body>

<div class="top">
  <a class="lockup" href="../" aria-label="SAT-C LLP &mdash; home">
    <svg class="seal" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path class="s-o" d="M3 3 H19 V11 H11 V19 H3 Z"></path>
      <rect class="s-i" x="22" y="22" width="8" height="8"></rect>
    </svg>
    <div class="text">
      <span class="wm">SAT<span class="hy"></span>C<i>LLP</i></span>
      <span class="tag">Sethuraman Accounting, Tax &amp; Consulting</span>
    </div>
  </a>
  <a class="top-back" href="../pricing.html">&larr; Pricing</a>
</div>

<header class="head"><div class="wrap">
  <p class="eyebrow">Guide</p>
  <h1>{title}</h1>
  <p class="lede">{lede}</p>
</div></header>

<main class="wrap body">
  {body}

  <section class="close">
    <h2>Where you start</h2>
    <a class="btn" href="../#intake">Tell us about your situation</a>
  </section>

  <p class="fine">This is general information, not advice about a particular {noun}.</p>

  <nav class="also">
    <span class="lab">Also here</span>
    {also}
  </nav>

  <a class="back" href="../pricing.html">&larr; Pricing</a>
</main>

<footer><div class="wrap">
  &copy; <span id="year">2026</span> Sethuraman Accounting, Tax &amp; Consulting
</div></footer>

<script>document.getElementById('year').textContent = new Date().getFullYear();</script>
</body></html>
"""

CSS = """/* GENERATED alongside the guide pages by build-guides.py. Tokens lifted from
   pricing.html so the guides belong to the same site; there is no build step
   that could share them. */
:root{--navy:#132437;--navy-deep:#0D1926;--charcoal:#242C36;--charcoal-2:#4A5360;--mute:#82817C;
      --oxblood:#6A2833;--oxblood-lt:#83323F;--gold:#C0A265;--gold-deep:#756228;
      --cream:#F7F7F5;--paper:#FFFFFF;--hairline:#E6E5E0;--hairline-2:#D8D7D1;
      --sans:"IBM Plex Sans",-apple-system,"Helvetica Neue",Arial,sans-serif;
      --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;
      --pad:clamp(20px,5vw,56px);--w:760px}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:var(--sans);color:var(--charcoal);background:var(--cream);line-height:1.68;
     -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--oxblood);text-decoration:none}
a:hover{color:var(--oxblood-lt);text-decoration:underline}
:focus-visible{outline:2px solid var(--oxblood);outline-offset:3px}

.top{background:var(--navy);padding:18px var(--pad);display:flex;align-items:center;
     justify-content:space-between;gap:20px}
.top-back{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
          color:rgba(255,255,255,.66);white-space:nowrap;flex:0 0 auto}
.top-back:hover{color:#fff;text-decoration:none}
.top-back:focus-visible{outline-color:var(--gold)}
.lockup{display:inline-flex;align-items:center;gap:13px;color:#fff}
.lockup .seal{width:30px;height:30px;flex:0 0 auto}
.lockup .seal .s-o{fill:none;stroke:currentColor;stroke-width:2.6}
.lockup .seal .s-i{fill:var(--gold)}
.lockup .text{display:flex;flex-direction:column;align-items:flex-start;gap:5px}
.lockup .wm{display:flex;align-items:flex-end;font-size:20px;font-weight:700;letter-spacing:-.04em;
            line-height:.74;white-space:nowrap}
.lockup .wm .hy{width:.3em;height:.3em;flex:0 0 auto;background:var(--gold);margin:0 .18em .2em}
.lockup .wm i{font-style:normal;font-weight:500;letter-spacing:0;margin-left:.22em}
.lockup .tag{font-family:var(--mono);font-size:8px;letter-spacing:.14em;text-transform:uppercase;
             color:rgba(255,255,255,.55);font-weight:400}

.wrap{max-width:var(--w);margin:0 auto;padding:0 var(--pad)}
.eyebrow{font-family:var(--mono);font-size:10.5px;letter-spacing:.18em;text-transform:uppercase;
         color:var(--mute);margin:0}
.head{padding:clamp(40px,6vw,72px) 0 clamp(18px,2.5vw,26px);background:var(--paper);
      border-bottom:1px solid var(--hairline-2)}
h1{font-weight:600;font-size:clamp(30px,4.8vw,44px);color:var(--navy);letter-spacing:-.042em;
   line-height:1.06;margin:13px 0 14px;text-wrap:balance}
.lede{font-size:clamp(16.5px,2vw,18.5px);color:var(--charcoal-2);margin:0;max-width:54ch}

.body{padding:clamp(32px,4.5vw,54px) var(--pad) 0}
.body h2{font-weight:600;font-size:clamp(19px,2.3vw,23px);color:var(--navy);letter-spacing:-.03em;
         line-height:1.2;margin:clamp(34px,4vw,48px) 0 14px;padding-top:18px;
         border-top:1px solid var(--hairline-2);display:flex;gap:13px;align-items:baseline}
.body h2:first-child{margin-top:0;padding-top:0;border-top:0}
.body h2 .n{font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.1em;
            color:var(--gold-deep);flex:0 0 auto}
.body p{font-size:16px;color:var(--charcoal-2);margin:0 0 15px;max-width:62ch}
.body strong{color:var(--navy);font-weight:600}
.body code{font-family:var(--mono);font-size:14px;color:var(--navy)}
.body ul{list-style:none;padding:0;margin:0 0 18px;max-width:62ch}
.body li{position:relative;padding:11px 0 11px 18px;font-size:15.5px;color:var(--charcoal-2);
         border-top:1px solid var(--hairline)}
.body li:first-child{border-top:1px solid var(--hairline-2)}
.body li::before{content:"";position:absolute;left:0;top:19px;width:6px;height:6px;background:var(--gold)}

.close{margin:clamp(38px,5vw,56px) 0 0;padding:clamp(24px,3.4vw,34px);background:var(--paper);
       border:1px solid var(--hairline);border-top:2px solid var(--navy);
       display:flex;align-items:center;justify-content:space-between;gap:22px;flex-wrap:wrap}
.close h2{margin:0;padding:0;border:0;font-size:20px}
.btn{display:inline-flex;align-items:center;gap:10px;background:var(--oxblood);color:#fff;
     font-size:15px;font-weight:600;letter-spacing:-.005em;padding:14px 26px;border-radius:2px;
     transition:background .18s}
.btn::after{content:"\\2192";font-size:14px}
.btn:hover{background:var(--oxblood-lt);color:#fff;text-decoration:none}

.fine{margin:20px 0 0;font-size:13.5px;color:var(--mute)}

.also{margin:clamp(30px,4vw,44px) 0 0;padding-top:18px;border-top:1px solid var(--hairline-2);
      display:flex;gap:10px 22px;flex-wrap:wrap;align-items:baseline}
.also .lab{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;
           color:var(--mute)}
.also a{font-size:15px}

.back{display:inline-block;margin:clamp(28px,4vw,40px) 0 0;font-family:var(--mono);font-size:10.5px;
      letter-spacing:.14em;text-transform:uppercase;color:var(--oxblood)}
footer{margin-top:clamp(34px,5vw,56px);padding:22px 0 42px;border-top:1px solid var(--hairline);
       font-size:13px;color:var(--mute)}
@media (max-width:640px){
  .close{flex-direction:column;align-items:flex-start}
  .btn{width:100%;justify-content:center}
}
"""


def build() -> dict[str, str]:
    files: dict[str, str] = {"guide.css": CSS}
    rendered = []
    for src, slug, desc in PAGES:
        md = (SRC / src).read_text(encoding="utf-8")
        title, lede, body = render_body(md)
        rendered.append((slug, title, lede, body, desc))

    for slug, title, lede, body, desc in rendered:
        # "Also here" links the sibling guides. Three pages with no way between
        # them is three dead ends; a visitor who lands on one from search is
        # often in scope for another.
        also = "\n    ".join(
            '<a href="{}">{}</a>'.format(s, html.escape(t))
            for s, t, _l, _b, _d in rendered if s != slug)
        noun = "business" if slug in ("business-records.html", "s-corp.html") else "return"
        files[slug] = SHELL.format(
            title=html.escape(title),
            title_esc=html.escape(title).replace('"', "&quot;"),
            desc=html.escape(desc, quote=True),
            slug=slug, lede=lede, body=body, also=also, noun=noun)
    return files


def main() -> int:
    check = "--check" in sys.argv
    files = build()

    # A CONFIRM marker on a public page is the one failure here that would
    # actually embarrass somebody, so it is asserted rather than trusted.
    for name, text in files.items():
        if "CONFIRM" in text or "<!--" in text.replace("<!doctype", ""):
            print(f"REFUSED: {name} carries a draft marker or comment")
            return 1

    if check:
        bad = []
        for name, text in files.items():
            p = OUT / name
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                bad.append(name)
        if bad:
            print("guides are out of date: " + ", ".join(bad))
            print("run: cd website && python3 build-guides.py")
            return 1
        print(f"{len(files)} generated guide files match docs/guides/")
        return 0

    OUT.mkdir(exist_ok=True)
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files into website/guides/ from docs/guides/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
