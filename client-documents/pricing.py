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

        amount = unit["amount"]
        total = amount if is_open(amount) else amount * count
        detail = unit.get("detail", "")
        if count > 1:
            each = amount if is_open(amount) else m.money(amount, code)
            detail = f"{detail} — {count} × {each}" if detail else f"{count} × {each}"
        items.append(_line(unit["label"], detail, total, code))

    # Banded lines. A band answered "none" is dropped rather than shown at zero:
    # the estimate lists what is being charged for, and "Brokerage activity —
    # $0.00" invites a client to wonder what they nearly paid for.
    for _, band in (s.get("bands") or {}).items():
        chosen = answers.get(band["count_from"])
        if not chosen:
            continue
        spec = (band.get("values") or {}).get(chosen)
        if spec is None:
            raise PricingError(
                f"the fee schedule has no band {chosen!r} for "
                f"{band['count_from']!r}; the interview offers it, so the "
                f"schedule must price it."
            )
        amount = spec.get("amount")
        if not is_open(amount) and not amount:
            continue
        items.append(_line(band["label"], spec.get("detail", ""), amount, code))

    return items


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
    """`LineItems` and `EstimateTotal`, ready to merge."""
    items = line_items(answers, schedule)
    total = estimate_total(items, schedule)
    return {
        "LineItems": [{k: v for k, v in i.items() if not k.startswith("_")}
                      for i in items],
        "EstimateTotal": total,
    }
