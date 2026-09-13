"""Turn a gate pack into a replay you scroll: round by round, every
character's line in turn, with what they did and what happened to them.

    python3 tools/replay_page.py gate/<run> out.html

Reads only ``transcripts/*.md`` (lettered, names stripped), never the key.
The eight per-character transcripts are re-interleaved by seed and round so
the page can play a match the way an audience would see it.
"""
from __future__ import annotations

import argparse
import html
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


def render_feed(match: dict, index: int) -> str:
    """One match as a scrolling feed: a round header, then every character's
    line in turn, then what happened to them. A character that leaves the
    board is announced once, in the first round it is missing."""
    out = [f'<section class="match" id="match-{index}" data-match="{index}">']
    seen_gone: set[str] = set()
    for r in match["rounds"]:
        out.append(f'<h2 class="round">Round {r["n"]} <span class="of">of {len(match["rounds"])}</span></h2>')
        for L in LETTERS:
            c = r["chars"][L]
            if not c:
                if L not in seen_gone:
                    seen_gone.add(L)
                    out.append(f'<p class="gone">Character {L} is gone from the board.</p>')
                continue
            said = (c.get("said") or "").strip()
            out.append('<article class="line">')
            out.append(f'<span class="badge" aria-hidden="true">{L}</span>')
            out.append('<div class="bubble">')
            out.append(f'<span class="who">Character {L}</span>')
            out.append(f'<p class="said{"" if said else " quiet"}">{E(said) if said else "(says nothing)"}</p>')
            if c.get("did"):
                out.append(f'<p class="did">{E(c["did"])}</p>')
            if c.get("happened"):
                out.append(f'<p class="hap">{E(c["happened"])}</p>')
            if c.get("objective") or c.get("reads"):
                out.append('<p class="priv">')
                if c.get("objective"):
                    out.append(f'<span class="lbl">thinking</span> {E(c["objective"])}')
                if c.get("reads"):
                    out.append(f'<br><span class="lbl">reads</span> {E(c["reads"])}')
                out.append('</p>')
            out.append('</div></article>')
    out.append('</section>')
    return "".join(out)


