"""What to ask the client for, derived from what they already told us.

The onboarding letter's `RequestList` — the list under "Below is everything we
need to start your work".

WHY THIS EXISTS. Until 26 August 2026 nothing built it. Every onboarding
letter ever rendered promised that list and delivered none, and nothing
complained, because an `[[EACH]]` over an empty list leaves no token behind
for the strict check to catch. It is the same failure that once produced an
invoice with a blank services table under a confident total.

THE RULE IT FOLLOWS is the one the fee schedule already follows: ask what is
ON the return, never how many of something there is. A client who ticks the
rentals schedule and leaves the count blank still has rentals and still needs
to send rental records. The gate evaluator is imported from `pricing` rather
than written again, so the two can never drift into asking for documents
nobody has, or failing to ask for the ones we need.

THE WORDING IS THE FIRM'S and lives in `registry/document-requests.yaml`.
Nothing here writes English.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

import pricing

REGISTRY = Path(__file__).resolve().parent / "registry" / "document-requests.yaml"


class RequestError(Exception):
    """The request list cannot be built honestly."""


@lru_cache(maxsize=1)
def _load(path: str | None = None) -> list[dict]:
    raw = yaml.safe_load(Path(path or REGISTRY).read_text(encoding="utf-8")) or {}
    entries = raw.get("requests")
    if not entries:
        raise RequestError(
            f"{REGISTRY.name} lists no requests, so every onboarding letter "
            f"would go out asking a client for nothing. Add them rather than "
            f"letting the letter render empty."
        )
    return entries


def for_answers(answers: dict, entries: list[dict] | None = None) -> list[dict]:
    """The documents this client should be asked for, in registry order.

    Registry order, not answer order, so two clients with the same return get
    the same letter -- and so the engagement letter and ID sit at the top
    where they belong rather than wherever a gate happened to fire.
    """
    out = []
    for i, entry in enumerate(entries if entries is not None else _load()):
        document = (entry.get("document") or "").strip()
        if not document:
            raise RequestError(
                f"request #{i + 1} in {REGISTRY.name} has no `document`, so it "
                f"would print as a blank bullet on a client's letter."
            )
        gate = entry.get("when")
        if gate is not None and not pricing.gate_holds(
                gate, answers, f"document-requests[{i + 1}]"):
            continue
        out.append({"Document": document, "Detail": (entry.get("detail") or "").strip()})

    if not out:
        raise RequestError(
            "no document request applies to this client, which cannot be "
            "right -- the engagement letter and identification are asked of "
            "everybody. Check that document-requests.yaml still has its "
            "ungated entries."
        )
    return out
