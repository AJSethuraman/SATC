"""ACTOR — who did this, stamped by the engine and never claimed by a caller.

Every state change in SATC names an actor. That sounds like bookkeeping; it is
actually the load-bearing field in the whole system. A confirmed value is not
"a number that is probably right" — it is *the preparer's own act*, the thing a
regulator relies on, the §1.6695-2(b)(4) record of how information was obtained.
If anything can assert "a human did this" without a human doing it, the record
is worthless.

The previous shape got this exactly backwards::

    def confirm(self, field_id: str, *, by: str = "preparer") -> bool:

``by`` was a caller-supplied string **whose default asserted a human**. Any
in-process caller — a model rung, an API tool, a future MCP write — could
confirm a staged field and have it recorded as the owner's own work, silently.

So:

* :class:`Actor` is a closed set of typed constructors. There is no
  ``Actor(kind="human")`` you can talk your way into from a config string;
  :func:`Actor.owner` is the only way to get a human, and only the app's own
  request path calls it.
* Provenance is **sticky and transitive**. A value a model produced stays
  model-produced through OCR correction, normalisation, and re-extraction. The
  taint follows the *value*, not the reader that happened to touch it last.
* Only a human may confirm, and a model-produced value may never be
  auto-confirmed at any confidence.

This is doctrine rule 6 — *policy lives at the engine choke point, not in
prompts* — applied to the one gate everything else flows through. A refusal
here is an exception, not a log line, because prompt policy holds one run in
three and a Markdown policy document is weaker than a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# What KIND of thing acted. Deliberately small and closed.
ActorKind = Literal["human", "model", "system", "import"]


class ActorRefused(Exception):
    """An actor attempted something its kind is not permitted to do.

    Raised, never returned as a falsy value, so a caller cannot ignore it by
    forgetting to check a boolean. Per doctrine rule 3, the message always names
    what would have been right.
    """


@dataclass(frozen=True, slots=True)
class Actor:
    """Who performed an act. Construct via the classmethods, never by hand.

    Frozen so an actor cannot be mutated into a different kind after a check has
    already passed.
    """

    kind: ActorKind
    name: str
    version: str = ""

    # -- the only ways to make one -------------------------------------------

    @classmethod
    def owner(cls) -> Actor:
        """The practice owner — the single human principal.

        Called only from the app's own request handling, where a real person is
        driving a browser. Nothing reachable from a tool, an API, or a model
        path may call this.
        """
        return cls("human", "owner")

    @classmethod
    def model(cls, name: str, version: str = "") -> Actor:
        """A local language model acting as junior staff. May propose, never accept."""
        if not (name or "").strip():
            raise ValueError("a model actor must name the model")
        return cls("model", name.strip(), version.strip())

    @classmethod
    def system(cls, name: str) -> Actor:
        """A deterministic engine process — intake, rollover, a scheduled sweep.

        Deterministic code is not a human, but it is also not a model: it can be
        read, tested, and proven. It may auto-confirm within the narrow rule
        below (deterministic reads only), which a model may never do.
        """
        return cls("system", (name or "engine").strip())

    @classmethod
    def imported(cls, source: str) -> Actor:
        """Data carried in from outside — a CSV roster, a Drake export."""
        return cls("import", (source or "import").strip())

    # -- what a kind is allowed to do ----------------------------------------

    @property
    def is_human(self) -> bool:
        return self.kind == "human"

    @property
    def is_model(self) -> bool:
        return self.kind == "model"

    @property
    def may_confirm(self) -> bool:
        """Only a human may turn a proposal into a fact.

        Not a style choice. AICPA SSTS §1.4.8 requires that a tool "enhance or
        improve the member's understanding ... not supplant the member's
        professional judgment", and §1.4.4 that using one "does not absolve the
        member of professional obligations". Neither mandates a specific review
        step — so this gate is stated as SATC policy, enforced in code, rather
        than dressed up as a citation it does not have.
        """
        return self.is_human

    @property
    def handle(self) -> str:
        """A stable, PII-free string for the audit record: ``model:qwen3:8b@1``."""
        base = f"{self.kind}:{self.name}"
        return f"{base}@{self.version}" if self.version else base

    def __str__(self) -> str:
        return self.handle


# The system actor that deterministic intake runs as.
INTAKE = Actor.system("intake")


def parse_handle(handle: str) -> Actor:
    """Rebuild an Actor from a stored handle — for READING history only.

    Persistence has to round-trip actors, so this exists. It is deliberately not
    a general constructor: an actor rebuilt from storage describes something
    that already happened. Never pass the result of this function into a gate as
    the actor performing a new act — that is precisely the "caller asserts it
    was a human" hole this module closes.
    """
    text = (handle or "").strip()
    if not text:
        return Actor.system("unknown")
    kind, _, rest = text.partition(":")
    if kind not in ("human", "model", "system", "import"):
        # An unrecognised handle is never upgraded into a human.
        return Actor.system("unknown")
    name, _, version = rest.partition("@")
    return Actor(kind, name or "unknown", version)  # type: ignore[arg-type]


def require_human(actor: Actor, action: str, *, instead: str = "") -> None:
    """Refuse a non-human actor, naming the right next step.

    The choke point itself. Every path that turns a proposal into a fact calls
    this, so the policy holds from the UI, the API, a tool, and anything added
    later — rather than living in a prompt that is obeyed one run in three.
    """
    if actor.may_confirm:
        return
    hint = instead or (
        "propose it instead — staged values are reviewed by the owner at the "
        "confirmation gate, and a proposal that is right is accepted in one click"
    )
    raise ActorRefused(
        f"{actor.handle} may not {action}. Only the practice owner can: a "
        f"confirmed value is recorded as the owner's own act and is relied on as "
        f"evidence. To proceed, {hint}."
    )
