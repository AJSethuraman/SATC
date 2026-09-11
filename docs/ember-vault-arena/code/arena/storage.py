from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AgentManifest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def state_hash(state: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(state).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# MID-MATCH REDACTION
#
# The replay bundle is served over an unauthenticated GET while a match is still
# running, so it is a live intelligence feed for anyone who polls it. The stored
# rows are never touched — only the published view is narrowed, and the full
# bundle (prompts, seed, dice proofs, private state) is restored verbatim once
# ``status == 'completed'`` so the audit chain stays independently verifiable.
# ---------------------------------------------------------------------------

# Per-agent state a rival must not read while the match is live.
PRIVATE_AGENT_STATE_KEYS = ("memory", "score_breakdown", "tokens_remaining")

# Payload change-log keys that carry the same private state.
PRIVATE_CHANGE_KEYS = ("memory", "tokens_remaining")

# The only parsed-action fields that describe a PUBLIC, observable act. Anything
# else (reasoning_summary, memory_write) is the agent's private thinking.
PUBLIC_ACTION_KEYS = ("action", "target", "destination", "item", "speech")

# Mid-match a die shows its face and nothing else: the seed/counter/digest are
# the material that lets a rival precompute future rolls.
PUBLIC_DICE_PROOF_KEYS = ("label", "sides", "result")


def _public_snapshot_state(state: dict[str, Any], reveal: bool) -> dict[str, Any]:
    if reveal:
        return state
    public = {key: value for key, value in state.items() if key != "seed"}
    agents = public.get("agents")
    if isinstance(agents, dict):
        public["agents"] = {
            agent_id: {
                key: value
                for key, value in agent.items()
                if key not in PRIVATE_AGENT_STATE_KEYS
            }
            if isinstance(agent, dict)
            else agent
            for agent_id, agent in agents.items()
        }
    return public


def _public_event_payload(payload: Any, reveal: bool) -> Any:
    if reveal or not isinstance(payload, dict):
        return payload
    public = dict(payload)
    changes = public.get("changes")
    if isinstance(changes, dict):
        public["changes"] = {
            key: value
            for key, value in changes.items()
            if key not in PRIVATE_CHANGE_KEYS
        }
    # invalid_action_fallback / stale_action echo the whole submitted action,
    # which carries the same private reasoning_summary + memory_write.
    if isinstance(public.get("submitted_action"), dict):
        public["submitted_action"] = _public_action(public["submitted_action"], reveal)
    proof = public.get("proof")
    if isinstance(proof, dict):
        public["proof"] = {
            key: value for key, value in proof.items() if key in PUBLIC_DICE_PROOF_KEYS
        }
    return public


def _public_action(action: Any, reveal: bool) -> Any:
    if reveal or not isinstance(action, dict):
        return action
    return {key: value for key, value in action.items() if key in PUBLIC_ACTION_KEYS}


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id TEXT PRIMARY KEY,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    max_rounds INTEGER NOT NULL,
    winner_agent_id TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS participants (
    match_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    seat INTEGER NOT NULL,
    secret_objective TEXT NOT NULL,
    final_score INTEGER,
    placement INTEGER,
    final_status TEXT,
    PRIMARY KEY (match_id, agent_id),
    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS turns (
    match_id TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    start_state_hash TEXT NOT NULL,
    end_state_hash TEXT,
    narration TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (match_id, round_no),
    FOREIGN KEY (match_id) REFERENCES matches(id)
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    prompt_json TEXT NOT NULL,
    raw_output TEXT NOT NULL,
    parsed_action_json TEXT NOT NULL,
    validity TEXT NOT NULL,
    fallback_reason TEXT,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    phase TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT,
    target_id TEXT,
    public_text TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    match_id TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    phase TEXT NOT NULL,
    state_json TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (match_id, round_no, phase)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    category TEXT NOT NULL,
    points INTEGER NOT NULL,
    detail TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    body_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_match ON events(match_id, seq);
CREATE INDEX IF NOT EXISTS idx_audit_match ON audit_log(match_id, seq);
CREATE INDEX IF NOT EXISTS idx_decisions_match ON decisions(match_id, round_no);
"""


class ArenaStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    def register_agent(self, manifest: AgentManifest) -> None:
        manifest_json = canonical_json(manifest.as_dict())
        prompt_hash = hashlib.sha256(
            manifest.system_prompt.encode("utf-8")
        ).hexdigest()
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO agents(id, name, manifest_json, prompt_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name,
                  manifest_json=excluded.manifest_json,
                  prompt_hash=excluded.prompt_hash
                """,
                (manifest.id, manifest.name, manifest_json, prompt_hash, utc_now()),
            )
            self.conn.commit()

    def create_match(
        self,
        match_id: str,
        seed: int,
        ruleset_version: str,
        max_rounds: int,
        manifests: list[AgentManifest],
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO matches(
                  id, seed, status, ruleset_version, max_rounds, created_at
                ) VALUES (?, ?, 'running', ?, ?, ?)
                """,
                (match_id, seed, ruleset_version, max_rounds, utc_now()),
            )
            for seat, manifest in enumerate(manifests, start=1):
                self.conn.execute(
                    """
                    INSERT INTO participants(
                      match_id, agent_id, seat, secret_objective
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (match_id, manifest.id, seat, manifest.secret_objective),
                )
            self.conn.commit()
        self.append_audit(
            match_id,
            "match_created",
            {
                "seed": seed,
                "ruleset_version": ruleset_version,
                "max_rounds": max_rounds,
                "agent_ids": [manifest.id for manifest in manifests],
            },
        )

    def start_turn(
        self, match_id: str, round_no: int, start_hash: str
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO turns(
                  match_id, round_no, start_state_hash, started_at
                ) VALUES (?, ?, ?, ?)
                """,
                (match_id, round_no, start_hash, utc_now()),
            )
            self.conn.commit()

    def end_turn(
        self,
        match_id: str,
        round_no: int,
        end_hash: str,
        narration: str,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                UPDATE turns
                SET end_state_hash=?, narration=?, completed_at=?
                WHERE match_id=? AND round_no=?
                """,
                (end_hash, narration, utc_now(), match_id, round_no),
            )
            self.conn.commit()

    def save_snapshot(
        self, match_id: str, round_no: int, phase: str, state: dict[str, Any]
    ) -> str:
        snapshot_hash = state_hash(state)
        body = {
            "round_no": round_no,
            "phase": phase,
            "state_hash": snapshot_hash,
            "state": state,
        }
        with self.lock:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO snapshots(
                  match_id, round_no, phase, state_json, state_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    round_no,
                    phase,
                    canonical_json(state),
                    snapshot_hash,
                    utc_now(),
                ),
            )
            self.conn.commit()
        self.append_audit(match_id, "snapshot", body)
        return snapshot_hash

    def log_decision(
        self,
        match_id: str,
        round_no: int,
        agent_id: str,
        prompt: dict[str, Any],
        raw_output: str,
        parsed_action: dict[str, Any],
        validity: str,
        fallback_reason: str | None,
        input_tokens: int,
        output_tokens: int,
        provider: str,
        model: str,
    ) -> None:
        body = {
            "round_no": round_no,
            "agent_id": agent_id,
            "prompt": prompt,
            "raw_output": raw_output,
            "parsed_action": parsed_action,
            "validity": validity,
            "fallback_reason": fallback_reason,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "provider": provider,
                "model": model,
            },
        }
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO decisions(
                  match_id, round_no, agent_id, prompt_json, raw_output,
                  parsed_action_json, validity, fallback_reason, input_tokens,
                  output_tokens, provider, model, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    round_no,
                    agent_id,
                    canonical_json(prompt),
                    raw_output,
                    canonical_json(parsed_action),
                    validity,
                    fallback_reason,
                    input_tokens,
                    output_tokens,
                    provider,
                    model,
                    utc_now(),
                ),
            )
            self.conn.commit()
        self.append_audit(match_id, "agent_decision", body)

    def append_event(
        self,
        match_id: str,
        round_no: int,
        phase: str,
        event_type: str,
        actor_id: str | None,
        target_id: str | None,
        public_text: str,
        payload: dict[str, Any],
        current_state: dict[str, Any],
    ) -> None:
        current_hash = state_hash(current_state)
        body = {
            "round_no": round_no,
            "phase": phase,
            "event_type": event_type,
            "actor_id": actor_id,
            "target_id": target_id,
            "public_text": public_text,
            "payload": payload,
            "state_hash": current_hash,
        }
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO events(
                  match_id, round_no, phase, event_type, actor_id, target_id,
                  public_text, payload_json, state_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    round_no,
                    phase,
                    event_type,
                    actor_id,
                    target_id,
                    public_text,
                    canonical_json(payload),
                    current_hash,
                    utc_now(),
                ),
            )
            self.conn.commit()
        self.append_audit(match_id, "referee_event", body)

    def events_for_match(self, match_id: str) -> list[dict[str, Any]]:
        """Read-only projection of the committed event log, ordered by seq ASC.

        DELIBERATELY OMITS ``seq`` (globally autoincrementing, so it differs
        between databases holding different numbers of matches) and
        ``created_at`` (wall clock).  Either leaking into an observation would
        make prompt bytes — and therefore the audit chain — run-dependent.  The
        per-match ``ordinal`` is the only ordering identity that may leave the
        store.
        """
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT round_no, phase, event_type, actor_id, target_id,
                       public_text, payload_json
                FROM events WHERE match_id=? ORDER BY seq
                """,
                (match_id,),
            ).fetchall()
        return [
            {
                "ordinal": ordinal,
                "round_no": row["round_no"],
                "phase": row["phase"],
                "event_type": row["event_type"],
                "actor_id": row["actor_id"],
                "target_id": row["target_id"],
                "public_text": row["public_text"],
                "payload": json.loads(row["payload_json"]),
            }
            for ordinal, row in enumerate(rows)
        ]

    def add_score(
        self,
        match_id: str,
        round_no: int,
        agent_id: str,
        category: str,
        points: int,
        detail: str,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO scores(match_id, agent_id, round_no, category, points, detail)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (match_id, agent_id, round_no, category, points, detail),
            )
            self.conn.commit()
        self.append_audit(
            match_id,
            "score_change",
            {
                "round_no": round_no,
                "agent_id": agent_id,
                "category": category,
                "points": points,
                "detail": detail,
            },
        )

    def finish_match(
        self, match_id: str, state: dict[str, Any], placements: dict[str, int]
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                UPDATE matches SET status='completed', winner_agent_id=?,
                  completed_at=? WHERE id=?
                """,
                (state["winner_agent_id"], utc_now(), match_id),
            )
            for agent_id, agent in state["agents"].items():
                self.conn.execute(
                    """
                    UPDATE participants SET final_score=?, placement=?, final_status=?
                    WHERE match_id=? AND agent_id=?
                    """,
                    (
                        agent["score"],
                        placements[agent_id],
                        agent["status"],
                        match_id,
                        agent_id,
                    ),
                )
            self.conn.commit()
        self.append_audit(
            match_id,
            "match_completed",
            {
                "winner_agent_id": state["winner_agent_id"],
                "placements": placements,
                "scores": {
                    agent_id: agent["score"]
                    for agent_id, agent in state["agents"].items()
                },
            },
        )

    def append_audit(self, match_id: str, kind: str, body: dict[str, Any]) -> str:
        with self.lock:
            row = self.conn.execute(
                """
                SELECT entry_hash FROM audit_log
                WHERE match_id=? ORDER BY seq DESC LIMIT 1
                """,
                (match_id,),
            ).fetchone()
            previous = row["entry_hash"] if row else "GENESIS"
            envelope = {"match_id": match_id, "kind": kind, "body": body}
            entry_hash = hashlib.sha256(
                (previous + canonical_json(envelope)).encode("utf-8")
            ).hexdigest()
            self.conn.execute(
                """
                INSERT INTO audit_log(
                  match_id, kind, body_json, prev_hash, entry_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    kind,
                    canonical_json(body),
                    previous,
                    entry_hash,
                    utc_now(),
                ),
            )
            self.conn.commit()
            return entry_hash

    def list_matches(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT m.*, COUNT(p.agent_id) AS agent_count
                FROM matches m
                LEFT JOIN participants p ON p.match_id=m.id
                GROUP BY m.id
                ORDER BY m.created_at DESC
                """
            ).fetchall()
        # Same rule as replay_bundle: a live match must not publish its seed, or
        # withholding it from /replay buys nothing.
        return [
            {
                **dict(row),
                "seed": row["seed"] if row["status"] == "completed" else None,
            }
            for row in rows
        ]

    def list_agents(self) -> list[dict[str, Any]]:
        """PUBLIC ROSTER — projection only.

        ``system_prompt``, ``strategy`` and ``secret_objective`` are the exact
        set ``replay_bundle`` withholds until a match completes, so they must
        never ride out on the unauthenticated roster either. The UI picker needs
        id / name / build; nothing here needs more.
        """
        with self.lock:
            rows = self.conn.execute(
                "SELECT id, name, manifest_json, prompt_hash, created_at FROM agents ORDER BY name"
            ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "manifest": AgentManifest.from_dict(
                    json.loads(row["manifest_json"])
                ).public_dict(reveal_secret=False),
                "prompt_hash": row["prompt_hash"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_manifests(self, agent_ids: list[str]) -> list[AgentManifest]:
        if not agent_ids:
            return []
        placeholders = ",".join("?" for _ in agent_ids)
        with self.lock:
            rows = self.conn.execute(
                f"SELECT id, manifest_json FROM agents WHERE id IN ({placeholders})",
                tuple(agent_ids),
            ).fetchall()
        by_id = {
            row["id"]: AgentManifest.from_dict(json.loads(row["manifest_json"]))
            for row in rows
        }
        missing = [agent_id for agent_id in agent_ids if agent_id not in by_id]
        if missing:
            raise KeyError(f"unknown agents: {', '.join(missing)}")
        return [by_id[agent_id] for agent_id in agent_ids]

    def leaderboard(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT a.id, a.name, COUNT(p.match_id) AS matches,
                  SUM(CASE WHEN p.placement=1 THEN 1 ELSE 0 END) AS wins,
                  ROUND(AVG(p.final_score), 1) AS avg_score,
                  MAX(p.final_score) AS best_score
                FROM participants p
                JOIN agents a ON a.id=p.agent_id
                JOIN matches m ON m.id=p.match_id AND m.status='completed'
                GROUP BY a.id, a.name
                ORDER BY wins DESC, avg_score DESC, a.name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def replay_bundle(self, match_id: str) -> dict[str, Any]:
        with self.lock:
            match = self.conn.execute(
                "SELECT * FROM matches WHERE id=?", (match_id,)
            ).fetchone()
            if not match:
                raise KeyError(match_id)
            reveal = match["status"] == "completed"
            participants = self.conn.execute(
                """
                SELECT p.*, a.name, a.manifest_json, a.prompt_hash
                FROM participants p JOIN agents a ON a.id=p.agent_id
                WHERE p.match_id=? ORDER BY p.seat
                """,
                (match_id,),
            ).fetchall()
            events = self.conn.execute(
                "SELECT * FROM events WHERE match_id=? ORDER BY seq", (match_id,)
            ).fetchall()
            snapshots = self.conn.execute(
                """
                SELECT round_no, phase, state_json, state_hash
                FROM snapshots WHERE match_id=?
                ORDER BY round_no, CASE phase WHEN 'start' THEN 0 ELSE 1 END
                """,
                (match_id,),
            ).fetchall()
            decisions = self.conn.execute(
                """
                SELECT round_no, agent_id, parsed_action_json, validity,
                  fallback_reason, input_tokens, output_tokens, provider, model,
                  prompt_json, raw_output
                FROM decisions WHERE match_id=? ORDER BY round_no, id
                """,
                (match_id,),
            ).fetchall()
            scores = self.conn.execute(
                "SELECT * FROM scores WHERE match_id=? ORDER BY id", (match_id,)
            ).fetchall()

        participant_data = []
        for row in participants:
            manifest = json.loads(row["manifest_json"])
            public_manifest = {
                "id": manifest["id"],
                "name": manifest["name"],
                "personality": manifest["personality"],
                "build": manifest["build"],
            }
            if reveal or row["final_status"] == "eliminated":
                public_manifest = manifest
            participant_data.append(
                {
                    "seat": row["seat"],
                    "final_score": row["final_score"],
                    "placement": row["placement"],
                    "final_status": row["final_status"],
                    "prompt_hash": row["prompt_hash"],
                    "manifest": public_manifest,
                }
            )

        match_data = dict(match)
        if not reveal:
            # [4] the seed is the whole RNG. HashRNG is SHA-256(seed:counter:
            # label), so a rival polling mid-match could precompute every future
            # roll from a known label. It publishes after the match, when the
            # proofs exist to be checked and nothing is left to game.
            match_data["seed"] = None

        return {
            "match": match_data,
            "redacted": not reveal,
            "participants": participant_data,
            "events": [
                {
                    **{key: row[key] for key in row.keys() if key != "payload_json"},
                    "payload": _public_event_payload(
                        json.loads(row["payload_json"]), reveal
                    ),
                }
                for row in events
            ],
            "snapshots": [
                {
                    "round_no": row["round_no"],
                    "phase": row["phase"],
                    "state": _public_snapshot_state(
                        json.loads(row["state_json"]), reveal
                    ),
                    "state_hash": row["state_hash"],
                }
                for row in snapshots
            ],
            "decisions": [
                {
                    **{
                        key: row[key]
                        for key in row.keys()
                        if key
                        not in {"parsed_action_json", "prompt_json"}
                        and (reveal or key != "raw_output")
                    },
                    "action": _public_action(
                        json.loads(row["parsed_action_json"]), reveal
                    ),
                    **(
                        {"prompt": json.loads(row["prompt_json"])}
                        if reveal
                        else {}
                    ),
                }
                for row in decisions
            ],
            "scores": [dict(row) for row in scores],
        }

    def verify_audit(self, match_id: str) -> dict[str, Any]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM audit_log WHERE match_id=? ORDER BY seq", (match_id,)
            ).fetchall()
        previous = "GENESIS"
        for index, row in enumerate(rows):
            body = json.loads(row["body_json"])
            envelope = {"match_id": match_id, "kind": row["kind"], "body": body}
            expected = hashlib.sha256(
                (previous + canonical_json(envelope)).encode("utf-8")
            ).hexdigest()
            if row["prev_hash"] != previous or row["entry_hash"] != expected:
                return {
                    "valid": False,
                    "entries": len(rows),
                    "failed_index": index,
                    "failed_seq": row["seq"],
                }
            previous = row["entry_hash"]
        return {
            "valid": True,
            "entries": len(rows),
            "head_hash": previous,
        }
