"""The walkthrough as one file: every screen, photographed, with what to press.

Run it: `python cli.py walkthrough` after `python capture.py`.

WHY IT IS ONE FILE. The firm reads these on a phone, and hands them to a
designer. A document that only renders while a stylesheet and a folder of
screenshots happen to sit beside it is a document that arrives blank. Every
image is embedded and the styling is inline; `external_references()` refuses to
emit a page that still points anywhere else.

WHAT IS GENERATED AND WHAT IS NOT. The screens, their order, and every control
on them come from `capture.py` -- which found them by driving the real
application in a real browser. The sentences come from
`registry/walkthrough.yaml`, written by a person, because a machine has nothing
useful to say about why you would ever press something. What the generator
guarantees is that the two agree: a control with nothing written about it, or a
sentence about a control that is gone, stops the build rather than reaching a
reader who would believe it.
"""

from __future__ import annotations

import base64
import html as H
from pathlib import Path

import walkthrough as wt

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "out" / "walkthrough"

# Lifted verbatim from `satc-handoff/04-TEMPLATES/satc-doc.css`, the same way
# `procedures_html` lifts them, so the two documents are the same family.
CSS = """
:root{--navy:#132437;--oxblood:#6A2833;--ink:#242C36;--ink-2:#4A5360;
--mute:#82817C;--hairline:#D8D7D1;--hairline-2:#E6E5E0;--paper:#FCFCFA}
*{box-sizing:border-box}
body{margin:0;background:#F1F0EC;color:var(--ink);
font:16px/1.62 "IBM Plex Sans",-apple-system,Segoe UI,sans-serif}
.sheet{max-width:860px;margin:0 auto;background:var(--paper);
padding:56px 64px 80px;min-height:100vh}
.wm{font:600 20px/1 "IBM Plex Sans",sans-serif;letter-spacing:.02em;
color:var(--navy)}
.wm .hy{display:inline-block;width:11px;height:2px;background:var(--oxblood);
margin:0 3px 5px;vertical-align:middle}
.wm i{font-style:normal;font-size:11px;letter-spacing:.14em;
color:var(--mute);margin-left:5px}
.tg{font-size:12.5px;color:var(--ink-2);margin-top:3px}
.rule{height:2px;background:var(--navy);margin:14px 0 10px}
.meta{display:flex;justify-content:space-between;
font:10.5px/1.5 "IBM Plex Mono",monospace;letter-spacing:.1em;
text-transform:uppercase;color:var(--mute);margin-bottom:34px}
h1{font-size:27px;line-height:1.25;margin:0 0 10px;font-weight:600;
color:var(--navy);text-wrap:balance}
.lede{font-size:16.5px;color:var(--ink-2);margin:0 0 40px;max-width:62ch}
h2{font-size:19px;margin:0 0 4px;font-weight:600;color:var(--navy)}
.step{border-top:1px solid var(--hairline);padding-top:30px;margin-top:44px}
.no{font:11px/1 "IBM Plex Mono",monospace;letter-spacing:.16em;
text-transform:uppercase;color:var(--oxblood);margin:0 0 9px}
.says{font-size:15px;color:var(--ink-2);margin:0 0 20px;max-width:62ch}
figure{margin:0 0 26px}
figure img{display:block;width:100%;height:auto;
border:1px solid var(--hairline);border-radius:3px}
figcaption{font:11px/1.5 "IBM Plex Mono",monospace;letter-spacing:.08em;
text-transform:uppercase;color:var(--mute);margin-top:8px}
dl{margin:0}
dt{font-weight:600;color:var(--navy);font-size:15.5px;margin-top:18px}
dt .kind{font:10px/1 "IBM Plex Mono",monospace;letter-spacing:.12em;
text-transform:uppercase;color:var(--mute);margin-left:9px;font-weight:400}
dt .rep{font:10px/1 "IBM Plex Mono",monospace;letter-spacing:.08em;
color:var(--oxblood);margin-left:8px;font-weight:400}
dd{margin:5px 0 0;color:var(--ink-2);font-size:15px;max-width:62ch}
dd.plain{color:var(--mute);font-style:italic}
dd .eg{display:block;font:12px/1.7 "IBM Plex Mono",monospace;
color:var(--mute);margin-top:5px}
.foot{border-top:1px solid var(--hairline);margin-top:56px;padding-top:16px;
font-size:12.5px;color:var(--mute);max-width:66ch}
code{font-family:"IBM Plex Mono",monospace;font-size:.92em}
@media (max-width:640px){.sheet{padding:34px 22px 60px}h1{font-size:23px}}
@media print{body{background:#fff}.sheet{padding:0;max-width:none}
.step{break-inside:avoid}}
"""

LEDE = (
    "Everything below is a photograph of the software, taken by driving it. "
    "Work down the page with the client in front of you; each screen says what "
    "it is for, then names every button and box on it. Where a control is "
    "obvious it is marked so and left alone — the notes are for the ones "
    "you would otherwise have to guess about."
)


