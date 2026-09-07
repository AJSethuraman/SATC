"""FIRM POLICY — the owner's own dates, kept strictly apart from the law.

A tax practice runs on two kinds of date that look identical on a screen and
are nothing alike underneath. A statutory deadline is computed from a cited
rule and cannot be argued with. A firm cutoff — *"documents to us by March 1 or
we extend"* — is a preference the owner can change over coffee.

The operating model's blunt finding: these *"must be visually distinguishable
from law so nobody mistakes one for the other."* So they live in a different
file (``configs/firm_policy.yaml``, outside ``configs/obligations/``), load
through a different function, and everything derived from them is flagged
:attr:`~satc.obligations.due_dates.DueDates.documents_due_is_firm_policy`.

Nothing here carries a citation, because nothing here has an authority behind
it. That is the point — the statutory loader *refuses* an uncited rule; this
one requires no citation at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from satc.config import CONFIG_ROOT, ConfigError, read_yaml

POLICY_FILE = "firm_policy.yaml"

# Used when the practice has set no alerting preference at all.
_DEFAULT_APPROACHING_DAYS = 30
_DEFAULT_URGENT_DAYS = 7


@dataclass(frozen=True, slots=True)
class FirmPolicy:
    """The owner's dates and thresholds. No citations, by design."""

    cutoffs: dict[str, tuple[int, int]] = field(default_factory=dict)
    approaching_days: int = _DEFAULT_APPROACHING_DAYS
    urgent_days: int = _DEFAULT_URGENT_DAYS
    standing_text: dict[str, str] = field(default_factory=dict)
    """Wording identical for every client — how the firm says a thing.

    Not a fact about anyone, so it cannot be wrong about anyone. Written once
    here instead of asked for on every draft."""

    def cutoff_for(self, rule_key: str, deadline: date) -> date | None:
        """The document cutoff preceding a deadline, or ``None`` if unset.

        A fixed month/day, resolved into the same year as the deadline. Not
        shifted off weekends: a cutoff is a request to a client, not an act with
        legal consequence.
        """
        md = self.cutoffs.get(rule_key)
        if md is None:
            return None
        month, day = md
        try:
            cutoff = date(deadline.year, month, day)
        except ValueError as exc:
            raise ConfigError(
                f"Firm cutoff for {rule_key!r} is not a real date "
                f"(month {month}, day {day}): {exc}") from None
        if cutoff >= deadline:
            # A cutoff on or after the deadline is meaningless — it would mean
            # asking for documents after the return was due. Name the fix.
            raise ConfigError(
                f"Firm cutoff for {rule_key!r} ({cutoff}) is not before the "
                f"deadline it precedes ({deadline}). Move it earlier in "
                f"configs/{POLICY_FILE}.")
        return cutoff


def load_policy(config_root: Path | None = None) -> FirmPolicy:
    """Read ``configs/firm_policy.yaml``. A missing file means "no preferences"."""
    path = (config_root or CONFIG_ROOT) / POLICY_FILE
    if not path.exists():
        return FirmPolicy()

    data = read_yaml(path)
    if not isinstance(data, dict):
        raise ConfigError(f"Firm policy must be a mapping: {path}")

    cutoffs: dict[str, tuple[int, int]] = {}
    for key, spec in (data.get("cutoffs") or {}).items():
        if not isinstance(spec, dict) or "month" not in spec or "day" not in spec:
            raise ConfigError(f"Firm cutoff {key!r} needs a month and a day: {spec!r}")
        cutoffs[str(key)] = (int(spec["month"]), int(spec["day"]))

    alerts = data.get("alerts") or {}
    return FirmPolicy(
        cutoffs=cutoffs,
        approaching_days=int(alerts.get("approaching_days", _DEFAULT_APPROACHING_DAYS)),
        urgent_days=int(alerts.get("urgent_days", _DEFAULT_URGENT_DAYS)),
        standing_text={str(k): " ".join(str(v).split())
                       for k, v in (data.get("standing_text") or {}).items()})


@lru_cache(maxsize=1)
def _cached_policy() -> FirmPolicy:
    return load_policy()


def policy() -> FirmPolicy:
    """The installed firm policy (cached — config doesn't change while running)."""
    return _cached_policy()
