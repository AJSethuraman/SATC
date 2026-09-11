from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo import DEFAULT_AGENT_DIR, load_manifests
from .engine import ArenaEngine
from .brains import load_brains
from .providers import PROVIDER_NAMES, provider_from_name
from .server import serve
from .storage import ArenaStore


DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "arena.db"


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="agent-arena")
    root.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    sub = root.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="run the four sample agents")
    demo.add_argument("--seed", type=int, default=20260724)
    demo.add_argument("--provider", choices=PROVIDER_NAMES, default="mock")
    demo.add_argument("--agents", default=str(DEFAULT_AGENT_DIR),
                      help="folder of JSON manifests (July's examples)")
    demo.add_argument("--brains", default=None,
                      help="folder of brain .md files; overrides --agents")
    demo.add_argument("--rounds", type=int, default=None)

    web = sub.add_parser("serve", help="start spectator UI and local API")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8787)

    verify = sub.add_parser("verify", help="verify a match audit hash chain")
    verify.add_argument("match_id")

    replay = sub.add_parser("replay", help="export a replay bundle as JSON")
    replay.add_argument("match_id")
    replay.add_argument("--output")

    ledger = sub.add_parser("ledger", help="one line per model call: who answered, how fast, at what cost")
    ledger.add_argument("match_id")
    return root


def print_ledger(store: ArenaStore, match_id: str) -> None:
    """The call ledger, readable. This is the morning checklist's first
    answer: did the model answer, or did the referee's default stand in."""
    decisions = store.replay_bundle(match_id)["decisions"]
    if not decisions:
        print("no decisions recorded")
        return
    print(f"{'round':>5} {'agent':<10} {'validity':<18} {'kind':<8} {'ms':>7} {'in':>6} {'out':>5} {'cost':>8}  reason")
    for d in decisions:
        cost = d.get("cost_usd")
        print(
            f"{d['round_no']:>5} {d['agent_id']:<10} {d['validity']:<18} "
            f"{(d.get('error_kind') or '-'):<8} {float(d.get('latency_ms') or 0):>7.0f} "
            f"{d['input_tokens']:>6} {d['output_tokens']:>5} "
            f"{('$%.4f' % cost) if cost is not None else '-':>8}  "
            f"{(d.get('fallback_reason') or '')[:70]}"
        )
    answered = sum(d["validity"] == "valid" for d in decisions)
    network = sum(d["validity"] == "network_fallback" for d in decisions)
    panic = sum(d["validity"] in ("panic_fallback", "invalid_output") for d in decisions)
    total_cost = sum(float(d.get("cost_usd") or 0) for d in decisions)
    providers = sorted({(d["provider"], d["model"]) for d in decisions})
    print(
        f"answered by the model: {answered} of {len(decisions)}; network: {network}; "
        f"panic: {panic}; cost recorded: ${total_cost:.4f}; provider/model: "
        + ", ".join(f"{p}/{m}" for p, m in providers)
    )


def main() -> None:
    args = parser().parse_args()
    store = ArenaStore(args.db)
    try:
        if args.command == "demo":
            manifests = load_brains(args.brains) if args.brains else load_manifests(args.agents)
            kwargs = {"max_rounds": args.rounds} if args.rounds else {}
            match_id = ArenaEngine(
                store, provider_from_name(args.provider), **kwargs
            ).run(manifests, args.seed)
            result = store.replay_bundle(match_id)
            print(f"Completed {match_id}")
            for participant in sorted(
                result["participants"], key=lambda item: item["placement"]
            ):
                print(
                    f"  #{participant['placement']} "
                    f"{participant['manifest']['name']}: "
                    f"{participant['final_score']} points"
                )
            print(f"Audit: {json.dumps(store.verify_audit(match_id))}")
            print_ledger(store, match_id)
            print("Run `python run.py serve` to watch the replay.")
        elif args.command == "serve":
            serve(store, args.host, args.port)
        elif args.command == "verify":
            print(json.dumps(store.verify_audit(args.match_id), indent=2))
        elif args.command == "ledger":
            print_ledger(store, args.match_id)
        elif args.command == "replay":
            payload = json.dumps(
                store.replay_bundle(args.match_id), indent=2, ensure_ascii=False
            )
            if args.output:
                Path(args.output).write_text(payload, encoding="utf-8")
                print(f"Wrote {args.output}")
            else:
                print(payload)
    finally:
        if args.command != "serve":
            store.close()


if __name__ == "__main__":
    main()

