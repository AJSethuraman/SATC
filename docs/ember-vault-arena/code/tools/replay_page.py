"""Turn a match into a replay you scroll.

Two sources:

    python3 tools/replay_page.py gate/<run> out.html            # a gate pack: letters, no key read
    python3 tools/replay_page.py runs/<match>.replay.json out.html   # a full match record, names and all

From a gate pack the page carries what the pack carries: each character's
spoken line, action and what happened to them, re-joined by seed and round.
From a replay bundle (``python run.py replay <match_id> --output ...``) it
carries everything the referee recorded, in the order it happened: every
line spoken, every move, every swing and its dice, every monster step, the
narration, and where everyone stood at the end of each round.
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

CSS = """
  :root {
    --ground: #ECEBE5; --surface: #FBFAF7; --ink: #1B1D1C; --muted: #626864; --line: #D3D3CB;
    --ember: #B4461A; --ember-soft: #F6E3DA; --seed: #2E5F5B; --seed-soft: #DDEAE8; --focus: #2E5F5B;
    --serif: "Fraunces", Georgia, "Times New Roman", serif;
    --sans: "Source Sans 3", "Segoe UI", Helvetica, Arial, sans-serif;
    --mono: "JetBrains Mono", Consolas, "Courier New", monospace;
    color-scheme: light dark;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
      --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --seed-soft: #1F3331; --focus: #86C3BC;
    }
  }
  :root[data-theme="dark"] {
    --ground: #141617; --surface: #1C1F21; --ink: #E7E5DF; --muted: #9CA29E; --line: #2D3134;
    --ember: #E67E4E; --ember-soft: #3A2418; --seed: #86C3BC; --seed-soft: #1F3331; --focus: #86C3BC;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--ground); color: var(--ink); font-family: var(--sans); font-size: 17px; line-height: 1.45; padding-inline: 16px; padding-block: 0 72px; }
  .page { max-width: 680px; margin: 0 auto; }
  h1 { font-family: var(--serif); font-weight: 600; font-size: 2rem; line-height: 1.1; margin: 0; letter-spacing: -.01em; font-variation-settings: "opsz" 144; }
  .top { padding-top: 26px; }
  .lede { color: var(--muted); margin: .4rem 0 0; max-width: 60ch; }
  .lbl { font-family: var(--mono); font-size: .7rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
  a { color: var(--seed); }

  .bar { position: sticky; top: 0; z-index: 5; background: var(--ground); padding: .6rem 0 .55rem; border-bottom: 1px solid var(--line); margin-top: 1rem; display: flex; gap: .45rem; flex-wrap: wrap; align-items: stretch; }
  .tab { flex: 1 1 0; min-width: 6.5rem; font: 600 .95rem var(--sans); color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: .4rem .6rem; cursor: pointer; text-align: left; line-height: 1.2; }
  .tab .sub { display: block; font: 400 .74rem var(--mono); color: var(--muted); margin-top: .15rem; letter-spacing: .02em; }
  .tab[aria-pressed="true"] { background: var(--ink); color: var(--surface); border-color: var(--ink); }
  .tab[aria-pressed="true"] .sub { color: var(--surface); opacity: .75; }
  .tab:focus-visible, .reveal:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
  .reveal { flex: 0 0 auto; font: 600 .85rem var(--sans); color: var(--seed); background: transparent; border: 1px solid var(--line); border-radius: 6px; padding: .4rem .7rem; cursor: pointer; }
  .reveal[aria-pressed="true"] { background: var(--seed); color: var(--surface); border-color: var(--seed); }

  .match[hidden] { display: none; }
  h2.round { font-family: var(--serif); font-weight: 600; font-size: 1.35rem; margin: 1.8rem 0 .7rem; padding-bottom: .3rem; border-bottom: 2px solid var(--ember); }
  h2.round .of { color: var(--muted); font-size: .95rem; font-family: var(--sans); font-weight: 400; }
  .act { font-family: var(--serif); font-size: 1.1rem; color: var(--ember); margin: 1.6rem 0 0; text-align: center; letter-spacing: .02em; }
  .line { display: grid; grid-template-columns: 3.6rem 1fr; gap: .6rem; margin: .6rem 0; }
  .badge { width: 2.3rem; height: 2.3rem; justify-self: center; border-radius: 50%; background: var(--ember-soft); color: var(--ember); font-family: var(--serif); font-weight: 600; font-size: 1.05rem; display: flex; align-items: center; justify-content: center; margin-top: .15rem; }
  .bubble { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; border-top-left-radius: 3px; padding: .6rem .85rem .65rem; min-width: 0; }
  .bubble .who { font-family: var(--mono); font-size: .7rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
  .bubble p { margin: .2rem 0 0; overflow-wrap: anywhere; }
  .said { font-size: 1.06rem; line-height: 1.4; }
  .said.quiet { color: var(--muted); font-style: italic; }
  .did { font-family: var(--mono); font-size: .76rem; color: var(--muted); }
  .hap { font-size: .88rem; color: var(--muted); font-style: italic; }
  .priv { font-size: .88rem; color: var(--seed); border-top: 1px dashed var(--line); padding-top: .4rem; margin-top: .45rem !important; }
  .priv .lbl { color: var(--seed); }
  body:not(.reveal-on) .priv, body:not(.reveal-on) .note { display: none; }
  .gone { color: var(--muted); font-style: italic; margin: .6rem 0 .6rem 4.2rem; }

  .ev { display: grid; grid-template-columns: 3.6rem 1fr; gap: .6rem; margin: .35rem 0; align-items: baseline; }
  .ev .tag { font-family: var(--mono); font-size: .62rem; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); text-align: right; padding-top: .25rem; white-space: nowrap; }
  .ev .tag.monster { color: var(--ember); }
  .ev p { margin: 0; overflow-wrap: anywhere; }
  .ev.monster p { color: var(--ember); }
  .ev.referee p { color: var(--muted); }
  .ev.dice p { font-family: var(--mono); font-size: .74rem; color: var(--muted); }
  body:not(.dice-on) .ev.dice { display: none; }
  .note { font-size: .88rem; color: var(--seed); margin: .1rem 0 .1rem 4.2rem; }
  .narr { margin: .9rem 0 .2rem; padding: .6rem .85rem; background: var(--seed-soft); border-radius: 8px; font-style: italic; }
  .narr p { margin: 0; }
  .state { margin: .9rem 0 0; padding: .55rem .7rem .6rem; background: var(--surface); border: 1px dashed var(--line); border-radius: 8px; }
  .state .lbl { display: block; margin-bottom: .35rem; }
  .chips { display: flex; flex-wrap: wrap; gap: .35rem .55rem; }
  .chip { font-size: .84rem; display: inline-flex; flex-direction: column; gap: .15rem; min-width: 8.5rem; }
  .chip .nm { font-weight: 600; }
  .chip .nm.out { color: var(--muted); text-decoration: line-through; }
  .chip .hp { height: 4px; background: var(--line); border-radius: 2px; overflow: hidden; }
  .chip .hp > i { display: block; height: 100%; background: var(--seed); }
  .chip.mon .hp > i { background: var(--ember); }
  .chip .wh { font-size: .76rem; color: var(--muted); font-family: var(--mono); }
  .legend { margin-top: .9rem; font-size: .9rem; color: var(--muted); }
  .legend b { color: var(--ink); font-weight: 600; }
  .foot { margin-top: 2.4rem; padding-top: 1rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .92rem; }
  @media (max-width: 560px) { h1 { font-size: 1.7rem; } .tab { min-width: 5.6rem; } }
"""

FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600'
         '&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap">')

SCRIPT = """
<script>
(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
  var matches = Array.prototype.slice.call(document.querySelectorAll(".match"));
  function show(i) {
    tabs.forEach(function (t, j) { t.setAttribute("aria-pressed", String(i === j)); });
    matches.forEach(function (m, j) { m.hidden = (i !== j); });
    window.scrollTo({ top: 0 });
  }
  tabs.forEach(function (t, i) { t.addEventListener("click", function () { show(i); }); });
  if (matches.length) show(0);
  function toggle(id, cls, on, off) {
    var b = document.getElementById(id); if (!b) return;
    b.addEventListener("click", function () {
      var now = document.body.classList.toggle(cls);
      b.setAttribute("aria-pressed", String(now));
      b.textContent = now ? off : on;
    });
  }
  toggle("reveal", "reveal-on", "Show what they were thinking", "Hide what they were thinking");
  toggle("dice", "dice-on", "Show the dice", "Hide the dice");
})();
</script>
"""


def shell(lede: str, bar: str, body: str, foot: str) -> str:
    return (f"<title>Ember Vault Replay</title>\n{FONTS}\n<style>{CSS}</style>\n\n"
            f'<div class="page">\n  <header class="top">\n    <h1>Ember Vault Replay</h1>\n    <p class="lede">{lede}</p>\n  </header>\n\n'
            f'  <div class="bar">\n{bar}\n  </div>\n\n{body}\n\n  <div class="foot">{foot}</div>\n</div>\n{SCRIPT}')


# ---------------------------------------------------------------- gate packs

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
    """One pack match as a feed: a round header, then every character's line
    in turn, then what happened to them. A character that leaves the board is
    announced once, in the first round it is missing."""
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
    bar = tabs + '\n    <button type="button" class="reveal" id="reveal" aria-pressed="false">Show what they were thinking</button>'
    feeds = "".join(render_feed(m, i) for i, m in enumerate(matches))
    link = f'<a href="{E(blind_read_url)}">the blind read</a>' if blind_read_url else "the blind read"
    lede = ("Three short matches, real model, names stripped to letters. Scroll. Each round, every character speaks once; "
            "under each line is what they did and what happened to them.")
    foot = (f"Gate run {E(run)} · {len(matches)} matches · {total_rounds} rounds. Picks belong on {link}. "
            "Built from the pack's lettered transcripts only; the answer key was never read.")
    return shell(lede, bar, feeds, foot)


# ------------------------------------------------------------ replay bundles

SKIP = {"dice_roll", "agent_resource_update", "round_started", "match_started"}


def load_bundle(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"[\s\-]+", name) if p and p[0].isalpha()]
    return "".join(p[0] for p in parts[:2]).upper() or name[:2].upper()


def render_bundle(bundle: dict) -> str:
    """Everything the referee recorded, round by round, in the order it happened."""
    names = {p["manifest"]["id"]: p["manifest"]["name"] for p in bundle.get("participants", [])}
    builds = {p["manifest"]["id"]: p["manifest"].get("build", "") for p in bundle.get("participants", [])}
    snaps = bundle.get("snapshots", [])
    end_state = {s["round_no"]: s["state"] for s in snaps if s.get("phase") == "end"}
    last_state = snaps[-1]["state"] if snaps else {}
    monster_names = {mid: m.get("name", mid) for mid, m in (last_state.get("monsters") or {}).items()}
    room_names = {rid: r.get("name", rid) for rid, r in (last_state.get("rooms") or {}).items()}
    events = sorted(bundle.get("events", []), key=lambda e: e["seq"])
    rounds = sorted({e["round_no"] for e in events if e["round_no"] >= 1})
    played = len(rounds)

    out = ['<section class="match" id="match-0" data-match="0">']
    opening = [e for e in events if e["event_type"] == "match_started"]
    if opening:
        out.append(f'<p class="narr"><p>{E(opening[0]["public_text"])}</p></p>'.replace('<p class="narr"><p>', '<div class="narr"><p>').replace('</p></p>', '</p></div>'))
    for n in rounds:
        out.append(f'<h2 class="round">Round {n} <span class="of">of {played} played</span></h2>')
        for e in (x for x in events if x["round_no"] == n):
            t = e["event_type"]
            text = e.get("public_text") or ""
            if t in SKIP:
                if t == "dice_roll":
                    out.append(f'<div class="ev dice"><span class="tag">dice</span><p>{E(text)}</p></div>')
                continue
            if t == "act_started":
                out.append(f'<p class="act">{E(text)}</p>')
                continue
            actor = e.get("actor_id") or ""
            if t == "agent_speech":
                pl = e.get("payload") or {}
                speech = (pl.get("speech") or "").strip()
                mode = pl.get("mode") or "say"
                who = names.get(actor, actor)
                label = who if mode == "say" else f"{who} whispers to {names.get(pl.get('to') or '', pl.get('to') or '')}" if mode == "whisper" else f"{who} says nothing"
                out.append('<article class="line">')
                out.append(f'<span class="badge" aria-hidden="true">{E(_initials(who))}</span>')
                out.append('<div class="bubble">')
                out.append(f'<span class="who">{E(label)}</span>')
                out.append(f'<p class="said{"" if speech else " quiet"}">{("“" + E(speech) + "”") if speech else "(says nothing)"}</p>')
                out.append('</div></article>')
                continue
            if t == "note_written":
                note = ((e.get("payload") or {}).get("note") or {})
                obj = note.get("objective") or ""
                reads = note.get("reads") or []
                reads_txt = "; ".join(f"{names.get(r.get('who'), r.get('who'))}: {r.get('stance')}" + (f" ({r.get('why')})" if r.get("why") else "") for r in reads)
                out.append(f'<p class="note"><span class="lbl">{E(names.get(actor, actor))} thinking</span> {E(obj)}' + (f'<br><span class="lbl">reads</span> {E(reads_txt)}' if reads_txt else "") + '</p>')
                continue
            if t == "round_narration":
                out.append(f'<div class="narr"><p>{E(text)}</p></div>')
                continue
            phase = e.get("phase") or ""
            cls = "monster" if phase == "monster" or t.startswith("monster") else "referee" if phase in ("referee",) else "agent"
            tag = {"monster": "monster", "referee": "referee", "agent": ""}[cls]
            out.append(f'<div class="ev {cls}"><span class="tag {cls}">{tag}</span><p>{E(text)}</p></div>')
        st = end_state.get(n)
        if st:
            chips = []
            for aid in sorted(st.get("agents") or {}, key=lambda a: names.get(a, a)):
                a = st["agents"][aid]
                hp, mx = int(a.get("hp") or 0), max(1, int(a.get("max_hp") or 1))
                outc = a.get("status") != "active" or hp <= 0
                chips.append(f'<span class="chip"><span class="nm{" out" if outc else ""}">{E(names.get(aid, a.get("name", aid)))}</span>'
                             f'<span class="hp"><i style="width:{max(0, min(100, round(100 * hp / mx)))}%"></i></span>'
                             f'<span class="wh">{hp}/{mx} · {E(room_names.get(a.get("room"), a.get("room") or ""))}{" · out" if outc else ""}</span></span>')
            for mid in sorted(st.get("monsters") or {}):
                m = st["monsters"][mid]
                hp, mx = int(m.get("hp") or 0), max(1, int(m.get("max_hp") or 1))
                if hp <= 0:
                    continue
                chips.append(f'<span class="chip mon"><span class="nm">{E(m.get("name", monster_names.get(mid, mid)))}</span>'
                             f'<span class="hp"><i style="width:{max(0, min(100, round(100 * hp / mx)))}%"></i></span>'
                             f'<span class="wh">{hp}/{mx} · {E(room_names.get(m.get("room"), m.get("room") or ""))}</span></span>')
            crown = st.get("crown") or {}
            crown_line = ""
            if crown.get("carrier_id"):
                crown_line = f' · the Crown: {E(names.get(crown["carrier_id"], crown["carrier_id"]))} carries it'
            elif crown.get("status") and crown["status"] != "locked":
                crown_line = f' · the Crown: {E(str(crown["status"]))}'
            out.append(f'<div class="state"><span class="lbl">end of round {n}{crown_line}</span><div class="chips">{"".join(chips)}</div></div>')
    out.append('</section>')
    return "".join(out)


def build_from_bundle(bundle: dict, note: str = "") -> str:
    """The page for one full match record. ``note`` is one sentence the
    caller adds to the lede: what the reader has to know about the rules the
    match was played under, which the record itself does not say."""
    m = bundle.get("match", {})
    names = {p["manifest"]["id"]: p["manifest"]["name"] for p in bundle.get("participants", [])}
    builds = {p["manifest"]["id"]: p["manifest"].get("build", "") for p in bundle.get("participants", [])}
    snaps = bundle.get("snapshots", [])
    ended = (snaps[-1]["state"].get("ended_reason") if snaps else None) or m.get("status") or ""
    rounds = sorted({e["round_no"] for e in bundle.get("events", []) if e["round_no"] >= 1})
    winner = names.get(m.get("winner_agent_id"), m.get("winner_agent_id") or "nobody")
    legend = " · ".join(f"<b>{E(n)}</b> ({E(builds.get(i, ''))})" for i, n in sorted(names.items(), key=lambda kv: kv[1]))
    lede = (f"Match {E(str(m.get('id', '')))}, seed {E(str(m.get('seed', '')))}: {len(rounds)} rounds played of {E(str(m.get('max_rounds', '')))}, "
            f"winner {E(winner)}, ended by {E(str(ended).replace('_', ' '))}. Everything the referee recorded, in the order it happened: "
            f"what was said, every move and swing, what the monsters did, the narration, and where everyone stood at the end of each round."
            + (f" {E(note)}" if note else ""))
    bar = ('    <button type="button" class="reveal" id="reveal" aria-pressed="false">Show what they were thinking</button>\n'
           '    <button type="button" class="reveal" id="dice" aria-pressed="false">Show the dice</button>')
    body = f'<p class="legend">{legend}</p>\n' + render_bundle(bundle)
    foot = f"Match record {E(str(m.get('id', '')))} · {len(bundle.get('events', []))} recorded events · ruleset {E(str(m.get('ruleset_version', '')))}."
    return shell(lede, bar, body, foot)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", type=Path, help="a gate pack folder, or a replay bundle .json")
    ap.add_argument("out", type=Path)
    ap.add_argument("--blind-read-url", default="", help="pack mode: link to the blind-read page for the same pack")
    ap.add_argument("--note", default="", help="bundle mode: one sentence added to the lede, e.g. which ending rule the match was played under")
    a = ap.parse_args(argv)
    if a.source.is_file():
        page = build_from_bundle(load_bundle(a.source), a.note)
        what = f"bundle {a.source.name}"
    else:
        page = build(a.source, a.blind_read_url)
        what = f"pack {a.source.name}"
    a.out.write_text(page, encoding="utf-8")
    print(f"wrote {a.out} ({len(page.encode())} bytes) from {what}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
