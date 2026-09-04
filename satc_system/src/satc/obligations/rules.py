"""Obligation RULES — dated, cited config describing what is owed and when.

A rule is the portable half of a deadline: "a 1040 is due the 15th day of the
4th month after the tax year ends, and may be extended 6 months on Form 4868."
It carries no dates. Landing a rule on a real period produces an
:class:`~satc.obligations.due_dates.DueDates`, which is where the calendar shift
happens.

Every rule carries its source. Per ``CLAUDE.md`` a tax parameter without a
citation is a bug, and the loader enforces it — a rule with no ``source`` fails
to load rather than quietly becoming folklore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from satc.config import CONFIG_ROOT, ConfigError, read_yaml

ObligationKind = Literal["file", "pay", "furnish", "deposit", "report"]

_KINDS = {"file", "pay", "furnish", "deposit", "report"}
_BASES = {"fiscal_year_end", "fixed", "quarter_end", "installments"}


@dataclass(frozen=True, slots=True)
class Extension:
    """Whether and how an obligation's deadline can be extended.

    ``available: False`` is a real answer, not a missing one — Form 990-N and
    the W-2 furnish duty genuinely cannot be extended, and the UI must be able
    to refuse rather than offer relief that does not exist.
    """

    available: bool = False
    form: str = ""
    months: float = 0.0
    note: str = ""
    condition: str = ""
    """What must be true for the extension to be VALID.

    Load-bearing, not commentary: Massachusetts grants its extensions
    automatically but only if 80% of the liability (or, for corporate excise,
    the greater of 50% of tax or the minimum excise) is paid by the original
    due date. An extension that fails its condition was never an extension, and
    the return is late — so this has to travel with the rule.
    """


@dataclass(frozen=True, slots=True)
class ObligationRule:
    """One duty, as a rule that a period can be landed on."""

    key: str
    kind: ObligationKind
    form: str
    label: str
    due: dict
    source: str
    extension: Extension = field(default_factory=Extension)
    entity_types: tuple[str, ...] = ()
    perfection_days: int = 0
    perfection_source: str = ""
    blocking_docs: tuple[str, ...] = ()
    blocking_source: str = ""
    effective_filing_year: int | None = None
    recurrence: str = ""
    note: str = ""
    jurisdiction: str = "US"

    @property
    def basis(self) -> str:
        return str(self.due.get("basis", ""))

    @property
    def is_extendable(self) -> bool:
        return self.extension.available

    def applies_to_entity(self, entity_type: str) -> bool:
        """Whether this duty can attach to a given entity type.

        An empty ``entity_types`` means "any" — payroll and information-return
        duties depend on what the client *does*, not what it *is*.
        """
        if not self.entity_types:
            return True
        return (entity_type or "").upper() in self.entity_types


def _extension(raw) -> Extension:
    if not isinstance(raw, dict):
        return Extension()
    return Extension(
        available=bool(raw.get("available", False)),
        form=str(raw.get("form", "") or ""),
        months=float(raw.get("months", 0) or 0),
        note=" ".join(str(raw.get("note", "")).split()),
        condition=" ".join(str(raw.get("condition", "")).split()))


def _rule(entry: dict, jurisdiction: str) -> ObligationRule:
    key = str(entry.get("key", "")).strip()
    if not key:
        raise ConfigError(f"An obligation rule has no key: {entry!r}")

    kind = str(entry.get("kind", "")).strip().lower()
    if kind not in _KINDS:
        raise ConfigError(f"Obligation rule {key!r} has an unknown kind: {kind!r}")

    due = entry.get("due")
    if not isinstance(due, dict) or str(due.get("basis", "")) not in _BASES:
        raise ConfigError(f"Obligation rule {key!r} has no usable due basis: {due!r}")

    source = str(entry.get("source", "")).strip()
    if not source:
        # CLAUDE.md: a tax parameter without a citation is a bug. Refuse it here
        # rather than let an uncited deadline reach a real return.
        raise ConfigError(f"Obligation rule {key!r} cites no source")

    ext = _extension(entry.get("extension"))
    if ext.available and not ext.months:
        raise ConfigError(f"Obligation rule {key!r} says extendable but gives no length")

    return ObligationRule(
        key=key, kind=kind, form=str(entry.get("form", "")),  # type: ignore[arg-type]
        label=str(entry.get("label", key)), due=due, source=source, extension=ext,
        entity_types=tuple(str(e).upper() for e in (entry.get("entity_types") or [])),
        perfection_days=int(entry.get("perfection_days", 0) or 0),
        perfection_source=" ".join(str(entry.get("perfection_source", "")).split()),
        blocking_docs=tuple(str(d) for d in (entry.get("blocking_docs") or [])),
        blocking_source=" ".join(str(entry.get("blocking_source", "")).split()),
        effective_filing_year=entry.get("effective_filing_year"),
        recurrence=str(entry.get("recurrence", "")),
        note=" ".join(str(entry.get("note", "")).split()),
        jurisdiction=jurisdiction)


def load_rules(config_root: Path | None = None) -> tuple[ObligationRule, ...]:
    """Read every ``configs/obligations/*.yaml`` file."""
    folder = (config_root or CONFIG_ROOT) / "obligations"
    if not folder.is_dir():
        raise ConfigError(f"Obligation rules folder not found: {folder}")

    out: list[ObligationRule] = []
    for path in sorted(folder.glob("*.yaml")):
        data = read_yaml(path)
        if not isinstance(data, dict):
            raise ConfigError(f"Obligation config must be a mapping: {path}")
        jurisdiction = str((data.get("meta") or {}).get("jurisdiction", "US"))
        for entry in data.get("rules") or []:
            out.append(_rule(entry, jurisdiction))

    if not out:
        raise ConfigError(f"No obligation rules found in {folder}")

    keys = [r.key for r in out]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ConfigError(f"Duplicate obligation rule keys: {sorted(dupes)}")
    return tuple(out)


@lru_cache(maxsize=1)
def _cached_rules() -> tuple[ObligationRule, ...]:
    return load_rules()


def rules() -> tuple[ObligationRule, ...]:
    """The installed rule set (cached — config doesn't change while running)."""
    return _cached_rules()


def rule(key: str) -> ObligationRule:
    for r in rules():
        if r.key == key:
            return r
    raise ConfigError(f"No obligation rule named {key!r}")


def jurisdictions() -> tuple[str, ...]:
    """Every jurisdiction SATC actually holds sourced rules for."""
    seen: list[str] = []
    for r in rules():
        if r.jurisdiction not in seen:
            seen.append(r.jurisdiction)
    return tuple(sorted(seen))


def rules_for_jurisdiction(jurisdiction: str) -> tuple[ObligationRule, ...]:
    """Every rule for a jurisdiction — or a refusal naming what is missing.

    **This function exists to refuse.** The single most dangerous thing a tax
    calendar can do is default an unknown state deadline to the federal one:
    Massachusetts has Patriots' Day, Virginia's extension is automatic with no
    form, and several states diverge on the date itself. Silently answering
    "April 15" for a state whose rules were never sourced produces a confident
    wrong deadline, which is worse than no deadline at all.

    So a jurisdiction with no config raises, and the error names the exact next
    step (doctrine rule 3) rather than saying "not found".
    """
    code = (jurisdiction or "").strip().upper()
    matching = tuple(r for r in rules() if r.jurisdiction.upper() == code)
    if matching:
        return matching
    raise ConfigError(
        f"No obligation rules on file for jurisdiction {code!r}. SATC will not "
        f"fall back to the federal calendar — a state deadline guessed from the "
        f"federal one is a confident wrong answer. Add "
        f"configs/obligations/{code.lower()}.yaml with cited rules. "
        f"Currently sourced: {', '.join(jurisdictions())}.")


def has_jurisdiction(jurisdiction: str) -> bool:
    """Whether rules exist for a jurisdiction — the check before offering it."""
    return (jurisdiction or "").strip().upper() in jurisdictions()


def rules_for_entity(entity_type: str) -> tuple[ObligationRule, ...]:
    """Every rule that could attach to this entity type.

    "Could", not "does": whether a client actually owes a 941 depends on
    whether they run payroll, which is a fact about them, not about their type.
    """
    return tuple(r for r in rules() if r.applies_to_entity(entity_type))
