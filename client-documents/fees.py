"""Turn "how long does this take me" into a fee schedule.

The problem this exists for: the firm has never priced itself, has no past
invoices to read prices off, and cannot answer eighteen questions that each
begin "what do you charge for…". Nobody knows their own prices in the
abstract. They know their own work.

So the questions are re-asked in the one unit a preparer *does* know:

    fee = hours it takes  ×  what an hour of yours is worth

Both numbers are the firm's. This module does the multiplication and nothing
else — it never supplies an hour count, never supplies a rate, and never fills
a blank it was not given. An item left blank stays a `[CONFIRM:` in the output,
so a half-finished session produces a half-priced schedule that still refuses
to render rather than a complete-looking one with invented numbers in it. That
is §9 of the authoring contract: an invented fee figure is worse than a blank.

Rounding is the firm's decision too, and deliberately off by default. "$420.00"
is what 2.4 hours at $175 costs; "$425.00" is a pricing policy, and a policy
invented in a config file is a policy nobody decided.
"""

from __future__ import annotations

import copy
import typing
from pathlib import Path

import yaml

import pricing

ROOT = Path(__file__).resolve().parent
SCHEDULE = ROOT / "registry" / "fee-schedule.yaml"


class FeeBasisError(RuntimeError):
    pass


# Every priced item in the schedule, as (dotted path, what the hours mean).
#
# The wording matters more than it looks. "Hours for a state return" is
# ambiguous — the first one, or each one? Every prompt below says *additional*
# where the amount is incremental, because the arithmetic is only honest if the
# hours mean what the schedule's structure says they mean.
ITEMS: list[tuple[str, str]] = [
    # The individual base is a ladder now, so there is no single "a 1040" to
    # price. Each package is its own figure, and the hours behind them differ
    # by more than the price does -- which is the point of having four.
    ("base.1040.tiers.starter.amount",
     "a Starter return — W-2 income only, standard deduction"),
    ("base.1040.tiers.essentials.amount",
     "an Essentials return — no schedules"),
    ("base.1040.tiers.standard.amount",
     "a Standard return — schedules, but nothing that scales"),
    ("base.1040.tiers.property.amount",
     "a Property & Business return — rentals, or a full Schedule C"),
    ("base.1120S", "a plain Form 1120-S"),
    ("base.1065",  "a plain Form 1065"),
    ("base.1120",  "a plain Form 1120"),
    ("per_unit.state_return.amount", "each state return, on top of the federal"),
    ("per_unit.local_return.amount", "each local return (municipal, RITA, CCA, school district)"),
    ("per_unit.rental.amount",       "each rental property on Schedule E"),
    ("per_unit.k1.amount",           "each K-1 received and entered"),
    ("per_unit.owner_k1.amount",     "each K-1 issued to an owner of an entity"),
    ("per_unit.schedule_c.tiers.simple.amount",
     "a gig-worker Schedule C -- standard mileage, no assets or inventory"),
    ("per_unit.schedule_c.tiers.standard.amount",
     "a Schedule C with actual expenses, a home office, depreciation or inventory"),
    ("per_unit.brokerage.amount",
     "each brokerage statement past the one the package includes"),
    ("per_unit.brokerage_keyed.amount",
     "each brokerage statement that has to be keyed rather than summarised"),
    ("per_unit.foreign_account.amount", "each foreign account reported"),
    ("per_form.amount",
     "any one of the named per-form situations -- one price, whichever it is"),
]

# Cleanup used to be here, in bands. It is not priced any more and cannot be:
# see `assumed:` in the schedule. It is billed hourly beyond a stated
# assumption, at the rate `basis` already carries, so there is nothing for a
# human to set and nothing for derivation to reach.
#
# Brokerage was there too and has come BACK, on 25 August 2026, as two counted
# lines. That is the direction of travel worth noticing: an assumption with an
# hourly consequence is what a firm writes when it has not decided the price.

