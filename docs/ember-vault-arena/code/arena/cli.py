from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo import DEFAULT_AGENT_DIR, load_manifests
from .engine import ArenaEngine
from .providers import provider_from_name
from .server import serve
from .storage import ArenaStore


DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "arena.db"


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="agent-arena")
    root.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    sub = root.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="run the four sample agents")
    demo.add_argument("--seed", type=int, default=20260724)
    demo.add_argument("--provider", choices=["mock", "compatible"], default="mock")
    demo.add_argument("--agents", default=str(DEFAULT_AGENT_DIR))

    web = sub.add_parser("serve", help="start spectator UI and local API")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8787)

    verify = sub.add_parser("verify", help="verify a match audit hash chain")
    verify.add_argument("match_id")

    replay = sub.add_parser("replay", help="export a replay bundle as JSON")
    replay.add_argument("match_id")
    replay.add_argument("--output")
    return root


def main() -> None:
    args = parser().parse_args()
    store = ArenaStore(args.db)
    try:
        if args.command == "demo":
            manifests = load_manifests(args.agents)
            match_id = ArenaEngine(
                store, provider_from_name(args.provider)
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
            print("Run `python run.py serve` to watch the replay.")
        elif args.command == "serve":
            serve(store, args.host, args.port)
        elif args.command == "verify":
            print(json.dumps(store.verify_audit(args.match_id), indent=2))
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

