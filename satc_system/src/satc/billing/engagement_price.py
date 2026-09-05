"""The price the client was actually quoted, read from the engagement record.

**THE PRACTICE HAD TWO PRICE LISTS AND THEY DISAGREED BY 55%.** Priced on
identical facts on 4 September 2026, `client-documents` said $645 from its
package ladder and this catalogue totalled $1,005 from its per-service rates.
Nothing in either repository said which was the firm's price, and the firm's own
operating procedure had already named the danger: *"the one the client keeps is
the one that says the larger number."*

They were never two numbers for one service. They are two pricing **models**.
The ladder bundles — a `starter` 1040 at $100 covers the federal return, the
first state, the first local and the standard deduction, with additions priced
on top. The catalogue itemises: a 1040 at $450 standing alone, whatever its
complexity. The two were never comparable, which is exactly why nobody caught
it.

**The firm settled ownership on 4 September 2026** — *"client-documents owns the
engagement; satc_system holds the return"* — and the price the next day:
*"Show the engagement price via the ref."*

So this module does not price anything. It **reads** what the client was
already quoted, through the `engagement_ref` recorded on the engagement, and the
quote engine shows that figure instead of inventing a second one. The ref is the
seam, and it is the same seam `collect` resolves a drop folder on.

WHY A READER AND NOT A PORT. Reimplementing the ladder here — tiers, gates,
`per_unit`, what the base covers — would recreate the exact problem it is meant
to end: two implementations of one price, drifting from the day the second was
written. The figure a client holds is the one on their estimate, so that is the
one to read.

SILENCE IS AN ANSWER. No ref recorded, no store configured, no record on disk,
no figure in the record: each returns `None` with a reason a person can act on,
never a zero and never a guess. A quote that says "$0.00" when it means "nobody
has priced this" is the confident wrong answer this system is built against.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

#: Where `client-documents` keeps its engagements. The same variable
#: `client-documents/web.py` reads, so one export scopes both applications --
#: and a scratch store points them at the same scratch.
ENGAGEMENTS_ENV = "SATC_ENGAGEMENTS"


@dataclass(frozen=True, slots=True)
class EngagementPrice:
    """What the client was quoted, as their own paperwork states it."""

    ref: str
    total: str
    """As WRITTEN, not re-formatted. `"$645.00"` is what is on the estimate the
    client is holding; re-deriving it from a float here would be a second
    rendering of the same money and the two would eventually disagree."""

    lines: tuple[tuple[str, str], ...] = ()
    source: Path | None = None

    @property
    def is_priced(self) -> bool:
        return bool(self.total.strip())


@dataclass(frozen=True, slots=True)
class NoPrice:
    """Why there is no figure, in words a preparer can act on.

    Carries `next_step` for the same reason every refusal in this codebase
    does: an error that does not say what would have worked is an error people
    route around.
    """

    reason: str
    next_step: str = ""

    is_priced: bool = False


def engagements_root(root: Path | str | None = None) -> Path | None:
    """Where the engagement records live, or None if nothing says.

    Explicit argument beats the environment; there is deliberately no built-in
    default path. `satc_system` and `client-documents` are separate
    applications that happen to share a machine, and guessing at a sibling
    directory would work on this box and silently fail on any other.
    """
    if root:
        return Path(root)
    named = os.environ.get(ENGAGEMENTS_ENV)
    return Path(named) if named else None


def price_for_ref(ref: str, *, root: Path | str | None = None):
    """The quoted price for an engagement ref, or a `NoPrice` saying why not.

    Never raises on a missing or malformed record. A quote screen that crashes
    because a JSON file somewhere else is half-written is worse than one that
    says the figure could not be read.
    """
    ref = (ref or "").strip()
    if not ref:
        return NoPrice(
            "no engagement ref is recorded on this engagement",
            "record it in the Engagement ref box on the engagement screen, and "
            "the price the client was quoted will show here")

    store = engagements_root(root)
    if store is None:
        return NoPrice(
            f"engagement {ref} carries the price, and this machine has not "
            f"been told where the engagement records are",
            f"set {ENGAGEMENTS_ENV} to the client-documents engagements "
            f"directory")

    path = Path(store) / ref / "record.json"
    if not path.exists():
        return NoPrice(
            f"no record for engagement {ref} at {path}",
            "check the ref, or check that this is the right engagements store")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return NoPrice(f"engagement {ref} could not be read: {exc}",
                       "the record is missing or not valid JSON")
    if not isinstance(raw, dict):
        return NoPrice(f"engagement {ref} is not a record",
                       "the file holds something other than an object")

    # `EstimateTotal` first: it is what the ESTIMATE said, which is the figure
    # the client agreed to. `Total` is what a later invoice settled at, and the
    # two are allowed to differ -- a requote is a real event. A quote screen is
    # about what was agreed, so the estimate wins where both exist.
    total = ""
    for field in ("EstimateTotal", "Total", "Subtotal"):
        value = str(raw.get(field, "") or "").strip()
        if value:
            total = value
            break
    if not total:
        return NoPrice(
            f"engagement {ref} exists but carries no priced figure",
            "price it in client-documents; an engagement with no estimate has "
            "not been quoted yet")

    lines: list[tuple[str, str]] = []
    for item in raw.get("LineItems") or ():
        if not isinstance(item, dict):
            continue
        label = str(item.get("Service") or item.get("label") or "").strip()
        amount = str(item.get("Amount") or item.get("amount") or "").strip()
        if label:
            lines.append((label, amount))

    return EngagementPrice(ref=ref, total=total, lines=tuple(lines),
                           source=path)
