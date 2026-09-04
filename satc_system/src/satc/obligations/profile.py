"""OBLIGATION PROFILE — the facts about a client that generate duties.

The goal of this whole area is that **nobody ever has to remember to create
work**. That only works if the system knows enough about a client to derive what
they owe::

    client facts (this module)
        x obligation rules (dated, cited config)
        -> obligation instances (materialised per period)
        -> jobs -> tasks

So a profile is not a settings screen. It is the answer to "what duties does
this client have, and how do we know?" — and every answer carries where it came
from.

**Facts are recorded, never inferred.** The temptation is to guess: they filed a
941 last year, so they still run payroll; they have a Massachusetts address, so
they file there. Both guesses generate confident wrong work. The clearest case
is payroll filing frequency — whether an employer files Form 941 quarterly or
Form 944 annually is *assigned by the IRS in writing*, not chosen and not
derivable from what they filed before. So :class:`ProfileFact` carries a source,
and a fact with no source is visibly unsourced rather than quietly authoritative.

The one thing without which nothing works is ``fiscal_year_end``: no due date
can be computed at all until a client's year-end is known.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from satc.config import ConfigError
from satc.obligations.due_dates import Period, month_period, quarter, tax_year
from satc.obligations.rules import ObligationRule, has_jurisdiction, rules

# How often a recurring duty comes round. Drives which periods get materialised.
Recurrence = Literal["annual", "quarterly", "monthly", "none"]

# How sure we are a fact is true — and therefore whether work built on it is safe.
FactBasis = Literal[
    "stated_by_client",     # they told us
    "agency_notice",        # an IRS/state letter says so (the strongest)
    "prior_filing",         # we filed it this way before
    "observed_document",    # a document on file implies it
    "assumed_default",      # nothing told us; this is a default and is FLAGGED
]


@dataclass(frozen=True, slots=True)
class ProfileFact:
    """One fact about a client, with where it came from.

    ``basis`` is not decoration. An obligation generated from an
    ``assumed_default`` is a guess wearing a deadline, and the queue must be able
    to say so.
    """

    value: str
    basis: FactBasis = "assumed_default"
    source: str = ""
    as_of: date | None = None

    @property
    def is_assumed(self) -> bool:
        return self.basis == "assumed_default"

    def __str__(self) -> str:
        return self.value


@dataclass(slots=True)
class ObligationProfile:
    """What a client owes, expressed as facts rather than as a list of duties.

    The duties themselves are derived (:func:`materialise`), so adding a rule to
    config gives every matching client that duty without anyone editing a
    client record.
    """

    client_id: str
    entity_type: str = "INDIVIDUAL"
    fiscal_year_end: date | None = None
    """Year-end. ``None`` means calendar year — the overwhelmingly common case.

    Without this no date in the system can be computed for a fiscal-year filer,
    which is why it sits at the top of the profile rather than in an advanced tab.
    """

    jurisdictions: tuple[str, ...] = ("US",)
    """Where they file. A jurisdiction with no sourced rules is REFUSED at
    materialisation rather than silently defaulted to the federal calendar."""

    runs_payroll: ProfileFact | None = None
    payroll_form: ProfileFact | None = None
    """``941`` (quarterly) or ``944`` (annual) — IRS-ASSIGNED BY WRITTEN NOTICE.
    Never inferred from what they filed last year; store the notice as its source."""

    sales_tax_frequency: ProfileFact | None = None
    """monthly / quarterly / annual. In Massachusetts this is set by PRIOR-YEAR
    LIABILITY (<=$100 annual, $101-1,200 quarterly, >$1,200 monthly) and is
    re-checked each year — so it is a dated fact, not a preference."""

    files_1099s: ProfileFact | None = None
    pays_estimates: ProfileFact | None = None
    notes: str = ""

    # -- derived -------------------------------------------------------------

    def year_end_for(self, year: int) -> date:
        return self.fiscal_year_end or date(year, 12, 31)

    def period_for(self, year: int) -> Period:
        return tax_year(year, fiscal_year_end=self.fiscal_year_end)

    def assumed_facts(self) -> list[tuple[str, ProfileFact]]:
        """Every fact nobody actually told us — what the queue must flag."""
        out = []
        for name in ("runs_payroll", "payroll_form", "sales_tax_frequency",
                     "files_1099s", "pays_estimates"):
            fact = getattr(self, name)
            if fact is not None and fact.is_assumed:
                out.append((name, fact))
        return out

    def wants(self, rule: ObligationRule) -> bool:
        """Whether this client actually owes a given duty.

        Entity type is necessary but not sufficient. A duty whose rule names no
        entity types depends on what the client *does* — payroll, sales, paying
        contractors — and is only owed when a fact says so. Absent that fact the
        answer is NO: inventing a payroll obligation for someone with no
        employees fills the queue with work that does not exist.
        """
        if rule.jurisdiction not in self.jurisdictions:
            return False
        if not rule.applies_to_entity(self.entity_type):
            return False

        form = (rule.form or "").upper()
        if form in ("941", "944"):
            if self.runs_payroll is None or self.runs_payroll.value != "yes":
                return False
            chosen = self.payroll_form.value if self.payroll_form else "941"
            return form == chosen.upper()
        if form in ("W-2",):
            return self.runs_payroll is not None and self.runs_payroll.value == "yes"
        if form in ("1099-NEC",):
            return self.files_1099s is not None and self.files_1099s.value == "yes"
        if rule.kind == "pay" and "ES" in form:
            return self.pays_estimates is not None and self.pays_estimates.value == "yes"
        if form in ("ST-9", "MEALS"):
            freq = self.sales_tax_frequency.value if self.sales_tax_frequency else ""
            if not freq:
                return False
            return (rule.recurrence or "").lower() == freq.lower()
        return True


@dataclass(frozen=True, slots=True)
class ObligationInstance:
    """A duty materialised for one period — the thing a job discharges.

    ``obligation_key`` is the IDEMPOTENCE KEY for the whole recurring model
    (doctrine rule 4). Re-running materialisation for a period must find the
    same instance, not mint a second one: "already exists as requested" is
    success, never a conflict.
    """

    obligation_key: str
    client_id: str
    rule_key: str
    kind: str
    form: str
    jurisdiction: str
    period_key: str
    statutory_due: date
    due: date
    shift_reason: str = ""
    extended_due: date | None = None
    extension_form: str = ""
    extension_condition: str = ""
    documents_due: date | None = None
    blocking_docs: tuple[str, ...] = ()
    from_assumed_facts: tuple[str, ...] = ()
    """Profile facts behind this duty that nobody actually confirmed.

    An obligation derived from an assumption is a guess wearing a deadline. The
    queue shows it, but says so.
    """

    @property
    def is_assumed(self) -> bool:
        return bool(self.from_assumed_facts)

    def days_until(self, today: date, *, extended: bool = False) -> int:
        target = self.extended_due if (extended and self.extended_due) else self.due
        return (target - today).days


def obligation_key(client_id: str, kind: str, form: str, jurisdiction: str,
                   period_key: str) -> str:
    """The composite identity of a duty: one taxpayer, one duty, one period.

    Note it keys on ``period_key`` and NOT on tax year — a tax year cannot
    express a payroll quarter (``2026Q1``) or a monthly sales-tax period
    (``2026-03``), and a key that cannot express them cannot deduplicate them.
    """
    parts = [client_id, kind, form.replace(" ", ""), jurisdiction, period_key]
    return "/".join(p.strip() for p in parts if p is not None)


def _periods_for(rule: ObligationRule, profile: ObligationProfile,
                 year: int) -> list[Period]:
    """Which periods of ``year`` this rule generates."""
    recurrence = (rule.recurrence or "").lower()
    if recurrence == "quarterly" or rule.basis == "quarter_end":
        return [quarter(year, q) for q in (1, 2, 3, 4)]
    if recurrence == "monthly":
        return [month_period(year, m) for m in range(1, 13)]
    return [profile.period_for(year)]


def materialise(profile: ObligationProfile, year: int) -> list[ObligationInstance]:
    """Every duty this client owes for a year, with its dates computed.

    Deterministic and idempotent: same profile + same year gives the same
    instances with the same keys, so re-running is safe and cheap.
    """
    from satc.obligations.due_dates import compute, installment_due_dates

    for juris in profile.jurisdictions:
        if not has_jurisdiction(juris):
            raise ConfigError(
                f"Client {profile.client_id} is marked as filing in {juris!r}, but no "
                f"obligation rules are on file for it. SATC will not fall back to the "
                f"federal calendar. Add configs/obligations/{juris.lower()}.yaml with "
                f"cited rules, or remove {juris!r} from the client's jurisdictions.")

    assumed = tuple(name for name, _ in profile.assumed_facts())
    out: list[ObligationInstance] = []

    for rule in rules():
        if not profile.wants(rule):
            continue
        for period in _periods_for(rule, profile, year):
            dues = (installment_due_dates(rule, period)
                    if rule.basis == "installments" else [compute(rule, period)])
            for d in dues:
                out.append(ObligationInstance(
                    obligation_key=obligation_key(
                        profile.client_id, rule.kind, rule.form,
                        rule.jurisdiction, d.period_key),
                    client_id=profile.client_id, rule_key=rule.key, kind=rule.kind,
                    form=rule.form, jurisdiction=rule.jurisdiction,
                    period_key=d.period_key,
                    statutory_due=d.statutory, due=d.due, shift_reason=d.shift_reason,
                    extended_due=d.extended_due, extension_form=d.extension_form,
                    extension_condition=rule.extension.condition,
                    documents_due=d.documents_due,
                    blocking_docs=rule.blocking_docs,
                    from_assumed_facts=assumed if rule.entity_types == () else ()))

    out.sort(key=lambda o: (o.due, o.jurisdiction, o.form))
    return out


def merge(existing: list[ObligationInstance],
          fresh: list[ObligationInstance]) -> tuple[list[ObligationInstance], int]:
    """Fold newly-materialised duties into what is already on file.

    Doctrine rule 4: re-materialising a period is SUCCESS, not a conflict. An
    instance whose key already exists is left alone — its job may have progress
    against it — and only genuinely new keys are added. Returns the merged list
    and the count actually added.
    """
    by_key = {o.obligation_key: o for o in existing}
    added = 0
    for instance in fresh:
        if instance.obligation_key not in by_key:
            by_key[instance.obligation_key] = instance
            added += 1
    merged = sorted(by_key.values(), key=lambda o: (o.due, o.jurisdiction, o.form))
    return merged, added
