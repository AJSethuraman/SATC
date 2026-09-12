"""One call through the Agent SDK with the adapter's own options, printing the
raw ResultMessage fields the ledger is derived from, and nothing else.

    python tools/probe_sdk.py            # model alias "opus", as the arena uses
    python tools/probe_sdk.py claude-opus-5

Answers, on the machine where `claude` is logged in: which model id the alias
resolves to (`model_usage` keys), what the SDK counts (`usage`) and what it
prices (`total_cost_usd`, `model_usage[...]["costUSD"]`), for one trivial
prompt with no brain and no observation. Prints whether a key is set, never
the key. Costs one call.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arena.providers import AgentSDKProvider  # noqa: E402

FIELDS = ("subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms",
          "stop_reason", "total_cost_usd", "usage", "model_usage", "errors", "result")


def main(argv: list[str]) -> int:
    print("ANTHROPIC_API_KEY set:", "ANTHROPIC_API_KEY" in os.environ)
    provider = AgentSDKProvider(model=argv[1] if len(argv) > 1 else None)
    print("asked for model:", provider.model, "| effort:", provider.effort)
    query, factory = provider._sdk()
    options = provider._options(factory, "Reply with the single word ok.", None)
    started = time.monotonic()
    result = asyncio.run(provider._collect(query, "ok?", options))
    print("latency_ms:", round((time.monotonic() - started) * 1000))
    if result is None:
        print("no result message")
        return 1
    for field in FIELDS:
        print(f"{field}:", json.dumps(getattr(result, field, None), default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
