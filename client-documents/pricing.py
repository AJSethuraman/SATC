"""Interview counts + fee schedule -> the estimate's line items and total.

The seam the pipeline was missing. The interview collected `count_states`,
`count_k1s` and the rest and nothing turned them into money, so `LineItems` and
`EstimateTotal` stayed unfilled and the fee estimate could not render.

**An unpriced item does not become zero.** Every amount in `fee-schedule.yaml`
is a `[CONFIRM:` until the firm sets it, and a `[CONFIRM:` is carried through to
the line and to the total rather than skipped or defaulted. The estimate then
refuses to render, which is the correct outcome: quoting a client $0 for a
service is worse than quoting nothing at all.
"""

from __future__ import annotations

from pathlib import Path

import yaml

import money as m

ROOT = Path(__file__).resolve().parent
SCHEDULE = ROOT / "registry" / "fee-schedule.yaml"


class PricingError(RuntimeError):
    pass


def load(path: Path | str = SCHEDULE) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def is_open(value) -> bool:
    """Is this an amount nobody has set?"""
    return isinstance(value, str) and "[CONFIRM:" in value


def open_amounts(schedule: dict | None = None) -> list[tuple[str, str]]:
    """Every unset amount, as (path, question). What `doctor` reports."""
    s = schedule if schedule is not None else load()
    found: list[tuple[str, str]] = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif is_open(node):
            q = node.split("[CONFIRM:", 1)[1].rsplit("]", 1)[0].strip()
            found.append((path, q))

    walk(s, "")
    return found


def _line(service: str, detail: str, amount, code: str) -> dict:
    return {"Service": service, "Detail": detail,
            "Amount": m.money(amount, code), "_raw": amount}


def _resolve_tier(unit: dict, answers: dict) -> dict:
    """A tiered item, reduced to the flat one its answer selects.

    Returns the unit unchanged when it has no tiers, so every caller downstream
    sees one shape. An unanswered `tier_from` is NOT a default: which tier the
    client is in changes the price, and picking the cheapest to keep the
    estimate rendering would quote a business return at a gig-worker fee. It
    carries the question instead, and the `[CONFIRM:` stops the render -- the
    same way an unpriced line does.
    """
    tiers = unit.get("tiers")
    if not tiers:
        return unit
    key = unit.get("tier_from")
    if not key:
        raise PricingError(
            f"{unit.get('label', 'an item')!r} has tiers but no `tier_from`, so "
            f"nothing says which one applies. Name the interview answer."
        )
    chosen = answers.get(key)
    if chosen is None or chosen == "":
        return {**unit, "label": unit.get("label", key),
                "detail": "", "amount":
                f"[CONFIRM: the interview did not answer {key!r}, so the tier "
                f"is unknown. One of: {', '.join(sorted(tiers))}.]"}
    if chosen not in tiers:
        raise PricingError(
            f"{key} = {chosen!r} is not a tier of {unit.get('count_from')!r}. "
            f"Known tiers: {', '.join(sorted(tiers))}."
        )
    tier = tiers[chosen]
    for field in ("label", "detail", "amount"):
        if field not in tier:
            raise PricingError(
                f"tier {chosen!r} is missing {field!r}. A tier supplies the "
                f"whole line, so a missing field would print blank."
            )
    return {**unit, **tier}


# ── deriving the package ──────────────────────────────────────────────────

_GATE_OPS = ("schedules_none", "schedules_any", "schedules_none_of",
             "answer_is", "any_of")


def _schedules(answers: dict) -> set:
    raw = answers.get("federal_schedules") or []
    if isinstance(raw, str):
        raw = [s.strip() for s in raw.split(",") if s.strip()]
    return set(raw)


def _gate_holds(gate, answers: dict, where: str) -> bool:
    """Does one gate hold for this client? Every operator in it must.

    Gates key on what is ON the return, never on how many of something there
    is. A count can be blank when the thing exists -- a client ticks the
    rentals schedule and leaves the number for later -- and a gate that reads
    that as zero sends a landlord to the cheapest package.
    """
    if not isinstance(gate, dict):
        raise PricingError(
            f"{where}: a gate must be a mapping of conditions, got "
            f"{type(gate).__name__}. An unreadable gate cannot be allowed to "
            f"quietly never match."
        )
    unknown = set(gate) - set(_GATE_OPS)
    if unknown:
        raise PricingError(
            f"{where}: unknown gate condition(s) {sorted(unknown)}. Known: "
            f"{sorted(_GATE_OPS)}. A misspelled condition would never hold, "
            f"and a package that can never be selected is invisible."
        )
    have = _schedules(answers)
    for op, val in gate.items():
        if op == "schedules_none":
            if bool(val) != (not have):
                return False
        elif op == "schedules_any":
            if not (have & set(val)):
                return False
        elif op == "schedules_none_of":
            if have & set(val):
                return False
        elif op == "answer_is":
            for q, expected in val.items():
                if answers.get(q) != expected:
                    return False
        elif op == "any_of":
            if not any(_gate_holds(sub, answers, f"{where}.any_of")
                       for sub in val):
                return False
    return True


