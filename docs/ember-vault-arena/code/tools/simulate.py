#!/usr/bin/env python3
"""Headless balance simulator for Ember Vault Arena v0.2.

Runs N seeded matches with the deterministic MockDecisionProvider (no model
calls, no network) and reports the balance metrics the ruleset is tuned against.

It is a pure OBSERVER: it imports arena/ read-only, writes each match to its own
throwaway SQLite file, and never touches arena/ or tests/.

Usage
-----
    python3 tools/simulate.py --seeds 160
    python3 tools/simulate.py --seeds 160 --agents 8 --workers 4 --json out.json
    python3 tools/simulate.py --seeds 60  --rogue-rate 0.10   # exercise the -2 path
    python3 tools/simulate.py --seeds 60  --determinism 3     # same seed twice

Roster construction
-------------------
Agent identity is what the engine keys on (RNG labels, sorted tie-breaks), so
seat identity is held FIXED (``seat1``..``seatN``, alphabetical == seat order)
while build and secret objective are re-dealt by a seeded shuffle every match.
That decorrelates build from seat and from identity, which is the only way
"win rate by build" and "win rate by seat" mean anything: with 8 agents each
build is present exactly twice in every match, so a fair game gives each build
a 25% win rate and each seat 12.5%.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import random
import shutil
import statistics
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arena.engine import ArenaEngine  # noqa: E402
from arena.models import AgentManifest  # noqa: E402
from arena.providers import MockDecisionProvider  # noqa: E402
from arena.storage import ArenaStore  # noqa: E402


BUILD_ORDER = ["vanguard", "scout", "mystic", "scoundrel"]
OBJECTIVE_ORDER = ["monster_hunter", "lorekeeper", "oathbreaker", "treasure_hoarder"]

NEUTRAL_SYSTEM_PROMPT = (
    "Compete in the Ember Vault. Follow the referee, take the highest-value "
    "legal action available, and stay alive long enough to spend it."
)
NEUTRAL_PERSONALITY = "Measured, opportunistic, and hard to insult."
NEUTRAL_STRATEGY = (
    "Light a seal, clear what blocks the vault, claim the Crown when it drops, "
    "and hold it long enough to leave with it."
)


# ---------------------------------------------------------------------------
# roster
# ---------------------------------------------------------------------------


def build_roster(seed: int, n_agents: int) -> list[AgentManifest]:
    """Seat-stable ids; builds and objectives re-dealt per seed."""
    rng = random.Random(f"roster:{seed}:{n_agents}")

    def deal(pool: list[str]) -> list[str]:
        """Deal n_agents values, shuffling a fresh copy of the pool each cycle.

        Shuffling per cycle matters when n_agents is not a multiple of 4: it is
        the only way the *identity* of the doubled-up builds varies by seed
        instead of being pinned to whatever order the constant happens to use.
        """
        dealt: list[str] = []
        while len(dealt) < n_agents:
            cycle = list(pool)
            rng.shuffle(cycle)
            dealt.extend(cycle)
        return dealt[:n_agents]

    builds = deal(BUILD_ORDER)
    objectives = deal(OBJECTIVE_ORDER)

    return [
        AgentManifest.from_dict(
            {
                "id": f"seat{index + 1}",
                "name": f"Seat {index + 1}",
                "system_prompt": NEUTRAL_SYSTEM_PROMPT,
                "personality": NEUTRAL_PERSONALITY,
                "strategy": NEUTRAL_STRATEGY,
                "build": builds[index],
                "secret_objective": objectives[index],
            }
        )
        for index in range(n_agents)
    ]


# ---------------------------------------------------------------------------
# one match
# ---------------------------------------------------------------------------


class RogueDecisionProvider:
    """MockDecisionProvider that sometimes emits a schema-valid ILLEGAL action.

    The reference policy picks entries out of ``legal_actions``, so it can never
    trip the -2 illegal-action penalty and a plain run measures an invalid-action
    rate of exactly 0 by construction.  This wrapper injects off-list actions at
    a fixed rate so the penalty path is actually exercised and measurable.
    """

    def __init__(self, rate: float, seed: int):
        self.inner = MockDecisionProvider()
        self.rate = rate
        self.seed = seed
        self.model = "rogue-" + self.inner.model

    def decide(self, manifest, prompt, observation):  # type: ignore[no-untyped-def]
        rng = random.Random(
            f"rogue:{self.seed}:{manifest.id}:"
            f"{observation['public_state']['round']}"
        )
        if rng.random() >= self.rate:
            return self.inner.decide(manifest, prompt, observation)
        # Schema-valid, deliberately not in legal_actions: attack a body that
        # is not in the room (the engine must reject it, score -2, and guard).
        rogue = {
            "action": "attack",
            "target": "not_a_real_body",
            "destination": None,
            "item": None,
            "speech": "",
            "reasoning_summary": "injected illegal action (simulator probe)",
            "memory_write": "",
        }
        raw = json.dumps(rogue, sort_keys=True)
        from arena.models import ProviderResult  # local import: worker-side only

        return ProviderResult(
            raw_output=raw,
            input_tokens=1,
            output_tokens=1,
            provider="mock",
            model=self.model,
        )

    def narrate(self, round_no, prompt, event_lines):  # type: ignore[no-untyped-def]
        return self.inner.narrate(round_no, prompt, event_lines)


def _final_state(bundle: dict[str, Any]) -> dict[str, Any]:
    for snapshot in reversed(bundle["snapshots"]):
        if snapshot["phase"] == "final":
            return snapshot["state"]
    return bundle["snapshots"][-1]["state"]


def run_match(
    seed: int,
    n_agents: int,
    keep_hashes: bool = False,
    rogue_rate: float = 0.0,
) -> dict[str, Any]:
    manifests = build_roster(seed, n_agents)
    seat_of = {manifest.id: index + 1 for index, manifest in enumerate(manifests)}
    build_of = {manifest.id: manifest.build for manifest in manifests}

    workdir = tempfile.mkdtemp(prefix=f"emberSim{seed}_")
    store = None
    try:
        store = ArenaStore(os.path.join(workdir, "arena.db"))
        provider = (
            RogueDecisionProvider(rogue_rate, seed)
            if rogue_rate > 0
            else MockDecisionProvider()
        )
        match_id = ArenaEngine(
            store, provider, parallel_agents=False
        ).run(manifests, seed)
        bundle = store.replay_bundle(match_id)
        audit = store.verify_audit(match_id)
        record = _summarize(
            seed, n_agents, bundle, audit, seat_of, build_of, keep_hashes
        )
        return record
    except Exception as exc:  # noqa: BLE001 - a crash IS a balance datum
        return {
            "seed": seed,
            "n_agents": n_agents,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=6),
        }
    finally:
        if store is not None:
            store.close()
        shutil.rmtree(workdir, ignore_errors=True)


def _summarize(
    seed: int,
    n_agents: int,
    bundle: dict[str, Any],
    audit: dict[str, Any],
    seat_of: dict[str, int],
    build_of: dict[str, str],
    keep_hashes: bool,
) -> dict[str, Any]:
    events = bundle["events"]
    state = _final_state(bundle)

    counts = Counter(event["event_type"] for event in events)

    rounds_played = max(
        [event["round_no"] for event in events if event["event_type"] == "round_started"]
        or [0]
    )

    attacks_agent = attacks_monster = 0
    hits_agent = misses_agent = wild_swings = 0
    wild_faces: Counter[str] = Counter()
    fell_through = 0
    for event in events:
        if event["event_type"] not in {"attack_hit", "attack_miss"}:
            continue
        payload = event["payload"]
        attacker_kind = payload.get("attacker_kind")
        if attacker_kind == "agent":
            attacks_agent += 1
            if event["event_type"] == "attack_hit":
                hits_agent += 1
            else:
                misses_agent += 1
                swing = payload.get("wild_swing")
                if swing:
                    wild_swings += 1
                    wild_faces[swing.get("face_id", "?")] += 1
                    if swing.get("fell_through"):
                        fell_through += 1
        else:
            attacks_monster += 1

    eliminations = [
        {
            "round": event["round_no"],
            "victim": event["target_id"],
            "killer": event["actor_id"],
            "collateral": bool(event["payload"].get("collateral")),
            "credited": event["payload"].get("credited_to"),
        }
        for event in events
        if event["event_type"] == "agent_eliminated"
    ]

    crown = state.get("crown", {})
    crown_take_events = [e for e in events if e["event_type"] == "crown_taken"]
    crown_carriers = [event["actor_id"] for event in crown_take_events]

    decisions = len(bundle["decisions"])
    invalid = counts.get("invalid_action_fallback", 0)
    stale = counts.get("stale_action", 0)
    stale_reasons = Counter(
        event["payload"].get("reason", "?")
        for event in events
        if event["event_type"] == "stale_action"
    )
    stale_actions_by_verb = Counter(
        event["payload"].get("submitted_action", {}).get("action", "?")
        for event in events
        if event["event_type"] == "stale_action"
    )
    invalid_reasons = Counter(
        event["payload"].get("reason", "?")
        for event in events
        if event["event_type"] == "invalid_action_fallback"
    )
    action_verbs = Counter(
        decision["action"].get("action", "?") for decision in bundle["decisions"]
    )
    validity = Counter(
        decision.get("validity", "?") for decision in bundle["decisions"]
    )
    # First round each agent got autopiloted for running out of tokens.
    autopilot_round: dict[str, int] = {}
    for decision in bundle["decisions"]:
        if decision.get("validity") == "autopilot":
            agent_id = decision["agent_id"]
            autopilot_round.setdefault(agent_id, decision["round_no"])
    tokens_left = {
        agent_id: agent.get("tokens_remaining", 0)
        for agent_id, agent in state["agents"].items()
    }

    winner = state.get("winner_agent_id")
    ended_reason = state.get("ended_reason")

    survivors = [
        agent_id
        for agent_id, agent in state["agents"].items()
        if agent["status"] == "active"
    ]

    record: dict[str, Any] = {
        "seed": seed,
        "n_agents": n_agents,
        "ok": True,
        "match_id": bundle["match"]["id"],
        "status": bundle["match"]["status"],
        "audit_ok": bool(audit.get("valid")),
        "ruleset_version": state.get("ruleset_version"),
        "rounds": rounds_played,
        "ended_reason": ended_reason,
        "reached_act3": rounds_played >= 8,
        "final_act": state.get("act"),
        "winner": winner,
        "winner_build": build_of.get(winner or ""),
        "winner_seat": seat_of.get(winner or ""),
        "winner_escaped": ended_reason == "extraction",
        "survivors": len(survivors),
        # crown
        "crown_status": crown.get("status"),
        "crown_unlocked": bool(counts.get("crown_unlocked", 0)),
        "crown_takes": len(crown_take_events),
        "crown_transfers": crown.get("transfers", 0),
        "crown_distinct_carriers": len(set(crown_carriers)),
        "crown_drops": counts.get("crown_dropped", 0),
        "crown_attune_ticks": counts.get("crown_attuned", 0),
        # combat
        "attacks_agent": attacks_agent,
        "attacks_monster": attacks_monster,
        "attacks_total": attacks_agent + attacks_monster,
        "hits_agent": hits_agent,
        "misses_agent": misses_agent,
        "wild_swings": wild_swings,
        "wild_faces": dict(wild_faces),
        "wild_fell_through": fell_through,
        # discipline
        "decisions": decisions,
        "invalid_actions": invalid,
        "stale_actions": stale,
        "stale_reasons": dict(stale_reasons),
        "stale_by_verb": dict(stale_actions_by_verb),
        "invalid_reasons": dict(invalid_reasons),
        "action_verbs": dict(action_verbs),
        "validity": dict(validity),
        "autopilot_first_round": autopilot_round,
        "tokens_left": tokens_left,
        # outcomes
        "eliminations": eliminations,
        "seals_activated": counts.get("seal_activated", 0),
        "seals_voided": counts.get("seal_voided", 0),
        "monsters_defeated": counts.get("monster_defeated", 0),
        "monsters_entombed": counts.get("monster_entombed", 0),
        "vault_opened": bool(counts.get("vault_gate_opened", 0)),
        "caches_found": counts.get("cache_found", 0),
        "scores": {
            agent_id: state["agents"][agent_id]["score"]
            for agent_id in sorted(state["agents"])
        },
        "builds": {agent_id: build_of[agent_id] for agent_id in sorted(build_of)},
        "seats": {agent_id: seat_of[agent_id] for agent_id in sorted(seat_of)},
        "per_agent": {
            agent_id: {
                "build": build_of[agent_id],
                "seat": seat_of[agent_id],
                "score": agent["score"],
                "placement": None,
                "status": agent["status"],
                "eliminated_round": agent.get("eliminated_round"),
                "invalid_actions": agent.get("invalid_actions", 0),
                "monster_damage": agent.get("monster_damage", 0),
                "agent_damage": agent.get("agent_damage", 0),
                "collateral_dealt": agent.get("collateral_dealt", 0),
                "crown_takes": agent.get("crown_takes", 0),
            }
            for agent_id, agent in sorted(state["agents"].items())
        },
    }
    for participant in bundle["participants"]:
        agent_id = participant["manifest"]["id"]
        if agent_id in record["per_agent"]:
            record["per_agent"][agent_id]["placement"] = participant["placement"]
    if keep_hashes:
        record["snapshot_hashes"] = [
            snapshot["state_hash"] for snapshot in bundle["snapshots"]
        ]
    return record


def _worker(args: tuple[int, int, float]) -> dict[str, Any]:
    seed, n_agents, rogue_rate = args
    return run_match(seed, n_agents, rogue_rate=rogue_rate)


# ---------------------------------------------------------------------------
# aggregation + report
# ---------------------------------------------------------------------------


def _pct(numerator: float, denominator: float) -> float:
    return 100.0 * numerator / denominator if denominator else 0.0


def _fmt_hist(counter: Counter, keys: list[Any], total: int) -> str:
    lines = []
    for key in keys:
        value = counter.get(key, 0)
        bar = "#" * int(round(40 * value / max(1, max(counter.values(), default=1))))
        lines.append(f"    {str(key):>14}  {value:5d}  {_pct(value, total):5.1f}%  {bar}")
    return "\n".join(lines)


def aggregate(records: list[dict[str, Any]], n_agents: int) -> dict[str, Any]:
    total = len(records)
    good = [record for record in records if record.get("ok")]
    completed = [
        record
        for record in good
        if record["status"] == "completed" and record["audit_ok"]
    ]

    rounds = [record["rounds"] for record in completed]
    act3 = [record for record in completed if record["reached_act3"]]
    reasons = Counter(record["ended_reason"] for record in completed)

    transfers = [record["crown_takes"] for record in completed]
    attacks_agent = sum(record["attacks_agent"] for record in completed)
    attacks_all = sum(record["attacks_total"] for record in completed)
    wild = sum(record["wild_swings"] for record in completed)

    wins_build: Counter[str] = Counter()
    wins_seat: Counter[int] = Counter()
    plays_build: Counter[str] = Counter()
    plays_seat: Counter[int] = Counter()
    slots_build: Counter[str] = Counter()
    score_by_build: dict[str, list[int]] = {build: [] for build in BUILD_ORDER}
    place_by_build: dict[str, list[int]] = {build: [] for build in BUILD_ORDER}
    survive_by_build: Counter[str] = Counter()
    agent_rows = 0

    elim_rounds: Counter[int] = Counter()
    elim_collateral = 0
    elim_total = 0

    for record in completed:
        if record["winner_build"]:
            wins_build[record["winner_build"]] += 1
        if record["winner_seat"]:
            wins_seat[record["winner_seat"]] += 1
        for build in set(record["builds"].values()):
            plays_build[build] += 1
        for seat in set(record["seats"].values()):
            plays_seat[seat] += 1
        for row in record["per_agent"].values():
            agent_rows += 1
            slots_build[row["build"]] += 1
            score_by_build.setdefault(row["build"], []).append(row["score"])
            if row["placement"]:
                place_by_build.setdefault(row["build"], []).append(row["placement"])
            if row["status"] == "active":
                survive_by_build[row["build"]] += 1
        for elimination in record["eliminations"]:
            elim_total += 1
            elim_rounds[elimination["round"]] += 1
            if elimination["collateral"]:
                elim_collateral += 1

    decisions = sum(record["decisions"] for record in completed)
    invalid = sum(record["invalid_actions"] for record in completed)
    stale = sum(record["stale_actions"] for record in completed)

    wild_faces: Counter[str] = Counter()
    stale_reasons: Counter[str] = Counter()
    stale_by_verb: Counter[str] = Counter()
    invalid_reasons: Counter[str] = Counter()
    action_verbs: Counter[str] = Counter()
    validity: Counter[str] = Counter()
    autopilot_rounds: Counter[int] = Counter()
    autopiloted_agents = 0
    tokens_left_all: list[int] = []
    for record in completed:
        wild_faces.update(record["wild_faces"])
        stale_reasons.update(record.get("stale_reasons", {}))
        stale_by_verb.update(record.get("stale_by_verb", {}))
        invalid_reasons.update(record.get("invalid_reasons", {}))
        action_verbs.update(record.get("action_verbs", {}))
        validity.update(record.get("validity", {}))
        for round_no in record.get("autopilot_first_round", {}).values():
            autopilot_rounds[int(round_no)] += 1
            autopiloted_agents += 1
        tokens_left_all.extend(record.get("tokens_left", {}).values())

    return {
        "matches_run": total,
        "matches_ok": len(good),
        "matches_completed": len(completed),
        "completion_rate": _pct(len(completed), total),
        "errors": [
            {"seed": record["seed"], "error": record.get("error")}
            for record in records
            if not record.get("ok")
        ],
        "act3_rate": _pct(len(act3), len(completed)),
        "ended_reasons": dict(reasons),
        "escape_rate": _pct(reasons.get("extraction", 0), len(completed)),
        "round_limit_rate": _pct(reasons.get("rounds_exhausted", 0), len(completed)),
        "wipe_rate": _pct(reasons.get("all_eliminated", 0), len(completed)),
        "rounds_median": statistics.median(rounds) if rounds else 0,
        "rounds_mean": statistics.fmean(rounds) if rounds else 0,
        "rounds_hist": Counter(rounds),
        "crown_unlocked_rate": _pct(
            sum(1 for record in completed if record["crown_unlocked"]), len(completed)
        ),
        "crown_transfers_median": statistics.median(transfers) if transfers else 0,
        "crown_transfers_mean": statistics.fmean(transfers) if transfers else 0,
        "crown_transfers_hist": Counter(transfers),
        "crown_ge1_rate": _pct(
            sum(1 for value in transfers if value >= 1), len(completed)
        ),
        "crown_ge2_rate": _pct(
            sum(1 for value in transfers if value >= 2), len(completed)
        ),
        "attacks_agent": attacks_agent,
        "attacks_all": attacks_all,
        "wild_swings": wild,
        "mishap_rate_agent": _pct(wild, attacks_agent),
        "mishap_rate_all": _pct(wild, attacks_all),
        "wild_faces": dict(wild_faces),
        "wins_build": dict(wins_build),
        "plays_build": dict(plays_build),
        "wins_seat": dict(wins_seat),
        "plays_seat": dict(plays_seat),
        "winrate_build": {
            build: _pct(wins_build.get(build, 0), plays_build.get(build, 0))
            for build in BUILD_ORDER
        },
        "slots_build": dict(slots_build),
        # Per-slot win probability rescaled to "what this build's win rate would
        # be under equal representation (n/4 slots)".  Identical to the raw win
        # rate whenever n_agents is a multiple of 4; the only honest comparison
        # against the 25% target when it is not.
        "winrate_build_norm": {
            build: (
                _pct(wins_build.get(build, 0), slots_build.get(build, 0))
                * n_agents
                / 4.0
            )
            for build in BUILD_ORDER
        },
        "winrate_seat": {
            seat: _pct(wins_seat.get(seat, 0), plays_seat.get(seat, 0))
            for seat in range(1, n_agents + 1)
        },
        "mean_score_build": {
            build: (statistics.fmean(values) if values else 0.0)
            for build, values in score_by_build.items()
        },
        "mean_place_build": {
            build: (statistics.fmean(values) if values else 0.0)
            for build, values in place_by_build.items()
        },
        "survival_build": {
            build: _pct(
                survive_by_build.get(build, 0),
                sum(
                    1
                    for record in completed
                    for row in record["per_agent"].values()
                    if row["build"] == build
                ),
            )
            for build in BUILD_ORDER
        },
        "elim_rounds": elim_rounds,
        "elim_total": elim_total,
        "elim_collateral": elim_collateral,
        "elim_per_match": elim_total / len(completed) if completed else 0,
        "decisions": decisions,
        "invalid_actions": invalid,
        "invalid_rate": _pct(invalid, decisions),
        "stale_actions": stale,
        "stale_rate": _pct(stale, decisions),
        "stale_reasons": dict(stale_reasons),
        "stale_by_verb": dict(stale_by_verb),
        "invalid_reasons": dict(invalid_reasons),
        "action_verbs": dict(action_verbs),
        "agent_rows": agent_rows,
        "validity": dict(validity),
        "autopilot_rounds": autopilot_rounds,
        "autopiloted_agents": autopiloted_agents,
        "agent_slots": agent_rows,
        "tokens_left_mean": (
            statistics.fmean(tokens_left_all) if tokens_left_all else 0.0
        ),
        "tokens_exhausted_pct": _pct(
            sum(1 for value in tokens_left_all if value == 0), len(tokens_left_all)
        ),
        "seals_per_match": (
            statistics.fmean([record["seals_activated"] for record in completed])
            if completed
            else 0
        ),
        "vault_open_rate": _pct(
            sum(1 for record in completed if record["vault_opened"]), len(completed)
        ),
        "monsters_per_match": (
            statistics.fmean([record["monsters_defeated"] for record in completed])
            if completed
            else 0
        ),
    }


TARGETS = [
    ("completion rate >= 95%", "completion_rate", lambda value: value >= 95.0),
    ("reach Act III (round >= 8) >= 70%", "act3_rate", lambda value: value >= 70.0),
    (
        "median match has >= 1 Crown transfer",
        "crown_transfers_median",
        lambda value: value >= 1,
    ),
    (
        "mishap rate 35-45% of agent attacks",
        "mishap_rate_agent",
        lambda value: 35.0 <= value <= 45.0,
    ),
]


def report(summary: dict[str, Any], n_agents: int, elapsed: float) -> list[str]:
    out: list[str] = []
    add = out.append

    add("=" * 74)
    add(f"EMBER VAULT ARENA v0.2 — BALANCE SIMULATION ({n_agents} agents/match)")
    add("=" * 74)
    add(
        f"matches run: {summary['matches_run']}   "
        f"completed+audited: {summary['matches_completed']}   "
        f"wall clock: {elapsed:.1f}s"
    )
    add("")
    add("-- COMPLETION ------------------------------------------------------------")
    add(f"  completion rate            {summary['completion_rate']:.1f}%")
    if summary["errors"]:
        add(f"  errors ({len(summary['errors'])}):")
        for error in summary["errors"][:10]:
            add(f"    seed {error['seed']}: {error['error']}")
    add("")
    add("-- MATCH SHAPE -----------------------------------------------------------")
    add(f"  reached Act III (r>=8)     {summary['act3_rate']:.1f}%")
    add(f"  median rounds              {summary['rounds_median']}")
    add(f"  mean rounds                {summary['rounds_mean']:.2f}")
    add("  rounds histogram:")
    add(
        _fmt_hist(
            summary["rounds_hist"],
            sorted(summary["rounds_hist"]),
            summary["matches_completed"],
        )
    )
    add("  ended reason:")
    for reason, count in sorted(
        summary["ended_reasons"].items(), key=lambda item: -item[1]
    ):
        add(
            f"    {str(reason):>18}  {count:5d}  "
            f"{_pct(count, summary['matches_completed']):5.1f}%"
        )
    add(
        f"  escapes {summary['escape_rate']:.1f}%  vs  "
        f"round-limit {summary['round_limit_rate']:.1f}%  vs  "
        f"wipe {summary['wipe_rate']:.1f}%"
    )
    add("")
    add("-- CROWN -----------------------------------------------------------------")
    add(f"  matches where warden died  {summary['crown_unlocked_rate']:.1f}%")
    add(f"  vault gate opened          {summary['vault_open_rate']:.1f}%")
    add(f"  crown transfers, median    {summary['crown_transfers_median']}")
    add(f"  crown transfers, mean      {summary['crown_transfers_mean']:.2f}")
    add(f"  matches with >=1 transfer  {summary['crown_ge1_rate']:.1f}%")
    add(f"  matches with >=2 transfers {summary['crown_ge2_rate']:.1f}%")
    add("  transfers histogram:")
    add(
        _fmt_hist(
            summary["crown_transfers_hist"],
            sorted(summary["crown_transfers_hist"]),
            summary["matches_completed"],
        )
    )
    add("")
    add("-- COMBAT / MISHAPS ------------------------------------------------------")
    add(f"  agent attack resolutions   {summary['attacks_agent']}")
    add(f"  all attack resolutions     {summary['attacks_all']}")
    add(f"  wild swings                {summary['wild_swings']}")
    add(f"  mishap rate (agent atks)   {summary['mishap_rate_agent']:.1f}%")
    add(f"  mishap rate (all atks)     {summary['mishap_rate_all']:.1f}%")
    add("  wild swing faces:")
    for face, count in sorted(summary["wild_faces"].items()):
        add(f"    {face:>20}  {count:5d}  {_pct(count, summary['wild_swings']):5.1f}%")
    add("")
    add("-- WIN RATE BY BUILD -----------------------------------------------------")
    add(
        "    build        slots   wins   winrate   norm'd   mean score   "
        "mean place   survival"
    )
    for build in BUILD_ORDER:
        add(
            f"    {build:<12} {summary['slots_build'].get(build, 0):5d}  "
            f"{summary['wins_build'].get(build, 0):5d}   "
            f"{summary['winrate_build'][build]:6.1f}%  "
            f"{summary['winrate_build_norm'][build]:6.1f}%   "
            f"{summary['mean_score_build'][build]:10.2f}   "
            f"{summary['mean_place_build'][build]:10.2f}   "
            f"{summary['survival_build'][build]:7.1f}%"
        )
    add("")
    add("-- WIN RATE BY SEAT ------------------------------------------------------")
    for seat in range(1, n_agents + 1):
        add(
            f"    seat {seat}   wins {summary['wins_seat'].get(seat, 0):4d}   "
            f"{summary['winrate_seat'][seat]:6.1f}%"
        )
    add("")
    add("-- ELIMINATIONS ----------------------------------------------------------")
    add(f"  total eliminations         {summary['elim_total']}")
    add(f"  per match                  {summary['elim_per_match']:.2f}")
    add(
        f"  collateral (accidental)    {summary['elim_collateral']} "
        f"({_pct(summary['elim_collateral'], summary['elim_total']):.1f}%)"
    )
    add("  elimination round distribution:")
    add(
        _fmt_hist(
            summary["elim_rounds"],
            list(range(1, 13)),
            max(1, summary["elim_total"]),
        )
    )
    add("")
    add("-- ACTION DISCIPLINE -----------------------------------------------------")
    add(f"  agent decisions            {summary['decisions']}")
    add(
        f"  invalid actions (-2)       {summary['invalid_actions']}  "
        f"({summary['invalid_rate']:.2f}%)"
    )
    add(
        f"  stale actions (no penalty) {summary['stale_actions']}  "
        f"({summary['stale_rate']:.2f}%)"
    )
    if summary["invalid_reasons"]:
        add("  invalid reasons:")
        for reason, count in sorted(
            summary["invalid_reasons"].items(), key=lambda item: -item[1]
        ):
            add(f"    {count:6d}  {reason}")
    if summary["stale_reasons"]:
        add("  stale reasons:")
        for reason, count in sorted(
            summary["stale_reasons"].items(), key=lambda item: -item[1]
        ):
            add(f"    {count:6d}  {reason}")
        add("  stale by submitted verb:")
        for verb, count in sorted(
            summary["stale_by_verb"].items(), key=lambda item: -item[1]
        ):
            add(
                f"    {verb:>10}  {count:6d}  "
                f"({_pct(count, summary['action_verbs'].get(verb, 0)):.1f}% of "
                f"{summary['action_verbs'].get(verb, 0)} submitted)"
            )
    add("  decision provenance (validity):")
    for label, count in sorted(
        summary["validity"].items(), key=lambda item: -item[1]
    ):
        add(
            f"    {label:>18}  {count:6d}  "
            f"{_pct(count, summary['decisions']):5.1f}%"
        )
    add(
        f"  agent-matches autopiloted (token budget): "
        f"{summary['autopiloted_agents']} / {summary['agent_slots']} "
        f"({_pct(summary['autopiloted_agents'], summary['agent_slots']):.1f}%)"
    )
    if summary["autopilot_rounds"]:
        add("  first autopilot round:")
        add(
            _fmt_hist(
                summary["autopilot_rounds"],
                sorted(summary["autopilot_rounds"]),
                summary["autopiloted_agents"],
            )
        )
    add(
        f"  mean tokens left at end   {summary['tokens_left_mean']:.0f} of 18000 "
        f"({summary['tokens_exhausted_pct']:.1f}% of agents hit 0)"
    )
    add("  submitted action mix:")
    total_verbs = sum(summary["action_verbs"].values())
    for verb, count in sorted(
        summary["action_verbs"].items(), key=lambda item: -item[1]
    ):
        add(f"    {verb:>10}  {count:6d}  {_pct(count, total_verbs):5.1f}%")
    add("")
    add("-- OTHER -----------------------------------------------------------------")
    add(f"  seals activated per match  {summary['seals_per_match']:.2f}")
    add(f"  monsters killed per match  {summary['monsters_per_match']:.2f}")
    add("")
    add("-- TARGETS ---------------------------------------------------------------")
    build_rates = list(summary["winrate_build_norm"].values())
    checks = [
        (label, summary[key], predicate(summary[key])) for label, key, predicate in TARGETS
    ]
    spread_ok = all(15.0 <= rate <= 35.0 for rate in build_rates)
    checks.append(
        (
            "no build win rate outside 25% +/- 10pp",
            f"min {min(build_rates):.1f}% / max {max(build_rates):.1f}%",
            spread_ok,
        )
    )
    for label, value, ok in checks:
        shown = f"{value:.1f}" if isinstance(value, float) else str(value)
        add(f"  [{'MET ' if ok else 'MISS'}] {label:<42} actual: {shown}")
    add("=" * 74)
    return out


# ---------------------------------------------------------------------------
# determinism spot check
# ---------------------------------------------------------------------------


def determinism_check(seeds: list[int], n_agents: int) -> list[str]:
    lines = []
    for seed in seeds:
        first = run_match(seed, n_agents, keep_hashes=True)
        second = run_match(seed, n_agents, keep_hashes=True)
        same = first.get("snapshot_hashes") == second.get("snapshot_hashes")
        lines.append(
            f"  seed {seed}: {len(first.get('snapshot_hashes', []))} snapshots  "
            f"{'IDENTICAL' if same else 'DIVERGED'}"
        )
    return lines


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=160, help="number of matches")
    parser.add_argument("--start", type=int, default=1_000_000, help="first seed")
    parser.add_argument("--agents", type=int, default=8, help="agents per match (4..8)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    parser.add_argument("--json", default=None, help="write raw per-match records here")
    parser.add_argument("--determinism", type=int, default=0)
    parser.add_argument(
        "--rogue-rate",
        type=float,
        default=0.0,
        help=(
            "fraction of decisions replaced with a schema-valid but ILLEGAL "
            "action, to exercise the -2 penalty path the reference policy "
            "structurally cannot reach"
        ),
    )
    args = parser.parse_args()

    if not 4 <= args.agents <= 8:
        parser.error("--agents must be 4..8")

    seeds = [args.start + index for index in range(args.seeds)]
    started = time.time()

    jobs = [(seed, args.agents, args.rogue_rate) for seed in seeds]
    records: list[dict[str, Any]] = []
    if args.workers > 1:
        with mp.get_context("fork").Pool(args.workers) as pool:
            for index, record in enumerate(pool.imap_unordered(_worker, jobs, 4), 1):
                records.append(record)
                if index % 20 == 0 or index == len(jobs):
                    print(
                        f"  ... {index}/{len(jobs)} matches "
                        f"({time.time() - started:.0f}s)",
                        file=sys.stderr,
                        flush=True,
                    )
    else:
        for index, job in enumerate(jobs, 1):
            records.append(_worker(job))
            if index % 20 == 0:
                print(f"  ... {index}/{len(jobs)}", file=sys.stderr, flush=True)

    records.sort(key=lambda record: record["seed"])
    elapsed = time.time() - started
    summary = aggregate(records, args.agents)
    for line in report(summary, args.agents, elapsed):
        print(line)

    if args.determinism:
        print("\n-- DETERMINISM SPOT CHECK ---------------------------------------")
        for line in determinism_check(seeds[: args.determinism], args.agents):
            print(line)

    if args.json:
        Path(args.json).write_text(
            json.dumps({"records": records}, indent=1, default=str), encoding="utf-8"
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
