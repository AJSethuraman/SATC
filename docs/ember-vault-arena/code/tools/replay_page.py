"""Turn a gate pack into a live replay page: a round at a time, all eight
characters together, plus the voices side by side and one voice at a time.

    python3 tools/replay_page.py gate/<run> out.html

Reads only ``transcripts/*.md`` (lettered, names stripped), never the key.
The eight per-character transcripts are re-interleaved by seed and round so
the page can play a match the way an audience would see it.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

E = html.escape
LETTERS = "ABCDEFGH"
FIELD = re.compile(r"^- \*\*(.+?):\*\* ?(.*)$")
KEYS = {"Said": "said", "Did": "did", "Private objective": "objective", "Reads": "reads", "Happened to them": "happened"}


def parse_transcript(path: Path) -> dict[str, dict[int, dict[str, str]]]:
    """{seed name: {round number: {said, did, objective, reads, happened}}}"""
    seeds: dict[str, dict[int, dict[str, str]]] = {}
    cur_seed, cur_round = None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Seed"):
            cur_seed = line[3:].strip()
            seeds[cur_seed] = {}
        elif line.startswith("### Round"):
            cur_round = int(line.split()[-1])
            seeds[cur_seed][cur_round] = {}
        else:
            m = FIELD.match(line)
            if m and cur_round is not None and m.group(1) in KEYS:
                seeds[cur_seed][cur_round][KEYS[m.group(1)]] = m.group(2).strip()
    return seeds


def interleave(pack: Path) -> list[dict]:
    """[{seed, rounds: [{n, chars: {A: {...} or None}}]}] in seed order."""
    per_letter = {L: parse_transcript(pack / "transcripts" / f"{L}.md") for L in LETTERS}
    seed_names: list[str] = []
    for L in LETTERS:
        for s in per_letter[L]:
            if s not in seed_names:
                seed_names.append(s)
    out = []
    for s in seed_names:
        max_round = max((max(per_letter[L].get(s, {0: None}).keys()) for L in LETTERS), default=0)
        rounds = []
        for n in range(1, max_round + 1):
            rounds.append({"n": n, "chars": {L: per_letter[L].get(s, {}).get(n) for L in LETTERS}})
        out.append({"seed": s, "rounds": rounds})
    return out


def build(pack: Path, blind_read_url: str = "") -> str:
    matches = interleave(pack)
    data = json.dumps(matches, ensure_ascii=False).replace("</", "<\\/")
    run = pack.name
    total_rounds = sum(len(m["rounds"]) for m in matches)
    link = f'<a href="{E(blind_read_url)}">the blind read</a>' if blind_read_url else "the blind read"
    return f'''<title>Ember Vault Replay</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {{
    --ground: #ECEBE5; --surface: #FBFAF7; --ink: #1B1D1C; --muted: #626864; --line: #D3D3CB;
    --ember: #B4461A; --ember-soft: #F6E3DA; --seed: #2E5F5B; --seed-soft: #DDEAE8; --focus: #2E5F5B;
    --serif: "Fraunces", Georgia, "Times New Roman", serif;
    --sans: "Source Sans 3", "Segoe UI", Helvetica, Arial, sans-serif;
    --mono: "JetBrains Mono", Consolas, "Courier New", monospace;
    color-scheme: light dark;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
      --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --seed-soft: #1F3331; --focus: #86C3BC;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
    --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --seed-soft: #1F3331; --focus: #86C3BC;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--ground); color: var(--ink); font-family: var(--sans); font-size: 17px; line-height: 1.45; padding-inline: 16px; padding-block: 0 72px; }}
  .page {{ max-width: 860px; margin: 0 auto; }}
  h1, h2, h3 {{ font-family: var(--serif); font-weight: 600; line-height: 1.15; margin: 0; text-wrap: balance; }}
  h1 {{ font-size: 2.2rem; font-variation-settings: "opsz" 144; letter-spacing: -.01em; }}
  h2 {{ font-size: 1.4rem; margin-top: 2.2rem; padding-bottom: .35rem; border-bottom: 1px solid var(--line); }}
  p {{ margin: .5rem 0; max-width: 66ch; }}
  .eyebrow, .lbl {{ font-family: var(--mono); font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
  .lede {{ color: var(--muted); font-size: 1.05rem; }}
  .muted {{ color: var(--muted); }}
  a {{ color: var(--seed); }}
  .top {{ padding-top: 28px; }}
  button {{ font: 600 .92rem var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 999px; padding: .38rem .9rem; cursor: pointer; }}
  button:hover {{ border-color: var(--muted); }}
  button[aria-pressed="true"] {{ background: var(--ink); color: var(--surface); border-color: var(--ink); }}
  button.play {{ background: var(--ember); color: #FFFFFF; border-color: var(--ember); min-width: 6rem; }}
  button:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}

  .deck {{ position: sticky; top: 0; z-index: 5; background: var(--ground); padding: .7rem 0 .6rem; border-bottom: 1px solid var(--line); margin-top: 1.2rem; }}
  .row {{ display: flex; flex-wrap: wrap; gap: .45rem; align-items: center; }}
  .row + .row {{ margin-top: .5rem; }}
  .spacer {{ flex: 1; }}
  .roundmark {{ font-family: var(--serif); font-size: 1.35rem; font-variant-numeric: tabular-nums; }}
  .roundmark .of {{ color: var(--muted); font-size: 1rem; font-family: var(--sans); }}
  .bar {{ height: 3px; background: var(--line); margin-top: .5rem; border-radius: 2px; overflow: hidden; }}
  .bar > div {{ height: 100%; background: var(--ember); width: 0; transition: width .2s linear; }}

  .stage {{ display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; margin-top: 1rem; }}
  .card {{ background: var(--surface); border: 1px solid var(--line); padding: .7rem .85rem .75rem; min-height: 6rem; display: flex; flex-direction: column; gap: .35rem; }}
  .card.gone {{ opacity: .45; }}
  .card .who {{ display: flex; align-items: baseline; gap: .5rem; }}
  .card .who .l {{ font-family: var(--serif); font-size: 1.3rem; color: var(--ember); line-height: 1; }}
  .card .said {{ font-size: 1.02rem; color: var(--ink); margin: 0; }}
  .card .said.quiet {{ color: var(--muted); font-style: italic; }}
  .card .did {{ font-family: var(--mono); font-size: .76rem; color: var(--muted); margin: 0; }}
  .card .hap {{ font-size: .86rem; color: var(--muted); font-style: italic; margin: 0; }}
  .card .priv {{ font-size: .86rem; color: var(--seed); margin: 0; border-top: 1px dashed var(--line); padding-top: .35rem; }}
  .card .priv .lbl {{ color: var(--seed); }}
  body:not(.reveal) .card .priv {{ display: none; }}

  .voices {{ overflow-x: auto; margin-top: .8rem; border: 1px solid var(--line); background: var(--surface); }}
  table {{ border-collapse: collapse; min-width: 900px; width: 100%; font-size: .88rem; }}
  th, td {{ text-align: left; vertical-align: top; padding: .5rem .55rem; border-bottom: 1px solid var(--line); }}
  th {{ font-family: var(--mono); font-size: .74rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); position: sticky; top: 0; background: var(--surface); }}
  th button {{ font: 600 .8rem var(--serif); color: var(--ember); border: 0; background: transparent; padding: 0; cursor: pointer; }}
  td.rn {{ font-family: var(--mono); font-size: .74rem; color: var(--muted); white-space: nowrap; }}
  td.cur {{ background: var(--ember-soft); }}
  td.none {{ color: var(--muted); }}

  .one {{ display: grid; grid-template-columns: 1fr; gap: .4rem; margin-top: .8rem; }}
  .one .line {{ background: var(--surface); border: 1px solid var(--line); padding: .55rem .8rem; display: grid; grid-template-columns: 5.2rem 1fr; gap: .6rem; }}
  .one .tag {{ font-family: var(--mono); font-size: .72rem; color: var(--muted); padding-top: .2rem; }}
  .one .line p {{ margin: 0; max-width: none; }}
  .one .line .sub {{ font-size: .84rem; color: var(--muted); font-style: italic; margin-top: .15rem; }}
  .foot {{ margin-top: 2.4rem; padding-top: 1rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .92rem; }}
  @media (max-width: 560px) {{
    h1 {{ font-size: 1.75rem; }}
    .stage {{ grid-template-columns: 1fr; }}
    .card {{ min-height: 0; }}
  }}
  @media (prefers-reduced-motion: reduce) {{ .bar > div {{ transition: none; }} }}
</style>

<div class="page">
  <header class="top">
    <div class="eyebrow">Gate run {E(run)} · {len(matches)} short matches · {total_rounds} rounds · real model, names stripped</div>
    <h1>Ember Vault Replay</h1>
    <p class="lede">The same three scouting matches as {link}, played back a round at a time with all eight characters on screen, as an audience would see it. Below that, every voice side by side, and one voice on its own.</p>
  </header>

  <div class="deck">
    <div class="row" id="seeds"></div>
    <div class="row">
      <button type="button" class="play" id="play">Play</button>
      <button type="button" id="prev" aria-label="Previous round">‹ Back</button>
      <button type="button" id="next" aria-label="Next round">Next ›</button>
      <span class="spacer"></span>
      <span class="roundmark"><span id="rn">1</span> <span class="of">of <span id="rt">6</span></span></span>
    </div>
    <div class="row">
      <span class="lbl">Pace</span>
      <button type="button" data-pace="8000" aria-pressed="false">Quick</button>
      <button type="button" data-pace="20000" aria-pressed="true">Read along</button>
      <button type="button" data-pace="45000" aria-pressed="false">Slow</button>
      <span class="spacer"></span>
      <button type="button" id="reveal" aria-pressed="false">Show private thoughts</button>
    </div>
    <div class="bar"><div id="prog"></div></div>
  </div>

  <div class="stage" id="stage"></div>

  <h2>Every voice, side by side</h2>
  <p class="muted">Rows are rounds, columns are characters, cells are only what they said out loud. Read down a column to hear one character; read across a row to compare the eight in the same moment. The current round is shaded. Tap a letter to open that voice alone below.</p>
  <div class="voices"><table id="voices"></table></div>

  <h2 id="one-h">One voice on its own</h2>
  <p class="muted" id="one-p">Every line one character spoke, across all three matches, in order. Tap a letter above to change who.</p>
  <div class="row" id="pick"></div>
  <div class="one" id="one"></div>

  <div class="foot">Nothing here is saved; it is a viewer. Picks belong on the blind read page. Built from the pack's lettered transcripts only; the answer key was never read.</div>
</div>

<script>
(function () {{
  var DATA = {data};
  var LETTERS = "ABCDEFGH".split("");
  var st = {{ seed: 0, round: 0, playing: false, pace: 20000, voice: "A" }};
  var timer = null, tick = null, started = 0;
  function $(s) {{ return document.querySelector(s); }}
  function el(tag, cls, text) {{ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }}
  function match() {{ return DATA[st.seed]; }}
  function rounds() {{ return match().rounds; }}

  function renderSeeds() {{
    var box = $("#seeds"); box.innerHTML = "";
    var lbl = el("span", "lbl", "Match"); box.appendChild(lbl);
    DATA.forEach(function (m, i) {{
      var b = el("button", "", (i + 1) + " · " + m.seed + " · " + m.rounds.length + " rounds");
      b.setAttribute("aria-pressed", String(i === st.seed));
      b.addEventListener("click", function () {{ stop(); st.seed = i; st.round = 0; renderAll(); }});
      box.appendChild(b);
    }});
  }}

  function renderStage() {{
    var r = rounds()[st.round]; var stage = $("#stage"); stage.innerHTML = "";
    LETTERS.forEach(function (L) {{
      var c = r.chars[L]; var card = el("article", "card" + (c ? "" : " gone"));
      var who = el("div", "who"); who.appendChild(el("span", "l", L)); who.appendChild(el("span", "lbl", "Character " + L)); card.appendChild(who);
      if (!c) {{ card.appendChild(el("p", "said quiet", "Gone from the board.")); stage.appendChild(card); return; }}
      var said = c.said && c.said.trim();
      card.appendChild(el("p", "said" + (said ? "" : " quiet"), said || "(says nothing)"));
      if (c.did) card.appendChild(el("p", "did", c.did));
      if (c.happened) card.appendChild(el("p", "hap", c.happened));
      if (c.objective || c.reads) {{
        var pv = el("p", "priv");
        var l1 = el("span", "lbl", "Thinking "); pv.appendChild(l1); pv.appendChild(document.createTextNode(c.objective || ""));
        if (c.reads) {{ pv.appendChild(el("br")); var l2 = el("span", "lbl", "Reads "); pv.appendChild(l2); pv.appendChild(document.createTextNode(c.reads)); }}
        card.appendChild(pv);
      }}
      stage.appendChild(card);
    }});
    $("#rn").textContent = String(st.round + 1); $("#rt").textContent = String(rounds().length);
    document.querySelectorAll("#voices td").forEach(function (td) {{ td.classList.toggle("cur", td.getAttribute("data-round") === String(st.round)); }});
  }}

  function renderVoices() {{
    var t = $("#voices"); t.innerHTML = "";
    var thead = el("thead"); var tr = el("tr"); tr.appendChild(el("th", "", "Round"));
    LETTERS.forEach(function (L) {{ var th = el("th"); var b = el("button", "", L); b.addEventListener("click", function () {{ st.voice = L; renderOne(); $("#one-h").scrollIntoView({{ behavior: "smooth" }}); }}); th.appendChild(b); tr.appendChild(th); }});
    thead.appendChild(tr); t.appendChild(thead);
    var tb = el("tbody");
    rounds().forEach(function (r, i) {{
      var row = el("tr"); var rn = el("td", "rn", "R" + r.n); rn.setAttribute("data-round", String(i)); row.appendChild(rn);
      LETTERS.forEach(function (L) {{
        var c = r.chars[L]; var said = c && c.said && c.said.trim();
        var td = el("td", said ? "" : "none", c ? (said || "(silent)") : "—"); td.setAttribute("data-round", String(i));
        td.addEventListener("click", function () {{ stop(); st.round = i; renderStage(); }});
        row.appendChild(td);
      }});
      tb.appendChild(row);
    }});
    t.appendChild(tb);
  }}

  function renderOne() {{
    var pick = $("#pick"); pick.innerHTML = "";
    LETTERS.forEach(function (L) {{ var b = el("button", "", L); b.setAttribute("aria-pressed", String(L === st.voice)); b.addEventListener("click", function () {{ st.voice = L; renderOne(); }}); pick.appendChild(b); }});
    var box = $("#one"); box.innerHTML = "";
    var count = 0;
    DATA.forEach(function (m, mi) {{
      m.rounds.forEach(function (r) {{
        var c = r.chars[st.voice]; if (!c) return;
        var line = el("div", "line"); line.appendChild(el("span", "tag", "M" + (mi + 1) + " R" + r.n));
        var body = el("div"); var said = c.said && c.said.trim();
        var p = el("p", said ? "" : "muted", said || "(says nothing)"); body.appendChild(p);
        if (document.body.classList.contains("reveal") && c.objective) body.appendChild(el("div", "sub", c.objective));
        line.appendChild(body); box.appendChild(line); count++;
      }});
    }});
    $("#one-p").textContent = "Every line Character " + st.voice + " spoke, across all three matches, in order: " + count + " rounds on the board. Tap a letter to change who.";
  }}

  function renderAll() {{ renderSeeds(); renderVoices(); renderStage(); renderOne(); }}

  function step(d) {{ var n = rounds().length; st.round = (st.round + d + n) % n; renderStage(); started = Date.now(); }}
  function start() {{
    st.playing = true; $("#play").textContent = "Pause"; started = Date.now();
    timer = setInterval(function () {{ step(1); }}, st.pace);
    tick = setInterval(function () {{ var f = Math.min(1, (Date.now() - started) / st.pace); $("#prog").style.width = (f * 100) + "%"; }}, 200);
  }}
  function stop() {{ st.playing = false; $("#play").textContent = "Play"; clearInterval(timer); clearInterval(tick); $("#prog").style.width = "0%"; }}

  $("#play").addEventListener("click", function () {{ if (st.playing) stop(); else start(); }});
  $("#prev").addEventListener("click", function () {{ stop(); step(-1); }});
  $("#next").addEventListener("click", function () {{ stop(); step(1); }});
  document.querySelectorAll("[data-pace]").forEach(function (b) {{
    b.addEventListener("click", function () {{
      document.querySelectorAll("[data-pace]").forEach(function (x) {{ x.setAttribute("aria-pressed", "false"); }});
      b.setAttribute("aria-pressed", "true"); st.pace = +b.getAttribute("data-pace");
      if (st.playing) {{ stop(); start(); }}
    }});
  }});
  $("#reveal").addEventListener("click", function () {{
    var on = document.body.classList.toggle("reveal");
    $("#reveal").setAttribute("aria-pressed", String(on));
    $("#reveal").textContent = on ? "Hide private thoughts" : "Show private thoughts";
    renderOne();
  }});
  document.addEventListener("keydown", function (e) {{
    if (e.target && /INPUT|TEXTAREA|BUTTON/.test(e.target.tagName)) return;
    if (e.key === "ArrowRight") {{ stop(); step(1); }} else if (e.key === "ArrowLeft") {{ stop(); step(-1); }} else if (e.key === " ") {{ e.preventDefault(); if (st.playing) stop(); else start(); }}
  }});
  renderAll();
}})();
</script>
'''


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--blind-read-url", default="", help="link to the blind-read page for the same pack")
    a = ap.parse_args(argv)
    page = build(a.pack, a.blind_read_url)
    a.out.write_text(page, encoding="utf-8")
    print(f"wrote {a.out} ({len(page.encode())} bytes) for {a.pack.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
