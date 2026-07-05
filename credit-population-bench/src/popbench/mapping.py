"""Column mapping — auto-propose, then reviewer confirm (never silent).

The bench refuses to guess a column into meaning. On load it *proposes* a
mapping from the file's raw headers to canonical fields (exact normalized-alias
hit first, then a conservative token-overlap fallback), but nothing is applied
until the reviewer confirms/overrides every row. The confirmed mapping — plus
the declared unit/scale for any ambiguous field — is what the engine consumes
and what persists in the ``_map`` tab that travels with the workbook.

This module is pure: it proposes and validates; it does not read/write Excel.
"""

from __future__ import annotations

from dataclasses import dataclass

from popbench import contract


class MappingError(ValueError):
    """A confirmed mapping is structurally invalid (unknown field, missing
    universal field, missing/invalid unit for an ambiguous-scale field)."""

    def __init__(self, message: str, issues: list[str] | None = None):
        super().__init__(message)
        self.issues = issues or [message]


@dataclass(frozen=True)
class Proposal:
    """One proposed header -> canonical mapping, with a confidence signal."""

    header: str
    field_id: str | None       # None => "no confident match, reviewer must decide"
    confidence: str            # "exact" | "partial" | "none"
    needs_unit: bool           # ambiguous-scale field -> reviewer must pick a unit


@dataclass(frozen=True)
class ColumnMap:
    """A confirmed mapping of one raw header to a canonical field."""

    header: str
    field_id: str
    unit: str | None = None    # required iff the field is ambiguous-scale


def _token_overlap(header: str, field: contract.CanonicalField) -> bool:
    """Conservative fallback: does the normalized header contain a full alias
    token (or vice-versa) for this field? Used only when no exact hit exists."""
    h = contract.normalize_header(header)
    for alias in (field.id, *field.aliases):
        a = contract.normalize_header(alias)
        if len(a) >= 4 and (a in h or h in a):
            return True
    return False


def propose(headers: list[str]) -> list[Proposal]:
    """Propose a mapping for each raw header. Deterministic; order preserved.

    A field is proposed to at most one header (the first exact hit wins, then
    the first partial hit) so the reviewer never sees the same canonical field
    claimed twice — collisions are surfaced as "none" for the loser.
    """
    claimed: set[str] = set()
    proposals: list[Proposal] = []

    # Pass 1: exact normalized-alias hits.
    exact: dict[int, str] = {}
    for i, header in enumerate(headers):
        fid = contract.field_for_alias(header)
        if fid is not None and fid not in claimed:
            exact[i] = fid
            claimed.add(fid)

    # Pass 2: token-overlap fallback for the rest.
    for i, header in enumerate(headers):
        if i in exact:
            continue
        for f in contract.all_fields():
            if f.id in claimed:
                continue
            if _token_overlap(header, f):
                exact[i] = f.id
                claimed.add(f.id)
                break

    for i, header in enumerate(headers):
        fid = exact.get(i)
        if fid is None:
            proposals.append(Proposal(header, None, "none", False))
            continue
        confident = contract.field_for_alias(header) == fid
        f = contract.get(fid)
        proposals.append(Proposal(
            header, fid, "exact" if confident else "partial", f.ambiguous_units))
    return proposals


def confirm(columns: list[ColumnMap]) -> "Mapping":
    """Validate reviewer-confirmed column mappings into a usable Mapping.

    Raises MappingError if a field is unknown, a universal field is unmapped, a
    canonical field is mapped twice, or an ambiguous-scale field lacks a valid
    unit. This is the gate that makes "confirm" mean something.
    """
    issues: list[str] = []
    seen_fields: dict[str, str] = {}
    by_field: dict[str, ColumnMap] = {}

    for cm in columns:
        if cm.field_id not in contract._BY_ID:
            issues.append(f"unknown canonical field {cm.field_id!r} (header {cm.header!r})")
            continue
        if cm.field_id in seen_fields:
            issues.append(
                f"canonical field {cm.field_id!r} mapped twice "
                f"({seen_fields[cm.field_id]!r} and {cm.header!r})")
            continue
        seen_fields[cm.field_id] = cm.header
        f = contract.get(cm.field_id)
        if f.ambiguous_units:
            if cm.unit is None:
                issues.append(f"field {cm.field_id!r} needs a unit ({', '.join(f.units)})")
            elif cm.unit not in f.units:
                issues.append(
                    f"field {cm.field_id!r} unit {cm.unit!r} invalid "
                    f"(expected one of {', '.join(f.units)})")
        by_field[cm.field_id] = cm

    for uid in contract.universal_ids():
        if uid not in by_field:
            issues.append(f"universal field {uid!r} is required but unmapped")

    if issues:
        raise MappingError("mapping is invalid: " + "; ".join(issues), issues)
    return Mapping(by_field)


class Mapping:
    """A confirmed, validated mapping. field_id -> ColumnMap."""

    def __init__(self, by_field: dict[str, ColumnMap]):
        self._by_field = dict(by_field)

    def has(self, field_id: str) -> bool:
        return field_id in self._by_field

    def header(self, field_id: str) -> str:
        return self._by_field[field_id].header

    def unit(self, field_id: str) -> str | None:
        return self._by_field[field_id].unit

    @property
    def field_ids(self) -> tuple[str, ...]:
        return tuple(self._by_field)

    def rename_map(self) -> dict[str, str]:
        """raw header -> canonical id, for a DataFrame column rename."""
        return {cm.header: fid for fid, cm in self._by_field.items()}

    def as_rows(self) -> list[tuple[str, str, str]]:
        """(canonical_id, header, unit-or-'') rows for the ``_map`` tab."""
        return [(fid, cm.header, cm.unit or "")
                for fid, cm in self._by_field.items()]
