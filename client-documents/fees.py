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
    ("base.1040",  "a plain Form 1040 — start to filed, no states, no schedules"),
    ("base.1120S", "a plain Form 1120-S"),
    ("base.1065",  "a plain Form 1065"),
    ("base.1120",  "a plain Form 1120"),
    ("per_unit.state_return.amount", "each state return, on top of the federal"),
    ("per_unit.local_return.amount", "each local return (municipal, RITA, CCA, school district)"),
    ("per_unit.rental.amount",       "each rental property on Schedule E"),
    ("per_unit.k1.amount",           "each K-1 received and entered"),
    ("per_unit.owner_k1.amount",     "each K-1 issued to an owner of an entity"),
    ("per_unit.schedule_c.amount",   "each Schedule C business"),
    ("bands.brokerage.values.light.amount",  "a handful of brokerage transactions"),
    ("bands.brokerage.values.medium.amount", "a consolidated 1099-B, moderate activity"),
    ("bands.brokerage.values.heavy.amount",  "high-volume brokerage, or multiple brokers"),
    ("bands.cleanup.values.light.amount",    "light records cleanup before the return can start"),
    ("bands.cleanup.values.heavy.amount",    "substantial reconstruction of the records"),
]

# `none` bands are a real zero, not a placeholder, and `base_covers` is a
# structure rather than an amount. Neither is derived from hours.
NOT_DERIVED = {"bands.brokerage.values.none.amount",
               "bands.cleanup.values.none.amount",
               "base_covers"}


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