def _img(path: Path) -> str:
    """The screenshot, in the page rather than beside it."""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _entry(control: wt.Control, said) -> str:
    kind = {"disclosure": "opens", "textarea": "box", "text": "box",
            "checkbox": "tick box", "radio": "choice", "select": "list",
            "link": "link", "button": "button"}.get(control.kind,
                                                    control.kind)
    rep = (f"<span class=rep>drawn {control.count}×</span>"
           if control.count > 1 else "")
    # A LABEL IS NOT ALWAYS A NAME. The manual door's summary is three
    # sentences, and three sentences set in bold is not a heading -- so the
    # display is trimmed while the key stays whole, because the key is what
    # has to match the screen.
    shown = control.shown if control.label else "One on each row"
    if len(shown) > 54:
        shown = shown[:53].rsplit(" ", 1)[0].rstrip(" ,;\u2014-") + "\u2026"
    name = H.escape(shown)
    out = [f"<dt>{name}<span class=kind>{kind}</span>{rep}</dt>"]
    if said:
        out.append(f"<dd>{H.escape(str(said))}</dd>")
    else:
        out.append("<dd class=plain>Does what it says.</dd>")
    if not control.label and control.examples:
        shown = ", ".join(control.examples[:4])
        more = (f", and {len(control.examples) - 4} more"
                if len(control.examples) > 4 else "")
        out.append(f"<dd><span class=eg>{H.escape(shown)}{more}</span></dd>")
    return "".join(out)


def render(screens: list[wt.Screen], registry: dict, shots: Path) -> str:
    gaps = wt.missing(screens, registry)
    if gaps:
        raise RuntimeError(
            "refusing to write a walkthrough that would be wrong about "
            + f"{len(gaps)} thing(s):\n  " + "\n  ".join(gaps))

    everywhere = registry.get("_everywhere") or {}
    by_key = {s.key: s for s in screens}
    parts = []
    for n, (key, heading) in enumerate(wt.SCREENS, start=1):
        screen = by_key[key]
        entries = registry.get(key) or {}
        shot = shots / screen.shot
        parts.append(f'<section class="step"><p class=no>Step {n:02d}</p>'
                     f"<h2>{H.escape(heading)}</h2>")
        if screen.help:
            parts.append(f'<p class=says>{H.escape(screen.help)}</p>')
        if shot.is_file():
            parts.append(f'<figure><img alt="{H.escape(heading)}" '
                         f'src="{_img(shot)}">'
                         f'<figcaption>{H.escape(screen.heading)}'
                         f'</figcaption></figure>')
        body = [_entry(c, entries.get(c.key, everywhere.get(c.key)))
                for c in screen.controls if c.key not in everywhere]
        parts.append("<dl>" + "".join(body) + "</dl>" if body
                     else "<p class=says>Nothing to press. Read it and go on."
                          "</p>")
        parts.append("</section>")

    chrome = "".join(f"<dt>{H.escape(k.split(':', 1)[-1])}</dt>"
                     f"<dd>{H.escape(str(v))}</dd>"
                     for k, v in everywhere.items())
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAT-C &mdash; running a sitting</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>{CSS}</style></head>
<body><div class="sheet">
  <div class="wm">SAT<span class="hy"></span>C<i>LLP</i></div>
  <div class="tg">Sethuraman Accounting, Tax &amp; Consulting</div>
  <div class="rule"></div>
  <div class="meta"><span>Internal &mdash; running a sitting</span>
    <span>Photographed from the software</span></div>
  <h1>Taking a client through, start to finish</h1>
  <p class="lede">{LEDE}</p>
  <section class="step"><p class=no>On every screen</p>
  <h2>The one thing that is always there</h2><dl>{chrome}</dl></section>
  {''.join(parts)}
  <div class="foot">Every screen here was photographed by driving the software,
  and every button on every screen is accounted for &mdash; a control nobody
  has written about, or a note about a control that has gone, stops this
  document being written at all. Regenerate it with
  <code>python capture.py &amp;&amp; python cli.py walkthrough</code>. The
  people in the screenshots are invented; no client's details appear here.</div>
</div></body></html>
"""
    stranded = external_references(doc)
    if stranded:
        raise RuntimeError(
            f"not self-contained -- the page still points at {stranded}. A "
            f"file that only renders while its siblings happen to sit beside "
            f"it is the bug this exists to avoid.")
    return doc


# The one thing the page is allowed to fetch, and the reason it is allowed:
# the house typeface, from the host the templates already use. Everything else
# -- a stylesheet beside the file, a folder of screenshots, a script on a CDN --
# is the failure this check exists for, because the document arrives somewhere
# else and those things do not travel with it.
FONT_HOSTS = ("https://fonts.googleapis.com", "https://fonts.gstatic.com")


def external_references(doc: str) -> list[str]:
    """Anything besides the typeface the page would have to fetch to look right.

    Reads MARKUP, not code: scanning the whole document would count a `src="..."`
    inside a script's own string literal, which no browser ever fetches.
    """
    import re

    markup = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", doc,
                    flags=re.S | re.I)
    return sorted({r for r in re.findall(r'(?:href|src)="([^"]+)"', markup)
                   if not r.startswith(FONT_HOSTS + ("data:", "#"))})