def _unit_price(schedule: dict, count_from: str, answers: dict | None = None):
    """What one of a counted thing costs to THIS client, or None.

    None means "cannot be compared": either nothing prices it, the price is
    still open, or it is tiered and the interview has not said which tier.
    A tiered unit is read directly rather than through `_resolve_tier`, which
    raises when the tier question is unanswered -- correct when a line is
    being priced, wrong here, where the caller only wants to know whether a
    comparison is possible at all.
    """
    answers = answers or {}
    for unit in (schedule.get("per_unit") or {}).values():
        if unit.get("count_from") != count_from:
            continue
        amount = unit.get("amount")
        if unit.get("tiers"):
            chosen = answers.get(unit.get("tier_from"))
            tier = (unit["tiers"] or {}).get(chosen)
            amount = tier.get("amount") if isinstance(tier, dict) else None
        return None if amount is None or is_open(amount) else amount
    return None


def _allowance(tier: dict, answers: dict, schedule: dict | None = None) -> dict:
    """How many of each counted thing this package already covers.

    `allows` is flat and always applies. `allows_one_of` is the either/or --
    three rentals OR one full Schedule C, not both -- and the branch worth
    most to the CLIENT is the one applied, because a client must never lose
    money to an ambiguity in our own schedule.

    Branches are compared in money, which is the right comparator and the one
    that fails quietly: a branch whose price is not set yet scores zero,
    which is indistinguishable from a branch worth nothing, so the choice
    silently falls to file order. That is not a hypothetical -- with both
    prices open, a client with one full Schedule C and no rentals had the
    RENTALS branch applied and their Schedule C billed on top of a package
    that said it covered it. So when a branch the client actually uses has no
    price, no choice is made and the allowance carries the question instead.
    A branch the client has no units in cannot change the answer and is not
    grounds to refuse.
    """
    out = dict(tier.get("allows") or {})
    branches = tier.get("allows_one_of") or []
    if not branches:
        return out

    s = schedule or {}
    targets = {k for b in branches for k in b if k != "label"}
    blocked = [k for k in sorted(targets)
               if _count(answers.get(k), k) > 0 and _unit_price(s, k, answers) is None]
    if blocked:
        out["_open"] = (
            "[CONFIRM: this package covers one of several things and the "
            "cheaper choice cannot be worked out while "
            + ", ".join(blocked) + " has no price. Set it, or the client is "
            "charged by whichever option happens to be written first.]"
        )
        return out

    def saving(branch: dict) -> float:
        return sum(
            min(_count(answers.get(k), k), n) * (_unit_price(s, k, answers) or 0)
            for k, n in branch.items() if k != "label")

    best = max(branches, key=saving)
    for key, allowed in best.items():
        if key == "label":
            continue
        out[key] = max(out.get(key, 0), allowed)
    out["_branch"] = best.get("label", "")
    return out


def derive_tier(unit: dict, answers: dict, where: str) -> tuple:
    """(key, tier) for the highest tier whose gate holds -- or (None, None).

    Read top to bottom, last match wins: the ladder is ordered cheapest first
    and "the highest package whose gate is met" is the firm's rule.
    """
    chosen = (None, None)
    for key, tier in (unit.get("tiers") or {}).items():
        gate = tier.get("gate")
        if gate is None:
            raise PricingError(
                f"{where}.{key} has no gate, so nothing can ever select it."
            )
        if is_open(gate):
            # An undecided gate never matches. It is reported by `doctor`
            # rather than guessed at, which is the whole point of [CONFIRM:].
            continue
        if _gate_holds(gate, answers, f"{where}.{key}"):
            chosen = (key, tier)
    return chosen