# Structures rather than amounts: set by hand, never derived from hours. A
# gate says WHICH package a client is in; no number of hours can answer that,
# and `base_covers` says what the base already includes. Anything else that is
# open and not listed in ITEMS is a genuine gap and the tests say so.
NOT_DERIVED = {"base_covers"}
# `.cap_units` is a COUNT, not an amount: how many of a thing the firm is
# willing to charge for before the line stops climbing. No number of hours can
# answer that -- it is a judgement about what a client should be asked to pay,
# which is the same reason a gate is not derivable either.
NOT_DERIVED_SUFFIXES = (".gate", ".cap_units")


def is_derivable(path: str) -> bool:
    """Is this open value one that hours could ever answer?"""
    return (path not in NOT_DERIVED
            and not path.endswith(NOT_DERIVED_SUFFIXES))


def _dig(node: dict, path: str):
    cur = node
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise FeeBasisError(
                f"the fee schedule has no {path!r}. Its shape and this module's "
                f"ITEMS list have drifted apart; one of them is wrong."
            )
        cur = cur[part]
    return cur


def _plant(node: dict, path: str, value) -> None:
    parts = path.split(".")
    cur = node
    for part in parts[:-1]:
        cur = cur[part]
    cur[parts[-1]] = value


def round_to(amount: float, increment: float) -> float:
    """Round up to the firm's increment. Off unless asked for."""
    if not increment:
        return amount
    return -(-amount // increment) * increment


def derive(rate, hours: dict[str, float], *, increment: float = 0,
           base_covers: str | None = None,
           schedule: dict | None = None) -> dict:
    """`hours` keyed by the paths in ITEMS -> a fee schedule.

    Anything absent from `hours` keeps whatever the source schedule had, which
    for the firm's real one is a `[CONFIRM:`. Partial input is expected: the
    firm may know what a 1040 takes and genuinely not know what heavy cleanup
    takes, and guessing the second to fill the file out would be the whole
    failure mode this project is built against.
    """
    out = copy.deepcopy(schedule if schedule is not None else pricing.load())

    if base_covers is not None:
        if base_covers not in ("federal_only", "one_included"):
            raise FeeBasisError(
                f"base_covers is {base_covers!r}; it is 'federal_only' or "
                f"'one_included'. It decides whether the first state is already "
                f"paid for, so it cannot be guessed."
            )
        out["base_covers"] = base_covers

    known = {p for p, _ in ITEMS}
    stray = set(hours) - known
    if stray:
        raise FeeBasisError(
            f"nothing in the fee schedule is priced by {', '.join(sorted(stray))}. "
            f"Run `price --list` for the paths this accepts."
        )

    if rate is None:
        if hours:
            raise FeeBasisError("hours were given with no hourly rate to multiply them by.")
        return out

    try:
        rate = float(rate)
    except (TypeError, ValueError):
        raise FeeBasisError(f"the hourly rate {rate!r} is not a number.")
    if rate <= 0:
        raise FeeBasisError(f"the hourly rate is {rate}. An hour is worth something.")

    for path, h in hours.items():
        if h is None:
            continue
        try:
            h = float(h)
        except (TypeError, ValueError):
            raise FeeBasisError(f"hours for {path} are {h!r}, which is not a number.")
        if h < 0:
            raise FeeBasisError(f"hours for {path} are negative.")
        _plant(out, path, round(round_to(h * rate, increment), 2))

    return out


# ── the other direction: what a price buys ────────────────────────────────
#
# `derive` turns hours into prices, for a firm that knows its own work and not
# its own prices. This turns prices back into hours, which is the question that
# actually comes up once the prices exist: *how long have I got*.
#
# The two are not a round trip and are not meant to be. `derive` takes an
# estimate of effort and produces a price; this takes a price — whatever its
# provenance, and the firm's real ones came off a workbook, not off a stopwatch
# — and produces the budget that price implies at the target rate.


class Budget(typing.NamedTuple):
    """What one priced line buys, in hours."""

    raw: float          # amount / rate, unrounded — the honest number
    hours: float        # raw, rounded to the unit time is booked in
    under_floor: bool   # raw is less than the firm's minimum billing increment

    def __str__(self) -> str:
        return f"{self.hours:.2f} h" + (" (under floor)" if self.under_floor else "")


def basis_of(schedule: dict) -> tuple[float, float, float]:
    """`(rate, round_time_to, minimum_increment)` from the schedule's own basis.

    Read from the file rather than passed in: a budget that depended on what
    the caller happened to type would not be an expectation, it would be an
    opinion held once. Every caller gets the same rate the firm set.
    """
    basis = schedule.get("basis") or {}
    rate = basis.get("rate")
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise FeeBasisError(
            "the fee schedule has no usable `basis.rate`, so no price in it "
            "implies an hour budget. Set it in registry/fee-schedule.yaml."
        )
    step = basis.get("round_time_to") or 0.25
    floor = basis.get("minimum_increment") or 0.0
    return float(rate), float(step), float(floor)


def hours_for(amount, rate: float, *, step: float = 0.25,
              floor: float = 0.25) -> Budget:
    """The hours `amount` buys at `rate`.

    Rounded to the NEAREST step, not up: the budget is what the price supports,
    and rounding it up would quietly hand back time the price never paid for.
    The floor is reported, never applied — a $5 line does not become a $37.50
    line because the firm has a fifteen-minute minimum; it becomes a line worth
    asking about.
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise FeeBasisError(f"{amount!r} is not an amount, so it buys no hours.")
    if amount < 0:
        raise FeeBasisError(f"the amount is {amount}; a negative price buys nothing.")
    raw = amount / rate
    hours = round(raw / step) * step if step else raw
    return Budget(raw=raw, hours=round(hours, 4), under_floor=raw < floor)


def expected_hours(schedule: dict | None = None) -> dict[str, Budget]:
    """Every priced line in the schedule -> the budget it implies.

    Lines still carrying a `[CONFIRM:` are absent rather than zero. A schedule
    that is half-priced yields half a budget, which is the truth about it.
    """
    schedule = pricing.load() if schedule is None else schedule
    rate, step, floor = basis_of(schedule)
    out: dict[str, Budget] = {}
    for path, _ in ITEMS:
        try:
            amount = _dig(schedule, path)
        except FeeBasisError:
            continue
        if isinstance(amount, (int, float)):
            out[path] = hours_for(amount, rate, step=step, floor=floor)
    return out


def still_open(schedule: dict) -> list[tuple[str, str]]:
    """What derivation did not reach. Same shape as `pricing.open_amounts`."""
    return pricing.open_amounts(schedule)


def dump(schedule: dict) -> str:
    return yaml.safe_dump(schedule, sort_keys=False, allow_unicode=True,
                          default_flow_style=False)


# ── writing back ──────────────────────────────────────────────────────────
#
# `fee-schedule.yaml` is two thirds comment, and the comments are the part that
# makes it fillable by hand: what `base_covers` means, why `none` is a real
# zero, why there is no hourly rate on the estimate. Dumping the parsed dict
# back over it would produce a valid file that had lost all of that.
#
# So the write is surgical: each amount is swapped for its number on the line it
# already occupies, and nothing else in the file is touched.


def _sub_once(text: str, needle: str, value: str, path: str) -> str:
    """Swap one value, refusing anything ambiguous."""
    for quoted in (f'"{needle}"', f"'{needle}'", needle):
        n = text.count(quoted)
        if n == 1:
            return text.replace(quoted, value, 1)
        if n > 1:
            raise FeeBasisError(
                f"{path}: its current value appears {n} times in the file, so "
                f"replacing it in place could edit the wrong line. Write to a "
                f"new path instead and merge it by hand."
            )
    raise FeeBasisError(
        f"{path}: could not find its current value in the file to replace. "
        f"The file has been edited into a shape this cannot rewrite safely; "
        f"write to a new path instead."
    )


def _literal(value) -> str:
    """A number as YAML. Trailing `.0` dropped -- `450`, not `450.0`."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def apply_to_text(text: str, before: dict, after: dict) -> str:
    """Re-write only the values that changed, leaving comments and layout be."""
    for path in ["base_covers"] + [p for p, _ in ITEMS]:
        old, new = _dig(before, path), _dig(after, path)
        if old == new:
            continue
        text = _sub_once(text, str(old),
                         new if path == "base_covers" else _literal(new), path)
    return text
