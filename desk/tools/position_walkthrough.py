"""The seventeen positions, one at a time, generated FROM THE RECORD.

The firm asked to be walked through them rather than handed a list. So this is a
stepper: one position on screen, with what it rests on and what saying yes to it
would actually change, and nothing else competing for the decision.

WHY IT IS GENERATED. Hand-written, the page is a copy of the record that goes
wrong the moment a proposal changes, and the worst possible outcome is showing
the firm a position the desk does not hold.

THE FINDING THAT REFRAMED IT, measured here rather than assumed: of the seventeen,
**not one sits on a citation any of its own desk's problems turn on.** The cash
desk's two ratified positions do — 2 of 2 — which is why ratifying those made all
four problems answerable. These do not, so ratifying them changes NO score. What
they change is what the desk says when it cannot answer: twelve of the seventeen
are rules about how the firm works — hold it, ask who owns it, request these
documents by name — rather than conclusions about tax law.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import record                                               # noqa: E402

HERE = Path(__file__).resolve().parents[1]

#: A conclusion answers a tax question. A rule says what to do when nobody can
#: answer it yet. The distinction is not cosmetic: a conclusion can be wrong
#: about the law, and a rule can only be wrong about the practice — so they are
#: worth different amounts of the firm's attention and are asked differently.
CONCLUSIONS = {("capitalization-and-de-minimis", "POS2"),
               ("meals-and-entertainment", "POS2"),
               ("meals-and-entertainment", "POS3"),
               ("rewards-and-information-returns", "POS1"),
               ("rewards-and-information-returns", "POS2")}

#: Order the walk. The rewards position goes first because a case the firm handed
#: over this morning decides it, and it is the only one whose authority moved.
FIRST = [("rewards-and-information-returns", "POS1")]

#: What this session knows about a position that the record does not say, and the
#: firm needs before answering. Empty is fine; most stand on their own text.
NOTES = {
 ("rewards-and-information-returns","POS1"): {
   "read": "<b>You held this on 5 September asking for two things.</b> One of them now exists; the other is on this docket as its own question.",
   "for": "<b>Built since you held it.</b> You said <i>“we should probably be specifying. Hey this is the individual desk. This is the business desk.”</i> The desk now records <code>taxpayer</code> and this position declares it needs it — so it cannot be applied at all until the file says whose return it is. Not a second desk: one fact, passed in.",
   "against": "<i>Anikeev</i> is a personal return — the word “business” appears in it zero times — and it says nothing about a purchase that was <b>expensed</b> rather than capitalised, which is your actual open question. Ratifying it says what the desk answers for an individual; the business case still rests on nothing.",
   "silent": "<b>Your second ask is not built.</b> You wanted a fallback: <i>“if we don’t have an opinion and have a good reason to form one, maybe we just use a safe Harbor Rule which in this case would be deferring to whatever the IRS says.”</i> That is its own matter on this docket, because it changes what the gate will serve.",
   "rec": "Ratify it narrowed — <b>“a card reward earned by buying goods or services reduces what was paid for them”</b> — which is what survives the case. It now refuses outright unless the file says individual or business, so the thing you were worried about cannot happen silently.",
 },
 ("capitalization-and-de-minimis","POS2"): {
   "read": "<b>You held this asking one question, and the desk already held the answer.</b> Nobody had asked it.",
   "for": "<i>“I feel like I need to understand why would a confidently said $500 like where did this number come from?”</i> — <b>§ 1.263(a)-1(f)(1)(ii)(D) is where.</b> It says $500 and was never amended. The same sentence then delegates: <i>“or other amount as identified in published guidance in the Federal Register or in the Internal Revenue Bulletin.”</i>",
   "against": "<b>Notice 2015-82 is that guidance</b>, and the IRS page this desk stores says it <i>“increased the de minimis safe harbor threshold from $500 to $2500 per invoice or item for taxpayers without applicable financial statements”</i>, effective for years beginning on or after 1 January 2016 — $5,000 with an applicable financial statement.",
   "silent": "So the regulation is not stale and $2,500 is not a number somebody remembered: it is the amount the regulation points at. The two figures both being live is exactly why a desk holding only the regulation would have told you $500 with confidence.",
   "rec": "Ratify. The question you held it for is answered out of the desk’s own stored authority, cited.",
 },
 ("capitalization-and-de-minimis","POS1"): {
   "read": "<b>Held for a reason nothing in the software can express yet.</b>",
   "against": "You said it is <i>“the kind of policy that gets enacted because it makes sense and only enacted when we don’t have another Answer … it’s possible for a particular client we have to be needed treating differently.”</i> Every position today is unconditional: there is no way to write “default, unless this client”.",
   "rec": "<b>Do not ratify it yet.</b> The override question is its own matter on this docket and it decides the shape. If you pick the recommended answer there, this becomes ratifiable unchanged — the exception rides in as a recorded fact rather than as an exception table.",
 },
 ("personal-or-business","POS1"): {
   "read": "This is the J.Crew rule. <b>The input you held it for was built this afternoon.</b>",
   "for": "You said <i>“the Accountant should’ve already recorded and known what sort of business we’re dealing with … a Home Depot charge from a general contractor versus a Home Depot charge from a hairstylist.”</i> The desk now records <code>trade</code>, this position declares it needs it, and the brief prints <b>“trade: NOT ON FILE — do not infer it”</b> when it was not given. Unmet, the answer refuses <code>context_not_on_file</code> rather than reasoning from the vendor.",
   "against": "<b>The authority behind it is about members of the armed services and nothing else.</b> It is the clearest statement anywhere that the item and the profession decide and the seller does not — but it is not the authority that decides a contractor’s shirt. That runs through § 162 and adaptability case law, and this desk holds neither.",
   "rec": "Ratify. The rule is right, the input you asked for exists, and the caveat already says the coverage is narrower than the rule.",
 },
}


def positions():
    rows = []
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for q in desk.positions:
            if not q.proposed:
                continue
            src = next((s for s in desk.sources
                        if record.from_source(q.citation, s.citation_prefix)), None)
            rows.append({
                "desk": desk.name, "id": q.id, "title": q.title,
                "position": q.position, "citation": q.citation, "why": q.why,
                "tier": src.tier if src else "unresolved",
                "source": src.title if src else "unresolved",
                "kind": "conclusion" if (desk.name, q.id) in CONCLUSIONS else "rule",
                "unlocks": sum(1 for p in desk.problems if p.citation == q.citation),
                "note": NOTES.get((desk.name, q.id), {}),
            })
    rows.sort(key=lambda r: (0 if (r["desk"], r["id"]) in FIRST else 1,
                             r["desk"], r["id"]))
    return rows


def _md(t: str) -> str:
    out = html.escape(t)
    for mark, tag in (("**", "strong"), ("`", "code")):
        parts = out.split(mark)
        out = "".join(p if i % 2 == 0 else f"<{tag}>{p}</{tag}>"
                      for i, p in enumerate(parts))
    return re.sub(r"\n\s*\n", "</p><p>", out).replace("\n", " ")


if __name__ == "__main__":
    print(json.dumps(positions(), indent=2))


_CSS = """
:root{--paper:#F5F5F2;--sheet:#FFF;--rule:#DCDCD6;--soft:#E9E9E4;
 --ink:#161E28;--ink2:#4A5563;--ink3:#7A8494;
 --ox:#8C2F39;--ox-soft:#F3E3E4;--ledger:#2C6650;--ledger-soft:#E2EDE8;
 --amber:#8A5A16;--amber-soft:#F6EBD9;--focus:#2F5C9E;
 --shadow:0 1px 2px rgba(22,30,40,.05),0 8px 24px rgba(22,30,40,.06)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#12161C;--sheet:#1A1F27;--rule:#2C333D;--soft:#232A33;
 --ink:#E7E9EC;--ink2:#AEB6C2;--ink3:#7C8593;--ox:#E2848C;--ox-soft:#331E21;
 --ledger:#79C4A5;--ledger-soft:#16291F;--amber:#DCA85E;--amber-soft:#2A2114;
 --focus:#7FA9E8;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.3)}}
:root[data-theme="dark"]{--paper:#12161C;--sheet:#1A1F27;--rule:#2C333D;--soft:#232A33;
 --ink:#E7E9EC;--ink2:#AEB6C2;--ink3:#7C8593;--ox:#E2848C;--ox-soft:#331E21;
 --ledger:#79C4A5;--ledger-soft:#16291F;--amber:#DCA85E;--amber-soft:#2A2114;
 --focus:#7FA9E8;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.3)}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-size:16px;line-height:1.62;
 font-family:"Public Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:48rem;margin:0 auto;padding:2.25rem 1.25rem 5rem}
h1,h2,h3{font-family:Newsreader,Georgia,serif;font-weight:600;margin:0;text-wrap:balance}
a{color:var(--focus)} code{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-size:.85em}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:3px}
header.mast{border-bottom:2px solid var(--ink);padding-bottom:.9rem;margin-bottom:1.1rem}
.eyebrow{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:700}
h1{font-size:clamp(1.8rem,4.5vw,2.5rem);line-height:1.1;margin:.3rem 0 .3rem}
.mast p{color:var(--ink2);margin:0;max-width:60ch}
.preface{background:var(--sheet);border:1px solid var(--rule);border-left:3px solid var(--focus);
 padding:.9rem 1.1rem;margin-bottom:1.6rem}
.preface p{margin:.4rem 0;max-width:62ch}
.progress{display:flex;gap:3px;margin-bottom:.5rem}
.tick{flex:1;height:5px;background:var(--soft);border-radius:1px}
.tick.done{background:var(--ledger)} .tick.no{background:var(--ox)}
.tick.here{background:var(--ink)}
.counter{font-size:.76rem;color:var(--ink3);letter-spacing:.05em;text-transform:uppercase;
 font-weight:700;margin-bottom:1rem;display:flex;justify-content:space-between}
.card{background:var(--sheet);border:1px solid var(--rule);border-left:3px solid var(--amber);
 box-shadow:var(--shadow);padding:1.4rem 1.5rem}
.card[data-state="yes"]{border-left-color:var(--ledger)}
.card[data-state="no"]{border-left-color:var(--ox)}
@media (max-width:34rem){.card{padding:1.1rem}}
.chips{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.7rem}
.chip{font-size:.68rem;letter-spacing:.07em;text-transform:uppercase;font-weight:700;
 padding:.18rem .5rem;border-radius:2px;background:var(--soft);color:var(--ink3)}
.chip.primary{background:var(--ledger-soft);color:var(--ledger)}
.chip.secondary{background:var(--amber-soft);color:var(--amber)}
.chip.tertiary{background:var(--ox-soft);color:var(--ox)}
.chip.kind{background:var(--ink);color:var(--paper)}
h2.t{font-size:1.4rem;line-height:1.24;margin:0 0 .8rem}
.says{border-left:2px solid var(--ink);padding:.2rem 0 .2rem .95rem;margin:.9rem 0;
 font-family:Newsreader,Georgia,serif;font-size:1.12rem;line-height:1.5}
.says b{display:block;font-family:"Public Sans",sans-serif;font-size:.68rem;font-weight:700;
 letter-spacing:.09em;text-transform:uppercase;color:var(--ink3);margin-bottom:.3rem}
.rests{background:var(--soft);padding:.6rem .8rem;margin:.9rem 0;font-size:.88rem;color:var(--ink2)}
.rests .c{font-family:"JetBrains Mono",monospace;font-size:.8rem;word-break:break-word;color:var(--ink)}
.blk{margin:.9rem 0;padding:.65rem .85rem;font-size:.93rem}
.blk h4{margin:0 0 .2rem;font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;
 font-family:"Public Sans",sans-serif;font-weight:700}
.blk p{margin:.25rem 0;max-width:62ch}
.blk.for{background:var(--ledger-soft);border-left:2px solid var(--ledger)}
.blk.for h4{color:var(--ledger)}
.blk.against{background:var(--ox-soft);border-left:2px solid var(--ox)}
.blk.against h4{color:var(--ox)}
.blk.silent{background:var(--amber-soft);border-left:2px solid var(--amber)}
.blk.silent h4{color:var(--amber)}
.blk.rec{background:var(--soft);border-left:2px solid var(--ink)}
.blk.rec h4{color:var(--ink)}
details.why{margin:.9rem 0}
details.why summary{cursor:pointer;font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;
 color:var(--ink3);font-weight:700}
details.why .d{color:var(--ink2);font-size:.92rem;margin-top:.5rem;max-width:62ch}
.answer{border-top:1px dashed var(--rule);margin-top:1.2rem;padding-top:1rem}
.answer>label{font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink3);font-weight:700}
.picks{display:flex;gap:.45rem;flex-wrap:wrap;margin:.55rem 0}
button.pick{font-family:inherit;font-size:.92rem;font-weight:500;cursor:pointer;background:var(--sheet);
 color:var(--ink);border:1px solid var(--rule);padding:.45rem .95rem;border-radius:2px}
