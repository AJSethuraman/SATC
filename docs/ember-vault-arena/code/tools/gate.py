"""The gate (PRD §5.43-45): does a player-written brain show through?

Runs N seeds of R rounds with every brain on ONE build and the chosen
provider, then writes an anonymised blind-matching pack for two readers who
wrote none of the brains:

    gate/<run>/README.md            what was run, with what, and what it cost
    gate/<run>/transcripts/A.md ... one per character, lettered, names removed
    gate/<run>/brains/1.md ...      the brains, shuffled and numbered, names removed
    gate/<run>/ANSWER_SHEET.md      the form each reader fills in
    gate/<run>.key.json             the mapping, BESIDE the pack and outside source
                                    control -- do not open until both sheets are in

The key sits outside the readers' folder because the first model run
(12 Sep 2026) committed it inside the pack, where anyone browsing the pull
request could read it. Keep the key file; without it the run cannot be scored.

Score with tools/score_gate.py. A mock run proves this pipeline produces
readable artifacts; it cannot answer the question, because the mock's speech
never came from a brain (LOG.md, 11 Sep 2026).

    python3 tools/gate.py --provider agent_sdk --brains brains/house --seeds 3 --rounds 6 --build scout
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arena.brains import load_brains  # noqa: E402
from arena.engine import ArenaEngine  # noqa: E402
from arena.models import BRAIN_SECTIONS, BUILDS  # noqa: E402
from arena.providers import PROVIDER_NAMES, provider_from_name  # noqa: E402
from arena.storage import ArenaStore  # noqa: E402

LETTERS = "ABCDEFGH"
COMMON = {"the", "and", "with", "from", "that", "this", "your", "have", "will"}


def anonymiser(manifests, labels):
    """Replace every character's id, full name and distinctive name tokens with
    the label given for it. Tokens shorter than four letters or in a small
    common-word list are left alone so 'the' is not rewritten.

    TWO LABEL SETS, and the difference is the key. Transcripts use the letters
    (Character A ...). Brains use a neutral phrase, because a brain that says
    "Character A talks like a ledger" IS the answer sheet -- the first mock run
    wrote exactly that."""
    subs: list[tuple[re.Pattern[str], str]] = []
    for m, label in zip(manifests, labels):
        names = [m.name, m.id] + [t for t in re.split(r"[\s\-_]+", m.name) if len(t) >= 4 and t.lower() not in COMMON]
        for n in sorted(set(names), key=len, reverse=True):
            subs.append((re.compile(rf"\b{re.escape(n)}\b", re.I), label))
    def strip(text: str) -> str:
        for pat, label in subs:
            text = pat.sub(label, text)
        return text
    return strip


def run(args) -> Path:
    manifests = load_brains(args.brains)
    manifests = [replace(m, build=args.build) for m in manifests]
    provider = provider_from_name(args.provider)
    run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{args.provider}"
    out = Path(getattr(args, "out", None) or (ROOT / "gate")) / run_id
    (out / "transcripts").mkdir(parents=True)
    (out / "brains").mkdir()

    # letters by a shuffle seeded from the run id, so the key file is the only
    # place the mapping exists and nothing about seat order leaks it
    order = list(range(len(manifests)))
    random.Random(hashlib.sha256(run_id.encode()).hexdigest()).shuffle(order)
    letters = {manifests[i].id: LETTERS[k] for k, i in enumerate(order)}
    numbers = {manifests[i].id: k + 1 for k, i in enumerate(sorted(order, key=lambda i: hashlib.sha256(f"{run_id}:{i}".encode()).hexdigest()))}
    strip = anonymiser(manifests, [f"Character {letters[m.id]}" for m in manifests])
    strip_brain = anonymiser(manifests, ["the character"] * len(manifests))

    transcripts = {m.id: [] for m in manifests}
    cost_total, calls, answered = 0.0, 0, 0
    seeds = [args.first_seed + i for i in range(args.seeds)]
    db_dir = Path(tempfile.mkdtemp(prefix="gate-"))
    for seed in seeds:
        store = ArenaStore(db_dir / f"{seed}.db")
        engine = ArenaEngine(store, provider, max_rounds=args.rounds, parallel_agents=True)
        match_id = engine.run(manifests, seed)
        bundle = store.replay_bundle(match_id)
        by_round: dict[int, list[dict]] = {}
        for ev in bundle["events"]:
            by_round.setdefault(ev["round_no"], []).append(ev)
        decisions: dict[tuple[int, str], dict] = {(d["round_no"], d["agent_id"]): d for d in bundle["decisions"]}
        for d in bundle["decisions"]:
            calls += 1
            answered += d["validity"] == "valid"
            cost_total += float(d.get("cost_usd") or 0.0)
        for m in manifests:
            lines = [f"\n## Seed {seed}\n"]
            for rnd in range(1, args.rounds + 1):
                d = decisions.get((rnd, m.id))
                if d is None:
                    continue
                act = d["action"]
                lines.append(f"\n### Round {rnd}\n")
                verb = act["action"] + "".join(f" {k}={v}" for k in ("target", "destination", "item") if (v := act.get(k)))
                lines.append(f"- **Did:** {strip(verb)}" + ("" if d["validity"] == "valid" else f"  *({d['validity']})*"))
                sp = act.get("speech") or {}
                if sp.get("mode") == "say":
                    lines.append(f"- **Said:** “{strip(sp.get('text') or '')}”")
                elif sp.get("mode") == "whisper":
                    lines.append(f"- **Whispered to {strip(sp.get('to') or '')}:** “{strip(sp.get('text') or '')}”")
                else:
                    lines.append("- **Said:** *(nothing)*")
                note = act.get("note") or {}
                lines.append(f"- **Private objective:** {strip(note.get('objective') or '')}")
                reads = note.get("reads") or []
                if reads:
                    lines.append("- **Reads:** " + "; ".join(f"{strip(r['who'])}: {r['stance']} ({strip(r.get('why') or '')})" for r in reads))
                happened = [strip(ev["public_text"]) for ev in by_round.get(rnd, [])
                            if ev["event_type"] not in ("agent_speech", "note_written", "dice_roll", "agent_resource_update", "round_started", "initiative_order", "round_narration")
                            and (ev.get("actor_id") == m.id or ev.get("target_id") == m.id)]
                if happened:
                    lines.append("- **Happened to them:** " + " ".join(happened))
            transcripts[m.id].extend(lines)
        store.close()

    for m in manifests:
        letter = letters[m.id]
        (out / "transcripts" / f"{letter}.md").write_text(
            f"# Character {letter}\n\nBuild: {args.build} (everyone). Rounds per seed: {args.rounds}.\n"
            + "\n".join(transcripts[m.id]) + "\n", encoding="utf-8")
        body = "\n\n".join(f"## {s.title()}\n{strip_brain(getattr(m, s))}" for s in BRAIN_SECTIONS)
        (out / "brains" / f"{numbers[m.id]}.md").write_text(f"# Brain {numbers[m.id]}\n\n{body}\n", encoding="utf-8")

    key_path(out).write_text(json.dumps(
        {"letter_to_brain_number": {letters[m.id]: numbers[m.id] for m in manifests},
         "letter_to_id": {letters[m.id]: m.id for m in manifests}}, indent=2, sort_keys=True), encoding="utf-8")
    (out / "ANSWER_SHEET.md").write_text(
        "# Answer sheet\n\nReader name: ______\n\nFor each character, write the number of the brain you think wrote it. "
        "Every number is used exactly once.\n\n"
        + "\n".join(f"- Character {L}: brain ____" for L in LETTERS[:len(manifests)])
        + "\n\nThen save your answers as JSON next to this file, e.g. `reader_a.json`:\n\n```json\n"
        + json.dumps({L: 0 for L in LETTERS[:len(manifests)]}) + "\n```\n", encoding="utf-8")
    (out / "README.md").write_text(
        f"# Gate run {run_id}\n\n"
        f"- provider: **{args.provider}** (model: {getattr(provider, 'model', 'n/a')})\n"
        f"- brains: {args.brains} ({len(manifests)} loaded), all on build **{args.build}**\n"
        f"- seeds: {seeds}, rounds per seed: {args.rounds}\n"
        f"- calls: {calls}, answered by the model: {answered} of {calls}"
        f"{' (a mock answers everything and proves nothing about brains)' if args.provider == 'mock' else ''}\n"
        f"- cost recorded: ${cost_total:.2f} ({'ledger has no rates for this provider' if cost_total == 0 and args.provider != 'mock' else 'from the call ledger'})\n\n"
        "Hand `transcripts/` and `brains/` to two readers who wrote none of the brains. "
        "Each fills in `ANSWER_SHEET.md` and saves a JSON answer file. Then:\n\n"
        f"```\npython3 tools/score_gate.py gate/{run_id} reader_a.json reader_b.json\n```\n\n"
        f"The key is `gate/{run_id}.key.json`, beside this folder and outside source control: "
        "keep it, hand it to nobody, and do not open it until both sheets are in.\n", encoding="utf-8")
    return out


def key_path(pack: Path) -> Path:
    """The key lives beside the pack, never in it."""
    return pack.parent / f"{pack.name}.key.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=PROVIDER_NAMES, default="mock")
    ap.add_argument("--brains", default=str(ROOT / "brains" / "house"))
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--first-seed", type=int, default=101)
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--build", choices=sorted(BUILDS), default="scout")
    ap.add_argument("--out", default=None, help="folder to write packs under (default: gate/)")
    args = ap.parse_args()
    out = run(args)
    print(f"gate pack written to {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    print(f"key written beside it: {key_path(out).name} (not in source control; keep it)")
    print((out / "README.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
