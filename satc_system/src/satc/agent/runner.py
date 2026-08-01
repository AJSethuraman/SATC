"""Driving the local model — a bounded loop over a read-only tool surface.

The model is the driver; every control is deterministic. It chooses which tool
to call; this module decides whether that is allowed, what the tool actually
returns, and when to stop.

The bounds are the interesting part, and each one is a measured failure from the
sister project rather than caution:

* **A turn cap.** Small models abandon long tasks (~1 in 6–9 runs). The loop
  stops and says what it got, rather than spinning.
* **Inert by construction** (rule 9). There is no write tool, so a half-finished
  run leaves nothing behind. Re-running is free.
* **Never restate the task mid-run.** A progress nudge that repeats the original
  instruction makes the model start over.
* **Results stay small** (rules 1, 2). Enforced in ``tools.py``, not here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from satc.agent.tools import TOOL_SPECS, dispatch
from satc.models.actor import Actor

DEFAULT_MODEL = "SATC-Assistant:latest"
MAX_TURNS = 6
"""How many tool round-trips before the loop gives up and reports.

Six covers every real question the surface can answer (look, maybe look again,
answer). Beyond that the model is lost, and continuing produces confident
nonsense rather than an answer."""

SYSTEM = """You are the assistant inside SATC, the practice-operations system for a \
solo US tax firm. You run entirely on the owner's own machine.

Your job is to READ the practice's own records through the tools and answer plainly.

Rules you must follow:
- Never state a figure, date, or document you did not get from a tool. If a tool \
did not tell you, say you don't know.
- You cannot send, sign, file, or change anything. Drafts you produce are for the \
owner to read and send themselves.
- Drake is the system of record for anything a tax return says. Never compute tax.
- When you render a draft, DO NOT retype or reword it. Say it is ready, name the client and template, and summarise in one line what it covers. The owner reads the real text in the app — a reworded copy looks like the draft and is not it.
- Be brief. The owner is busy and scanning."""


@dataclass(slots=True)
class AgentTurn:
    """One exchange, with everything the scoreboard needs to judge it."""

    question: str
    answer: str = ""
    tool_calls: list[tuple[str, dict]] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    turns_used: int = 0
    gave_up: bool = False
    error: str = ""

    @property
    def tools_used(self) -> list[str]:
        return [name for name, _ in self.tool_calls]

    @property
    def ok(self) -> bool:
        return bool(self.answer) and not self.error


def model_actor(model: str = DEFAULT_MODEL) -> Actor:
    """The principal this run acts as. May propose; may never confirm."""
    return Actor.model(model)


def available(host: str = "", timeout: float = 2.0) -> bool:
    """Whether Ollama is reachable — checked, never assumed."""
    import urllib.error
    import urllib.request

    from satc import settings

    url = (host or settings.ollama_host()).rstrip("/") + "/api/version"
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except (urllib.error.URLError, OSError):
        return False


def ask(question: str, *, state, model: str = DEFAULT_MODEL, host: str = "",
        max_turns: int = MAX_TURNS, timeout: float = 120.0) -> AgentTurn:
    """Put a question to the local model, letting it read through the tools."""
    import urllib.error
    import urllib.request

    from satc import settings

    turn = AgentTurn(question=question)
    base = (host or settings.ollama_host()).rstrip("/")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]

    for n in range(1, max_turns + 1):
        turn.turns_used = n
        payload = json.dumps({
            "model": model, "messages": messages, "tools": TOOL_SPECS,
            "stream": False,
            # Low temperature: this is a reading task, not a writing one.
            "options": {"temperature": 0.2},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{base}/api/chat", data=payload,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            turn.error = f"could not reach the local model: {exc}"
            return turn

        message = body.get("message") or {}
        calls = message.get("tool_calls") or []
        if not calls:
            turn.answer = (message.get("content") or "").strip()
            return turn

        messages.append(message)
        for call in calls:
            fn = call.get("function") or {}
            name = fn.get("name", "")
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            result = dispatch(name, args, state=state)
            turn.tool_calls.append((name, args))
            turn.tool_results.append(result)
            messages.append({"role": "tool", "name": name,
                             "content": json.dumps(result, default=str)})

    # Out of turns. Report what was gathered rather than pretending to an answer —
    # and do NOT restate the task, which makes a small model start over.
    turn.gave_up = True
    turn.answer = ""
    return turn
