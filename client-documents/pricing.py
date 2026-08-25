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
    if form:
        base = (s.get("base") or {}).get(form)
        if base is None:
            raise PricingError(
                f"the fee schedule has no base fee for federal form {form!r}. "
                f"Add it rather than letting the estimate quote without one."
            )
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
        count = answers.get(unit["count_from"]) or 0
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        if covers == "one_included" and unit["count_from"] in (
                "count_states", "count_localities"):
            count = max(0, count - 1)
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