button.pick:hover{border-color:var(--ink3)}
button.pick[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
textarea{width:100%;min-height:3.6rem;font-family:inherit;font-size:.95rem;line-height:1.55;
 color:var(--ink);background:var(--paper);border:1px solid var(--rule);padding:.6rem .7rem;
 border-radius:2px;resize:vertical}
textarea::placeholder{color:var(--ink3)}
.saved{font-size:.76rem;color:var(--ink3);margin-top:.4rem;min-height:1.1em}
.saved.ok{color:var(--ledger)} .saved.err{color:var(--ox)}
nav.step{display:flex;gap:.6rem;align-items:center;justify-content:space-between;margin-top:1.4rem}
nav.step button{font-family:inherit;font-size:.92rem;font-weight:600;cursor:pointer;
 background:var(--ink);color:var(--paper);border:1px solid var(--ink);padding:.55rem 1.2rem;border-radius:2px}
nav.step button.ghost{background:transparent;color:var(--ink);border-color:var(--rule)}
nav.step button:disabled{opacity:.35;cursor:not-allowed}
.done-note{background:var(--ledger-soft);border:1px solid var(--ledger);color:var(--ledger);
 padding:.8rem 1rem;margin-top:1.2rem;font-size:.93rem;display:none}
.done-note.show{display:block}
.banner{background:var(--amber-soft);border:1px solid var(--amber);color:var(--amber);
 padding:.6rem .85rem;font-size:.88rem;margin-bottom:1.2rem;display:none}
.banner.show{display:block}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

_PAGE = """<title>Seventeen positions, one at a time</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<style>%s</style>
<div class="wrap">
<header class="mast">
  <div class="eyebrow">Positions · Sethuraman Accounting, Tax &amp; Consulting</div>
  <h1>Seventeen positions, one at a time</h1>
  <p>Generated from the record, so nothing here is a position a desk does not hold. Each answer saves as you give it.</p>
</header>

<div id="offline" class="banner">Answers are not saving — this view could not reach the store. Tell me in the conversation instead.</div>

<div class="preface">
  <p><b>A correction before you start.</b> I have been telling you that ratifying these is the difference between desks that defer and desks that help. <b>That is wrong for fifteen of the seventeen</b>, and the measurement says so: not one of these sits on a citation any of its own desk's problems turn on. The cash desk's two do — 2 of 2 — which is why ratifying those made all four problems answerable. <b>Ratifying these changes no score.</b></p>
  <p><b>What they change is what a desk says when it cannot answer.</b> Twelve of the seventeen are not conclusions about tax law at all — they are rules about how you work: <i>hold it, ask who owns it, request these documents by name, obtain the figure rather than assume it.</i> Which is the thing you described wanting five minutes ago. They were already that; nobody had said so.</p>
  <p>So each card says which kind it is. <b>A conclusion can be wrong about the law. A rule can only be wrong about the practice</b> — and only you can say whether a rule is how you actually work.</p>
</div>

<div class="progress" id="prog"></div>
<div class="counter"><span id="count"></span><span id="tally"></span></div>
<div id="stage"></div>
<nav class="step">
  <button class="ghost" id="prev" type="button">← Back</button>
  <button id="next" type="button">Next →</button>
</nav>
<div class="done-note" id="done">That is all seventeen. Anything you left on <b>Not yet</b> stays a proposal and comes back next time — nothing is lost by skipping it.</div>
</div>
<script>const DATA = %s;</script>
<script>%s</script>
"""

_JS = """
const stage = document.getElementById("stage");
const prog = document.getElementById("prog");
const state = {};
let at = 0, db = null;

DATA.forEach(() => { const t = document.createElement("div"); t.className = "tick"; prog.appendChild(t); });

const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function paintProgress() {
  [...prog.children].forEach((t, i) => {
    const c = (state[DATA[i].key] || {}).choice;
    t.className = "tick" + (i === at ? " here" : c === "Ratify it" ? " done" : c === "No" ? " no" : "");
  });
  const answered = DATA.filter(d => (state[d.key] || {}).choice).length;
  document.getElementById("count").textContent = `Position ${at + 1} of ${DATA.length}`;
  document.getElementById("tally").textContent = `${answered} answered`;
  document.getElementById("prev").disabled = at === 0;
  document.getElementById("next").disabled = at === DATA.length - 1;
  document.getElementById("done").classList.toggle("show", answered === DATA.length);
}

function render() {
  const d = DATA[at], n = d.note || {}, s = state[d.key] || {};
  const kindLabel = d.kind === "conclusion" ? "a conclusion about the law" : "a rule about how you work";
  stage.innerHTML = `
   <div class="card" id="card" data-state="${s.choice === "Ratify it" ? "yes" : s.choice === "No" ? "no" : ""}">
    <div class="chips">
      <span class="chip">${esc(d.desk)} · ${esc(d.id)}</span>
      <span class="chip ${esc(d.tier)}">${esc(d.tier)} authority</span>
      <span class="chip kind">${kindLabel}</span>
    </div>
    <h2 class="t">${esc(d.title)}</h2>
    <div class="says"><b>What the desk would say, in your words</b>&ldquo;${esc(d.position)}&rdquo;</div>
    <div class="rests">Rests on <span class="c">${esc(d.citation)}</span><br>${esc(d.source)}</div>
    ${n.read ? `<div class="blk rec"><h4>Before you decide</h4><p>${n.read}</p></div>` : ""}
    ${n.for ? `<div class="blk for"><h4>What supports it</h4><p>${n.for}</p></div>` : ""}
    ${n.against ? `<div class="blk against"><h4>What cuts against it</h4><p>${n.against}</p></div>` : ""}
    ${n.silent ? `<div class="blk silent"><h4>What the authority does not say</h4><p>${n.silent}</p></div>` : ""}
    <div class="blk rec"><h4>What saying yes changes</h4><p>${
      d.unlocks > 0
        ? `<b>${d.unlocks}</b> of this desk's scored problems turn on this exact citation, so ratifying makes them answerable.`
        : `<b>No scored problem changes.</b> What changes is that the desk stops handing the question back and starts saying ${d.kind === "rule" ? "what to do next" : "this, in your words, with the citation behind it"}.`
    }</p></div>
    ${n.rec ? `<div class="blk rec"><h4>What I would do</h4><p>${n.rec}</p></div>` : ""}
    ${d.why ? `<details class="why"><summary>The full reasoning as drafted</summary><div class="d">${esc(d.why).replace(/\\n\\n/g, "</p><p>").replace(/\\n/g, " ")}</div></details>` : ""}
    <div class="answer">
      <label for="notes">Your answer</label>
      <div class="picks">
        ${["Ratify it", "No", "Not yet"].map(p =>
          `<button type="button" class="pick" data-choice="${p}" aria-pressed="${s.choice === p}">${p}</button>`).join("")}
      </div>
      <textarea id="notes" placeholder="Reword it and I will use your words, not the draft's.">${esc(s.notes || "")}</textarea>
      <div class="saved" role="status" aria-live="polite"></div>
    </div>
   </div>`;

  const card = document.getElementById("card");
  const notes = card.querySelector("textarea");
  const said = card.querySelector(".saved");
  let timer = null;

  const save = () => {
    const cur = state[d.key] || {};
    if (!db) { said.className = "saved err"; said.textContent = "Not saving — tell me in the conversation."; return; }
    said.className = "saved"; said.textContent = "Saving\\u2026";
    db.doc("positions/" + d.key).set({
      desk: d.desk, position_id: d.id, title: d.title,
      choice: cur.choice || "", notes: notes.value, answeredAt: new Date().toISOString()
    }).then(() => { said.className = "saved ok"; said.textContent = "Saved."; })
      .catch(e => { said.className = "saved err";
        said.textContent = "Not saved (" + ((e && e.code) || "unknown") + "). Your text is still on screen."; });
  };

  card.querySelectorAll(".pick").forEach(b => b.addEventListener("click", () => {
    const cur = state[d.key] || (state[d.key] = {});
    cur.choice = cur.choice === b.dataset.choice ? "" : b.dataset.choice;
    cur.notes = notes.value;
    card.dataset.state = cur.choice === "Ratify it" ? "yes" : cur.choice === "No" ? "no" : "";
    card.querySelectorAll(".pick").forEach(x =>
      x.setAttribute("aria-pressed", String(x.dataset.choice === cur.choice)));
    paintProgress(); clearTimeout(timer); save();
  }));
  notes.addEventListener("input", () => {
    (state[d.key] || (state[d.key] = {})).notes = notes.value;
    clearTimeout(timer); timer = setTimeout(save, 700);
  });
  paintProgress();
}

document.getElementById("prev").addEventListener("click", () => { if (at > 0) { at--; render(); } });
document.getElementById("next").addEventListener("click", () => { if (at < DATA.length - 1) { at++; render(); } });
document.addEventListener("keydown", e => {
  if (e.target.tagName === "TEXTAREA") return;
  if (e.key === "ArrowLeft" && at > 0) { at--; render(); }
  if (e.key === "ArrowRight" && at < DATA.length - 1) { at++; render(); }
});

render();

(async () => {
  db = await claude.use("db");
  if (!db) { document.getElementById("offline").classList.add("show"); return; }
  const snap = await db.collection("positions").get();
  snap.docs.forEach(doc => {
    const d = doc.data() || {};
    state[doc.id] = { choice: d.choice || "", notes: d.notes || "" };
  });
  render();
})();
"""


def page() -> str:
    rows = positions()
    for r in rows:
        r["key"] = f"{r['desk']}--{r['id']}"
    return _PAGE % (_CSS, json.dumps(rows), _JS)
