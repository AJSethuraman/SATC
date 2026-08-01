"""AGENT — the local model reading the practice's own records.

A natural-language front door: *"what needs me today?"*, *"what's missing for
Northshore?"*, *"draft the chase for Beacon Hill."* The model reads through a
small, read-only tool surface and answers in plain language.

What it can do: read aggregated views, render a draft, and say it doesn't know.

What it cannot do — not by prompt, but because the capability does not exist and
the engine refuses it anyway: send, sign, file, confirm a staged value, close a
client request, or compute a tax figure. See `docs/DESIGN-PRINCIPLES.md` §6 and
§9, and `docs/LOCAL-LLM-PATTERN.md`.

The deterministic engine did the noticing before the model was ever involved
(`satc.actions`). The model's budget goes on the margin: phrasing, and answering
the question the owner actually asked.
"""

from __future__ import annotations

from satc.agent.runner import (
    DEFAULT_MODEL,
    MAX_TURNS,
    AgentTurn,
    ask,
    available,
    model_actor,
)
from satc.agent.tools import TOOL_SPECS, TOOLS, dispatch

__all__ = [
    "DEFAULT_MODEL",
    "MAX_TURNS",
    "TOOLS",
    "TOOL_SPECS",
    "AgentTurn",
    "ask",
    "available",
    "dispatch",
    "model_actor",
]
