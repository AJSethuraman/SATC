"""Letting the local model write the WORDING, so a draft arrives finished.

The original design left every judgement slot blank for the owner to fill —
scope of services, fee terms, how you'd like to meet. That is not caution, it is
homework, and it made "render a draft" mean "start a draft".

The rule splits in two, and the split is the whole idea:

* **Facts** — a fee, a refund, a deadline, an invoice number. Never invented.
  If the practice does not hold it, the slot stays visibly marked. That
  guarantee is unchanged and is enforced in :mod:`satc.comms.render`.
* **Wording** — the sentences the owner would type anyway, carrying no figure.
  The model drafts those, and the owner edits rather than composes.

The model is given only what the engine already established: the client's name,
the year, the engagement. It is told, in the prompt AND by having no numbers
available to it, not to state a figure. Anything it writes is marked
``model_drafted`` so the owner can see at a glance which sentences are machine
words and which came off their own records.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

# Slots the model may write, and what it is being asked for. A slot NOT in this
# map is never handed to the model — which is how "invoice_number" stays a fact
# the owner supplies rather than something a language model invents.
COMPOSABLE = {
    "scope_of_services": (
        "one short paragraph describing what this engagement covers, in plain "
        "language, for a tax engagement letter"),
    "fee_terms": (
        "two or three sentences on how fees work: when the invoice comes and "
        "what it covers. Do NOT state any amount"),
    "proposed_times": (
        "one line inviting the client to suggest a couple of times that suit "
        "them. Do NOT invent specific dates or times"),
}

_SYSTEM = """You write short, warm, plain sentences for a small US tax firm's \
client letters. British-plain, never corporate.

Absolute rules:
- NEVER state a number: no fee, no refund, no deadline, no date. If a figure \
belongs somewhere, write around it — the system fills real figures separately.
- Write ONLY the requested text. No greeting, no sign-off, no preamble, no \
quotation marks, no explanation of what you wrote.
- Two or three sentences at most."""


@dataclass(frozen=True, slots=True)
class Composed:
    """One slot the model wrote."""

    name: str
    text: str

    @property
    def is_model_drafted(self) -> bool:
        return True


def _ask_for_text(prompt: str, *, model: str, host: str, timeout: float) -> str:
    payload = json.dumps({
        "model": model, "stream": False,
        "messages": [{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": prompt}],
        # Slightly warmer than the reading tasks: this is composition.
        "options": {"temperature": 0.5},
    }).encode("utf-8")
    request = urllib.request.Request(f"{host}/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return ((body.get("message") or {}).get("content") or "").strip()


def states_a_figure(text: str, *, known_year: str = "") -> bool:
    """Whether the model stated a number the practice did not establish.

    Belt and braces for doctrine rule 6 — policy at the CHOKE POINT, not in the
    prompt. The prompt says "no numbers"; this checks, and a sentence that
    states one is discarded rather than shown.

    Deliberately not "contains any digit": the tax year is already established
    and reads naturally in a sentence ("your 2024 return"). Rejecting that made
    the guard so strict it threw away every usable draft. What must never appear
    is an AMOUNT — a currency symbol, a percentage, or any other number.
    """
    import re

    if any(sym in text for sym in ("$", "%", "£", "€")):
        return True
    stripped = text.replace(known_year, " ") if known_year else text
    return bool(re.search(r"\d", stripped))


def compose_slots(names, *, client_name: str = "", tax_year: str = "",
                  engagement_name: str = "", model: str = "",
                  host: str = "", timeout: float = 60.0) -> dict[str, str]:
    """Draft the wording slots the model is allowed to write.

    Returns only what it actually produced. A slot the model declines, garbles,
    or sneaks a number into is simply absent — and an absent slot falls through
    to the visible "fill in" marker, which is the honest failure direction.
    """
    from satc import settings
    from satc.agent.runner import DEFAULT_MODEL

    base = (host or settings.ollama_host()).rstrip("/")
    model = model or DEFAULT_MODEL
    out: dict[str, str] = {}

    for name in names:
        brief = COMPOSABLE.get(name)
        if brief is None:
            continue          # not composable — stays a marked slot, by design
        about = ", ".join(p for p in (
            f"the client is {client_name}" if client_name else "",
            f"the tax year is {tax_year}" if tax_year else "",
            f"the engagement is {engagement_name}" if engagement_name else "",
        ) if p)
        prompt = f"Write {brief}."
        if about:
            prompt += f" Context: {about}."
        try:
            text = _ask_for_text(prompt, model=model, host=base, timeout=timeout)
        except (urllib.error.URLError, OSError, ValueError):
            continue          # model unreachable — the slot stays marked
        text = text.strip().strip('"').strip()
        if not text or states_a_figure(text, known_year=tax_year):
            continue
        out[name] = text
    return out
