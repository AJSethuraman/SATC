"""Build the page the firm ratifies positions on, FROM THE RECORD.

WHY IT IS GENERATED AND NOT WRITTEN. Seventeen proposals across five desks, each
with a citation, a tier and the reasoning behind it. Hand-written, the page is a
copy of the record that is wrong the moment a proposal changes — and the one
thing worse than no page is a page that shows the firm a position the desk does
not hold. So it is read from `record.load` every time it is built.

WHAT RATIFYING ACTUALLY DOES, which the page has to say plainly because it is the
whole of the decision: a PROPOSED position is invisible to a desk. It is not
served, not shown to an answerer, and does not stop an escalation. Saying yes
makes the desk answer in the firm's words where today it hands the question back.

    python tools/ratification_page.py > page.html
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import record                                               # noqa: E402

HERE = Path(__file__).resolve().parents[1]

#: Proposals the firm's docket answers already point at. Named here rather than
#: inferred, because "you already decided this" is a claim about what they said
#: and it has to be checkable against the answer it cites.
ALREADY_LEANING = {
    ("vehicle-expense", "POS1"):
        "M2 · you answered **Split it**. This is that split, written as the "
        "lines Publication 463 names.",
    ("meals-and-entertainment", "POS1"):
        "M3 · you answered **Three accounts**. This is that, from the "
        "regulation's own three answers.",
}

#: Proposals that must NOT be ratified yet, and why. A page that let the firm say
#: yes to one of these would be collecting a decision it had already been told to
#: hold.
BLOCKED = {
    ("rewards-and-information-returns", "POS1"):
        "M7 · you answered <b>“I'll read it first.”</b> This rests on a Private "
        "Letter Ruling that says in its own words it may not be cited as "
        "precedent, and <i>Anikeev v. Commissioner</i>, T.C. Memo. 2021-23 — the "
        "only place the general answer has been tested — could not be reached "
        "from this environment. Ratifying before reading it is the thing you "
        "said not to do.",
}


def proposals():
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for q in desk.positions:
            if not q.proposed:
                continue
            src = next((s for s in desk.sources
                        if record.from_source(q.citation, s.citation_prefix)), None)
            yield desk, q, (src.tier if src else "unresolved")


def main() -> int:
    rows = list(proposals())
    by_desk: dict[str, list] = {}
    for desk, q, tier in rows:
        by_desk.setdefault(desk.name, []).append((desk, q, tier))
    print(render(by_desk, len(rows)))
    return 0


def _md(text: str) -> str:
    """The little of Markdown these fields actually use, escaped first."""
    out = html.escape(text)
    for a, b in (("**", "strong"), ("*", "em"), ("`", "code")):
        parts = out.split(a)
        out = "".join(p if i % 2 == 0 else f"<{b}>{p}</{b}>"
                      for i, p in enumerate(parts))
    return out.replace("\n\n", "</p><p>").replace("\n", " ")


_CSS = """
:root{--paper:#F4F4F1;--sheet:#FFF;--rule:#DBDBD4;--soft:#EBEBE6;
 --ink:#141C26;--ink2:#4B5563;--ink3:#7C8593;
 --yes:#2C6650;--yes-soft:#E1EDE8;--hold:#8A5A16;--hold-soft:#F6EBD9;
 --stop:#8C2F39;--stop-soft:#F3E3E4;--focus:#2F5C9E}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#11151B;--sheet:#191E26;--rule:#2B323C;--soft:#222932;
 --ink:#E6E9EC;--ink2:#AEB6C2;--ink3:#7B8492;
 --yes:#79C4A5;--yes-soft:#16291F;--hold:#DCA85E;--hold-soft:#2A2114;
 --stop:#E2848C;--stop-soft:#331E21;--focus:#7FA9E8}}
:root[data-theme="dark"]{--paper:#11151B;--sheet:#191E26;--rule:#2B323C;--soft:#222932;
 --ink:#E6E9EC;--ink2:#AEB6C2;--ink3:#7B8492;
 --yes:#79C4A5;--yes-soft:#16291F;--hold:#DCA85E;--hold-soft:#2A2114;
 --stop:#E2848C;--stop-soft:#331E21;--focus:#7FA9E8}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-size:16px;line-height:1.6;
 font-family:"Public Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:58rem;margin:0 auto;padding:2.5rem 1.25rem 6rem}
h1,h2,h3{font-family:Newsreader,Georgia,serif;font-weight:600;margin:0;text-wrap:balance}
a{color:var(--focus)}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:3px}
code{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-size:.85em}
header{border-bottom:2px solid var(--ink);padding-bottom:1rem;margin-bottom:1.5rem}
.eyebrow{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:700}
h1{font-size:clamp(2rem,5vw,2.8rem);line-height:1.1;margin:.3rem 0}
header p{color:var(--ink2);max-width:62ch;margin:.4rem 0 0}
.what{background:var(--sheet);border:1px solid var(--rule);border-left:3px solid var(--focus);
 padding:.9rem 1.1rem;margin:0 0 2.25rem}
.what p{margin:.35rem 0;max-width:64ch}
h2.desk{font-size:1.45rem;margin:2.25rem 0 .2rem;display:flex;gap:.6rem;align-items:baseline;flex-wrap:wrap}
h2.desk span{font-family:"JetBrains Mono",monospace;font-size:.74rem;color:var(--ink3);font-weight:400}
.desk-sub{color:var(--ink2);margin:0 0 1rem;font-size:.94rem;max-width:64ch}
.pos{background:var(--sheet);border:1px solid var(--rule);border-left:3px solid var(--hold);
 margin-bottom:1rem;padding:1.05rem 1.15rem}
.pos[data-state="yes"]{border-left-color:var(--yes)}
.pos[data-state="no"]{border-left-color:var(--stop)}
.pos[data-blocked="1"]{border-left-color:var(--stop);opacity:.96}
.pos h3{font-size:1.12rem;line-height:1.3;margin:0 0 .5rem}
.meta{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.7rem}
.chip{font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;font-weight:700;
 padding:.16rem .45rem;border-radius:2px;background:var(--soft);color:var(--ink3)}
.chip.primary{background:var(--yes-soft);color:var(--yes)}
.chip.secondary{background:var(--hold-soft);color:var(--hold)}
.chip.tertiary{background:var(--stop-soft);color:var(--stop)}
.says{border-left:2px solid var(--rule);padding-left:.85rem;margin:.6rem 0;
 font-family:Newsreader,Georgia,serif;font-size:1.08rem}
.cite{font-family:"JetBrains Mono",monospace;font-size:.76rem;color:var(--ink3);
 word-break:break-word;margin:.5rem 0}
details.why{margin:.6rem 0}
details.why summary{cursor:pointer;font-size:.8rem;letter-spacing:.05em;
 text-transform:uppercase;color:var(--ink3);font-weight:700}
details.why div{color:var(--ink2);font-size:.94rem;margin-top:.5rem;max-width:64ch}
.note{padding:.6rem .8rem;margin:.7rem 0;font-size:.92rem}
.note.lean{background:var(--yes-soft);border-left:2px solid var(--yes)}
.note.stop{background:var(--stop-soft);border-left:2px solid var(--stop)}
.answer{border-top:1px dashed var(--rule);margin-top:.9rem;padding-top:.8rem}
.answer>label{font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink3);font-weight:700}
.picks{display:flex;gap:.4rem;flex-wrap:wrap;margin:.5rem 0}
button.pick{font-family:inherit;font-size:.88rem;font-weight:500;cursor:pointer;background:var(--sheet);
 color:var(--ink);border:1px solid var(--rule);padding:.35rem .8rem;border-radius:2px}