def _gate_sentence(key: str, tier: dict) -> str:
    """What the estimate prints under the package name.

    The point is that a wrong pick is visible on the page before the document
    reaches a client, so this says what selected the package rather than
    restating its price.
    """
    return tier.get("detail", "") or key


def _count(value, key: str) -> int:
    """An answer read as a number of things, or nothing at all.

    Absence is fine -- an unanswered count is zero, and a question the
    interview never reached because of a `showIf` is absent by design. What is
    not fine is a value that LOOKS countable and is not:

    * `True` is `int()`-able to 1, so a yes/no wired to a count question would
      bill for exactly one of whatever it counted, silently.
    * `2.7` truncated to 2. Nobody has 2.7 K-1s, so the answer is wrong rather
      than imprecise, and rounding it hides that it was ever wrong.

    Both were real behaviours of this function. Neither raised.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0
    if isinstance(value, bool):
        raise PricingError(
            f"{key} answered {value!r}, which is not a count. A yes/no cannot "
            f"say how many, and treating it as one would bill for exactly one."
        )
    if isinstance(value, float) and value != int(value):
        raise PricingError(
            f"{key} answered {value!r}, which is not a count. Rounding it "
            f"would hide that the answer was wrong rather than imprecise."
        )
    try:
        return int(value)
    except (TypeError, ValueError):
        # Free text where a number belongs is treated as absence, not as an
        # error: the interview coerces its own types, and a stray string here
        # means the count was never really asked.
        return 0


def line_items(answers: dict, schedule: dict | None = None) -> list[dict]:
    """The estimate's `LineItems`, in the order they read on the page.

    `answers` is the interview's raw answers, not a composed record: pricing is
    driven by what was counted, and the counts never become merge fields.
    """
    s = schedule if schedule is not None else load()
    code = s.get("currency", "USD")
    covers = s.get("base_covers")
    items: list[dict] = []

    form = answers.get("federal_form")
    if not form:
        # Not a soft skip. Guarding the base with `if form:` and pricing the
        # per-unit lines anyway produced an estimate for the ADD-ONS ALONE --
        # a confident total with no return in it. An unknown form already
        # refuses; a missing one is the same failure with less to go on.
        raise PricingError(
            "the record names no federal form, so there is no base fee to "
            "quote. An estimate for the add-ons alone is not an estimate."
        )
    base = (s.get("base") or {}).get(form)
    if base is None:
        raise PricingError(
            f"the fee schedule has no base fee for federal form {form!r}. "
            f"Add it rather than letting the estimate quote without one."
        )

    allowance: dict = {}
    if isinstance(base, dict) and base.get("tiers"):
        key, tier = derive_tier(base, answers, f"base.{form}")
        if tier is None:
            # Every gate was either undecided or unmet. Quoting the cheapest
            # tier here would be the single most expensive guess in the file.
            raise PricingError(
                f"no package gate matched this client, so there is no price "
                f"to quote for form {form!r}. Either a gate is wrong or this "
                f"is a client the ladder does not describe; both are worth "
                f"knowing before an estimate goes out."
            )
        for field in ("label", "amount"):
            if field not in tier:
                raise PricingError(
                    f"base.{form}.{key} is missing {field!r}, so the package "
                    f"line cannot be written."
                )
        label = tier["label"]
        detail = _gate_sentence(key, tier)
        base = tier["amount"]
        allowance = _allowance(tier, answers, s)
        if allowance.get("_open"):
            # The package price itself is knowable; which of its options the
            # client got is not. Carry the question on the line so it reaches
            # the total and the estimate refuses rather than guessing.
            base = allowance["_open"]
        elif allowance.get("_branch"):
            detail = f"{detail} — includes {allowance['_branch']}"
    else:
        label = {"1040": "Federal Form 1040", "1120S": "Federal Form 1120-S",
                 "1065": "Federal Form 1065", "1120": "Federal Form 1120"}.get(form, form)
        detail = ""
        if covers == "one_included":
            detail = "Includes the first state and locality"
        elif is_open(covers):
            # The structure itself is undecided, so the line cannot honestly
            # describe what it covers. Carry the question, not a guess.
            detail = covers
    items.append(_line(label, detail, base, code))

    # Per-unit lines. When the base includes the first state and locality, the
    # first of each is already paid for and only the rest are charged.
    for _, unit in (s.get("per_unit") or {}).items():
        count = _count(answers.get(unit["count_from"]), unit["count_from"])
        if covers == "one_included" and unit["count_from"] in (
                "count_states", "count_localities"):
            count = max(0, count - 1)
        # What the package already swallowed. Composes with the first state
        # and locality above rather than replacing it, and never goes below
        # zero -- a package covering more than the client has is not a credit.
        count = max(0, count - int(allowance.get(unit["count_from"], 0) or 0))
        if count <= 0:
            continue

        unit = _resolve_tier(unit, answers)
        amount = unit["amount"]
        total = amount if is_open(amount) else amount * count
        detail = unit.get("detail", "")
        if count > 1:
            each = amount if is_open(amount) else m.money(amount, code)
            detail = f"{detail} — {count} × {each}" if detail else f"{count} × {each}"
        items.append(_line(unit["label"], detail, total, code))

    # Nothing here for `assumed:` items. They carry no price, so they produce
    # no line: an estimate lists what is being charged for, and a line reading
    # "Records cleanup -- included" or "-- hourly" is a term of business
    # wearing a line item's clothes. Terms belong in `assumptions()` below,
    # which puts them in the estimate's own assumptions block in words.

    return items


def assumptions(answers: dict, schedule: dict | None = None) -> list[str]:
    """The sentences the estimate must carry, given what the fee assumes.

    One per `assumed:` item, always -- not only when something looks unusual.
    An assumption a client is told about only after it fails is not an
    assumption, it is a surprise, and the whole point of stating the boundary
    is that it is stated before the work rather than after.
    """
    s = pricing_schedule(schedule)
    basis = s.get("basis") or {}
    rate = basis.get("rate")
    out = []
    for _, spec in (s.get("assumed") or {}).items():
        label = spec.get("label", "").strip()
        assumes = spec.get("assumes", "").strip()
        trigger = spec.get("trigger", "").strip()
        if not (label and assumes and trigger):
            raise PricingError(
                f"the assumed item {label or '(unnamed)'} is missing its "
                f"label, assumption or trigger. Without all three there is no "
                f"honest sentence to print, and a boundary nobody stated is "
                f"not a boundary."
            )
        where = ("and includes it on that basis" if spec.get("inside_base")
                 else "and does not include work beyond it")
        if spec.get("beyond") != "hourly":
            raise PricingError(
                f"{label} says work beyond the assumption is "
                f"{spec.get('beyond')!r}. Only 'hourly' is supported; the firm "
                f"ruled out re-quoting deliberately."
            )
        rate_txt = f" at ${rate:,.0f} an hour" if isinstance(rate, (int, float)) else ""
        # The label leads rather than acting as the subject, or every sentence
        # says its own noun twice: "Brokerage activity assumes your brokerage
        # activity arrives as...".
        out.append(
            f"{label} \u2014 this estimate assumes {assumes}, {where}. "
            f"If {trigger}, the additional time is billed{rate_txt} as it is "
            f"worked, and we will tell you as soon as we see it."
        )
    return out


def pricing_schedule(schedule: dict | None) -> dict:
    return load() if schedule is None else schedule


def estimate_total(items: list[dict], schedule: dict | None = None) -> str:
    """The sum, formatted — or the reason it cannot be summed.

    Never typed, per the registry: computed from the lines. If any line is
    unpriced the total is a `[CONFIRM:` naming how many, because a total that
    silently omits an unpriced line is a quote the firm cannot stand behind.
    """
    s = schedule if schedule is not None else load()
    code = s.get("currency", "USD")

    unpriced = [i for i in items if is_open(i["_raw"])]
    if unpriced:
        names = ", ".join(i["Service"] for i in unpriced)
        return (f"[CONFIRM: {len(unpriced)} line(s) have no price in "
                f"fee-schedule.yaml — {names}]")
    return m.money(sum(i["_raw"] for i in items), code)


def price(answers: dict, schedule: dict | None = None) -> dict:
    """`LineItems`, `EstimateTotal` and `Assumptions`, ready to merge.

    Assumptions ride with the price rather than being fetched separately,
    because they are part of the price: they say what it covers and what it
    stops covering. Split them and the estimate can be built without them --
    which is exactly what happened the first time this was wired, and the
    template's [[EACH Assumptions]] block collapsed to nothing without the
    render so much as warning about it.
    """
    items = line_items(answers, schedule)
    total = estimate_total(items, schedule)
    return {
        "LineItems": [{k: v for k, v in i.items() if not k.startswith("_")}
                      for i in items],
        "EstimateTotal": total,
        "Assumptions": [{"Text": t} for t in assumptions(answers, schedule)],
    }
