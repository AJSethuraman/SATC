"""Wording the model CHOOSES between, rather than wording it writes.

The owner's principle, and the better one: *give the model the same limited
choices the human has.* A person picks a client from a list, a template from
eighteen, a service from the catalogue. Wording should work the same way — the
practice writes the sentences, the model picks which one fits.

What this replaces was free generation with a filter checking afterwards for
dollar signs. That has an **infinite output space**, so nobody can ever read
every sentence that might reach a client; the filter was the only thing standing
between a model's invention and a client's inbox. Here the output space is four,
and it lives in ``configs/comms/wording.yaml`` where it can be read in a minute
and edited in a second.

Three consequences worth naming:

* **The model never emits prose.** It returns a KEY. The engine looks up the
  text. A model that returns something not in the list gets the default, not
  its own sentence — the failure mode is "slightly wrong variant", never
  "invented paragraph".
* **A figure cannot appear** unless the practice wrote one, because the practice
  wrote every candidate sentence.
* **It works with no model at all.** Absent Ollama, the first variant is used.
  That is a real answer rather than a blank.

This is doctrine rule 5 — name the criterion, the engine selects — applied to
language instead of rows.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from satc.config import read_yaml

from satc.comms.library import comms_dir

WORDING_FILE = "wording.yaml"


@dataclass(frozen=True, slots=True)
class Variant:
    """One sentence the practice is willing to send, and when it fits."""

    key: str
    when: str
    text: str


@dataclass(frozen=True, slots=True)
class WordingSlot:
    """A merge field whose value is CHOSEN from a fixed set."""

    name: str
    label: str
    variants: tuple[Variant, ...]

    @property
    def default(self) -> Variant:
        """Used when there is no model, or the model picks something invalid.

        First in the file, so the ordering in config is a real decision: put the
        one you would pick if you had to pick blind at the top.
        """
        return self.variants[0]

    def get(self, key: str) -> Variant:
        return next((v for v in self.variants if v.key == key), self.default)


def load_wording(config_root: Path | None = None) -> dict[str, WordingSlot]:
    path = comms_dir(config_root) / WORDING_FILE
    if not path.exists():
        return {}
    data = read_yaml(path) or {}
    out: dict[str, WordingSlot] = {}
    for name, spec in (data.get("slots") or {}).items():
        variants = tuple(
            Variant(key=str(v.get("key", "")),
                    when=" ".join(str(v.get("when", "")).split()),
                    text=" ".join(str(v.get("text", "")).split()))
            for v in (spec.get("variants") or []) if v.get("text"))
        if variants:
            out[str(name)] = WordingSlot(
                name=str(name), label=str(spec.get("label", name)), variants=variants)
    return out


@lru_cache(maxsize=1)
def _cached_wording() -> dict[str, WordingSlot]:
    return load_wording()


def wording() -> dict[str, WordingSlot]:
    return _cached_wording()


@dataclass(frozen=True, slots=True)
class Choice:
    """Which variant was used, and whether a model or the default picked it."""

    slot: str
    variant_key: str
    text: str
    chosen_by_model: bool = False


def _ask_which(slot: WordingSlot, context: str, *, model: str, host: str,
               timeout: float) -> str:
    """Ask the model for a KEY. It never returns prose."""
    options = "\n".join(f"  {v.key} — use when {v.when}" for v in slot.variants)
    system = (
        "You choose between pre-written options for a tax practice's client "
        "letters. Reply with ONE option key, exactly as written, and nothing "
        "else. No explanation, no punctuation, no prose.")
    prompt = (f"Which option fits?\n\nOPTIONS:\n{options}\n\n"
              f"SITUATION: {context}\n\nReply with one key.")
    payload = json.dumps({
        "model": model, "stream": False,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        # A classification, not a composition. Keep it cold.
        "options": {"temperature": 0.0},
    }).encode("utf-8")
    request = urllib.request.Request(f"{host}/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return ((body.get("message") or {}).get("content") or "").strip().split()[0:1] and \
        ((body.get("message") or {}).get("content") or "").strip().split()[0] or ""


def choose(slot_names, *, context: str = "", model: str = "", host: str = "",
           timeout: float = 60.0) -> dict[str, Choice]:
    """Pick a variant for each named slot.

    Never fails: a slot with no model, an unreachable model, or a model that
    answers with something not on the list all fall back to the default. The
    worst case is a slightly-wrong sentence the practice already approved —
    which is a different order of problem from an invented one.
    """
    from satc import settings
    from satc.agent.runner import DEFAULT_MODEL

    slots = wording()
    base = (host or settings.ollama_host()).rstrip("/")
    model = model or DEFAULT_MODEL
    out: dict[str, Choice] = {}

    for name in slot_names:
        slot = slots.get(name)
        if slot is None:
            continue
        if len(slot.variants) == 1:
            chosen, by_model = slot.default, False
        else:
            try:
                key = _ask_which(slot, context, model=model, host=base, timeout=timeout)
            except (urllib.error.URLError, OSError, ValueError, IndexError):
                key = ""
            picked = slot.get(key) if key else slot.default
            chosen = picked
            by_model = bool(key) and picked.key == key
        out[name] = Choice(slot=name, variant_key=chosen.key, text=chosen.text,
                           chosen_by_model=by_model)
    return out
