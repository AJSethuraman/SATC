"""Turn a gate pack into one page a reader can read and answer on.

    python3 tools/blind_read_page.py gate/<run> out.html [--reader firm]

The page holds the anonymised brains, the lettered transcripts and eight
numbered chips per character; picks save to the page's store when it is
published as an artifact with the db capability, under ``reads/<reader>``
(``answers``, ``seen_key``, ``note``). Read back with the artifact's
``read_db``, write ``{"A": n, ...}`` as ``reader_x.json`` and score with
``tools/score_gate.py`` unchanged. The key is never read here.
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

E = html.escape
LETTERS = "ABCDEFGH"
FIELD = re.compile(r"^- \*\*(.+?):\*\* ?(.*)$")
ORDER = ["Said", "Did", "Private objective", "Reads", "Happened to them"]
SHORT = {"Said": "Said", "Did": "Did", "Private objective": "Objective", "Reads": "Reads", "Happened to them": "Happened"}



def brain(pack: Path, n: int) -> str:
    text = (pack / "brains" / f"{n}.md").read_text(encoding="utf-8")
    secs, cur = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip(); secs[cur] = []
        elif line.startswith("# "):
            continue
        elif cur and line.strip():
            secs[cur].append(line.strip())
    parts = "".join(f'<div class="sec"><span class="lbl">{E(k)}</span><p>{E(" ".join(v))}</p></div>' for k, v in secs.items())
    return f'<article class="brain" id="brain-{n}"><h3><span class="bn">{n}</span> Brain {n}</h3>{parts}</article>'

def transcript(pack: Path, letter: str):
    text = (pack / "transcripts" / f"{letter}.md").read_text(encoding="utf-8")
    seeds, cur_seed, cur_round, rounds = [], None, None, 0
    for line in text.splitlines():
        if line.startswith("## Seed"):
            cur_seed = {"name": line[3:].strip(), "rounds": []}; seeds.append(cur_seed)
        elif line.startswith("### Round"):
            cur_round = {"n": line[4:].strip(), "f": {}}; cur_seed["rounds"].append(cur_round); rounds += 1
        else:
            m = FIELD.match(line)
            if m and cur_round is not None:
                cur_round["f"][m.group(1)] = m.group(2).strip()
    out = []
    for s in seeds:
        out.append(f'<h4 class="seed">{E(s["name"])} <span class="muted">· {len(s["rounds"])} rounds</span></h4>')
        for r in s["rounds"]:
            f = r["f"]; rn = r["n"].replace("Round ", "R")
            said = f.get("Said", "")
            rows = [f'<div class="round"><span class="rn">{E(rn)}</span><div class="rb">']
            if said:
                rows.append(f'<p class="said">{E(said)}</p>')
            for k in ORDER[1:]:
                if k in f:
                    cls = {"Did": "did", "Private objective": "obj", "Reads": "reads", "Happened to them": "hap"}[k]
                    rows.append(f'<p class="{cls}"><span class="lbl">{SHORT[k]}</span> {E(f[k])}</p>')
            rows.append('</div></div>')
            out.append("".join(rows))
    return "".join(out), rounds, len(seeds)

def char(pack: Path, letter: str) -> str:
    body, rounds, nseeds = transcript(pack, letter)
    chips = "".join(f'<button type="button" class="chip" data-letter="{letter}" data-n="{n}" aria-pressed="false" aria-label="Character {letter} is brain {n}">{n}</button>' for n in range(1, 9))
    alive = "" if rounds == 18 else f' <span class="muted">· died early, {rounds} of 18 rounds</span>'
    return f'''<article class="char" id="char-{letter}">
  <div class="charhead"><h3>Character {letter}{alive}</h3>
    <div class="pick"><span class="lbl">Wrote by brain</span><div class="chips">{chips}</div></div>
  </div>
  <details><summary>Read the transcript <span class="muted">· {rounds} rounds over {nseeds} seeds</span></summary><div class="tx">{body}</div></details>
</article>'''

def build(pack: Path, reader: str = "firm") -> str:
  brains = "".join(brain(pack, n) for n in range(1, 9))
  chars = "".join(char(pack, l) for l in LETTERS)
  run = pack.name
  tiles = "".join(f'<a class="tile" href="#char-{l}" id="tile-{l}"><span class="tl">{l}</span><span class="tv">–</span></a>' for l in LETTERS)

  page = f'''<title>Ember Vault Blind Read</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {{
    --ground: #ECEBE5; --surface: #FBFAF7; --ink: #1B1D1C; --muted: #626864; --line: #D3D3CB;
    --ember: #B4461A; --ember-soft: #F6E3DA; --seed: #2E5F5B; --mono-bg: #E4E4DC; --focus: #2E5F5B;
    --serif: "Fraunces", Georgia, "Times New Roman", serif;
    --sans: "Source Sans 3", "Segoe UI", Helvetica, Arial, sans-serif;
    --mono: "JetBrains Mono", Consolas, "Courier New", monospace;
    color-scheme: light dark;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
      --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --mono-bg: #24282B; --focus: #86C3BC;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
    --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --mono-bg: #24282B; --focus: #86C3BC;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--ground); color: var(--ink); font-family: var(--sans); font-size: 17px; line-height: 1.5; padding-inline: 16px; padding-block: 0 72px; }}
  .page {{ max-width: 720px; margin: 0 auto; }}
  h1, h2, h3, h4 {{ font-family: var(--serif); font-weight: 600; line-height: 1.15; margin: 0; text-wrap: balance; }}
  h1 {{ font-size: 2.3rem; font-variation-settings: "opsz" 144; letter-spacing: -.01em; }}
  h2 {{ font-size: 1.5rem; margin-top: 2.4rem; padding-bottom: .35rem; border-bottom: 1px solid var(--line); }}
  h3 {{ font-size: 1.2rem; }}
  p {{ margin: .5rem 0; max-width: 66ch; }}
  .eyebrow, .lbl {{ font-family: var(--mono); font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
  .lede {{ color: var(--muted); font-size: 1.05rem; }}
  .muted {{ color: var(--muted); font-weight: 400; font-family: var(--sans); font-size: .9rem; }}
  a {{ color: var(--seed); }}
  .top {{ padding-top: 28px; }}

  .sticky {{ position: sticky; top: 0; z-index: 5; background: var(--ground); padding: .6rem 0 .5rem; border-bottom: 1px solid var(--line); margin-top: 1.2rem; }}
  .tiles {{ display: flex; gap: .35rem; }}
  .tile {{ flex: 1 1 0; text-decoration: none; color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: .3rem 0 .25rem; text-align: center; line-height: 1.1; }}
  .tile .tl {{ display: block; font-family: var(--mono); font-size: .68rem; color: var(--muted); letter-spacing: .06em; }}
  .tile .tv {{ display: block; font-family: var(--serif); font-size: 1.15rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
  .tile.done {{ border-color: var(--ember); }}
  .tile.done .tv {{ color: var(--ember); }}
  .tile.dup .tv {{ text-decoration: underline wavy var(--ember); }}
  .status {{ margin-top: .4rem; font-size: .84rem; color: var(--muted); min-height: 1.2em; display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }}
  .status .warn {{ color: var(--ember); }}

  .ask {{ margin-top: 1.4rem; background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--ember); padding: .9rem 1.1rem 1rem; }}
  .ask p {{ margin: .3rem 0 .6rem; max-width: none; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: .4rem; }}
  .chip {{ font: 600 .95rem var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 999px; padding: .32rem .8rem; cursor: pointer; min-width: 2.4rem; }}
  .chip:hover {{ border-color: var(--muted); }}
  .chip[aria-pressed="true"] {{ background: var(--ember); color: #FFFFFF; border-color: var(--ember); }}
  .chip.used:not([aria-pressed="true"]) {{ color: var(--muted); border-style: dashed; }}
  .chip:focus-visible, textarea:focus-visible, .tile:focus-visible, summary:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}

  .brains {{ display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; margin-top: 1rem; }}
  .brain {{ background: var(--surface); border: 1px solid var(--line); padding: .9rem 1rem 1rem; }}
  .brain h3 {{ display: flex; align-items: baseline; gap: .55rem; margin-bottom: .5rem; }}
  .bn {{ font-family: var(--serif); color: var(--ember); font-size: 1.6rem; line-height: 1; }}
  .brain .sec {{ margin-top: .55rem; }}
  .brain .sec p {{ margin: .1rem 0 0; font-size: .95rem; max-width: none; }}

  .char {{ margin-top: 1.2rem; background: var(--surface); border: 1px solid var(--line); }}
  .charhead {{ padding: .9rem 1.1rem .8rem; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .6rem 1rem; }}
  .pick {{ display: flex; flex-direction: column; gap: .3rem; }}
  .pick .chips {{ gap: .3rem; }}
  .pick .chip {{ padding: .28rem 0; min-width: 2.2rem; text-align: center; font-family: var(--mono); font-weight: 500; }}
  details {{ border-top: 1px solid var(--line); }}
  summary {{ cursor: pointer; padding: .7rem 1.1rem; font-weight: 600; list-style: none; display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }}
  summary::-webkit-details-marker {{ display: none; }}
  summary::after {{ content: "open"; font: 500 .72rem var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--seed); }}
  details[open] summary::after {{ content: "close"; }}
  .tx {{ padding: 0 1.1rem 1rem; }}
  .seed {{ font-size: 1.05rem; margin: 1rem 0 .4rem; color: var(--seed); }}
  .round {{ display: grid; grid-template-columns: 2.6rem 1fr; gap: .4rem; padding: .5rem 0; border-top: 1px dashed var(--line); }}
  .rn {{ font-family: var(--mono); font-size: .78rem; color: var(--muted); padding-top: .25rem; }}
  .rb p {{ margin: .15rem 0; max-width: none; }}
  .said {{ font-size: 1.02rem; color: var(--ember); font-weight: 400; }}
  .did {{ font-family: var(--mono); font-size: .8rem; color: var(--ink); }}
  .obj, .reads {{ font-size: .92rem; color: var(--muted); }}
  .hap {{ font-size: .88rem; color: var(--muted); font-style: italic; }}
  .rb .lbl {{ margin-right: .3rem; }}

  textarea {{ display: block; width: 100%; min-height: 6rem; margin-top: .6rem; padding: .6rem .7rem; font: 400 1rem/1.5 var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 3px; resize: vertical; }}
  .save {{ font-size: .82rem; color: var(--muted); margin-top: .35rem; min-height: 1.2em; }}
  .save.err {{ color: var(--ember); }}
  .foot {{ margin-top: 2.4rem; padding-top: 1rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .92rem; }}
  @media (max-width: 560px) {{
    h1 {{ font-size: 1.8rem; }}
    .brains {{ grid-template-columns: 1fr; }}
    .charhead {{ padding-inline: .9rem; }}
    summary, .tx {{ padding-inline: .9rem; }}
    .round {{ grid-template-columns: 2.2rem 1fr; }}
  }}
  @media (prefers-reduced-motion: no-preference) {{ .chip {{ transition: background .12s, color .12s; }} }}
</style>

<div class="page">
  <header class="top">
    <div class="eyebrow">Gate run {run} · the house characters · read blind</div>
    <h1>Ember Vault Blind Read</h1>
    <p class="lede">Eight brains, each a one-page character sheet, played three short matches as eight characters. Names are stripped. Match each character to the brain that wrote it; every brain is used exactly once. Read the eight brains first, then the characters. Picks save as you go.</p>
  </header>

  <div class="sticky">
    <div class="tiles">{tiles}</div>
    <div class="status"><span id="count">0 of 8 picked</span><span id="dups" class="warn"></span></div>
  </div>

  <section class="ask" id="ask-key">
    <span class="lbl">Before you start</span>
    <p>Have you already seen the answer key for this run, the file called <code>KEY.json</code>? It sat inside the pack on GitHub and was printed in one session. An honest "yes" does not stop you reading; it decides whether this counts as the blind read the spec asks for.</p>
    <div class="chips" id="key-chips">
      <button type="button" class="chip" data-key="no" aria-pressed="false">No, never opened it</button>
      <button type="button" class="chip" data-key="yes" aria-pressed="false">Yes, I have seen it</button>
      <button type="button" class="chip" data-key="unsure" aria-pressed="false">Not sure</button>
    </div>
  </section>

  <h2>The eight brains</h2>
  <p class="muted">What each player-written sheet says. About a page each. "The character" stands in for the name.</p>
  <div class="brains">{brains}</div>

  <h2>The eight characters</h2>
  <p class="muted">What each one said and did, round by round, over three seeds. The spoken line is in colour; the private objective and the reads on the others are what the referee saw and the audience would see beside the speech. Pick a brain number on each.</p>
  {chars}

  <h2>What you saw</h2>
  <p class="muted">What gave a character away, or what did not. Which two you could not tell apart. Anything the readers after you should know.</p>
  <textarea id="note" placeholder="Optional."></textarea>
  <div class="save" id="save"></div>

  <div class="foot">Your picks and note save to a store only you and I can read. When all eight are picked, say "read the blind read" in any session, or leave it; the hourly check-in reads it and scores it with the same scorer the spec names, then writes the score into the log.</div>
</div>

<script>
(function () {{
  var LETTERS = "ABCDEFGH".split("");
  var db = null, timer = null;
  var state = {{ answers: {{}}, seen_key: "", note: "" }};

  function $(s) {{ return document.querySelector(s); }}
  function all(s) {{ return Array.prototype.slice.call(document.querySelectorAll(s)); }}
  function setSave(text, err) {{ var el = $("#save"); el.textContent = text; el.className = "save" + (err ? " err" : ""); }}
  function clock(iso) {{ try {{ var d = iso ? new Date(iso) : new Date(); return d.toLocaleTimeString([], {{ hour: "2-digit", minute: "2-digit" }}); }} catch (e) {{ return ""; }} }}

  function render() {{
    var used = {{}}, picked = 0;
    LETTERS.forEach(function (l) {{ var n = state.answers[l]; if (n) {{ picked++; used[n] = (used[n] || 0) + 1; }} }});
    LETTERS.forEach(function (l) {{
      var n = state.answers[l] || 0;
      all('.chip[data-letter="' + l + '"]').forEach(function (c) {{
        var cn = +c.getAttribute("data-n");
        c.setAttribute("aria-pressed", String(cn === n));
        c.classList.toggle("used", !!used[cn]);
      }});
      var t = $("#tile-" + l);
      t.querySelector(".tv").textContent = n ? String(n) : "–";
      t.classList.toggle("done", !!n);
      t.classList.toggle("dup", !!n && used[n] > 1);
    }});
    $("#count").textContent = picked + " of 8 picked";
    var dups = Object.keys(used).filter(function (k) {{ return used[k] > 1; }});
    $("#dups").textContent = dups.length ? "Brain " + dups.join(", ") + " picked more than once" : "";
    all("#key-chips .chip").forEach(function (c) {{ c.setAttribute("aria-pressed", String(c.getAttribute("data-key") === state.seen_key)); }});
    var ta = $("#note");
    if (document.activeElement !== ta && ta.value !== state.note) ta.value = state.note;
  }}

  function write() {{
    var body = {{ answers: state.answers, seen_key: state.seen_key, note: state.note, updated: new Date().toISOString(), run: "{run}" }};
    if (!db) {{ setSave("Not saved: this view cannot reach the store. Open the link in claude.ai.", true); return; }}
    setSave("Saving…");
    db.doc("reads/{reader}").set(body).then(function () {{ setSave("Saved " + clock()); }})
      .catch(function (e) {{ setSave("Not saved (" + (e && e.code ? e.code : "error") + "). Try again.", true); }});
  }}

  all('.chip[data-letter]').forEach(function (c) {{
    c.addEventListener("click", function () {{
      var l = c.getAttribute("data-letter"), n = +c.getAttribute("data-n");
      if (state.answers[l] === n) delete state.answers[l]; else state.answers[l] = n;
      render(); write();
    }});
  }});
  all("#key-chips .chip").forEach(function (c) {{
    c.addEventListener("click", function () {{
      var k = c.getAttribute("data-key");
      state.seen_key = (state.seen_key === k) ? "" : k;
      render(); write();
    }});
  }});
  $("#note").addEventListener("input", function () {{
    state.note = $("#note").value; setSave("Typing…");
    clearTimeout(timer); timer = setTimeout(write, 700);
  }});

  function boot() {{
    render();
    var p = (window.claude && typeof window.claude.use === "function") ? window.claude.use("db") : Promise.resolve(null);
    p.then(function (ns) {{
      if (!ns) {{ setSave("Picks made on this view are not being saved. Open the link in claude.ai to have them kept.", true); return; }}
      db = ns;
      db.doc("reads/{reader}").onSnapshot(function (doc) {{
        if (!doc.exists) return;
        var d = doc.data() || {{}};
        state.answers = (d.answers && typeof d.answers === "object") ? d.answers : {{}};
        state.seen_key = typeof d.seen_key === "string" ? d.seen_key : "";
        state.note = typeof d.note === "string" ? d.note : "";
        render();
        if (doc.metadata && doc.metadata.hasPendingWrites) setSave("Saving…"); else if (d.updated) setSave("Saved " + clock(d.updated));
      }}, function (e) {{ setSave("Saving stopped (" + (e && e.code ? e.code : "error") + "). Reload the page.", true); }});
    }});
  }}
  boot();
}})();
</script>
'''
  return page


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--reader", default="firm", help="store document under reads/<reader>")
    a = ap.parse_args(argv)
    page = build(a.pack, a.reader)
    a.out.write_text(page, encoding="utf-8")
    print(f"wrote {a.out} ({len(page.encode())} bytes) for {a.pack.name}, reader {a.reader}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