def build(pack: Path, blind_read_url: str = "") -> str:
    matches = interleave(pack)
    run = pack.name
    total_rounds = sum(len(m["rounds"]) for m in matches)
    tabs = "".join(
        f'<button type="button" class="tab" data-tab="{i}" aria-pressed="{"true" if i == 0 else "false"}">Match {i + 1}<span class="sub">{E(m["seed"])} · {len(m["rounds"])} rounds</span></button>'
        for i, m in enumerate(matches))
    feeds = "".join(render_feed(m, i) for i, m in enumerate(matches))
    link = f'<a href="{E(blind_read_url)}">the blind read</a>' if blind_read_url else "the blind read"
    return f"""<title>Ember Vault Replay</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {{
    --ground: #ECEBE5; --surface: #FBFAF7; --ink: #1B1D1C; --muted: #626864; --line: #D3D3CB;
    --ember: #B4461A; --ember-soft: #F6E3DA; --seed: #2E5F5B; --focus: #2E5F5B;
    --serif: "Fraunces", Georgia, "Times New Roman", serif;
    --sans: "Source Sans 3", "Segoe UI", Helvetica, Arial, sans-serif;
    --mono: "JetBrains Mono", Consolas, "Courier New", monospace;
    color-scheme: light dark;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
      --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --focus: #86C3BC;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
    --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --focus: #86C3BC;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--ground); color: var(--ink); font-family: var(--sans); font-size: 17px; line-height: 1.45; padding-inline: 16px; padding-block: 0 72px; }}
  .page {{ max-width: 680px; margin: 0 auto; }}
  h1 {{ font-family: var(--serif); font-weight: 600; font-size: 2rem; line-height: 1.1; margin: 0; letter-spacing: -.01em; font-variation-settings: "opsz" 144; }}
  .top {{ padding-top: 26px; }}
  .lede {{ color: var(--muted); margin: .4rem 0 0; max-width: 60ch; }}
  .lbl {{ font-family: var(--mono); font-size: .7rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
  a {{ color: var(--seed); }}

  .bar {{ position: sticky; top: 0; z-index: 5; background: var(--ground); padding: .6rem 0 .55rem; border-bottom: 1px solid var(--line); margin-top: 1rem; display: flex; gap: .45rem; flex-wrap: wrap; align-items: stretch; }}
  .tab {{ flex: 1 1 0; min-width: 6.5rem; font: 600 .95rem var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: .4rem .6rem; cursor: pointer; text-align: left; line-height: 1.2; }}
  .tab .sub {{ display: block; font: 400 .74rem var(--mono); color: var(--muted); margin-top: .15rem; letter-spacing: .02em; }}
  .tab[aria-pressed="true"] {{ background: var(--ink); color: var(--surface); border-color: var(--ink); }}
  .tab[aria-pressed="true"] .sub {{ color: var(--surface); opacity: .75; }}
  .tab:focus-visible, .reveal:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
  .reveal {{ flex: 0 0 auto; font: 600 .85rem var(--sans); color: var(--seed); background: transparent; border: 1px solid var(--line); border-radius: 6px; padding: .4rem .7rem; cursor: pointer; }}
  .reveal[aria-pressed="true"] {{ background: var(--seed); color: var(--surface); border-color: var(--seed); }}

  .match[hidden] {{ display: none; }}
  h2.round {{ font-family: var(--serif); font-weight: 600; font-size: 1.35rem; margin: 1.8rem 0 .7rem; padding-bottom: .3rem; border-bottom: 2px solid var(--ember); }}
  h2.round .of {{ color: var(--muted); font-size: .95rem; font-family: var(--sans); font-weight: 400; }}
  .line {{ display: grid; grid-template-columns: 2.3rem 1fr; gap: .6rem; margin: .6rem 0; }}
  .badge {{ width: 2.3rem; height: 2.3rem; border-radius: 50%; background: var(--ember-soft); color: var(--ember); font-family: var(--serif); font-weight: 600; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; margin-top: .15rem; }}
  .bubble {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; border-top-left-radius: 3px; padding: .6rem .85rem .65rem; min-width: 0; }}
  .bubble .who {{ font-family: var(--mono); font-size: .7rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
  .bubble p {{ margin: .2rem 0 0; overflow-wrap: anywhere; }}
  .said {{ font-size: 1.06rem; line-height: 1.4; }}
  .said.quiet {{ color: var(--muted); font-style: italic; }}
  .did {{ font-family: var(--mono); font-size: .76rem; color: var(--muted); }}
  .hap {{ font-size: .88rem; color: var(--muted); font-style: italic; }}
  .priv {{ font-size: .88rem; color: var(--seed); border-top: 1px dashed var(--line); padding-top: .4rem; margin-top: .45rem !important; }}
  .priv .lbl {{ color: var(--seed); }}
  body:not(.reveal-on) .priv {{ display: none; }}
  .gone {{ color: var(--muted); font-style: italic; margin: .6rem 0 .6rem 2.9rem; }}
  .foot {{ margin-top: 2.4rem; padding-top: 1rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .92rem; }}
  @media (max-width: 560px) {{ h1 {{ font-size: 1.7rem; }} .tab {{ min-width: 5.6rem; }} }}
</style>

<div class="page">
  <header class="top">
    <h1>Ember Vault Replay</h1>
    <p class="lede">Three short matches, real model, names stripped to letters. Scroll. Each round, every character speaks once; under each line is what they did and what happened to them.</p>
  </header>

  <div class="bar">
    {tabs}
    <button type="button" class="reveal" id="reveal" aria-pressed="false">Show what they were thinking</button>
  </div>

  {feeds}

  <div class="foot">Gate run {E(run)} · {len(matches)} matches · {total_rounds} rounds. Picks belong on {link}. Built from the pack's lettered transcripts only; the answer key was never read.</div>
</div>

<script>
(function () {{
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
  var matches = Array.prototype.slice.call(document.querySelectorAll(".match"));
  function show(i) {{
    tabs.forEach(function (t, j) {{ t.setAttribute("aria-pressed", String(i === j)); }});
    matches.forEach(function (m, j) {{ m.hidden = (i !== j); }});
    window.scrollTo({{ top: 0 }});
  }}
  tabs.forEach(function (t, i) {{ t.addEventListener("click", function () {{ show(i); }}); }});
  show(0);
  var rv = document.getElementById("reveal");
  rv.addEventListener("click", function () {{
    var on = document.body.classList.toggle("reveal-on");
    rv.setAttribute("aria-pressed", String(on));
    rv.textContent = on ? "Hide what they were thinking" : "Show what they were thinking";
  }});
}})();
</script>
"""


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