button.pick:hover{border-color:var(--ink3)}
button.pick[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
button.pick:disabled{opacity:.45;cursor:not-allowed}
textarea{width:100%;min-height:3.4rem;font-family:inherit;font-size:.94rem;color:var(--ink);
 background:var(--paper);border:1px solid var(--rule);padding:.55rem .65rem;border-radius:2px;resize:vertical}
.saved{font-size:.76rem;color:var(--ink3);margin-top:.35rem;min-height:1.1em}
.saved.ok{color:var(--yes)} .saved.err{color:var(--stop)}
.banner{background:var(--hold-soft);border:1px solid var(--hold);color:var(--hold);
 padding:.6rem .85rem;font-size:.88rem;margin-bottom:1.5rem;display:none}
.banner.show{display:block}
footer{border-top:1px solid var(--rule);margin-top:3rem;padding-top:1rem;color:var(--ink3);font-size:.85rem}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

_HEAD = """<title>Seventeen positions awaiting a yes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Public+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>%s</style>"""


def render(by_desk: dict, total: int) -> str:
    out = [_HEAD % _CSS, '<div class="wrap">', '<header>',
           '<div class="eyebrow">Positions · Sethuraman Accounting, Tax &amp; Consulting</div>',
           f'<h1>{total} positions awaiting a yes</h1>',
           '<p>Read from the record as it stands, not written by hand — so nothing '
           'here is a position a desk does not actually hold. Each answer saves as '
           'you give it.</p></header>',
           '<div id="offline" class="banner">Answers are not saving — this view '
           'could not reach the store. Tell me in the conversation instead.</div>',
           '<div class="what">'
           '<p><strong>What saying yes does.</strong> A proposed position is '
           '<em>invisible</em>. The desk does not serve it, an answerer is never '
           'shown it, and it stops no escalation — it is one agent&rsquo;s '
           'suggestion sitting in a file.</p>'
           '<p>Ratified, it becomes <strong>the firm&rsquo;s answer in the '
           'firm&rsquo;s words</strong>. The engine returns it verbatim and '
           'refuses any desk that tries to restate it. Where a source is one no '
           'model may read, the position is the desk&rsquo;s <em>entire</em> '
           'knowledge of it.</p>'
           '<p><strong>No is as useful as yes</strong>, and faster. A proposal '
           'you reject stops being offered; one left open is offered again on '
           'every docket.</p></div>']

    for name, items in by_desk.items():
        desk = items[0][0]
        out.append(f'<h2 class="desk">{html.escape(name)}'
                   f'<span>{len(desk.passages)} passages · {len(desk.problems)} problems</span></h2>')
        out.append(f'<p class="desk-sub">{_md(desk.title if hasattr(desk, "title") else "")}</p>'
                   if getattr(desk, "title", "") else "")
        for _, q, tier in items:
            key = (name, q.id)
            blocked = BLOCKED.get(key)
            lean = ALREADY_LEANING.get(key)
            out.append(
                f'<div class="pos" id="{name}-{q.id}" data-state="" '
                f'data-blocked="{1 if blocked else 0}">'
                f'<h3>{html.escape(q.title)}</h3>'
                f'<div class="meta"><span class="chip">{name} · {q.id}</span>'
                f'<span class="chip {tier}">{tier} authority</span></div>'
                f'<div class="says">&ldquo;{html.escape(q.position)}&rdquo;</div>'
                f'<div class="cite">{html.escape(q.citation)}</div>')
            if lean:
                out.append(f'<div class="note lean">{_md(lean)}</div>')
            if blocked:
                out.append(f'<div class="note stop">{blocked}</div>')
            if q.why.strip():
                out.append('<details class="why"><summary>Why it says that</summary>'
                           f'<div><p>{_md(q.why.strip())}</p></div></details>')
            picks = ("Ratify it", "No", "Not yet")
            dis = " disabled" if blocked else ""
            out.append(
                f'<div class="answer"><label for="{name}-{q.id}-n">Your answer</label>'
                '<div class="picks">' +
                "".join(f'<button type="button" class="pick" data-choice="{p}" '
                        f'aria-pressed="false"{dis}>{p}</button>' for p in picks) +
                f'</div><textarea id="{name}-{q.id}-n" placeholder="'
                f'{"Say what you want read first, if anything." if blocked else "Reword it in your own words and I will use yours, not this."}'
                '"></textarea><div class="saved" role="status" aria-live="polite"></div>'
                '</div></div>')

    out.append('<footer><p>Generated from <code>desks/*/positions/</code> by '
               '<code>tools/ratification_page.py</code>. A position you ratify is '
               'written into the record with your words and the date; nothing is '
               'recorded from this page without one.</p></footer></div>')
    out.append(_JS)
    return "\n".join(x for x in out if x)


_JS = """<script>
(async () => {
  const cards = [...document.querySelectorAll(".pos")];
  const db = await claude.use("db");
  if (!db) { document.getElementById("offline").classList.add("show"); return; }

  cards.forEach(card => {
    const picks = [...card.querySelectorAll(".pick")];
    const notes = card.querySelector("textarea");
    const said  = card.querySelector(".saved");
    const doc   = db.doc("positions/" + card.id);
    let choice = "", timer = null;

    const paint = () => {
      picks.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.choice === choice)));
      card.dataset.state = choice === "Ratify it" ? "yes" : choice === "No" ? "no" : "";
    };
    const save = () => {
      said.className = "saved"; said.textContent = "Saving\\u2026";
      doc.set({ position: card.querySelector("h3").textContent, choice,
                notes: notes.value, answeredAt: new Date().toISOString() })
        .then(() => { said.className = "saved ok"; said.textContent = "Saved."; })
        .catch(e => { said.className = "saved err";
          said.textContent = "Not saved (" + ((e && e.code) || "unknown") + ")."; });
    };
    picks.forEach(b => b.addEventListener("click", () => {
      choice = choice === b.dataset.choice ? "" : b.dataset.choice;
      paint(); clearTimeout(timer); save();
    }));
    notes.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(save, 700); });

    doc.onSnapshot(s => {
      if (!s.exists) return;
      const d = s.data() || {};
      if (document.activeElement !== notes) notes.value = d.notes || "";
      choice = d.choice || ""; paint();
    }, () => { said.className = "saved err"; said.textContent = "Live updates stopped."; });
  });
})();
</script>"""


if __name__ == "__main__":
    raise SystemExit(main())
