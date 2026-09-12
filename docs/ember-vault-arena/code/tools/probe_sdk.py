"""One call through the Agent SDK with the adapter's own options, printing the
raw ResultMessage fields the ledger is derived from, and nothing else.

    python tools/probe_sdk.py                       # trivial prompt, no schema
    python tools/probe_sdk.py --match ember-7-830ff8da
                                                    # replay a stored arena prompt
                                                    # WITH the action schema attached
    python tools/probe_sdk.py --model claude-opus-5

Answers, on the machine where `claude` is logged in: which model id the alias
resolves to (`model_usage` keys), what the SDK counts (`usage`, its
`iterations`, `model_usage`) and what it prices (`total_cost_usd`), and how
those compare with the repo's own rate table. `--match` takes the first
stored decision's prompt from the database so the call is a real arena call:
that is the one that shows whether a schema-constrained query is billed on
more than the top-level `usage` reports (forge probe, 12 Sep 2026). Prints
whether a key is set, never the key. Costs one call.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arena.models import action_json_schema  # noqa: E402
from arena.providers import AgentSDKProvider, AnthropicProvider, sdk_counts  # noqa: E402
from arena.storage import ArenaStore  # noqa: E402

FIELDS = ("subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms",
          "stop_reason", "total_cost_usd", "usage", "model_usage", "errors")


def stored_prompt(db: Path, match_id: str) -> dict:
    store = ArenaStore(db)
    try:
        decisions = store.replay_bundle(match_id)["decisions"]
    finally:
        store.close()
    if not decisions:
        raise SystemExit(f"no decisions stored for {match_id}")
    first = decisions[0]
    print(f"replaying the prompt of round {first['round_no']} / {first['agent_id']} from {match_id}")
    return first["prompt"]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=None, help="model or alias (default: the adapter's, 'opus')")
    ap.add_argument("--match", default=None, help="replay the first stored prompt of this match, schema attached")
    ap.add_argument("--db", default=str(ROOT / "data" / "arena.db"))
    args = ap.parse_args(argv[1:])

    print("ANTHROPIC_API_KEY set:", "ANTHROPIC_API_KEY" in os.environ)
    provider = AgentSDKProvider(model=args.model)
    print("asked for model:", provider.model, "| effort:", provider.effort)
    if args.match:
        prompt, schema = stored_prompt(Path(args.db), args.match), action_json_schema()
    else:
        prompt = {"messages": [{"role": "system", "content": "Reply with the single word ok."},
                               {"role": "user", "content": "ok?"}]}
        schema = None
    print("schema attached:", schema is not None,
          "| prompt characters:", sum(len(m.get("content", "")) for m in prompt.get("messages", [])))

    started = time.monotonic()
    result = provider.raw_result(prompt, schema=schema)
    print("latency_ms:", round((time.monotonic() - started) * 1000))
    if result is None:
        print("no result message")
        return 1
    for field in FIELDS:
        print(f"{field}:", json.dumps(getattr(result, field, None), default=str))
    text = getattr(result, "result", None)
    print("result characters:", len(text) if isinstance(text, str) else None,
          "| structured_output:", getattr(result, "structured_output", None) is not None)

    inp, out, cached, wrote, model = sdk_counts(result, provider.model)
    table = AnthropicProvider(client=object(), model=model).cost_of(model, inp, out, cached, wrote)
    model_usage = getattr(result, "model_usage", None) or {}
    priced = sum(float((v or {}).get("costUSD") or 0) for v in model_usage.values() if isinstance(v, dict))
    print(f"ledger would record: in {inp}, cached {cached}, wrote {wrote}, out {out}, model {model}")
    print(f"at the repo's rate table: {'$%.6f' % table if table is not None else 'no rates for ' + model}"
          f" | sum of model_usage costUSD: ${priced:.6f}"
          f" | total_cost_usd: {getattr(result, 'total_cost_usd', None)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
